"""Deterministic text representation formatter for structured SIF precursors."""

from typing import Optional
from app.domain.precursor.model import StructuredSIFPrecursor


class PrecursorTextFormatter:
    """Formats a StructuredSIFPrecursor into a deterministic, clean string representation.
    
    Exclusively includes populated precursor dimensions with clear labels, omitting
    missing dimensions without filler text or wildcard placeholders (*, UNKNOWN, OTHER).
    """

    DIMENSION_LABELS = [
        ("hazard", "Hazard"),
        ("activity", "Activity"),
        ("barrier_failure", "Barrier Failure"),
        ("exposure", "Exposure"),
        ("potential_consequence", "Potential Consequence"),
        ("life_saving_rule", "Life-Saving Rule"),
        ("location", "Location"),
    ]

    @classmethod
    def format_to_text(cls, precursor: Optional[StructuredSIFPrecursor]) -> Optional[str]:
        """Convert structured precursor into deterministic multi-line key-value text.
        
        Returns None if precursor is None or has no populated dimensions.
        """
        if precursor is None:
            return None

        lines = []
        for field_name, label in cls.DIMENSION_LABELS:
            val = getattr(precursor, field_name, None)
            if val is not None and str(val).strip():
                clean_val = str(val).strip()
                # Ensure no wildcard / placeholder tokens
                if clean_val not in ("*", "UNKNOWN", "OTHER"):
                    lines.append(f"{label}: {clean_val}")

        if not lines:
            return None

        return "\n".join(lines)
