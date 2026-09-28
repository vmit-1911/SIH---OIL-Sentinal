"""Deterministic Structured SIF Precursor Synthesizer."""

from typing import Optional, Tuple
from app.domain.enums import DerivationType, EvidenceStrength, PotentialOutcome
from app.domain.lsr.evidence import LSRMappingResult
from app.domain.precursor.model import (
    PrecursorDimensionProvenance,
    StructuredSIFPrecursor,
)
from app.domain.safety_event import ExtractedItem, SafetyEventContext
from app.domain.sif.evidence import SIFScreeningResult


class StructuredPrecursorSynthesizer:
    """Synthesizes canonical 7D Structured SIF Precursors from extraction and screening engines.
    
    Consumes:
    1. SafetyEventContext (Phase 1A NLP extraction)
    2. SIFScreeningResult (Phase 1B SIF evidence evaluation)
    3. LSRMappingResult (Phase 1B IOGP Life-Saving Rules mapping)
    
    Produces:
    - Canonical StructuredSIFPrecursor with auditable field-level provenance.
    """

    def synthesize(
        self,
        context: SafetyEventContext,
        screening_result: SIFScreeningResult,
        lsr_result: LSRMappingResult,
        reported_location: Optional[str] = None,
    ) -> StructuredSIFPrecursor:
        """Synthesize a canonical precursor object deterministically."""
        provenance_map = {}

        # 1. Hazard
        hazard_val, hazard_prov = self._select_hazard(context, screening_result)
        if hazard_prov:
            provenance_map["hazard"] = hazard_prov

        # 2. Activity
        activity_val, activity_prov = self._select_activity(context)
        if activity_prov:
            provenance_map["activity"] = activity_prov

        # 3. Barrier Failure
        barrier_val, barrier_prov = self._select_barrier_failure(context, screening_result)
        if barrier_prov:
            provenance_map["barrier_failure"] = barrier_prov

        # 4. Exposure
        exposure_val, exposure_prov = self._select_exposure(context, screening_result)
        if exposure_prov:
            provenance_map["exposure"] = exposure_prov

        # 5. Potential Consequence
        consequence_val, consequence_prov = self._select_potential_consequence(context, screening_result)
        if consequence_prov:
            provenance_map["potential_consequence"] = consequence_prov

        # 6. Life-Saving Rule
        lsr_val, lsr_prov = self._select_life_saving_rule(lsr_result)
        if lsr_prov:
            provenance_map["life_saving_rule"] = lsr_prov

        # 7. Location
        location_val, location_prov = self._select_location(context, reported_location)
        if location_prov:
            provenance_map["location"] = location_prov

        return StructuredSIFPrecursor(
            hazard=hazard_val,
            activity=activity_val,
            barrier_failure=barrier_val,
            exposure=exposure_val,
            potential_consequence=consequence_val,
            life_saving_rule=lsr_val,
            location=location_val,
            field_provenance=provenance_map,
        )

    def _select_hazard(
        self,
        context: SafetyEventContext,
        screening_result: SIFScreeningResult,
    ) -> Tuple[Optional[str], Optional[PrecursorDimensionProvenance]]:
        """Select the most defensible hazard contributing to SIF screening."""
        candidates = [h for h in context.hazards if not h.is_negated]
        if not candidates:
            return None, None

        sif_items = screening_result.evidence_breakdown.energy_hazard.evidence_items

        def rank_hazard(h: ExtractedItem) -> Tuple[int, int, int, str]:
            # Priority 1: Contributes to SIF energy hazard
            is_sif_contributor = 1 if (h.canonical_name in sif_items or h.raw_match in sif_items) else 0
            # Priority 2: Evidence strength
            strength_val = 3 if h.evidence_strength == EvidenceStrength.HIGH else (2 if h.evidence_strength == EvidenceStrength.MEDIUM else 1)
            # Priority 3: Earliest text span (lower start_char is earlier)
            earliest_char = min((s.start_char for s in h.evidence_spans), default=999999)
            # Priority 4: Alphabetical tie-breaker
            return (-is_sif_contributor, -strength_val, earliest_char, h.canonical_name)

        selected = min(candidates, key=rank_hazard)
        provenance = PrecursorDimensionProvenance(
            dimension="hazard",
            value=selected.canonical_name,
            derivation_type=selected.derivation_type,
            evidence_spans=selected.evidence_spans,
            provenance_rule=selected.provenance_rule or "LEXICON_HAZARD",
        )
        return selected.canonical_name, provenance

    def _select_activity(
        self,
        context: SafetyEventContext,
    ) -> Tuple[Optional[str], Optional[PrecursorDimensionProvenance]]:
        """Select operational task from context extraction."""
        if context.activity and not context.activity.is_negated:
            act = context.activity
            provenance = PrecursorDimensionProvenance(
                dimension="activity",
                value=act.canonical_name,
                derivation_type=act.derivation_type,
                evidence_spans=act.evidence_spans,
                provenance_rule=act.provenance_rule or "LEXICON_ACTIVITY",
            )
            return act.canonical_name, provenance
        return None, None

    def _select_barrier_failure(
        self,
        context: SafetyEventContext,
        screening_result: SIFScreeningResult,
    ) -> Tuple[Optional[str], Optional[PrecursorDimensionProvenance]]:
        """Select the barrier failure most directly associated with SIF screening."""
        candidates = [b for b in context.barrier_failures if not b.is_negated]
        if not candidates:
            return None, None

        sif_items = screening_result.evidence_breakdown.barrier_degradation.evidence_items

        def rank_barrier(b: ExtractedItem) -> Tuple[int, int, int, str]:
            is_sif_contributor = 1 if (b.canonical_name in sif_items or b.raw_match in sif_items) else 0
            strength_val = 3 if b.evidence_strength == EvidenceStrength.HIGH else (2 if b.evidence_strength == EvidenceStrength.MEDIUM else 1)
            earliest_char = min((s.start_char for s in b.evidence_spans), default=999999)
            return (-is_sif_contributor, -strength_val, earliest_char, b.canonical_name)

        selected = min(candidates, key=rank_barrier)
        provenance = PrecursorDimensionProvenance(
            dimension="barrier_failure",
            value=selected.canonical_name,
            derivation_type=selected.derivation_type,
            evidence_spans=selected.evidence_spans,
            provenance_rule=selected.provenance_rule or "LEXICON_BARRIER_FAILURE",
        )
        return selected.canonical_name, provenance

    def _select_exposure(
        self,
        context: SafetyEventContext,
        screening_result: SIFScreeningResult,
    ) -> Tuple[Optional[str], Optional[PrecursorDimensionProvenance]]:
        """Select worker exposure / proximity to hazard."""
        candidates = [e for e in context.exposure if not e.is_negated]
        if not candidates:
            return None, None

        sif_items = screening_result.evidence_breakdown.exposure.evidence_items

        def rank_exposure(e: ExtractedItem) -> Tuple[int, int, int, str]:
            is_sif_contributor = 1 if (e.canonical_name in sif_items or e.raw_match in sif_items) else 0
            strength_val = 3 if e.evidence_strength == EvidenceStrength.HIGH else (2 if e.evidence_strength == EvidenceStrength.MEDIUM else 1)
            earliest_char = min((s.start_char for s in e.evidence_spans), default=999999)
            return (-is_sif_contributor, -strength_val, earliest_char, e.canonical_name)

        selected = min(candidates, key=rank_exposure)
        provenance = PrecursorDimensionProvenance(
            dimension="exposure",
            value=selected.canonical_name,
            derivation_type=selected.derivation_type,
            evidence_spans=selected.evidence_spans,
            provenance_rule=selected.provenance_rule or "LEXICON_EXPOSURE",
        )
        return selected.canonical_name, provenance

    def _select_potential_consequence(
        self,
        context: SafetyEventContext,
        screening_result: SIFScreeningResult,
    ) -> Tuple[Optional[str], Optional[PrecursorDimensionProvenance]]:
        """Derive potential consequence strictly from Phase 1B screening result."""
        if screening_result.potential_severity and screening_result.potential_severity != PotentialOutcome.LOW_IMPACT:
            val = screening_result.potential_severity.value
            spans = screening_result.evidence_breakdown.potential_consequence.evidence_spans
            if not spans and context.potential_consequences:
                spans = [s for c in context.potential_consequences for s in c.evidence_spans]
            
            rule_id = screening_result.rule_provenance[0].rule_id if screening_result.rule_provenance else "SIF_SCREENING_POTENTIAL_CONSEQUENCE"
            provenance = PrecursorDimensionProvenance(
                dimension="potential_consequence",
                value=val,
                derivation_type=DerivationType.RULE_INFERENCE,
                evidence_spans=spans,
                provenance_rule=rule_id,
            )
            return val, provenance

        if context.potential_consequences:
            cand = context.potential_consequences[0]
            provenance = PrecursorDimensionProvenance(
                dimension="potential_consequence",
                value=cand.canonical_name,
                derivation_type=cand.derivation_type,
                evidence_spans=cand.evidence_spans,
                provenance_rule=cand.provenance_rule or "LEXICON_POTENTIAL_CONSEQUENCE",
            )
            return cand.canonical_name, provenance

        return None, None

    def _select_life_saving_rule(
        self,
        lsr_result: LSRMappingResult,
    ) -> Tuple[Optional[str], Optional[PrecursorDimensionProvenance]]:
        """Select primary Life-Saving Rule code from LSR mapper result."""
        target_rule = lsr_result.primary_rule
        if not target_rule and lsr_result.mapped_rules:
            target_rule = lsr_result.mapped_rules[0]

        if target_rule:
            provenance = PrecursorDimensionProvenance(
                dimension="life_saving_rule",
                value=target_rule.rule_code,
                derivation_type=DerivationType.RULE_INFERENCE,
                evidence_spans=target_rule.evidence_spans,
                provenance_rule=target_rule.provenance_rule,
            )
            return target_rule.rule_code, provenance

        return None, None

    def _select_location(
        self,
        context: SafetyEventContext,
        reported_location: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[PrecursorDimensionProvenance]]:
        """Select operating location from narrative extraction or report metadata."""
        if context.location and not context.location.is_negated:
            loc = context.location
            provenance = PrecursorDimensionProvenance(
                dimension="location",
                value=loc.canonical_name,
                derivation_type=loc.derivation_type,
                evidence_spans=loc.evidence_spans,
                provenance_rule=loc.provenance_rule or "LEXICON_LOCATION",
            )
            return loc.canonical_name, provenance

        if reported_location and reported_location.strip():
            loc_str = reported_location.strip()
            provenance = PrecursorDimensionProvenance(
                dimension="location",
                value=loc_str,
                derivation_type=DerivationType.METADATA,
                evidence_spans=[],
                provenance_rule="REPORT_METADATA_LOCATION",
            )
            return loc_str, provenance

        return None, None

