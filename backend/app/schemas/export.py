"""Pydantic schemas for Export Filters, Metadata, and Reporting (Phase 15)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExportFilterParams(BaseModel):
    """Common filter parameters for PDF and CSV export endpoints."""
    from_date: Optional[datetime] = Field(None, description="Start date filter (ISO 8601)")
    to_date: Optional[datetime] = Field(None, description="End date filter (ISO 8601)")
    location: Optional[str] = Field(None, description="Location substring filter")
    lsr_code: Optional[str] = Field(None, description="Life-Saving Rule filter")
    status: Optional[str] = Field(None, description="Action or Case status filter")
    priority: Optional[str] = Field(None, description="Action or Case priority filter")


class ExportMetadataDTO(BaseModel):
    """Metadata describing a generated export artifact."""
    export_type: str
    format: str
    generated_at: datetime
    record_count: int
    filter_summary: Dict[str, Any]
    filename: str
