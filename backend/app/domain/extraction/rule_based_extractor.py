"""Deterministic, domain-aware safety event NLP context extractor."""

import re
from typing import Any, Dict, List, Optional

from app.domain.enums import DerivationType, EvidenceStrength
from app.domain.extraction.negation import NegationAnalyzer
from app.domain.extraction.normalizer import TextNormalizer
from app.domain.interfaces.extractor import NLPExtractorInterface
from app.domain.lexicon.loader import (
    LexiconEntry,
    SafetyLexicon,
    get_default_safety_lexicon,
)
from app.domain.safety_event import (
    EvidenceSpan,
    ExtractedItem,
    SafetyEventContext,
)


class RuleBasedSafetyExtractor(NLPExtractorInterface):
    """Deterministic, domain-aware safety context extractor implementing NLPExtractorInterface."""

    def __init__(self, lexicon: Optional[SafetyLexicon] = None):
        self.lexicon = lexicon or get_default_safety_lexicon()
        self.negation_analyzer = NegationAnalyzer(self.lexicon.negation_config)
        self._compiled_patterns = self._compile_lexicon_patterns()

    def _compile_lexicon_patterns(self) -> Dict[str, List[tuple[LexiconEntry, re.Pattern]]]:
        """Compile regex patterns for each category with word boundaries."""
        compiled = {}
        category_entries = {
            "HAZARDS": self.lexicon.hazards,
            "ACTIVITIES": self.lexicon.activities,
            "EQUIPMENT": self.lexicon.equipment,
            "BARRIER_FAILURES": self.lexicon.barrier_failures,
            "EXPOSURE": self.lexicon.exposure,
            "UNSAFE_ACTS": self.lexicon.unsafe_acts,
            "UNSAFE_CONDITIONS": self.lexicon.unsafe_conditions,
            "POTENTIAL_CONSEQUENCES": self.lexicon.potential_consequences,
            "PEOPLE_ROLES": self.lexicon.people_roles,
        }

        for cat, entries in category_entries.items():
            compiled[cat] = []
            for entry in entries:
                for pat in entry.patterns:
                    escaped = re.escape(pat)
                    regex = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
                    compiled[cat].append((entry, regex))

        return compiled

    def extract_safety_event_context(self, raw_text: str | None) -> SafetyEventContext:
        """Process raw text and return a fully structured SafetyEventContext."""
        norm_result = TextNormalizer.normalize(raw_text)
        text = norm_result.normalized_text

        if not text:
            return SafetyEventContext(
                original_text=norm_result.original_text,
                normalized_text="",
            )

        # Temporary collectors: map canonical_name -> ExtractedItem
        extracted_hazards: Dict[str, ExtractedItem] = {}
        extracted_activities: Dict[str, ExtractedItem] = {}
        extracted_equipment: Dict[str, ExtractedItem] = {}
        extracted_barrier_failures: Dict[str, ExtractedItem] = {}
        extracted_exposure: Dict[str, ExtractedItem] = {}
        extracted_unsafe_acts: Dict[str, ExtractedItem] = {}
        extracted_unsafe_conditions: Dict[str, ExtractedItem] = {}
        extracted_potential_consequences: Dict[str, ExtractedItem] = {}
        extracted_people_roles: Dict[str, ExtractedItem] = {}
        energy_sources_map: Dict[str, ExtractedItem] = {}
        all_spans: List[EvidenceSpan] = []

        # 1. Extract Hazards & Energy Sources
        for entry, pattern in self._compiled_patterns["HAZARDS"]:
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_str = text[start:end]
                span = EvidenceSpan(
                    text=matched_str,
                    category="HAZARD",
                    start_char=start,
                    end_char=end,
                )
                all_spans.append(span)

                is_neg, trigger = self.negation_analyzer.is_hazard_negated(text, start, end)

                if entry.canonical_name not in extracted_hazards:
                    extracted_hazards[entry.canonical_name] = ExtractedItem(
                        canonical_name=entry.canonical_name,
                        category="HAZARD",
                        raw_match=matched_str,
                        evidence_spans=[span],
                        evidence_strength=EvidenceStrength.HIGH if not is_neg else EvidenceStrength.LOW,
                        is_negated=is_neg,
                        provenance_rule=f"LEXICON_HAZARD_{entry.energy_type or 'GENERAL'}",
                        attributes={"energy_type": entry.energy_type},
                    )
                else:
                    extracted_hazards[entry.canonical_name].evidence_spans.append(span)

                # If hazard is not negated and has high energy type, add to energy_sources
                if not is_neg and entry.energy_type and entry.energy_type != "LOW_ENERGY":
                    energy_name = f"High Energy: {entry.energy_type}"
                    if energy_name not in energy_sources_map:
                        energy_sources_map[energy_name] = ExtractedItem(
                            canonical_name=energy_name,
                            category="ENERGY_SOURCE",
                            raw_match=matched_str,
                            evidence_spans=[span],
                            evidence_strength=EvidenceStrength.HIGH,
                            is_negated=False,
                            provenance_rule=f"ENERGY_{entry.energy_type}",
                            attributes={"energy_type": entry.energy_type},
                        )
                    else:
                        energy_sources_map[energy_name].evidence_spans.append(span)

        # 2. Extract Activities
        for entry, pattern in self._compiled_patterns["ACTIVITIES"]:
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_str = text[start:end]
                span = EvidenceSpan(
                    text=matched_str,
                    category="ACTIVITY",
                    start_char=start,
                    end_char=end,
                )
                all_spans.append(span)

                if entry.canonical_name not in extracted_activities:
                    extracted_activities[entry.canonical_name] = ExtractedItem(
                        canonical_name=entry.canonical_name,
                        category="ACTIVITY",
                        raw_match=matched_str,
                        evidence_spans=[span],
                        evidence_strength=EvidenceStrength.HIGH,
                        is_negated=False,
                        provenance_rule="LEXICON_ACTIVITY",
                    )
                else:
                    extracted_activities[entry.canonical_name].evidence_spans.append(span)

        # 3. Extract Equipment
        for entry, pattern in self._compiled_patterns["EQUIPMENT"]:
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_str = text[start:end]
                span = EvidenceSpan(
                    text=matched_str,
                    category="EQUIPMENT",
                    start_char=start,
                    end_char=end,
                )
                all_spans.append(span)

                if entry.canonical_name not in extracted_equipment:
                    extracted_equipment[entry.canonical_name] = ExtractedItem(
                        canonical_name=entry.canonical_name,
                        category="EQUIPMENT",
                        raw_match=matched_str,
                        evidence_spans=[span],
                        evidence_strength=EvidenceStrength.MEDIUM,
                        is_negated=False,
                        provenance_rule="LEXICON_EQUIPMENT",
                    )
                else:
                    extracted_equipment[entry.canonical_name].evidence_spans.append(span)

        # 4. Extract Barrier Failures
        for entry, pattern in self._compiled_patterns["BARRIER_FAILURES"]:
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_str = text[start:end]
                span = EvidenceSpan(
                    text=matched_str,
                    category="BARRIER_FAILURE",
                    start_char=start,
                    end_char=end,
                )
                all_spans.append(span)

                if entry.canonical_name not in extracted_barrier_failures:
                    extracted_barrier_failures[entry.canonical_name] = ExtractedItem(
                        canonical_name=entry.canonical_name,
                        category="BARRIER_FAILURE",
                        raw_match=matched_str,
                        evidence_spans=[span],
                        evidence_strength=EvidenceStrength.HIGH,
                        is_negated=False,
                        provenance_rule="LEXICON_BARRIER_FAILURE",
                    )
                else:
                    extracted_barrier_failures[entry.canonical_name].evidence_spans.append(span)

        # 5. Extract Exposure
        for entry, pattern in self._compiled_patterns["EXPOSURE"]:
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_str = text[start:end]
                span = EvidenceSpan(
                    text=matched_str,
                    category="EXPOSURE",
                    start_char=start,
                    end_char=end,
                )
                all_spans.append(span)

                if entry.canonical_name not in extracted_exposure:
                    extracted_exposure[entry.canonical_name] = ExtractedItem(
                        canonical_name=entry.canonical_name,
                        category="EXPOSURE",
                        raw_match=matched_str,
                        evidence_spans=[span],
                        evidence_strength=EvidenceStrength.HIGH,
                        is_negated=False,
                        provenance_rule="LEXICON_EXPOSURE",
                    )
                else:
                    extracted_exposure[entry.canonical_name].evidence_spans.append(span)

        # 6. Extract Unsafe Acts
        for entry, pattern in self._compiled_patterns["UNSAFE_ACTS"]:
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_str = text[start:end]
                span = EvidenceSpan(
                    text=matched_str,
                    category="UNSAFE_ACT",
                    start_char=start,
                    end_char=end,
                )
                all_spans.append(span)

                if entry.canonical_name not in extracted_unsafe_acts:
                    extracted_unsafe_acts[entry.canonical_name] = ExtractedItem(
                        canonical_name=entry.canonical_name,
                        category="UNSAFE_ACT",
                        raw_match=matched_str,
                        evidence_spans=[span],
                        evidence_strength=EvidenceStrength.HIGH,
                        is_negated=False,
                        provenance_rule="LEXICON_UNSAFE_ACT",
                    )
                else:
                    extracted_unsafe_acts[entry.canonical_name].evidence_spans.append(span)

        # 7. Extract Unsafe Conditions
        for entry, pattern in self._compiled_patterns["UNSAFE_CONDITIONS"]:
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_str = text[start:end]
                span = EvidenceSpan(
                    text=matched_str,
                    category="UNSAFE_CONDITION",
                    start_char=start,
                    end_char=end,
                )
                all_spans.append(span)

                if entry.canonical_name not in extracted_unsafe_conditions:
                    extracted_unsafe_conditions[entry.canonical_name] = ExtractedItem(
                        canonical_name=entry.canonical_name,
                        category="UNSAFE_CONDITION",
                        raw_match=matched_str,
                        evidence_spans=[span],
                        evidence_strength=EvidenceStrength.MEDIUM,
                        is_negated=False,
                        provenance_rule="LEXICON_UNSAFE_CONDITION",
                    )
                else:
                    extracted_unsafe_conditions[entry.canonical_name].evidence_spans.append(span)

        # 8. Extract Potential Consequences
        for entry, pattern in self._compiled_patterns["POTENTIAL_CONSEQUENCES"]:
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_str = text[start:end]
                span = EvidenceSpan(
                    text=matched_str,
                    category="POTENTIAL_CONSEQUENCE",
                    start_char=start,
                    end_char=end,
                )
                all_spans.append(span)

                if entry.canonical_name not in extracted_potential_consequences:
                    extracted_potential_consequences[entry.canonical_name] = ExtractedItem(
                        canonical_name=entry.canonical_name,
                        category="POTENTIAL_CONSEQUENCE",
                        raw_match=matched_str,
                        evidence_spans=[span],
                        evidence_strength=EvidenceStrength.HIGH,
                        is_negated=False,
                        provenance_rule="LEXICON_POTENTIAL_CONSEQUENCE",
                    )
                else:
                    extracted_potential_consequences[entry.canonical_name].evidence_spans.append(span)

        # 9. Extract People Roles
        for entry, pattern in self._compiled_patterns["PEOPLE_ROLES"]:
            for match in pattern.finditer(text):
                start, end = match.span()
                matched_str = text[start:end]
                span = EvidenceSpan(
                    text=matched_str,
                    category="PEOPLE_ROLE",
                    start_char=start,
                    end_char=end,
                )
                all_spans.append(span)

                if entry.canonical_name not in extracted_people_roles:
                    extracted_people_roles[entry.canonical_name] = ExtractedItem(
                        canonical_name=entry.canonical_name,
                        category="PEOPLE_ROLE",
                        raw_match=matched_str,
                        evidence_spans=[span],
                        evidence_strength=EvidenceStrength.MEDIUM,
                        is_negated=False,
                        provenance_rule="LEXICON_PEOPLE_ROLE",
                    )
                else:
                    extracted_people_roles[entry.canonical_name].evidence_spans.append(span)

        # Determine Primary Activity (first matched activity if available)
        primary_activity = next(iter(extracted_activities.values()), None)

        # Filter active (non-negated) hazards
        active_hazards = [h for h in extracted_hazards.values() if not h.is_negated]

        return SafetyEventContext(
            original_text=norm_result.original_text,
            normalized_text=text,
            activity=primary_activity,
            hazards=list(extracted_hazards.values()),
            energy_sources=list(energy_sources_map.values()),
            equipment=list(extracted_equipment.values()),
            exposure=list(extracted_exposure.values()),
            barrier_failures=list(extracted_barrier_failures.values()),
            unsafe_acts=list(extracted_unsafe_acts.values()),
            unsafe_conditions=list(extracted_unsafe_conditions.values()),
            potential_consequences=list(extracted_potential_consequences.values()),
            people_roles=list(extracted_people_roles.values()),
            all_evidence_spans=all_spans,
        )

    # --- NLPExtractorInterface Implementations ---

    async def extract_entities(self, raw_text: str) -> Dict[str, Any]:
        """Extract domain entities as dictionary representation."""
        context = self.extract_safety_event_context(raw_text)
        return context.model_dump()

