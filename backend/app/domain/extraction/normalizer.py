"""Deterministic text preprocessing and normalization."""

import re
import unicodedata
from typing import List, Tuple

from app.domain.safety_event import TextNormalizationResult


class TextNormalizer:
    """Deterministic, lightweight text preprocessor."""

    # Sentence boundary regex (handles periods, exclamation marks, question marks followed by space/end)
    SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

    @classmethod
    def normalize(cls, raw_text: str | None) -> TextNormalizationResult:
        """Clean and normalize raw safety text while preserving original text."""
        if not raw_text:
            return TextNormalizationResult(
                original_text="",
                normalized_text="",
                sentence_spans=[],
            )

        original = raw_text

        # 1. Unicode Normalization (NFKC)
        normalized = unicodedata.normalize("NFKC", original)

        # 2. Normalize whitespace (tabs, newlines, multiple spaces) to single space, stripping edges
        # Note: We keep punctuation and casing intact for accurate display and sentence splitting.
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # 3. Sentence segmentation with character spans in normalized text
        sentence_spans: List[Tuple[int, int]] = []
        if normalized:
            current_pos = 0
            # Split sentences
            sentences = cls.SENTENCE_SPLIT_REGEX.split(normalized)
            for sent in sentences:
                sent_len = len(sent)
                if sent_len > 0:
                    start_idx = normalized.find(sent, current_pos)
                    if start_idx != -1:
                        end_idx = start_idx + sent_len
                        sentence_spans.append((start_idx, end_idx))
                        current_pos = end_idx

        return TextNormalizationResult(
            original_text=original,
            normalized_text=normalized,
            sentence_spans=sentence_spans,
        )
