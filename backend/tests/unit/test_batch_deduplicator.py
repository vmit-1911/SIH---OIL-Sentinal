"""Unit tests for BatchDeduplicator."""

from datetime import datetime, timezone
from app.domain.batch.deduplicator import BatchDeduplicator
from app.domain.enums import SourceType


def test_deduplicator_source_id_resolution():
    """Verify resolve_report_ref preserves explicit source_report_id if provided."""
    ref = BatchDeduplicator.resolve_report_ref(
        source_report_id="INC-9999",
        raw_text="Worker observed without hard hat near pump house.",
        reported_location="Rig-04 Moran",
    )
    assert ref == "INC-9999"


def test_deduplicator_deterministic_fingerprint_generation():
    """Verify generate_fingerprint produces deterministic 16-hex SR-FP-<HEX> format."""
    dt = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
    fp1 = BatchDeduplicator.generate_fingerprint(
        raw_text="Gas release from flange during nitrogen purge.",
        reported_location="GGS-01",
        reported_department="Production",
        source_type=SourceType.NEAR_MISS,
        event_timestamp=dt,
    )
    fp2 = BatchDeduplicator.generate_fingerprint(
        raw_text="  Gas release from flange during nitrogen purge.  ",
        reported_location="GGS-01",
        reported_department="Production",
        source_type=SourceType.NEAR_MISS,
        event_timestamp=dt,
    )

    assert fp1.startswith("SR-FP-")
    assert len(fp1) == 6 + 16  # "SR-FP-" + 16 chars
    assert fp1 == fp2


def test_deduplicator_fingerprint_case_and_whitespace_insensitivity():
    """Verify fingerprint normalizes lowercase and whitespace variations."""
    fp_lower = BatchDeduplicator.generate_fingerprint(
        raw_text="crane hoist line snapped",
        reported_location="rig-04",
        source_type=SourceType.NEAR_MISS,
    )
    fp_upper = BatchDeduplicator.generate_fingerprint(
        raw_text="CRANE HOIST LINE SNAPPED",
        reported_location="RIG-04",
        source_type=SourceType.NEAR_MISS,
    )
    assert fp_lower == fp_upper


def test_deduplicator_distinct_content_different_fingerprints():
    """Verify distinct narrative contents produce unique fingerprints."""
    fp1 = BatchDeduplicator.generate_fingerprint(
        raw_text="Scaffolding collapsed on platform deck.",
    )
    fp2 = BatchDeduplicator.generate_fingerprint(
        raw_text="Forklift battery overheated in workshop.",
    )
    assert fp1 != fp2


def test_deduplicator_fallback_in_resolve_report_ref():
    """Verify resolve_report_ref falls back to fingerprint when source_report_id is None or empty."""
    ref_none = BatchDeduplicator.resolve_report_ref(
        source_report_id=None,
        raw_text="High voltage cable exposed on rig floor.",
        reported_location="Rig-07",
    )
    assert ref_none.startswith("SR-FP-")

    ref_empty = BatchDeduplicator.resolve_report_ref(
        source_report_id="   ",
        raw_text="High voltage cable exposed on rig floor.",
        reported_location="Rig-07",
    )
    assert ref_empty.startswith("SR-FP-")
    assert ref_none == ref_empty
