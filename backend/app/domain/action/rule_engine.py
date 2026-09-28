"""Deterministic rule engine for generating explainable HSE Action Recommendations."""

import uuid
from typing import Any, Dict, List, Optional

from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ConcentrationDimension,
    ObservedTrend,
    PotentialOutcome,
    ReviewDecision,
    SIFClassification,
)


class ActionRuleEngine:
    """Deterministic, auditable rule engine translating SIF intelligence into targeted HSE recommendations."""

    VERSION = "1.0.0"

    # --------------------------------------------------------------------------
    # 1. Assessment Evaluation
    # --------------------------------------------------------------------------
    def evaluate_assessment(
        self,
        assessment_id: uuid.UUID,
        report_id: uuid.UUID,
        report_ref: str,
        raw_text: str,
        sif_classification: SIFClassification,
        evidence_score: float,
        potential_severity: Optional[PotentialOutcome],
        structured_precursor: Optional[Dict[str, Any]],
        primary_lsr_code: Optional[str],
        primary_lsr_name: Optional[str],
        review_decision: Optional[ReviewDecision] = None,
        final_classification: Optional[SIFClassification] = None,
        final_structured_precursor: Optional[Dict[str, Any]] = None,
        final_lsr_code: Optional[str] = None,
        evidence_spans: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluate deterministic action rules for a single SIF assessment or human review."""
        actions: List[Dict[str, Any]] = []

        # Human review gating
        if review_decision == ReviewDecision.REJECT_AI:
            # Explicitly rejected by HSE expert -> do not generate SIF-driven actions
            return []

        if review_decision == ReviewDecision.MARK_UNDETERMINED:
            # Ambiguous/undetermined -> no definitive SIF actions
            return []

        # Resolve authoritative classification, precursor, and LSR
        active_classification = final_classification if (review_decision == ReviewDecision.CORRECT and final_classification) else sif_classification
        active_precursor = final_structured_precursor if (review_decision == ReviewDecision.CORRECT and final_structured_precursor) else (structured_precursor or {})
        active_lsr = final_lsr_code if (review_decision == ReviewDecision.CORRECT and final_lsr_code) else primary_lsr_code

        # Only SIF-relevant reports generate SIF action recommendations
        is_sif = active_classification in (SIFClassification.POTENTIAL_SIF, SIFClassification.ACTUAL_SIF)
        if not is_sif:
            return []

        is_actual = active_classification == SIFClassification.ACTUAL_SIF
        is_high_consequence = potential_severity in (
            PotentialOutcome.FATALITY,
            PotentialOutcome.PERMANENT_DISABLING_INJURY,
            PotentialOutcome.MAJOR_PROCESS_SAFETY_EVENT,
        )

        prec_hazard = self._normalize_dim_val(active_precursor.get("hazard"))
        prec_barrier = self._normalize_dim_val(active_precursor.get("barrier_failure"))
        prec_exposure = self._normalize_dim_val(active_precursor.get("exposure"))
        prec_activity = self._normalize_dim_val(active_precursor.get("activity"))
        prec_location = self._normalize_dim_val(active_precursor.get("location"))
        prec_consequence = self._normalize_dim_val(active_precursor.get("potential_consequence"))

        base_evidence = [
            {"report_id": str(report_id), "report_ref": report_ref, "assessment_id": str(assessment_id)}
        ]
        if evidence_spans:
            base_evidence.extend(evidence_spans[:5])

        source_dims = {
            "hazard": prec_hazard,
            "activity": prec_activity,
            "barrier_failure": prec_barrier,
            "exposure": prec_exposure,
            "potential_consequence": prec_consequence,
            "life_saving_rule": active_lsr,
            "location": prec_location,
        }

        # ----------------------------------------------------------------------
        # ACT-R01-BARRIER: Barrier Verification
        # ----------------------------------------------------------------------
        if prec_barrier:
            rule_id = "ACT-R01-BARRIER"
            action_key = f"ACTION|ASSESSMENT|{assessment_id}|BARRIER_VERIFICATION|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.ASSESSMENT,
                "source_id": str(assessment_id),
                "action_category": ActionCategory.BARRIER_VERIFICATION,
                "action_title": "Review Barrier Controls and Integrity",
                "action_description": f"Review safety barrier controls associated with identified barrier degradation ('{prec_barrier}') at {prec_location or 'operational site'}.",
                "priority": ActionPriority.HIGH,
                "rationale": f"Generated under rule {rule_id}: Assessment identifies barrier failure ('{prec_barrier}').",
                "evidence_refs": base_evidence,
                "source_dimensions": source_dims,
                "lsr_code": active_lsr,
                "precursor_signature": f"{prec_hazard or 'HAZARD'} | {prec_barrier}",
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        # ----------------------------------------------------------------------
        # ACT-R02-ENERGY-ISOLATION: Energy Isolation Verification
        # ----------------------------------------------------------------------
        is_energy_lsr = active_lsr and "ENERGY_ISOLATION" in active_lsr.upper()
        hazard_text = str(prec_hazard or "").upper()
        barrier_text = str(prec_barrier or "").upper()
        has_energy_indicators = any(term in hazard_text or term in barrier_text for term in ["PRESSURE", "PRESSURIZED", "GAS LEAK", "LOTO", "ISOLATION", "ELECTRICAL", "HIGH PRESSURE", "VALVE"])

        if is_energy_lsr or has_energy_indicators:
            rule_id = "ACT-R02-ENERGY-ISOLATION"
            action_key = f"ACTION|ASSESSMENT|{assessment_id}|ENERGY_ISOLATION_VERIFICATION|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.ASSESSMENT,
                "source_id": str(assessment_id),
                "action_category": ActionCategory.ENERGY_ISOLATION_VERIFICATION,
                "action_title": "Review Energy Isolation Controls",
                "action_description": "Review energy isolation controls associated with the identified barrier failure or hazardous energy condition.",
                "priority": ActionPriority.HIGH,
                "rationale": f"Generated under rule {rule_id}: Energy isolation failure or pressurized hazardous energy identified in safety observation.",
                "evidence_refs": base_evidence,
                "source_dimensions": source_dims,
                "lsr_code": active_lsr or "LSR_04_ENERGY_ISOLATION",
                "precursor_signature": f"{prec_hazard or 'PRESSURIZED_ENERGY'} | {prec_barrier or 'ISOLATION_DEGRADATION'}",
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        # ----------------------------------------------------------------------
        # ACT-R03-HEIGHT-FALL: Fall Protection Verification
        # ----------------------------------------------------------------------
        is_height_lsr = active_lsr and "HEIGHT" in active_lsr.upper()
        has_height_indicators = any(term in hazard_text or term in barrier_text or term in str(prec_activity or "").upper() for term in ["HEIGHT", "SCAFFOLD", "LADDER", "MONKEY BOARD", "ELEVATION", "FALL PROTECTION", "HARNESS", "TIE-OFF", "LANYARD"])

        if is_height_lsr or has_height_indicators:
            rule_id = "ACT-R03-HEIGHT-FALL"
            action_key = f"ACTION|ASSESSMENT|{assessment_id}|FALL_PROTECTION_VERIFICATION|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.ASSESSMENT,
                "source_id": str(assessment_id),
                "action_category": ActionCategory.FALL_PROTECTION_VERIFICATION,
                "action_title": "Review Fall Protection Controls",
                "action_description": "Review fall-protection controls associated with the identified working at height exposure.",
                "priority": ActionPriority.HIGH,
                "rationale": f"Generated under rule {rule_id}: Working at height hazard or fall protection barrier deficiency identified.",
                "evidence_refs": base_evidence,
                "source_dimensions": source_dims,
                "lsr_code": active_lsr or "LSR_03_WORKING_AT_HEIGHT",
                "precursor_signature": f"{prec_hazard or 'WORKING_AT_HEIGHT'} | {prec_barrier or 'FALL_PROTECTION_DEGRADATION'}",
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        # ----------------------------------------------------------------------
        # ACT-R04-LIFTING: Lifting Control Verification
        # ----------------------------------------------------------------------
        is_lifting_lsr = active_lsr and ("LIFTING" in active_lsr.upper() or "MECHANICAL_LIFTING" in active_lsr.upper())
        has_lifting_indicators = any(term in hazard_text or term in barrier_text or term in str(prec_activity or "").upper() for term in ["CRANE", "WINCH", "HOIST", "RIGGING", "SLING", "SUSPENDED LOAD", "WIRE ROPE", "ELEVATOR"])

        if is_lifting_lsr or has_lifting_indicators:
            rule_id = "ACT-R04-LIFTING"
            action_key = f"ACTION|ASSESSMENT|{assessment_id}|LIFTING_CONTROL_VERIFICATION|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.ASSESSMENT,
                "source_id": str(assessment_id),
                "action_category": ActionCategory.LIFTING_CONTROL_VERIFICATION,
                "action_title": "Review Lifting Controls",
                "action_description": "Review lifting controls associated with the identified precursor.",
                "priority": ActionPriority.HIGH,
                "rationale": f"Generated under rule {rule_id}: Mechanical lifting equipment hazard, crane operation, or rigging failure identified.",
                "evidence_refs": base_evidence,
                "source_dimensions": source_dims,
                "lsr_code": active_lsr or "LSR_07_SAFE_MECHANICAL_LIFTING",
                "precursor_signature": f"{prec_hazard or 'SUSPENDED_LOAD'} | {prec_barrier or 'RIGGING_FAILURE'}",
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        # ----------------------------------------------------------------------
        # ACT-R05-LINE-OF-FIRE: Line of Fire Control Review
        # ----------------------------------------------------------------------
        is_lof_lsr = active_lsr and "LINE_OF_FIRE" in active_lsr.upper()
        exposure_text = str(prec_exposure or "").upper()
        has_lof_indicators = any(term in exposure_text or term in hazard_text for term in ["LINE OF FIRE", "SWING PATH", "PINCH POINT", "STORED ENERGY", "STAND UNDER", "TRAJECTORY"])

        if is_lof_lsr or has_lof_indicators:
            rule_id = "ACT-R05-LINE-OF-FIRE"
            action_key = f"ACTION|ASSESSMENT|{assessment_id}|LINE_OF_FIRE_CONTROL_REVIEW|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.ASSESSMENT,
                "source_id": str(assessment_id),
                "action_category": ActionCategory.LINE_OF_FIRE_CONTROL_REVIEW,
                "action_title": "Review Line-of-Fire Controls",
                "action_description": "Review line-of-fire controls associated with the identified exposure.",
                "priority": ActionPriority.HIGH if is_high_consequence else ActionPriority.MEDIUM,
                "rationale": f"Generated under rule {rule_id}: Personnel exposure to hazard trajectory or line-of-fire identified.",
                "evidence_refs": base_evidence,
                "source_dimensions": source_dims,
                "lsr_code": active_lsr or "LSR_02_LINE_OF_FIRE",
                "precursor_signature": f"{prec_hazard or 'TRAJECTORY_HAZARD'} | {prec_exposure or 'LINE_OF_FIRE'}",
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        # ----------------------------------------------------------------------
        # ACT-R06-CONFINED-SPACE: Confined Space Control Review
        # ----------------------------------------------------------------------
        is_cs_lsr = active_lsr and "CONFINED_SPACE" in active_lsr.upper()
        has_cs_indicators = any(term in hazard_text or term in str(prec_activity or "").upper() for term in ["CONFINED SPACE", "VESSEL ENTRY", "TANK ENTRY", "SUMP", "ASPHYXIATION", "TOXIC GAS", "H2S", "OXYGEN DEFICIENT"])

        if is_cs_lsr or has_cs_indicators:
            rule_id = "ACT-R06-CONFINED-SPACE"
            action_key = f"ACTION|ASSESSMENT|{assessment_id}|CONFINED_SPACE_CONTROL_REVIEW|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.ASSESSMENT,
                "source_id": str(assessment_id),
                "action_category": ActionCategory.CONFINED_SPACE_CONTROL_REVIEW,
                "action_title": "Review Confined Space Controls",
                "action_description": "Review confined-space controls associated with the identified precursor.",
                "priority": ActionPriority.HIGH,
                "rationale": f"Generated under rule {rule_id}: Confined space entry hazard, hazardous atmosphere, or entry control deficiency identified.",
                "evidence_refs": base_evidence,
                "source_dimensions": source_dims,
                "lsr_code": active_lsr or "LSR_05_CONFINED_SPACE",
                "precursor_signature": f"{prec_hazard or 'CONFINED_SPACE'} | {prec_activity or 'VESSEL_ENTRY'}",
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        # ----------------------------------------------------------------------
        # ACT-R07-HOT-WORK: Hot Work Control Review
        # ----------------------------------------------------------------------
        is_hw_lsr = active_lsr and "HOT_WORK" in active_lsr.upper()
        has_hw_indicators = any(term in hazard_text or term in str(prec_activity or "").upper() for term in ["HOT WORK", "WELDING", "CUTTING", "GRINDING", "IGNITION SOURCE", "FLAMMABLE GAS"])

        if is_hw_lsr or has_hw_indicators:
            rule_id = "ACT-R07-HOT-WORK"
            action_key = f"ACTION|ASSESSMENT|{assessment_id}|HOT_WORK_CONTROL_REVIEW|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.ASSESSMENT,
                "source_id": str(assessment_id),
                "action_category": ActionCategory.HOT_WORK_CONTROL_REVIEW,
                "action_title": "Review Hot Work Controls",
                "action_description": "Review hot-work controls associated with the identified precursor.",
                "priority": ActionPriority.HIGH,
                "rationale": f"Generated under rule {rule_id}: Hot work or ignition source identified in classified operational environment.",
                "evidence_refs": base_evidence,
                "source_dimensions": source_dims,
                "lsr_code": active_lsr or "LSR_06_HOT_WORK",
                "precursor_signature": f"{prec_hazard or 'HOT_WORK'} | {prec_activity or 'WELDING'}",
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        # ----------------------------------------------------------------------
        # ACT-R08-DRIVING: Driving Safety Review
        # ----------------------------------------------------------------------
        is_drv_lsr = active_lsr and "DRIVING" in active_lsr.upper()
        has_drv_indicators = any(term in hazard_text or term in str(prec_activity or "").upper() for term in ["DRIVING", "VEHICLE", "SPEEDING", "SEATBELT", "ROLLOVER", "TRANSPORT", "TANKER TRUCK"])

        if is_drv_lsr or has_drv_indicators:
            rule_id = "ACT-R08-DRIVING"
            action_key = f"ACTION|ASSESSMENT|{assessment_id}|DRIVING_CONTROL_REVIEW|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.ASSESSMENT,
                "source_id": str(assessment_id),
                "action_category": ActionCategory.DRIVING_CONTROL_REVIEW,
                "action_title": "Review Driving Safety Controls",
                "action_description": "Review driving controls associated with the identified precursor.",
                "priority": ActionPriority.HIGH if is_high_consequence else ActionPriority.MEDIUM,
                "rationale": f"Generated under rule {rule_id}: Driving safety violation or transport hazard identified.",
                "evidence_refs": base_evidence,
                "source_dimensions": source_dims,
                "lsr_code": active_lsr or "LSR_08_DRIVING_SAFETY",
                "precursor_signature": f"{prec_hazard or 'DRIVING_SAFETY'} | {prec_activity or 'VEHICLE_OPERATION'}",
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        # ----------------------------------------------------------------------
        # ACT-R09-WORK-AUTH: Work Authorization Review
        # ----------------------------------------------------------------------
        is_ptw_lsr = active_lsr and "WORK_AUTHORIZATION" in active_lsr.upper()
        has_ptw_indicators = any(term in barrier_text or term in str(prec_activity or "").upper() for term in ["PERMIT TO WORK", "PTW", "WORK AUTHORIZATION", "UNAUTHORIZED", "TOOLBOX TALK", "JSA", "NO PERMIT"])

        if is_ptw_lsr or has_ptw_indicators:
            rule_id = "ACT-R09-WORK-AUTH"
            action_key = f"ACTION|ASSESSMENT|{assessment_id}|WORK_AUTHORIZATION_REVIEW|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.ASSESSMENT,
                "source_id": str(assessment_id),
                "action_category": ActionCategory.WORK_AUTHORIZATION_REVIEW,
                "action_title": "Review Work Authorization Controls",
                "action_description": "Review work-authorization controls associated with the identified precursor.",
                "priority": ActionPriority.HIGH,
                "rationale": f"Generated under rule {rule_id}: Work authorization omission or bypassed permit procedure identified.",
                "evidence_refs": base_evidence,
                "source_dimensions": source_dims,
                "lsr_code": active_lsr or "LSR_01_WORK_AUTHORIZATION",
                "precursor_signature": f"{prec_activity or 'MAINTENANCE'} | {prec_barrier or 'PTW_OMISSION'}",
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        # ----------------------------------------------------------------------
        # ACT-R13-CRITICAL-REVIEW: Management Review for Authoritative ACTUAL_SIF
        # ----------------------------------------------------------------------
        if is_actual:
            rule_id = "ACT-R13-CRITICAL-REVIEW"
            action_key = f"ACTION|ASSESSMENT|{assessment_id}|MANAGEMENT_ATTENTION|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.ASSESSMENT,
                "source_id": str(assessment_id),
                "action_category": ActionCategory.MANAGEMENT_ATTENTION,
                "action_title": "Management Review for Authoritative SIF Event",
                "action_description": f"Consider management-level HSE review following authoritative or human-validated actual SIF event at {prec_location or 'facility'}.",
                "priority": ActionPriority.CRITICAL_REVIEW,
                "rationale": f"Generated under rule {rule_id}: Authoritative ACTUAL_SIF classification recorded.",
                "evidence_refs": base_evidence,
                "source_dimensions": source_dims,
                "lsr_code": active_lsr,
                "precursor_signature": f"{prec_hazard or 'CRITICAL_SIF'} | {prec_barrier or 'FAILED_CONTROL'}",
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        return actions

    # --------------------------------------------------------------------------
    # 2. Pattern Evaluation
    # --------------------------------------------------------------------------
    def evaluate_pattern(
        self,
        pattern_id: uuid.UUID,
        pattern_code: str,
        title: str,
        hazard_category: Optional[str],
        failed_barrier_type: Optional[str],
        occurrence_count: int,
        affected_locations: List[str],
        supporting_report_ids: List[str],
        lsr_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluate systemic action rules for an existing persisted recurring precursor pattern."""
        actions: List[Dict[str, Any]] = []

        is_multi_site = len(affected_locations) >= 2
        is_high_frequency = occurrence_count >= 4
        priority = ActionPriority.CRITICAL_REVIEW if (is_multi_site and is_high_frequency) else (ActionPriority.HIGH if (is_multi_site or is_high_frequency) else ActionPriority.MEDIUM)

        rule_id = "ACT-R10-PATTERN-INVESTIGATION"
        action_key = f"ACTION|PATTERN|{pattern_id}|PATTERN_INVESTIGATION|{rule_id}"

        evidence_refs = [
            {"pattern_id": str(pattern_id), "pattern_code": pattern_code, "supporting_report_count": occurrence_count},
        ]
        for rid in supporting_report_ids[:5]:
            evidence_refs.append({"report_id": rid})

        source_dims = {
            "hazard_category": hazard_category,
            "failed_barrier_type": failed_barrier_type,
            "occurrence_count": occurrence_count,
            "affected_locations": affected_locations,
            "lsr_code": lsr_code,
        }

        loc_str = ", ".join(affected_locations[:3]) if affected_locations else "affected operations"
        actions.append({
            "action_key": action_key,
            "source_type": ActionSourceType.PATTERN,
            "source_id": str(pattern_id),
            "action_category": ActionCategory.PATTERN_INVESTIGATION,
            "action_title": f"Review Systemic Factors for Pattern '{pattern_code}'",
            "action_description": f"Review and investigate systemic organizational factors associated with recurring precursor pattern '{title}' across {loc_str}.",
            "priority": priority,
            "rationale": f"Generated under rule {rule_id}: Persisted recurring precursor pattern '{pattern_code}' detected.",
            "evidence_refs": evidence_refs,
            "source_dimensions": source_dims,
            "lsr_code": lsr_code,
            "pattern_key": pattern_code,
            "rule_id": rule_id,
            "rule_version": self.VERSION,
        })

        return actions

    # --------------------------------------------------------------------------
    # 3. Concentration Evaluation
    # --------------------------------------------------------------------------
    def evaluate_concentration(
        self,
        concentration_key: str,
        dimension_type: ConcentrationDimension,
        dimension_value: str,
        occurrence_count: int,
        distinct_report_count: int,
        distinct_location_count: int,
        observed_trend: ObservedTrend,
        supporting_report_ids: List[str],
        supporting_locations: List[str],
    ) -> List[Dict[str, Any]]:
        """Evaluate operational focus rules for an existing persisted risk concentration."""
        actions: List[Dict[str, Any]] = []

        is_increasing = observed_trend == ObservedTrend.INCREASING
        priority = ActionPriority.HIGH if is_increasing else ActionPriority.MEDIUM

        evidence_refs = [
            {"concentration_key": concentration_key, "dimension_type": dimension_type.value, "distinct_reports": distinct_report_count},
        ]
        for rid in supporting_report_ids[:5]:
            evidence_refs.append({"report_id": rid})

        source_dims = {
            "dimension_type": dimension_type.value,
            "dimension_value": dimension_value,
            "distinct_report_count": distinct_report_count,
            "distinct_location_count": distinct_location_count,
            "observed_trend": observed_trend.value,
        }

        if dimension_type == ConcentrationDimension.LOCATION:
            rule_id = "ACT-R11-SITE-CONCENTRATION"
            action_key = f"ACTION|CONCENTRATION|{concentration_key}|SITE_FOCUSED_REVIEW|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.CONCENTRATION,
                "source_id": concentration_key,
                "action_category": ActionCategory.SITE_FOCUSED_REVIEW,
                "action_title": f"Consider Site-Focused Review for Location: '{dimension_value}'",
                "action_description": f"Consider targeted operational review for location '{dimension_value}' based on persisted concentration finding.",
                "priority": priority,
                "rationale": f"Generated under rule {rule_id}: Persisted LOCATION concentration exists for '{dimension_value}'.",
                "evidence_refs": evidence_refs,
                "source_dimensions": source_dims,
                "concentration_key": concentration_key,
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        elif dimension_type in (ConcentrationDimension.ACTIVITY, ConcentrationDimension.BARRIER_FAILURE, ConcentrationDimension.LIFE_SAVING_RULE):
            rule_id = "ACT-R12-ACTIVITY-PROCEDURE"
            category = ActionCategory.TREND_INVESTIGATION if is_increasing else ActionCategory.PROCEDURE_REVIEW
            action_key = f"ACTION|CONCENTRATION|{concentration_key}|{category.value}|{rule_id}"
            actions.append({
                "action_key": action_key,
                "source_type": ActionSourceType.CONCENTRATION,
                "source_id": concentration_key,
                "action_category": category,
                "action_title": f"Review Procedures and Controls for {dimension_type.value}: '{dimension_value}'",
                "action_description": f"Review operational procedures and controls associated with persisted concentration for {dimension_type.value} '{dimension_value}'.",
                "priority": priority,
                "rationale": f"Generated under rule {rule_id}: Persisted concentration exists for {dimension_type.value} '{dimension_value}'.",
                "evidence_refs": evidence_refs,
                "source_dimensions": source_dims,
                "concentration_key": concentration_key,
                "rule_id": rule_id,
                "rule_version": self.VERSION,
            })

        return actions

    @staticmethod
    def _normalize_dim_val(val: Any) -> Optional[str]:
        """Safely normalize precursor dimension values from strings or dict structures."""
        if not val:
            return None
        if isinstance(val, str):
            cleaned = val.strip()
            return cleaned if cleaned and cleaned not in ("*", "UNKNOWN", "OTHER", "N/A") else None
        if isinstance(val, dict):
            for k in ("value", "failure_type", "category", "description", "rule_code", "name", "type"):
                sub = val.get(k)
                if isinstance(sub, str) and sub.strip() and sub.strip() not in ("*", "UNKNOWN", "OTHER", "N/A"):
                    return sub.strip()
        return None

