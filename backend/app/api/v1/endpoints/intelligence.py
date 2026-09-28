"""HSE intelligence, explainability, evidence graph, and investigation context endpoints."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AssessmentNotFoundException,
    ConcentrationNotFoundException,
    PatternNotFoundException,
    ReportNotFoundException,
)
from app.db.session import get_db_session
from app.schemas.common import ErrorResponse
from app.schemas.intelligence import (
    AssessmentPatternResponse,
    AssessmentSimilarityResponse,
    ConcentrationEvidenceResponse,
    PatternEvidenceResponse,
    ReportEvidenceListResponse,
    ScreeningExplanationDTO,
    SIFInvestigationContextResponse,
)
from app.services.evidence_explanation_service import EvidenceExplanationService

router = APIRouter()


@router.get(
    "/sif/reports/{report_id}/evidence",
    response_model=ReportEvidenceListResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Safety report not found"},
    },
    summary="Get Safety Report Evidence Items",
    description="Extracts and returns normalized evidence items with character offsets, normalized concepts, provenance rules, and negation status from the narrative.",
)
async def get_report_evidence(
    report_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ReportEvidenceListResponse:
    """Retrieve all extracted factual evidence spans for a safety report."""
    service = EvidenceExplanationService(db)
    try:
        return await service.get_report_evidence(report_id)
    except ReportNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/reports/{report_id}/explanation",
    response_model=ScreeningExplanationDTO,
    responses={
        404: {"model": ErrorResponse, "description": "Report or SIF assessment not found"},
    },
    summary="Get SIF Screening Explanation",
    description="Returns structured explainability detailing factor breakdowns, triggered screening rules, precursor field provenance, and LSR justifications.",
)
async def get_report_explanation(
    report_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ScreeningExplanationDTO:
    """Retrieve structured explanation and factor breakdown for an assessment."""
    service = EvidenceExplanationService(db)
    try:
        return await service.get_screening_explanation(report_id)
    except (ReportNotFoundException, AssessmentNotFoundException) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/reports/{report_id}/investigation-context",
    response_model=SIFInvestigationContextResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Safety report not found"},
    },
    summary="Get Consolidated HSE Investigation Context",
    description="Aggregates the complete 10-dimension investigation context: Report, AI Assessment, Evidence Items, Screening Reasoning, Precursor 7D, Similar Reports, Recurring Pattern, Risk Concentrations, Review Decisions, and Audit Trail.",
)
async def get_investigation_context(
    report_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> SIFInvestigationContextResponse:
    """Retrieve full consolidated HSE investigation context for a report."""
    service = EvidenceExplanationService(db)
    try:
        return await service.get_investigation_context(report_id)
    except ReportNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/assessments/{assessment_id}/evidence",
    response_model=ReportEvidenceListResponse,
    responses={
        404: {"model": ErrorResponse, "description": "SIF assessment not found"},
    },
    summary="Get SIF Assessment Evidence Items",
    description="Retrieves factual evidence spans supporting a specific SIF assessment.",
)
async def get_assessment_evidence(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ReportEvidenceListResponse:
    """Retrieve factual evidence spans supporting an individual assessment."""
    service = EvidenceExplanationService(db)
    try:
        return await service.get_assessment_evidence(assessment_id)
    except (AssessmentNotFoundException, ReportNotFoundException) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/assessments/{assessment_id}/similarity",
    response_model=AssessmentSimilarityResponse,
    responses={
        404: {"model": ErrorResponse, "description": "SIF assessment not found"},
    },
    summary="Get Historically Similar Reports",
    description="Evaluates pairwise multi-modal similarity (structured precursor + dense embedding) between the target assessment and other historical reports.",
)
async def get_assessment_similarity(
    assessment_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Maximum similar reports to return"),
    threshold: float = Query(0.50, ge=0.0, le=1.0, description="Minimum hybrid similarity threshold"),
    db: AsyncSession = Depends(get_db_session),
) -> AssessmentSimilarityResponse:
    """Retrieve historically similar reports with dimension alignment breakdown."""
    service = EvidenceExplanationService(db)
    try:
        return await service.get_assessment_similar_reports(
            assessment_id=assessment_id,
            limit=limit,
            threshold=threshold,
        )
    except (AssessmentNotFoundException, ReportNotFoundException) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/assessments/{assessment_id}/pattern",
    response_model=AssessmentPatternResponse,
    responses={
        404: {"model": ErrorResponse, "description": "SIF assessment not found"},
    },
    summary="Get Associated Recurring Precursor Pattern",
    description="Retrieves the recurring pattern cluster associated with this assessment and lists co-member report IDs.",
)
async def get_assessment_pattern(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> AssessmentPatternResponse:
    """Retrieve associated precursor pattern and co-member IDs."""
    service = EvidenceExplanationService(db)
    try:
        return await service.get_assessment_pattern(assessment_id)
    except AssessmentNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/patterns/{pattern_id}/evidence",
    response_model=PatternEvidenceResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Precursor pattern not found"},
    },
    summary="Get Pattern Evidence & Supporting Reports",
    description="Provides complete traceability for a recurring precursor pattern back to its supporting safety reports, assessments, and narratives.",
)
async def get_pattern_evidence(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> PatternEvidenceResponse:
    """Retrieve supporting reports, temporal distributions, and cohesion evidence for a pattern."""
    service = EvidenceExplanationService(db)
    try:
        return await service.get_pattern_evidence(pattern_id)
    except PatternNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)


@router.get(
    "/sif/concentrations/{concentration_key}/evidence",
    response_model=ConcentrationEvidenceResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Risk concentration not found"},
    },
    summary="Get Concentration Evidence & Supporting Reports",
    description="Provides explainable evidence, temporal trend classifications, and underlying reports for a SIF risk concentration finding.",
)
async def get_concentration_evidence(
    concentration_key: str,
    db: AsyncSession = Depends(get_db_session),
) -> ConcentrationEvidenceResponse:
    """Retrieve underlying reports and temporal metrics for a risk concentration finding."""
    service = EvidenceExplanationService(db)
    try:
        return await service.get_concentration_evidence(concentration_key)
    except ConcentrationNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
