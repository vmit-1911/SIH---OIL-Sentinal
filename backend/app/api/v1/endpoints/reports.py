"""Historical report retrieval and filtering endpoints."""

from math import ceil
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ReportNotFoundException
from app.db.session import get_db_session
from app.domain.enums import ActualOutcome, SIFClassification, SourceType, TriageStatus
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.report import ReportFilterParams, ReportListItemDTO
from app.services.report_service import ReportService

router = APIRouter()


@router.get(
    "/sif/reports",
    response_model=PaginatedResponse[ReportListItemDTO],
    summary="List & Filter Safety Reports",
    description="Query historical safety reports with pagination and filtering by SIF classification, source type, location, and triage status.",
)
async def list_reports(
    sif_classification: SIFClassification | None = Query(default=None),
    source_type: SourceType | None = Query(default=None),
    location: str | None = Query(default=None),
    triage_status: TriageStatus | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[ReportListItemDTO]:
    """Retrieve filtered list of safety reports."""
    service = ReportService(db)
    params = ReportFilterParams(
        sif_classification=sif_classification,
        source_type=source_type,
        location=location,
        triage_status=triage_status,
        page=page,
        page_size=page_size,
    )

    reports, total = await service.list_reports(params)
    total_pages = ceil(total / page_size) if total > 0 else 0

    items = [
        ReportListItemDTO(
            id=r.id,
            report_ref=r.report_ref,
            source_type=r.source_type,
            reported_location=r.reported_location,
            actual_severity=r.actual_severity,
            sif_classification=r.assessment.sif_classification if r.assessment else None,
            evidence_score=r.assessment.evidence_score if r.assessment else None,
            potential_severity=r.assessment.potential_severity if r.assessment else None,
            triage_status=r.assessment.triage_status if r.assessment else TriageStatus.AUTO_SCREENED,
            event_timestamp=r.event_timestamp,
            created_at=r.created_at,
        )
        for r in reports
    ]

    return PaginatedResponse[ReportListItemDTO](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/sif/reports/{report_id}",
    response_model=ReportListItemDTO,
    responses={
        404: {"model": ErrorResponse, "description": "Report not found"},
    },
    summary="Get Safety Report by ID",
    description="Retrieve safety report details and triage assessment by report ID.",
)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ReportListItemDTO:
    """Fetch report by UUID."""
    service = ReportService(db)
    report = await service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Safety report with ID '{report_id}' not found",
        )

    return ReportListItemDTO(
        id=report.id,
        report_ref=report.report_ref,
        source_type=report.source_type,
        reported_location=report.reported_location,
        actual_severity=report.actual_severity,
        sif_classification=report.assessment.sif_classification if report.assessment else None,
        evidence_score=report.assessment.evidence_score if report.assessment else None,
        potential_severity=report.assessment.potential_severity if report.assessment else None,
        triage_status=report.assessment.triage_status if report.assessment else TriageStatus.AUTO_SCREENED,
        event_timestamp=report.event_timestamp,
        created_at=report.created_at,
    )
