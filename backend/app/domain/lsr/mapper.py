"""IOGP Report 459 Life-Saving Rules Mapping Engine."""

from typing import List, Optional

from app.domain.enums import EvidenceStrength
from app.domain.lsr.evidence import LSREvidenceMapping, LSRMappingResult
from app.domain.safety_event import EvidenceSpan, SafetyEventContext
from app.domain.taxonomy.loader import TaxonomyDefinition, get_default_taxonomy


class LSRMapper:
    """Evaluates SafetyEventContext against the versioned IOGP Report 459 taxonomy."""

    def __init__(self, taxonomy: Optional[TaxonomyDefinition] = None):
        self.taxonomy = taxonomy or get_default_taxonomy()

    def map_rules(self, context: SafetyEventContext) -> LSRMappingResult:
        """Map safety event context to zero, one, or multiple Life-Saving Rules."""
        mappings: List[LSREvidenceMapping] = []
        text_lower = context.normalized_text.lower()

        # Helper to find a rule definition by code
        def find_rule(code: str):
            return self.taxonomy.get_rule_by_code(code)

        # -------------------------------------------------------------
        # 1. LSR_07: Safe Mechanical Lifting
        # -------------------------------------------------------------
        is_lifting_activity = (
            context.activity and "Casing" in context.activity.canonical_name
        ) or any("Air Winch" in eq.canonical_name or "Crane" in eq.canonical_name for eq in context.equipment)
        has_rigging_failure = any("Lifting Line" in b.canonical_name for b in context.barrier_failures)
        has_suspended_load = any("Suspended" in h.canonical_name for h in context.hazards if not h.is_negated)

        if (is_lifting_activity and (has_rigging_failure or has_suspended_load)) or (has_rigging_failure and has_suspended_load):
            rule_def = find_rule("LSR_07_SAFE_MECHANICAL_LIFTING")
            if rule_def:
                spans: List[EvidenceSpan] = []
                triggers = []
                for b in context.barrier_failures:
                    if "Lifting Line" in b.canonical_name:
                        triggers.append(b.raw_match)
                        spans.extend(b.evidence_spans)
                for h in context.hazards:
                    if "Suspended" in h.canonical_name and not h.is_negated:
                        triggers.append(h.raw_match)
                        spans.extend(h.evidence_spans)

                mappings.append(
                    LSREvidenceMapping(
                        taxonomy_id=self.taxonomy.taxonomy_id,
                        taxonomy_version=self.taxonomy.version,
                        rule_code=rule_def.code,
                        rule_name=rule_def.name,
                        evidence_strength=EvidenceStrength.HIGH,
                        trigger_evidence=triggers,
                        evidence_spans=spans,
                        provenance_rule="LSR_RULE_MECHANICAL_LIFTING_001",
                        is_primary=False,
                    )
                )

        # -------------------------------------------------------------
        # 2. LSR_06: Line of Fire
        # -------------------------------------------------------------
        has_line_of_fire_exposure = any("Line of Fire" in ex.canonical_name for ex in context.exposure)
        if has_line_of_fire_exposure:
            rule_def = find_rule("LSR_06_LINE_OF_FIRE")
            if rule_def:
                spans = []
                triggers = []
                for ex in context.exposure:
                    if "Line of Fire" in ex.canonical_name:
                        triggers.append(ex.raw_match)
                        spans.extend(ex.evidence_spans)

                mappings.append(
                    LSREvidenceMapping(
                        taxonomy_id=self.taxonomy.taxonomy_id,
                        taxonomy_version=self.taxonomy.version,
                        rule_code=rule_def.code,
                        rule_name=rule_def.name,
                        evidence_strength=EvidenceStrength.HIGH,
                        trigger_evidence=triggers,
                        evidence_spans=spans,
                        provenance_rule="LSR_RULE_LINE_OF_FIRE_002",
                        is_primary=False,
                    )
                )

        # -------------------------------------------------------------
        # 3. LSR_09: Working at Height
        # -------------------------------------------------------------
        has_height_hazard = any("Height" in h.canonical_name for h in context.hazards if not h.is_negated)
        has_height_barrier_failure = any("Fall Protection" in b.canonical_name for b in context.barrier_failures)
        if has_height_hazard or has_height_barrier_failure:
            rule_def = find_rule("LSR_09_WORKING_AT_HEIGHT")
            if rule_def:
                spans = []
                triggers = []
                for b in context.barrier_failures:
                    if "Fall Protection" in b.canonical_name:
                        triggers.append(b.raw_match)
                        spans.extend(b.evidence_spans)
                for h in context.hazards:
                    if "Height" in h.canonical_name and not h.is_negated:
                        triggers.append(h.raw_match)
                        spans.extend(h.evidence_spans)

                mappings.append(
                    LSREvidenceMapping(
                        taxonomy_id=self.taxonomy.taxonomy_id,
                        taxonomy_version=self.taxonomy.version,
                        rule_code=rule_def.code,
                        rule_name=rule_def.name,
                        evidence_strength=EvidenceStrength.HIGH,
                        trigger_evidence=triggers,
                        evidence_spans=spans,
                        provenance_rule="LSR_RULE_WORKING_AT_HEIGHT_003",
                        is_primary=False,
                    )
                )

        # -------------------------------------------------------------
        # 4. LSR_04: Energy Isolation
        # -------------------------------------------------------------
        has_energy_isolation_failure = any("Energy Isolation" in b.canonical_name for b in context.barrier_failures)
        has_pressure_hazard = any("Pressure" in h.canonical_name for h in context.hazards if not h.is_negated)
        has_electrical_hazard = any("Electrical" in h.canonical_name for h in context.hazards if not h.is_negated)

        if has_energy_isolation_failure or (has_pressure_hazard and any("valve" in eq.canonical_name.lower() or "manifold" in eq.canonical_name.lower() for eq in context.equipment)):
            rule_def = find_rule("LSR_04_ENERGY_ISOLATION")
            if rule_def:
                spans = []
                triggers = []
                for b in context.barrier_failures:
                    if "Energy Isolation" in b.canonical_name:
                        triggers.append(b.raw_match)
                        spans.extend(b.evidence_spans)
                for h in context.hazards:
                    if ("Pressure" in h.canonical_name or "Electrical" in h.canonical_name) and not h.is_negated:
                        triggers.append(h.raw_match)
                        spans.extend(h.evidence_spans)

                mappings.append(
                    LSREvidenceMapping(
                        taxonomy_id=self.taxonomy.taxonomy_id,
                        taxonomy_version=self.taxonomy.version,
                        rule_code=rule_def.code,
                        rule_name=rule_def.name,
                        evidence_strength=EvidenceStrength.HIGH,
                        trigger_evidence=triggers,
                        evidence_spans=spans,
                        provenance_rule="LSR_RULE_ENERGY_ISOLATION_004",
                        is_primary=False,
                    )
                )

        # -------------------------------------------------------------
        # 5. LSR_02: Confined Space
        # -------------------------------------------------------------
        has_confined_hazard = any("Confined Space" in h.canonical_name for h in context.hazards if not h.is_negated)
        has_confined_failure = any("Confined Space Control" in b.canonical_name for b in context.barrier_failures)
        if has_confined_hazard or has_confined_failure:
            rule_def = find_rule("LSR_02_CONFINED_SPACE")
            if rule_def:
                spans = []
                triggers = []
                for b in context.barrier_failures:
                    if "Confined Space Control" in b.canonical_name:
                        triggers.append(b.raw_match)
                        spans.extend(b.evidence_spans)
                for h in context.hazards:
                    if "Confined Space" in h.canonical_name and not h.is_negated:
                        triggers.append(h.raw_match)
                        spans.extend(h.evidence_spans)

                mappings.append(
                    LSREvidenceMapping(
                        taxonomy_id=self.taxonomy.taxonomy_id,
                        taxonomy_version=self.taxonomy.version,
                        rule_code=rule_def.code,
                        rule_name=rule_def.name,
                        evidence_strength=EvidenceStrength.HIGH,
                        trigger_evidence=triggers,
                        evidence_spans=spans,
                        provenance_rule="LSR_RULE_CONFINED_SPACE_005",
                        is_primary=False,
                    )
                )

        # -------------------------------------------------------------
        # 6. LSR_05: Hot Work
        # -------------------------------------------------------------
        has_hot_work_activity = context.activity and "Hot Work" in context.activity.canonical_name
        if has_hot_work_activity or "welding" in text_lower or "gas cutting" in text_lower:
            rule_def = find_rule("LSR_05_HOT_WORK")
            if rule_def:
                spans = []
                triggers = []
                if context.activity and "Hot Work" in context.activity.canonical_name:
                    triggers.append(context.activity.raw_match)
                    spans.extend(context.activity.evidence_spans)

                mappings.append(
                    LSREvidenceMapping(
                        taxonomy_id=self.taxonomy.taxonomy_id,
                        taxonomy_version=self.taxonomy.version,
                        rule_code=rule_def.code,
                        rule_name=rule_def.name,
                        evidence_strength=EvidenceStrength.HIGH,
                        trigger_evidence=triggers,
                        evidence_spans=spans,
                        provenance_rule="LSR_RULE_HOT_WORK_006",
                        is_primary=False,
                    )
                )

        # -------------------------------------------------------------
        # 7. LSR_03: Driving
        # -------------------------------------------------------------
        has_driving = (context.activity and "Vehicle" in context.activity.canonical_name) or "driving" in text_lower or "bowser" in text_lower
        if has_driving and ("overspeeding" in text_lower or "seatbelt" in text_lower or "rollover" in text_lower or "driver" in text_lower):
            rule_def = find_rule("LSR_03_DRIVING")
            if rule_def:
                spans = []
                triggers = []
                if context.activity:
                    triggers.append(context.activity.raw_match)
                    spans.extend(context.activity.evidence_spans)

                mappings.append(
                    LSREvidenceMapping(
                        taxonomy_id=self.taxonomy.taxonomy_id,
                        taxonomy_version=self.taxonomy.version,
                        rule_code=rule_def.code,
                        rule_name=rule_def.name,
                        evidence_strength=EvidenceStrength.HIGH,
                        trigger_evidence=triggers,
                        evidence_spans=spans,
                        provenance_rule="LSR_RULE_DRIVING_007",
                        is_primary=False,
                    )
                )

        # -------------------------------------------------------------
        # 8. LSR_01: Bypassing Safety Controls
        # -------------------------------------------------------------
        has_bypassed = any("guard removed" in text_lower or "interlock bypassed" in text_lower or "disabled" in text_lower or "bridged" in text_lower for _ in [1])
        if has_bypassed:
            rule_def = find_rule("LSR_01_BYPASS_SAFETY_CONTROLS")
            if rule_def:
                mappings.append(
                    LSREvidenceMapping(
                        taxonomy_id=self.taxonomy.taxonomy_id,
                        taxonomy_version=self.taxonomy.version,
                        rule_code=rule_def.code,
                        rule_name=rule_def.name,
                        evidence_strength=EvidenceStrength.HIGH,
                        trigger_evidence=["bypassed/defeated safety control"],
                        evidence_spans=[],
                        provenance_rule="LSR_RULE_BYPASS_CONTROLS_008",
                        is_primary=False,
                    )
                )

        # -------------------------------------------------------------
        # 9. LSR_08: Work Authorization
        # -------------------------------------------------------------
        has_unpermitted = "without permit" in text_lower or "permit to work" in text_lower or "ptw not obtained" in text_lower or "toolbox talk" in text_lower
        if has_unpermitted:
            rule_def = find_rule("LSR_08_WORK_AUTHORIZATION")
            if rule_def:
                mappings.append(
                    LSREvidenceMapping(
                        taxonomy_id=self.taxonomy.taxonomy_id,
                        taxonomy_version=self.taxonomy.version,
                        rule_code=rule_def.code,
                        rule_name=rule_def.name,
                        evidence_strength=EvidenceStrength.HIGH,
                        trigger_evidence=["permit to work violation"],
                        evidence_spans=[],
                        provenance_rule="LSR_RULE_WORK_AUTH_009",
                        is_primary=False,
                    )
                )

        # -------------------------------------------------------------
        # Primary Rule Determination Logic
        # -------------------------------------------------------------
        primary_rule: Optional[LSREvidenceMapping] = None
        if len(mappings) == 1:
            mappings[0].is_primary = True
            primary_rule = mappings[0]
        elif len(mappings) > 1:
            # Defensible primary selection: root barrier failure takes precedence
            if has_rigging_failure:
                target = next((m for m in mappings if m.rule_code == "LSR_07_SAFE_MECHANICAL_LIFTING"), None)
                if target:
                    target.is_primary = True
                    primary_rule = target
            elif has_height_barrier_failure:
                target = next((m for m in mappings if m.rule_code == "LSR_09_WORKING_AT_HEIGHT"), None)
                if target:
                    target.is_primary = True
                    primary_rule = target
            elif has_confined_failure:
                target = next((m for m in mappings if m.rule_code == "LSR_02_CONFINED_SPACE"), None)
                if target:
                    target.is_primary = True
                    primary_rule = target
            elif has_energy_isolation_failure:
                target = next((m for m in mappings if m.rule_code == "LSR_04_ENERGY_ISOLATION"), None)
                if target:
                    target.is_primary = True
                    primary_rule = target

        return LSRMappingResult(
            taxonomy_id=self.taxonomy.taxonomy_id,
            taxonomy_version=self.taxonomy.version,
            mapped_rules=mappings,
            primary_rule=primary_rule,
        )
