"""Deduplication engine for batch safety report ingestion."""

import hashlib
from datetime import datetime
from typing import Optional

from app.domain.enums import SourceType


class BatchDeduplicator:
    """Provides deterministic fingerprinting and reference resolution for safety reports."""

    @staticmethod
    def generate_fingerprint(
        raw_text: str,
        reported_location: Optional[str] = None,
        reported_department: Optional[str] = None,
        source_type: SourceType = SourceType.NEAR_MISS,
        event_timestamp: Optional[datetime] = None,
    ) -> str:
        """Compute deterministic 16-character SHA-256 fingerprint for a report narrative and context."""
        norm_text = raw_text.strip().lower()
        norm_loc = (reported_location or "").strip().lower()
        norm_dept = (reported_department or "").strip().lower()
        norm_type = source_type.value.lower()
        norm_date = event_timestamp.strftime("%Y-%m-%d") if event_timestamp else "NO_DATE"

        canonical_content = f"{norm_text}|{norm_loc}|{norm_dept}|{norm_type}|{norm_date}"
        digest = hashlib.sha256(canonical_content.encode("utf-8")).hexdigest()[:16].upper()
        return f"SR-FP-{digest}"

    @classmethod
    def resolve_report_ref(
        cls,
        source_report_id: Optional[str],
        raw_text: str,
        reported_location: Optional[str] = None,
        reported_department: Optional[str] = None,
        source_type: SourceType = SourceType.NEAR_MISS,
        event_timestamp: Optional[datetime] = None,
    ) -> str:
        """Resolve authoritative report_ref from source ID or fallback to deterministic content fingerprint."""
        if source_report_id and source_report_id.strip():
            return source_report_id.strip()

        return cls.generate_fingerprint(
            raw_text=raw_text,
            reported_location=reported_location,
            reported_department=reported_department,
            source_type=source_type,
            event_timestamp=event_timestamp,
        )
