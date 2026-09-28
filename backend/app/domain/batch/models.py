"""Domain models and DTOs for batch ingestion and processing."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.domain.enums import ActualOutcome, BatchRowStatus, SourceType


@dataclass
class ParsedReportRow:
    """Normalized DTO produced by a batch parser for an individual row."""
    row_number: int
    raw_text: str
    source_report_id: Optional[str] = None
    source_type: SourceType = SourceType.NEAR_MISS
    reported_location: Optional[str] = None
    reported_department: Optional[str] = None
    actual_severity: ActualOutcome = ActualOutcome.NO_INJURY
    actual_outcome_details: Optional[str] = None
    event_timestamp: Optional[datetime] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    ignored_columns: List[str] = field(default_factory=list)


@dataclass
class BatchRowResult:
    """Deterministic evaluation outcome for an input row during batch processing."""
    row_number: int
    status: BatchRowStatus
    report_id: Optional[uuid.UUID] = None
    report_ref: Optional[str] = None
    field_name: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class BatchIngestionSummary:
    """Mathematical reconciliation summary for a batch job."""
    total_rows: int = 0
    accepted_rows: int = 0
    rejected_rows: int = 0
    duplicate_rows: int = 0
    processed_rows: int = 0
    failed_processing_rows: int = 0
    sif_count: int = 0

    def validate_invariants(self) -> bool:
        """Verify mathematical integrity of counters."""
        ingestion_balanced = self.total_rows == (self.accepted_rows + self.rejected_rows + self.duplicate_rows)
        processing_balanced = self.accepted_rows == (self.processed_rows + self.failed_processing_rows)
        sif_bounded = self.sif_count <= self.processed_rows
        no_negative = all(
            c >= 0 for c in (
                self.total_rows,
                self.accepted_rows,
                self.rejected_rows,
                self.duplicate_rows,
                self.processed_rows,
                self.failed_processing_rows,
                self.sif_count,
            )
        )
        return ingestion_balanced and processing_balanced and sif_bounded and no_negative
