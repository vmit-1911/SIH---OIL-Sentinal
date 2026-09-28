"""FastAPI router for Phase 8 HSE Action & Recommendation Intelligence endpoints."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ActionNotFoundException,
    AssessmentNotFoundException,
    ConcentrationNotFoundException,
    InvalidStateTransitionException,
    PatternNotFoundException,
    ReportNotFoundException,
)
from app.db.session import get_db_session
from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
)
from app.schemas.action import (
    ActionAcknowledgeRequest,
    ActionGenerateRequest,
    ActionGenerateResponse,
    ActionListResponse,
    ActionStatusUpdateRequest,
    HSEActionRecommendationDTO,
)
from app.schemas.common import ErrorResponse
from app.services.action_service import HSEActionRecommendationService

router = APIRouter()


@router.get(
    "/sif/actions",
    response_model=ActionListResponse,
    summary="Query HSE Action Recommendations",
    description="Query and filter deterministic HSE action recommendations across operations with pagination.",
)
async def list_actions(
    source_type: Optional[ActionSourceType] = Query(None, description="Filter by source entity type"),
    source_id: Optional[str] = Query(None, description="Filter by source entity UUID/key"),
    status_filter: Optional[ActionStatus] = Query(None, alias="status", description="Filter by action status"),
    priority: Optional[ActionPriority] = Query(None, description="Filter by priority level"),
    action_category: Optional[ActionCategory] = Query(None, description="Filter by action category"),
    rule_id: Optional[str] = Query(None, description="Filter by generating rule ID"),
    lsr_code: Optional[str] = Query(None, description="Filter by associated LSR code"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    db: AsyncSession = Depends(get_db_session),
) -> ActionListResponse:
    """Retrieve filtered, paginated list of HSE action recommendations."""
    service = HSEActionRecommendationService(db)
    return await service.get_actions(
        source_type=source_type,
        source_id=source_id,
        status=status_filter,
        priority=priority,
        action_category=action_category,
        rule_id=rule_id,
        lsr_code=lsr_code,
        page=page,
        limit=limit,
    )


@router.get(
    "/sif/actions/{action_id}",
    response_model=HSEActionRecommendationDTO,
    responses={
        404: {"model": ErrorResponse, "description": "HSE action recommendation not found"},
    },
    summary="Get Action Recommendation Details",
    description="Retrieve full details, rationale, evidence links, and lifecycle metadata for an action recommendation.",
)
async def get_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> HSEActionRecommendationDTO:
    """Retrieve action recommendation by ID."""
    service = HSEActionRecommendationService(db)
    try:
        return await service.get_action_by_id(action_id)
    except ActionNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/reports/{report_id}/actions",
    response_model=List[HSEActionRecommendationDTO],
    responses={
        404: {"model": ErrorResponse, "description": "Safety report not found"},
    },
    summary="Get Actions for Safety Report",
    description="Retrieve all action recommendations associated with a specific safety report or its assessment.",
)
async def get_report_actions(
    report_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> List[HSEActionRecommendationDTO]:
    """Retrieve actions for a safety report."""
    service = HSEActionRecommendationService(db)
    try:
        return await service.get_actions_for_report(report_id)
    except ReportNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/assessments/{assessment_id}/actions",
    response_model=List[HSEActionRecommendationDTO],
    responses={
        404: {"model": ErrorResponse, "description": "SIF assessment not found"},
    },
    summary="Get Actions for SIF Assessment",
    description="Retrieve all action recommendations generated for a specific SIF assessment.",
)
async def get_assessment_actions(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> List[HSEActionRecommendationDTO]:
    """Retrieve actions for a SIF assessment."""
    service = HSEActionRecommendationService(db)
    try:
        return await service.get_actions_for_assessment(assessment_id)
    except AssessmentNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/patterns/{pattern_id}/actions",
    response_model=List[HSEActionRecommendationDTO],
    responses={
        404: {"model": ErrorResponse, "description": "Precursor pattern not found"},
    },
    summary="Get Actions for Precursor Pattern",
    description="Retrieve all action recommendations generated for a recurring precursor pattern.",
)
async def get_pattern_actions(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> List[HSEActionRecommendationDTO]:
    """Retrieve actions for a precursor pattern."""
    service = HSEActionRecommendationService(db)
    try:
        return await service.get_actions_for_pattern(pattern_id)
    except PatternNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/concentrations/{concentration_key}/actions",
    response_model=List[HSEActionRecommendationDTO],
    responses={
        404: {"model": ErrorResponse, "description": "Risk concentration not found"},
    },
    summary="Get Actions for Risk Concentration",
    description="Retrieve all action recommendations generated for a risk concentration finding.",
)
async def get_concentration_actions(
    concentration_key: str,
    db: AsyncSession = Depends(get_db_session),
) -> List[HSEActionRecommendationDTO]:
    """Retrieve actions for a risk concentration."""
    service = HSEActionRecommendationService(db)
    try:
        return await service.get_actions_for_concentration(concentration_key)
    except ConcentrationNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.post(
    "/sif/actions/generate",
    response_model=ActionGenerateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Target source entity not found"},
    },
    summary="Generate HSE Action Recommendations",
    description="Deterministically evaluates action rules against specified entity or all active intelligence and persists recommendations idempotently.",
)
async def generate_actions(
    request: ActionGenerateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ActionGenerateResponse:
    """Generate action recommendations on demand."""
    service = HSEActionRecommendationService(db)
    try:
        if request.assessment_id:
            dtos = await service.generate_actions_for_assessment(request.assessment_id, persist=request.persist)
            return ActionGenerateResponse(
                total_generated=len(dtos),
                new_actions=len(dtos),
                existing_actions=0,
                recommendations=dtos,
            )
        elif request.report_id:
            dtos = await service.generate_actions_for_report(request.report_id, persist=request.persist)
            return ActionGenerateResponse(
                total_generated=len(dtos),
                new_actions=len(dtos),
                existing_actions=0,
                recommendations=dtos,
            )
        elif request.pattern_id:
            dtos = await service.generate_actions_for_pattern(request.pattern_id, persist=request.persist)
            return ActionGenerateResponse(
                total_generated=len(dtos),
                new_actions=len(dtos),
                existing_actions=0,
                recommendations=dtos,
            )
        elif request.concentration_key:
            dtos = await service.generate_actions_for_concentration(request.concentration_key, persist=request.persist)
            return ActionGenerateResponse(
                total_generated=len(dtos),
                new_actions=len(dtos),
                existing_actions=0,
                recommendations=dtos,
            )
        else:
            return await service.generate_all_pending_actions(persist=request.persist)
    except (ReportNotFoundException, AssessmentNotFoundException, PatternNotFoundException, ConcentrationNotFoundException) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.post(
    "/sif/actions/{action_id}/acknowledge",
    response_model=HSEActionRecommendationDTO,
    responses={
        404: {"model": ErrorResponse, "description": "Action recommendation not found"},
    },
    summary="Acknowledge Action Recommendation",
    description="Transitions an action from OPEN to ACKNOWLEDGED state and records the acknowledging officer.",
)
async def acknowledge_action(
    action_id: UUID,
    request: ActionAcknowledgeRequest,
    db: AsyncSession = Depends(get_db_session),
) -> HSEActionRecommendationDTO:
    """Acknowledge action recommendation."""
    service = HSEActionRecommendationService(db)
    try:
        return await service.acknowledge_action(action_id, request)
    except ActionNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.post(
    "/sif/actions/{action_id}/status",
    response_model=HSEActionRecommendationDTO,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid status transition or missing rationale"},
        404: {"model": ErrorResponse, "description": "Action recommendation not found"},
    },
    summary="Update Action Status",
    description="Updates the lifecycle state (IN_PROGRESS, COMPLETED, DISMISSED) with deterministic validation and audit tracking.",
)
async def update_action_status(
    action_id: UUID,
    request: ActionStatusUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> HSEActionRecommendationDTO:
    """Update action status."""
    service = HSEActionRecommendationService(db)
    try:
        return await service.update_action_status(action_id, request)
    except ActionNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except InvalidStateTransitionException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
