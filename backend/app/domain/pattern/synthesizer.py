"""Synthesizer for building representative precursors, stable pattern keys, and explainable evidence."""

import hashlib
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.domain.enums import DerivationType, PatternStatus
from app.domain.pattern.models import (
    PatternEvidenceSummary,
    PatternRelationshipEvidence,
    PatternSimilaritySummary,
    RecurringPrecursorPattern,
)
from app.domain.precursor.model import (
    PrecursorDimensionProvenance,
    StructuredSIFPrecursor,
)
from app.domain.safety_event import EvidenceSpan


class PatternSynthesizer:
    """Deterministically synthesizes a RecurringPrecursorPattern from a group of member reports and similarity evidence."""

    CORE_DIMENSIONS = [
        "hazard",
        "activity",
        "barrier_failure",
        "exposure",
        "potential_consequence",
        "life_saving_rule",
        "location",
    ]

    @staticmethod
    def _clean_string(text: Optional[str]) -> Optional[str]:
        """Sanitize text and reject placeholder values."""
        if text is None:
            return None
        cleaned = str(text).strip()
        if not cleaned or cleaned.upper() in ("*", "UNKNOWN", "OTHER", "N/A", "NONE", "NULL"):
            return None
        return cleaned

    @classmethod
    def _slugify(cls, text: str, max_len: int = 24) -> str:
        """Convert a string into a clean uppercase identifier token."""
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", text.strip().upper()).strip("_")
        return normalized[:max_len]

    @classmethod
    def synthesize_representative_precursor(
        cls,
        member_precursors: List[Optional[Any]],
    ) -> StructuredSIFPrecursor:
        """Derive a deterministic representative precursor and field provenance from member precursors."""
        field_provenance: Dict[str, PrecursorDimensionProvenance] = {}
        dim_values: Dict[str, Optional[str]] = {}

        total_members = max(1, len(member_precursors))

        for dim in cls.CORE_DIMENSIONS:
            extracted_vals: List[str] = []
            extracted_spans: List[EvidenceSpan] = []
            seen_spans: Set[Tuple[str, int, int]] = set()

            for prec in member_precursors:
                if prec is None:
                    continue

                val: Optional[str] = None
                spans: List[EvidenceSpan] = []

                if isinstance(prec, StructuredSIFPrecursor):
                    val = getattr(prec, dim, None)
                    if dim in prec.field_provenance:
                        spans = prec.field_provenance[dim].evidence_spans
                elif isinstance(prec, dict):
                    val = prec.get(dim)
                    prov_dict = prec.get("field_provenance", {}).get(dim, {})
                    if prov_dict and "evidence_spans" in prov_dict:
                        for s in prov_dict["evidence_spans"]:
                            if isinstance(s, dict):
                                spans.append(EvidenceSpan(**s))
                            elif isinstance(s, EvidenceSpan):
                                spans.append(s)

                cleaned_val = cls._clean_string(val)
                if cleaned_val:
                    extracted_vals.append(cleaned_val)

                for span in spans:
                    span_key = (span.text, span.start_char, span.end_char)
                    if span_key not in seen_spans:
                        seen_spans.add(span_key)
                        extracted_spans.append(span)

            if not extracted_vals:
                dim_values[dim] = None
                continue

            # Special dimension handling
            if dim == "location":
                # Location is NOT a mandatory exact match. If locations differ, representative location remains null.
                unique_locs = {v.lower(): v for v in extracted_vals}
                if len(unique_locs) == 1:
                    chosen_val = next(iter(unique_locs.values()))
                else:
                    chosen_val = None
            elif dim == "life_saving_rule":
                # LSR: require consensus or clear majority
                counts = Counter(extracted_vals)
                most_common_val, count = counts.most_common(1)[0]
                if count >= len(extracted_vals) / 2.0:
                    chosen_val = most_common_val
                else:
                    chosen_val = None
            else:
                # Text dimensions: select most common value, tie-broken deterministically
                counts = Counter(extracted_vals)
                # Sort by frequency desc, then string asc
                sorted_items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
                chosen_val = sorted_items[0][0]

            dim_values[dim] = chosen_val

            if chosen_val:
                matching_count = sum(1 for v in extracted_vals if v.lower() == chosen_val.lower())
                consensus_type = "UNANIMOUS_CONSENSUS" if matching_count == total_members else "MAJORITY_CONSENSUS"
                provenance = PrecursorDimensionProvenance(
                    dimension=dim,
                    value=chosen_val,
                    derivation_type=DerivationType.RULE_INFERENCE,
                    evidence_spans=extracted_spans,
                    provenance_rule=f"{consensus_type} ({matching_count}/{total_members} member reports)",
                )
                field_provenance[dim] = provenance

        return StructuredSIFPrecursor(
            hazard=dim_values.get("hazard"),
            activity=dim_values.get("activity"),
            barrier_failure=dim_values.get("barrier_failure"),
            exposure=dim_values.get("exposure"),
            potential_consequence=dim_values.get("potential_consequence"),
            life_saving_rule=dim_values.get("life_saving_rule"),
            location=dim_values.get("location"),
            field_provenance=field_provenance,
        )

    @classmethod
    def _normalize_dimension_value(cls, text: Optional[str]) -> str:
        """Normalize a precursor dimension string deterministically for canonical identity."""
        cleaned = cls._clean_string(text)
        if not cleaned:
            return ""
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", cleaned.strip().upper()).strip("_")
        return normalized

    @classmethod
    def generate_pattern_key(
        cls,
        rep_precursor: StructuredSIFPrecursor,
    ) -> str:
        """Construct a stable, deterministic pattern key based solely on representative precursor identity.

        Member report IDs belong in supporting_report_ids and evidence_summary, NEVER in the pattern key.
        Location is omitted so the same recurring precursor across different operational locations retains identical semantic identity.
        """
        norm_lsr = cls._normalize_dimension_value(rep_precursor.life_saving_rule)
        norm_hazard = cls._normalize_dimension_value(rep_precursor.hazard)
        norm_barrier = cls._normalize_dimension_value(rep_precursor.barrier_failure)
        norm_activity = cls._normalize_dimension_value(rep_precursor.activity)
        norm_consequence = cls._normalize_dimension_value(rep_precursor.potential_consequence)
        norm_exposure = cls._normalize_dimension_value(rep_precursor.exposure)

        canonical_identity_str = (
            f"LSR={norm_lsr}|"
            f"HAZARD={norm_hazard}|"
            f"BARRIER={norm_barrier}|"
            f"ACTIVITY={norm_activity}|"
            f"CONSEQUENCE={norm_consequence}|"
            f"EXPOSURE={norm_exposure}"
        )

        identity_digest = hashlib.sha256(canonical_identity_str.encode("utf-8")).hexdigest()[:8].upper()

        tokens: List[str] = ["PAT"]
        if norm_lsr:
            tokens.append(norm_lsr[:16])
        if norm_hazard:
            tokens.append(norm_hazard[:20])
        if norm_barrier:
            tokens.append(norm_barrier[:20])
        elif norm_activity:
            tokens.append(norm_activity[:20])

        base_slug = "_".join(tokens)
        pattern_key = f"{base_slug}_{identity_digest}"
        return pattern_key[:100]

    @classmethod
    def generate_pattern_title(
        cls,
        rep_precursor: StructuredSIFPrecursor,
    ) -> str:
        """Generate a human-readable title for the recurring precursor pattern."""
        hazard = rep_precursor.hazard or "Systemic Precursor"
        barrier = rep_precursor.barrier_failure
        activity = rep_precursor.activity
        lsr = rep_precursor.life_saving_rule

        parts = [f"Recurring {hazard}"]
        if barrier:
            parts.append(f"with {barrier}")
        elif activity:
            parts.append(f"during {activity}")

        if lsr:
            parts.append(f"[{lsr}]")

        title = " ".join(parts)
        return title[:255]

    @classmethod
    def generate_explanation(
        cls,
        member_count: int,
        rep_precursor: StructuredSIFPrecursor,
        supporting_locations: List[str],
        similarity_summary: PatternSimilaritySummary,
    ) -> str:
        """Generate a deterministic, evidence-grounded explanation of the pattern."""
        shared_elements = []
        if rep_precursor.hazard:
            shared_elements.append(f"hazard '{rep_precursor.hazard}'")
        if rep_precursor.barrier_failure:
            shared_elements.append(f"barrier failure '{rep_precursor.barrier_failure}'")
        if rep_precursor.activity:
            shared_elements.append(f"activity '{rep_precursor.activity}'")
        if rep_precursor.exposure:
            shared_elements.append(f"exposure condition '{rep_precursor.exposure}'")
        if rep_precursor.life_saving_rule:
            shared_elements.append(f"Life-Saving Rule '{rep_precursor.life_saving_rule}'")

        if shared_elements:
            shared_str = ", ".join(shared_elements)
            msg = (
                f"{member_count} reports were deterministically grouped as a recurring pattern candidate "
                f"based on shared evidence across {shared_str} "
                f"(average pairwise similarity {similarity_summary.avg_score:.2f})."
            )
        else:
            msg = (
                f"{member_count} reports were deterministically grouped as a recurring pattern candidate "
                f"based on overall hybrid similarity (average score {similarity_summary.avg_score:.2f})."
            )

        if len(supporting_locations) > 1:
            loc_sample = ", ".join(supporting_locations[:3])
            more = f" (+{len(supporting_locations)-3} more)" if len(supporting_locations) > 3 else ""
            msg += f" Observed across {len(supporting_locations)} distinct locations: {loc_sample}{more}."
        elif len(supporting_locations) == 1:
            msg += f" Observed at location: {supporting_locations[0]}."

        return msg

    @classmethod
    def synthesize_pattern(
        cls,
        member_records: List[Dict[str, Any]],
        relationships: List[PatternRelationshipEvidence],
        discovery_method: str = "HYBRID_SIMILARITY_GROUPING_V1",
        existing_id: Optional[uuid.UUID] = None,
    ) -> RecurringPrecursorPattern:
        """Synthesize a complete RecurringPrecursorPattern domain model from member records."""
        member_count = len(member_records)
        member_ids = [r["report_id"] for r in member_records]
        member_precursors = [r.get("precursor") for r in member_records]

        # 1. Representative precursor
        rep_precursor = cls.synthesize_representative_precursor(member_precursors)

        # 2. Supporting locations and LSRs
        supporting_locations: List[str] = sorted(list({
            cls._clean_string(r.get("location"))
            for r in member_records
            if cls._clean_string(r.get("location")) is not None
        }))

        all_lsrs: Set[str] = set()
        for prec in member_precursors:
            if isinstance(prec, StructuredSIFPrecursor) and prec.life_saving_rule:
                cleaned = cls._clean_string(prec.life_saving_rule)
                if cleaned:
                    all_lsrs.add(cleaned)
            elif isinstance(prec, dict) and prec.get("life_saving_rule"):
                cleaned = cls._clean_string(prec.get("life_saving_rule"))
                if cleaned:
                    all_lsrs.add(cleaned)
        supporting_lsrs: List[str] = sorted(list(all_lsrs))

        # 3. Temporal bounds
        timestamps: List[datetime] = []
        for r in member_records:
            ts = r.get("event_timestamp") or r.get("created_at") or r.get("assessed_at")
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                else:
                    ts = ts.astimezone(timezone.utc)
                timestamps.append(ts)

        now = datetime.now(timezone.utc)
        first_observed = min(timestamps) if timestamps else now
        last_observed = max(timestamps) if timestamps else now

        # 4. Similarity summary
        scores = [rel.score for rel in relationships] if relationships else [1.0]
        mode_counts: Dict[str, int] = {}
        for rel in relationships:
            mode_counts[rel.mode] = mode_counts.get(rel.mode, 0) + 1

        sim_summary = PatternSimilaritySummary(
            min_score=min(scores) if scores else 1.0,
            max_score=max(scores) if scores else 1.0,
            avg_score=round(sum(scores) / len(scores), 4) if scores else 1.0,
            mode_counts=mode_counts,
            total_relationships=len(relationships),
        )

        # 5. Shared dimensions
        shared_dimensions: Dict[str, List[str]] = {}
        if rep_precursor.hazard:
            shared_dimensions["hazard"] = [rep_precursor.hazard]
        if rep_precursor.activity:
            shared_dimensions["activity"] = [rep_precursor.activity]
        if rep_precursor.barrier_failure:
            shared_dimensions["barrier_failure"] = [rep_precursor.barrier_failure]
        if rep_precursor.exposure:
            shared_dimensions["exposure"] = [rep_precursor.exposure]
        if rep_precursor.potential_consequence:
            shared_dimensions["potential_consequence"] = [rep_precursor.potential_consequence]
        if rep_precursor.life_saving_rule:
            shared_dimensions["life_saving_rule"] = [rep_precursor.life_saving_rule]

        # 6. Explanation
        explanation = cls.generate_explanation(
            member_count=member_count,
            rep_precursor=rep_precursor,
            supporting_locations=supporting_locations,
            similarity_summary=sim_summary,
        )

        # 7. Pattern key and title
        pattern_key = cls.generate_pattern_key(rep_precursor)
        title = cls.generate_pattern_title(rep_precursor)

        # 8. Evidence summary
        evidence_summary = PatternEvidenceSummary(
            member_count=member_count,
            member_report_ids=member_ids,
            relationships=relationships,
            shared_dimensions=shared_dimensions,
            supporting_locations=supporting_locations,
            supporting_lsr_codes=supporting_lsrs,
            first_observed_at=first_observed,
            last_observed_at=last_observed,
            similarity_summary=sim_summary,
            explanation=explanation,
        )

        return RecurringPrecursorPattern(
            id=existing_id or uuid.uuid4(),
            pattern_key=pattern_key,
            title=title,
            description=explanation,
            hazard_category=rep_precursor.hazard,
            activity_type=rep_precursor.activity,
            failed_barrier_type=rep_precursor.barrier_failure,
            lsr_code=rep_precursor.life_saving_rule,
            representative_precursor=rep_precursor,
            supporting_report_count=member_count,
            supporting_report_ids=member_ids,
            supporting_lsr_codes=supporting_lsrs,
            supporting_locations=supporting_locations,
            first_observed_at=first_observed,
            last_observed_at=last_observed,
            similarity_summary=sim_summary.model_dump(mode="json"),
            evidence_summary=evidence_summary.model_dump(mode="json"),
            discovery_method=discovery_method,
            status=PatternStatus.CANDIDATE,
        )
