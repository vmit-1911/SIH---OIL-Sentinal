"""Single safety report SIF analysis endpoint."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.common import ErrorResponse
from app.schemas.report import (
    SingleReportAnalysisRequest,
    SingleReportAnalysisResponse,
)
from app.services.sif_analysis_service import SIFAnalysisService

router = APIRouter()


@router.post(
    "/sif/analyze",
    response_model=SingleReportAnalysisResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid report input or validation failure"},
        500: {"model": ErrorResponse, "description": "Internal processing or inference failure"},
    },
    summary="Analyze Single Report for SIF Potential",
    description=(
        "Deterministic, explainable evaluation of a safety observation narrative. "
        "Executes Context Extraction (Phase 1A), Multi-Factor SIF Screening (Phase 1B), "
        "and IOGP Report 459 Life-Saving Rules Mapping (Phase 1B), persisting results "
        "and returning audit-grade provenance and structured precursor data."
    ),
)
async def analyze_report(
    request: SingleReportAnalysisRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SingleReportAnalysisResponse:
    """Analyze single safety report for SIF potential, map to LSR, and persist."""
    service = SIFAnalysisService(db)
    analysis_result = await service.analyze_and_persist(request)
    return analysis_result.to_api_response()
