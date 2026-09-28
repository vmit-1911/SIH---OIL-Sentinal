"""Common reusable schema components."""

from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standardized error response body."""
    error: str = Field(..., description="Error category or summary")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[dict] = Field(default=None, description="Detailed validation or context error map")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic pagination wrapper for list endpoints."""
    items: List[T]
    total: int = Field(..., ge=0, description="Total number of items available")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
