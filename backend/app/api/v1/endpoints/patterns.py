"""Precursor pattern and systemic cluster endpoints."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.domain.enums import PatternStatus
from app.schemas.common import ErrorResponse
from app.schemas.pattern import (
    PatternDiscoveryResponse,
    PrecursorPatternDTO,
    PrecursorPatternListResponse,
)
from app.services.pattern_discovery_service import PatternDiscoveryService
from app.services.pattern_service import PatternService

router = APIRouter()


@router.get(
    "/sif/patterns",
    response_model=PrecursorPatternListResponse,
    summary="List Recurring Precursor Patterns",
    description="Retrieves discovered recurring precursor patterns across operations and operating sites.",
)
async def list_patterns(
    status_filter: Optional[PatternStatus] = Query(
        None,
        alias="status",
        description="Filter by pattern status: CANDIDATE, ACTIVE, ARCHIVED",
    ),
    lsr_code: Optional[str] = Query(
        None,
        description="Filter by primary IOGP Life-Saving Rule code",
    ),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db_session),
) -> PrecursorPatternListResponse:
    """Retrieve identified recurring precursor clusters."""
    service = PatternService(db)
    patterns, total = await service.list_patterns(
        status=status_filter,
        lsr_code=lsr_code,
        limit=limit,
        offset=offset,
    )
    return PrecursorPatternListResponse(
        total_patterns=total,
        patterns=patterns,
    )


@router.get(
    "/sif/patterns/{pattern_id}",
    response_model=PrecursorPatternDTO,
    responses={
        404: {"model": ErrorResponse, "description": "Precursor pattern not found"},
    },
    summary="Get Precursor Pattern Details",
    description="Retrieve details, representative precursor, affected locations, and report associations for a specific pattern.",
)
async def get_pattern_detail(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> PrecursorPatternDTO:
    """Retrieve details of an individual precursor pattern."""
    service = PatternService(db)
    pattern = await service.get_pattern_by_id(pattern_id)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Precursor pattern '{pattern_id}' was not found.",
        )
    return pattern


@router.post(
    "/sif/patterns/discover",
    response_model=PatternDiscoveryResponse,
    summary="Trigger Recurring Precursor Pattern Discovery",
    description="Executes deterministic grouping and recurrence evaluation across all SIF assessments.",
)
async def trigger_pattern_discovery(
    min_report_count: Optional[int] = Query(
        None,
        ge=2,
        description="Override minimum report count engineering parameter (default: 3)",
    ),
    similarity_threshold: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Override candidate similarity threshold parameter (default: 0.65)",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> PatternDiscoveryResponse:
    """Execute on-demand precursor pattern discovery run."""
    discovery_service = PatternDiscoveryService(db)
    result = await discovery_service.discover_patterns(
        min_report_count=min_report_count,
        threshold=similarity_threshold,
    )
    return result
