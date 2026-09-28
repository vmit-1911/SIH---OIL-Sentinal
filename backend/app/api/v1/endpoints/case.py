"""FastAPI router for Phase 9 HSE Case Management and Operational Follow-up endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CaseClosureBlockedException,
    CaseNotFoundException,
    CaseSourceNotFoundException,
    DuplicateSourceAssociationException,
    InvalidStateTransitionException,
)
from app.db.session import get_db_session
from app.domain.enums import CasePriority, CaseStatus, CaseType
from app.schemas.case import (
    CaseListResponse,
    HSECaseAssignRequest,
    HSECaseCreateRequest,
    HSECaseDTO,
    HSECaseEventDTO,
    HSECaseReopenRequest,
    HSECaseSourceAttachRequest,
    HSECaseStatusUpdateRequest,
    HSECaseSummaryDTO,
    HSECaseUpdateRequest,
)
from app.schemas.common import ErrorResponse
from app.services.case_service import HSECaseManagementService

router = APIRouter()


@router.post(
    "/sif/cases",
    response_model=HSECaseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create HSE Investigation Case",
    description="Create an auditable HSE case/investigation grouping safety reports, assessments, patterns, concentrations, reviews, and actions.",
)
async def create_case(
    request: HSECaseCreateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> HSECaseDTO:
    """Explicitly create an HSE investigation case."""
    service = HSECaseManagementService(db)
    return await service.create_case(request)


@router.get(
    "/sif/cases",
    response_model=CaseListResponse,
    summary="List & Filter HSE Cases",
    description="Query and filter HSE cases by status, priority, type, owner, or date range with pagination.",
)
async def list_cases(
    status_filter: Optional[CaseStatus] = Query(None, alias="status", description="Filter by case lifecycle status"),
    priority: Optional[CasePriority] = Query(None, description="Filter by review priority"),
    case_type: Optional[CaseType] = Query(None, description="Filter by case type"),
    owner: Optional[str] = Query(None, description="Filter by assigned owner/investigator"),
    created_after: Optional[datetime] = Query(None, description="Filter cases created on or after timestamp"),
    created_before: Optional[datetime] = Query(None, description="Filter cases created on or before timestamp"),
    updated_after: Optional[datetime] = Query(None, description="Filter cases updated on or after timestamp"),
    updated_before: Optional[datetime] = Query(None, description="Filter cases updated on or before timestamp"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size limit"),
    db: AsyncSession = Depends(get_db_session),
) -> CaseListResponse:
    """Retrieve filtered, paginated list of HSE cases."""
    service = HSECaseManagementService(db)
    return await service.list_cases(
        status=status_filter,
        priority=priority,
        case_type=case_type,
        owner=owner,
        created_after=created_after,
        created_before=created_before,
        updated_after=updated_after,
        updated_before=updated_before,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/sif/cases/{case_id}",
    response_model=HSECaseDTO,
    summary="Get HSE Case Details",
    description="Retrieve full details and attached source intelligence for a specific HSE case by UUID.",
)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> HSECaseDTO:
    """Retrieve full details of an HSE case."""
    service = HSECaseManagementService(db)
    return await service.get_case(case_id)


@router.patch(
    "/sif/cases/{case_id}",
    response_model=HSECaseDTO,
    summary="Update HSE Case Metadata",
    description="Update mutable metadata (title, description, priority) of an HSE case.",
)
async def update_case(
    case_id: UUID,
    request: HSECaseUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> HSECaseDTO:
    """Update case title, description, or priority."""
    service = HSECaseManagementService(db)
    return await service.update_case(case_id, request)


@router.post(
    "/sif/cases/{case_id}/assign",
    response_model=HSECaseDTO,
    summary="Assign HSE Case Owner",
    description="Assign the HSE case to an investigator/owner and record an immutable audit event.",
)
async def assign_case(
    case_id: UUID,
    request: HSECaseAssignRequest,
    db: AsyncSession = Depends(get_db_session),
) -> HSECaseDTO:
    """Assign or reassign an HSE case."""
    service = HSECaseManagementService(db)
    return await service.assign_case(case_id, request)


@router.post(
    "/sif/cases/{case_id}/status",
    response_model=HSECaseDTO,
    summary="Update Case Lifecycle Status",
    description="Transition the operational lifecycle status of an HSE case according to valid state machine rules.",
)
async def update_case_status(
    case_id: UUID,
    request: HSECaseStatusUpdateRequest,
    require_actions_resolved: Optional[bool] = Query(None, description="Enforce that attached actions are COMPLETED/DISMISSED before closing (defaults to CASE_CLOSURE_REQUIRES_ACTION_RESOLUTION)"),
    db: AsyncSession = Depends(get_db_session),
) -> HSECaseDTO:
    """Advance or transition case lifecycle state."""
    service = HSECaseManagementService(db)
    return await service.update_case_status(
        case_id=case_id,
        request=request,
        require_actions_resolved=require_actions_resolved,
    )


@router.post(
    "/sif/cases/{case_id}/sources",
    response_model=HSECaseDTO,
    summary="Attach Source Intelligence to Case",
    description="Attach an authoritative safety report, assessment, pattern, concentration, review, or action to the case.",
)
async def attach_source(
    case_id: UUID,
    request: HSECaseSourceAttachRequest,
    db: AsyncSession = Depends(get_db_session),
) -> HSECaseDTO:
    """Attach a source reference to the HSE case."""
    service = HSECaseManagementService(db)
    return await service.attach_source(case_id, request)


@router.delete(
    "/sif/cases/{case_id}/sources/{source_id}",
    response_model=HSECaseDTO,
    summary="Detach Source Reference from Case",
    description="Detach an associated source intelligence reference from the HSE case and record an audit event.",
)
async def detach_source(
    case_id: UUID,
    source_id: str,
    actor_id: str = Query("system_auditor", description="Actor initiating detachment"),
    rationale: Optional[str] = Query(None, description="Optional detachment justification"),
    db: AsyncSession = Depends(get_db_session),
) -> HSECaseDTO:
    """Detach a source from the HSE case."""
    service = HSECaseManagementService(db)
    return await service.detach_source(
        case_id=case_id,
        source_id_or_assoc_id=source_id,
        actor_id=actor_id,
        rationale=rationale,
    )


@router.get(
    "/sif/cases/{case_id}/timeline",
    response_model=List[HSECaseEventDTO],
    summary="Get Case Audit Event Timeline",
    description="Retrieve the complete append-only chronological history of lifecycle events and source mutations for an HSE case.",
)
async def get_case_timeline(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> List[HSECaseEventDTO]:
    """Retrieve chronologically ordered audit events for a case."""
    service = HSECaseManagementService(db)
    return await service.get_case_timeline(case_id)


@router.get(
    "/sif/cases/{case_id}/summary",
    response_model=HSECaseSummaryDTO,
    summary="Get Case Summary Metrics",
    description="Retrieve deterministic aggregate counts and statistics for an HSE case.",
)
async def get_case_summary(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> HSECaseSummaryDTO:
    """Compute and retrieve aggregate case statistics."""
    service = HSECaseManagementService(db)
    return await service.get_case_summary(case_id)


@router.post(
    "/sif/cases/{case_id}/reopen",
    response_model=HSECaseDTO,
    summary="Reopen Closed HSE Case",
    description="Reopen a previously CLOSED HSE case with mandatory justification.",
)
async def reopen_case(
    case_id: UUID,
    request: HSECaseReopenRequest,
    db: AsyncSession = Depends(get_db_session),
) -> HSECaseDTO:
    """Reopen a closed HSE case."""
    service = HSECaseManagementService(db)
    return await service.reopen_case(case_id, request)
