"""Deterministic, domain-aware SIF Evidence Screening Engine."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.domain.enums import (
    ActualOutcome,
    DerivationType,
    EvidenceStrength,
    PotentialOutcome,
    SIFClassification,
)
from app.domain.interfaces.classifier import SIFClassifierInterface
from app.domain.safety_event import EvidenceSpan, SafetyEventContext
from app.domain.sif.evidence import (
    SIFEvidenceBreakdown,
    SIFFactorEvidence,
    SIFRuleProvenance,
    SIFScreeningResult,
)


class SIFScreeningRule(BaseModel):
    """Domain screening rule schema from configuration profile."""
    rule_id: str
    name: str
    description: str
    required_factors: List[str] = Field(default_factory=list)
    energy_types: List[str] = Field(default_factory=list)
    default_potential_severity: PotentialOutcome
    severity_details: str


class SIFScreeningProfile(BaseModel):
    """Complete SIF screening configuration profile."""
    profile_id: str
    version: str
    name: str
    description: str
    active: bool = True
    threshold_semantics: Optional[str] = None
    factor_weights: Dict[str, float]
    factor_descriptions: Dict[str, str] = Field(default_factory=dict)
    strength_thresholds: Dict[str, float]
    classification_thresholds: Dict[str, float]
    screening_rules: List[SIFScreeningRule] = Field(default_factory=list)


@lru_cache()
def load_default_sif_profile() -> SIFScreeningProfile:
    """Load and cache default SIF screening profile from JSON."""
    profile_path = Path(__file__).resolve().parent / "screening_profile.json"
    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return SIFScreeningProfile.model_validate(data)


class SIFScreeningEngine(SIFClassifierInterface):
    """Evaluates multi-factor safety event evidence to screen for SIF potential."""

    def __init__(self, profile: Optional[SIFScreeningProfile] = None):
        self.profile = profile or load_default_sif_profile()

    def evaluate_context(
        self,
        context: SafetyEventContext,
        actual_severity: ActualOutcome = ActualOutcome.NO_INJURY,
    ) -> SIFScreeningResult:
        """Evaluate a SafetyEventContext and return a structured SIFScreeningResult.
        
        Evaluates 4 primary weighted scoring factors (energy_hazard, exposure_proximity,
        barrier_degradation, potential_consequence) and 1 qualitative context factor.
        
        Automated screening outputs are strictly:
        - POTENTIAL_SIF
        - NON_SIF
        - UNDETERMINED
        
        ACTUAL_SIF is NOT automatically inferred from injury severity.
        """
        weights = self.profile.factor_weights
        all_spans: List[EvidenceSpan] = list(context.all_evidence_spans)

        # 1. Evaluate Energy / Hazard Factor
        active_hazards = [h for h in context.hazards if not h.is_negated]
        has_high_energy = len(context.energy_sources) > 0
        energy_present = len(active_hazards) > 0

        energy_spans: List[EvidenceSpan] = []
        for h in active_hazards:
            energy_spans.extend(h.evidence_spans)

        if has_high_energy:
            energy_strength = EvidenceStrength.HIGH
            energy_contrib = weights.get("energy_hazard", 0.35)
        elif energy_present:
            energy_strength = EvidenceStrength.LOW
            energy_contrib = weights.get("energy_hazard", 0.35) * 0.3
        else:
            energy_strength = EvidenceStrength.LOW
            energy_contrib = 0.0

        factor_energy = SIFFactorEvidence(
            factor_name="ENERGY_HAZARD",
            present=energy_present,
            evidence_strength=energy_strength,
            evidence_items=[h.canonical_name for h in active_hazards],
            evidence_spans=energy_spans,
            contribution_score=round(energy_contrib, 3),
        )

        # 2. Evaluate Exposure / Proximity Factor
        exposure_present = len(context.exposure) > 0
        exposure_spans: List[EvidenceSpan] = []
        for ex in context.exposure:
            exposure_spans.extend(ex.evidence_spans)

        if exposure_present:
            exposure_strength = EvidenceStrength.HIGH
            exposure_contrib = weights.get("exposure_proximity", 0.30)
        else:
            exposure_strength = EvidenceStrength.LOW
            exposure_contrib = 0.0

        factor_exposure = SIFFactorEvidence(
            factor_name="EXPOSURE",
            present=exposure_present,
            evidence_strength=exposure_strength,
            evidence_items=[ex.canonical_name for ex in context.exposure],
            evidence_spans=exposure_spans,
            contribution_score=round(exposure_contrib, 3),
        )

        # 3. Evaluate Barrier Degradation Factor
        barrier_present = len(context.barrier_failures) > 0
        barrier_spans: List[EvidenceSpan] = []
        for b in context.barrier_failures:
            barrier_spans.extend(b.evidence_spans)

        if barrier_present:
            barrier_strength = EvidenceStrength.HIGH
            barrier_contrib = weights.get("barrier_degradation", 0.25)
        else:
            barrier_strength = EvidenceStrength.LOW
            barrier_contrib = 0.0

        factor_barrier = SIFFactorEvidence(
            factor_name="BARRIER_DEGRADATION",
            present=barrier_present,
            evidence_strength=barrier_strength,
            evidence_items=[b.canonical_name for b in context.barrier_failures],
            evidence_spans=barrier_spans,
            contribution_score=round(barrier_contrib, 3),
        )

        # 4. Evaluate Potential Consequence Factor
        consequence_present = len(context.potential_consequences) > 0
        consequence_spans: List[EvidenceSpan] = []
        for c in context.potential_consequences:
            consequence_spans.extend(c.evidence_spans)

        if consequence_present:
            consequence_strength = EvidenceStrength.HIGH
            consequence_contrib = weights.get("potential_consequence", 0.10)
        else:
            consequence_strength = EvidenceStrength.LOW
            consequence_contrib = 0.0

        factor_consequence = SIFFactorEvidence(
            factor_name="POTENTIAL_CONSEQUENCE",
            present=consequence_present,
            evidence_strength=consequence_strength,
            evidence_items=[c.canonical_name for c in context.potential_consequences],
            evidence_spans=consequence_spans,
            contribution_score=round(consequence_contrib, 3),
        )

        # 5. Evaluate Operational Context Factor (Qualitative Dimension)
        # Context provides qualitative/operational evidence (activity, equipment) for review and provenance,
        # but does NOT directly contribute to the numeric evidence score in SIF_SCREENING_PROFILE_V1 (contribution_score = 0.0).
        context_present = context.activity is not None or len(context.equipment) > 0
        context_items = []
        context_spans: List[EvidenceSpan] = []
        if context.activity:
            context_items.append(context.activity.canonical_name)
            context_spans.extend(context.activity.evidence_spans)
        for eq in context.equipment:
            context_items.append(eq.canonical_name)
            context_spans.extend(eq.evidence_spans)

        factor_context = SIFFactorEvidence(
            factor_name="OPERATIONAL_CONTEXT",
            present=context_present,
            evidence_strength=EvidenceStrength.MEDIUM if context_present else EvidenceStrength.LOW,
            evidence_items=context_items,
            evidence_spans=context_spans,
            contribution_score=0.0,
        )

        # Assemble Evidence Breakdown
        breakdown = SIFEvidenceBreakdown(
            energy_hazard=factor_energy,
            exposure=factor_exposure,
            barrier_degradation=factor_barrier,
            potential_consequence=factor_consequence,
            context=factor_context,
        )

        # Multi-Factor Evidence Score Calculation (4 primary weighted scoring factors)
        evidence_score = round(
            energy_contrib + exposure_contrib + barrier_contrib + consequence_contrib,
            3,
        )
        evidence_score = min(1.0, max(0.0, evidence_score))

        # Determine Categorical Evidence Strength
        if evidence_score >= self.profile.strength_thresholds.get("high", 0.70):
            strength = EvidenceStrength.HIGH
        elif evidence_score >= self.profile.strength_thresholds.get("medium", 0.40):
            strength = EvidenceStrength.MEDIUM
        else:
            strength = EvidenceStrength.LOW

        # 6. Rule Matching & Potential Consequence Derivation
        fired_rules: List[SIFRuleProvenance] = []
        derived_potential_severity: Optional[PotentialOutcome] = None
        severity_details: Optional[str] = None

        extracted_energy_types = {
            h.attributes.get("energy_type") for h in active_hazards if h.attributes.get("energy_type")
        }

        for rule in self.profile.screening_rules:
            # Check energy types match
            matches_energy = bool(set(rule.energy_types).intersection(extracted_energy_types))
            if not matches_energy and rule.energy_types:
                continue

            # Check factor requirements
            req_satisfied = True
            if "energy_hazard" in rule.required_factors and not factor_energy.present:
                req_satisfied = False
            if "exposure_proximity" in rule.required_factors and not factor_exposure.present:
                req_satisfied = False
            if "barrier_degradation" in rule.required_factors and not factor_barrier.present:
                req_satisfied = False

            if req_satisfied:
                rule_spans = []
                if factor_energy.present:
                    rule_spans.extend(factor_energy.evidence_spans)
                if factor_exposure.present:
                    rule_spans.extend(factor_exposure.evidence_spans)
                if factor_barrier.present:
                    rule_spans.extend(factor_barrier.evidence_spans)

                fired_rules.append(
                    SIFRuleProvenance(
                        rule_id=rule.rule_id,
                        description=rule.description,
                        evidence_spans=rule_spans,
                        derivation_type=DerivationType.RULE_INFERENCE,
                    )
                )

                if derived_potential_severity is None:
                    derived_potential_severity = rule.default_potential_severity
                    severity_details = rule.severity_details

        # Fallback consequence derivation
        if derived_potential_severity is None:
            if factor_energy.present and factor_barrier.present:
                derived_potential_severity = PotentialOutcome.FATALITY
                severity_details = "Plausible serious injury or fatality exposure derived from high energy release and barrier failure."
            elif factor_energy.present and not has_high_energy:
                derived_potential_severity = PotentialOutcome.LOW_IMPACT
                severity_details = "Low energy hazard with low consequence potential."
            else:
                derived_potential_severity = None
                severity_details = None

        # 7. SIF Classification Decision (Heuristic Screening)
        # Automated classifications are strictly POTENTIAL_SIF, NON_SIF, or UNDETERMINED.
        # ACTUAL_SIF is NOT automatically inferred from injury severity; it is reserved for
        # authoritative source data or human HSE validation (TriageReview).
        min_potential_score = self.profile.classification_thresholds.get("potential_sif_min_score", 0.45)
        max_non_sif_score = self.profile.classification_thresholds.get("non_sif_max_score", 0.20)

        if evidence_score >= min_potential_score or (has_high_energy and barrier_present):
            classification = SIFClassification.POTENTIAL_SIF
            reasoning = (
                f"Classified as POTENTIAL_SIF (Evidence Score: {evidence_score:.2f}, Strength: {strength.value}): "
                f"Identified high-energy hazard exposure ({', '.join(factor_energy.evidence_items)}) combined with "
                f"barrier degradation ({', '.join(factor_barrier.evidence_items)}) and personnel proximity."
            )
        elif not energy_present and not exposure_present and not barrier_present:
            classification = SIFClassification.UNDETERMINED
            reasoning = (
                "Classified as UNDETERMINED: The report narrative lacks sufficient concrete evidence of hazards, "
                "worker exposure, or barrier integrity to perform a conclusive SIF determination."
            )
        elif evidence_score <= max_non_sif_score and not has_high_energy:
            classification = SIFClassification.NON_SIF
            reasoning = (
                f"Classified as NON_SIF (Evidence Score: {evidence_score:.2f}): Narrative describes routine low-energy "
                f"hazards or conditions without critical barrier degradation."
            )
        else:
            classification = SIFClassification.UNDETERMINED
            reasoning = (
                f"Classified as UNDETERMINED (Evidence Score: {evidence_score:.2f}): Inconclusive evidence balance. "
                "Hazard presence without verified worker exposure or clear barrier failure status."
            )

        return SIFScreeningResult(
            sif_classification=classification,
            evidence_score=evidence_score,
            evidence_strength=strength,
            rule_based_screening_score=evidence_score,
            actual_severity=actual_severity,
            potential_severity=derived_potential_severity,
            potential_outcome_details=severity_details,
            evidence_breakdown=breakdown,
            primary_reasoning=reasoning,
            rule_provenance=fired_rules,
            all_evidence_spans=all_spans,
        )

    # --- SIFClassifierInterface Implementation ---

    async def classify(
        self,
        raw_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Adapter implementing SIFClassifierInterface."""
        from app.domain.extraction.rule_based_extractor import RuleBasedSafetyExtractor

        extractor = RuleBasedSafetyExtractor()
        context = extractor.extract_safety_event_context(raw_text)

        actual_severity = ActualOutcome.NO_INJURY
        if metadata and "actual_severity" in metadata:
            actual_severity = ActualOutcome(metadata["actual_severity"])

        result = self.evaluate_context(context, actual_severity=actual_severity)
        return result.model_dump()
