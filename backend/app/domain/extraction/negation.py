"""Contextual negation and barrier-absence analyzer for safety narratives."""

import re
from typing import List, Tuple

from app.domain.lexicon.loader import NegationConfig


class NegationAnalyzer:
    """Evaluates contextual negation for safety hazards and controls."""

    def __init__(self, config: NegationConfig):
        self.config = config
        
        # Compile hazard negation regex
        escaped_hazard_triggers = [re.escape(t) for t in config.hazard_negation_triggers]
        self.hazard_neg_pattern = re.compile(
            rf"\b(?:{'|'.join(escaped_hazard_triggers)})\b",
            re.IGNORECASE,
        )

        # Compile barrier absence regex
        escaped_barrier_triggers = [re.escape(t) for t in config.barrier_absence_triggers]
        self.barrier_absence_pattern = re.compile(
            rf"\b(?:{'|'.join(escaped_barrier_triggers)})\b",
            re.IGNORECASE,
        )

    def is_hazard_negated(
        self,
        text: str,
        match_start: int,
        match_end: int,
        window_chars: int = 40,
    ) -> Tuple[bool, str | None]:
        """Check if a matched hazard or consequence is negated in preceding context.
        
        Example: 'no gas leak occurred' -> 'gas leak' is preceded by 'no' -> negated.
        """
        # Get preceding text window up to preceding sentence/clause boundary
        start_window = max(0, match_start - window_chars)
        window_text = text[start_window:match_start]

        # Break at clause delimiters (; . ! ?)
        clause_delimiters = [m.start() for m in re.finditer(r"[;.!?]", window_text)]
        if clause_delimiters:
            last_delim = clause_delimiters[-1]
            window_text = window_text[last_delim + 1:]

        match = self.hazard_neg_pattern.search(window_text)
        if match:
            trigger = match.group(0)
            return True, trigger

        return False, None

    def is_barrier_absence_triggered(
        self,
        text: str,
        match_start: int,
        match_end: int,
        window_chars: int = 35,
    ) -> Tuple[bool, str | None]:
        """Check if a safety control or barrier has an absence/omission trigger.
        
        Example: 'without safety harness' -> 'safety harness' has absence trigger 'without' -> Barrier Failure!
        """
        start_window = max(0, match_start - window_chars)
        window_text = text[start_window:match_start]

        clause_delimiters = [m.start() for m in re.finditer(r"[;.!?]", window_text)]
        if clause_delimiters:
            last_delim = clause_delimiters[-1]
            window_text = window_text[last_delim + 1:]

        match = self.barrier_absence_pattern.search(window_text)
        if match:
            trigger = match.group(0)
            return True, trigger

        return False, None
