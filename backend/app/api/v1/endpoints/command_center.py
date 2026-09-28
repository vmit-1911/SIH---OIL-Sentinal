"""FastAPI router for Phase 10 HSE Command Center / Operational Intelligence API endpoints."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
    CasePriority,
    CaseStatus,
    CaseType,
    ConcentrationDimension,
    ObservedTrend,
)
from app.schemas.command_center import (
    ActionOverviewDTO,
    CaseOverviewDTO,
    CommandCenterOverview,
    ConcentrationOverviewDTO,
    InvestigationSnapshotDTO,
    LSROverviewDTO,
    PrecursorOverviewDTO,
    ReviewQueueOverviewDTO,
    SIFOverviewDTO,
)
from app.schemas.common import ErrorResponse
from app.services.command_center_service import CommandCenterService

router = APIRouter()


def _validate_date_range(from_date: Optional[datetime], to_date: Optional[datetime]) -> None:
    """Validate that from_date is not after to_date."""
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date range: 'from_date' cannot be greater than 'to_date'.",
        )


@router.get(
    "/sif/command-center/overview",
    response_model=CommandCenterOverview,
    summary="Command Center Executive Overview",
    description="High-level descriptive overview of SIF operational activity, assessments, reviews, actions, and cases.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date range or filter parameter"},
    },
)
async def get_command_center_overview(
    from_date: Optional[datetime] = Query(None, description="Filter records created on or after this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter records created on or before this timestamp"),
    location: Optional[str] = Query(None, description="Filter by operational location string"),
    db: AsyncSession = Depends(get_db_session),
) -> CommandCenterOverview:
    _validate_date_range(from_date, to_date)
    service = CommandCenterService(db)
    return await service.get_overview(from_date=from_date, to_date=to_date, location=location)


@router.get(
    "/sif/command-center/sif",
    response_model=SIFOverviewDTO,
    summary="SIF Assessment & Severity Overview",
    description="Descriptive breakdown of SIF assessments, severities, LSR distributions, and monthly trends.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date range or filter parameter"},
    },
)
async def get_sif_overview(
    from_date: Optional[datetime] = Query(None, description="Filter records created on or after this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter records created on or before this timestamp"),
    location: Optional[str] = Query(None, description="Filter by operational location string"),
    lsr_code: Optional[str] = Query(None, description="Filter by Life-Saving Rule code"),
    db: AsyncSession = Depends(get_db_session),
) -> SIFOverviewDTO:
    _validate_date_range(from_date, to_date)
    service = CommandCenterService(db)
    return await service.get_sif_overview(from_date=from_date, to_date=to_date, location=location, lsr_code=lsr_code)


@router.get(
    "/sif/command-center/precursors",
    response_model=PrecursorOverviewDTO,
    summary="Precursor Pattern Intelligence Overview",
    description="Overview of recurring precursor patterns, top hazards, barrier failures, activities, and locations.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date range or filter parameter"},
    },
)
async def get_precursor_overview(
    from_date: Optional[datetime] = Query(None, description="Filter records created on or after this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter records created on or before this timestamp"),
    location: Optional[str] = Query(None, description="Filter by affected location string"),
    lsr_code: Optional[str] = Query(None, description="Filter by Life-Saving Rule code"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of patterns to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db_session),
) -> PrecursorOverviewDTO:
    _validate_date_range(from_date, to_date)
    service = CommandCenterService(db)
    return await service.get_precursor_overview(
        from_date=from_date,
        to_date=to_date,
        location=location,
        lsr_code=lsr_code,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/sif/command-center/concentrations",
    response_model=ConcentrationOverviewDTO,
    summary="Risk Concentration Findings Overview",
    description="Expose Phase 3 risk concentration intelligence across the 6 canonical dimensions.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date range or filter parameter"},
    },
)
async def get_concentration_overview(
    from_date: Optional[datetime] = Query(None, description="Filter records created on or after this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter records created on or before this timestamp"),
    dimension: Optional[ConcentrationDimension] = Query(None, description="Filter by canonical concentration dimension"),
    trend: Optional[ObservedTrend] = Query(None, description="Filter by observed temporal trend"),
    location: Optional[str] = Query(None, description="Filter by location string"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of concentrations to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db_session),
) -> ConcentrationOverviewDTO:
    _validate_date_range(from_date, to_date)
    service = CommandCenterService(db)
    return await service.get_concentration_overview(
        from_date=from_date,
        to_date=to_date,
        dimension_type=dimension,
        trend=trend,
        location=location,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/sif/command-center/lsr",
    response_model=LSROverviewDTO,
    summary="Life-Saving Rules Distribution Overview",
    description="Descriptive statistics and counts across all configured Life-Saving Rules.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date range or filter parameter"},
    },
)
async def get_lsr_overview(
    from_date: Optional[datetime] = Query(None, description="Filter records created on or after this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter records created on or before this timestamp"),
    location: Optional[str] = Query(None, description="Filter by location string"),
    lsr_code: Optional[str] = Query(None, description="Filter to a specific LSR rule code"),
    db: AsyncSession = Depends(get_db_session),
) -> LSROverviewDTO:
    _validate_date_range(from_date, to_date)
    service = CommandCenterService(db)
    return await service.get_lsr_overview(from_date=from_date, to_date=to_date, location=location, lsr_code=lsr_code)


@router.get(
    "/sif/command-center/actions",
    response_model=ActionOverviewDTO,
    summary="HSE Action Recommendations Overview",
    description="Overview of Phase 8 HSE action recommendations by status, priority, category, and age.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date range or filter parameter"},
    },
)
async def get_action_overview(
    from_date: Optional[datetime] = Query(None, description="Filter records created on or after this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter records created on or before this timestamp"),
    status_filter: Optional[ActionStatus] = Query(None, alias="status", description="Filter by action status"),
    priority: Optional[ActionPriority] = Query(None, description="Filter by action priority"),
    category: Optional[ActionCategory] = Query(None, description="Filter by action category"),
    source_type: Optional[ActionSourceType] = Query(None, description="Filter by originating source type"),
    db: AsyncSession = Depends(get_db_session),
) -> ActionOverviewDTO:
    _validate_date_range(from_date, to_date)
    service = CommandCenterService(db)
    return await service.get_action_overview(
        from_date=from_date,
        to_date=to_date,
        status=status_filter,
        priority=priority,
        category=category,
        source_type=source_type,
    )


@router.get(
    "/sif/command-center/cases",
    response_model=CaseOverviewDTO,
    summary="HSE Investigation Cases Overview",
    description="Overview of Phase 9 HSE cases by status, priority, type, owner, and recently updated items.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date range or filter parameter"},
    },
)
async def get_case_overview(
    from_date: Optional[datetime] = Query(None, description="Filter records created on or after this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter records created on or before this timestamp"),
    status_filter: Optional[CaseStatus] = Query(None, alias="status", description="Filter by case status"),
    priority: Optional[CasePriority] = Query(None, description="Filter by case priority"),
    case_type: Optional[CaseType] = Query(None, description="Filter by case type"),
    owner: Optional[str] = Query(None, description="Filter by case owner"),
    db: AsyncSession = Depends(get_db_session),
) -> CaseOverviewDTO:
    _validate_date_range(from_date, to_date)
    service = CommandCenterService(db)
    return await service.get_case_overview(
        from_date=from_date,
        to_date=to_date,
        status=status_filter,
        priority=priority,
        case_type=case_type,
        owner=owner,
    )


@router.get(
    "/sif/command-center/reviews",
    response_model=ReviewQueueOverviewDTO,
    summary="Human Triage & Review Queue Overview",
    description="Overview of Phase 5 human review workload, decision breakdowns, feedback categories, and age.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid date range or filter parameter"},
    },
)
async def get_review_queue_overview(
    from_date: Optional[datetime] = Query(None, description="Filter records created on or after this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter records created on or before this timestamp"),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewQueueOverviewDTO:
    _validate_date_range(from_date, to_date)
    service = CommandCenterService(db)
    return await service.get_review_queue_overview(from_date=from_date, to_date=to_date)


@router.get(
    "/sif/command-center/investigation-snapshot",
    response_model=InvestigationSnapshotDTO,
    summary="Multi-Phase Investigation Snapshot",
    description="Compact operational chain linking related reports, assessments, patterns, concentrations, reviews, actions, and cases.",
)
async def get_investigation_snapshot(
    report_ref: Optional[str] = Query(None, description="Target safety report reference (e.g. OIL-REP-001)"),
    case_key: Optional[str] = Query(None, description="Target HSE case key (e.g. CASE-01J...)"),
    pattern_code: Optional[str] = Query(None, description="Target precursor pattern code"),
    concentration_key: Optional[str] = Query(None, description="Target risk concentration key"),
    db: AsyncSession = Depends(get_db_session),
) -> InvestigationSnapshotDTO:
    service = CommandCenterService(db)
    return await service.get_investigation_snapshot(
        report_ref=report_ref,
        case_key=case_key,
        pattern_code=pattern_code,
        concentration_key=concentration_key,
    )
