"""Pydantic schemas for batch upload, status tracking, row-level error reporting, and retries."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.enums import BatchJobStatus


class BatchUploadItem(BaseModel):
    """Single report item within a JSON batch upload request."""
    report_ref: Optional[str] = None
    raw_text: str = Field(..., min_length=10)
    source_type: str = "NEAR_MISS"
    reported_location: Optional[str] = None
    reported_department: Optional[str] = None
    actual_severity: str = "NO_INJURY"
    event_timestamp: Optional[datetime] = None


class BatchUploadRequest(BaseModel):
    """Batch upload request containing multiple safety reports."""
    reports: List[BatchUploadItem] = Field(..., min_length=1, max_length=10000)


class BatchUploadResponse(BaseModel):
    """Response returned upon accepting a batch for asynchronous processing."""
    batch_id: UUID
    status: BatchJobStatus = BatchJobStatus.PENDING
    filename: str
    import_schema_version: str = "OIL_SAFETY_REPORT_CSV_V1"
    total_records: int = 0
    created_at: datetime
    status_check_url: str


class BatchSummaryDTO(BaseModel):
    """Summary metrics of processed batch."""
    top_life_saving_rules: List[Dict[str, Any]] = Field(default_factory=list)
    location_concentrations: List[Dict[str, Any]] = Field(default_factory=list)


class BatchStatusResponse(BaseModel):
    """Status, operational progress, and counter reconciliation for a batch processing job."""
    batch_id: UUID
    status: BatchJobStatus
    source_filename: str
    import_schema_version: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    duplicate_rows: int
    processed_rows: int
    failed_processing_rows: int
    sif_count: int = 0
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_summary: Optional[Dict[str, Any]] = None
    results_summary: Optional[Dict[str, Any]] = None

    # Backward-compatible fields
    @property
    def total_records(self) -> int:
        return self.total_rows

    @property
    def processed_records(self) -> int:
        return self.processed_rows

    @property
    def error_count(self) -> int:
        return self.rejected_rows + self.failed_processing_rows


class BatchRowErrorDTO(BaseModel):
    """Row-level error detail during batch ingestion or processing."""
    id: UUID
    row_number: int
    field_name: Optional[str] = None
    error_code: str
    error_message: str
    created_at: datetime


class BatchErrorListResponse(BaseModel):
    """Paginated listing of row-level errors for an individual batch job."""
    batch_id: UUID
    total_errors: int
    errors: List[BatchRowErrorDTO] = Field(default_factory=list)
    limit: int = 50
    offset: int = 0


class BatchRetryResponse(BaseModel):
    """Response returned when triggering a safe retry on failed or unanalyzed reports."""
    batch_id: UUID
    status: BatchJobStatus
    retried_reports_count: int
    message: str
