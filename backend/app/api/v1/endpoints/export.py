"""REST API Endpoints for PDF & CSV Intelligence Exports (Phase 15)."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CaseNotFoundException, ReportNotFoundException
from app.db.models.action import HSEActionRecommendation
from app.db.models.case import HSECase, HSECaseEvent, HSECaseSourceAssociation
from app.db.session import get_db_session
from app.domain.enums import CaseSourceType
from app.services.case_service import HSECaseManagementService
from app.services.command_center_service import CommandCenterService
from app.services.csv_export_service import CSVExportService
from app.services.pdf_export_service import PDFExportService
from app.services.report_service import ReportService

router = APIRouter(prefix="/sif/export", tags=["Intelligence Exports"])


@router.get(
    "/executive-brief/pdf",
    summary="Export Executive Safety Brief PDF",
    description="Generates an executive-ready PDF brief summarizing KPIs, SIF distribution, top recurring precursors, and risk concentrations.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Generated Executive Safety Brief PDF stream",
        }
    },
)
async def export_executive_brief_pdf(
    from_date: Optional[datetime] = Query(None, description="Start date filter (ISO 8601)"),
    to_date: Optional[datetime] = Query(None, description="End date filter (ISO 8601)"),
    location: Optional[str] = Query(None, description="Location filter"),
    lsr_code: Optional[str] = Query(None, description="Life-Saving Rule code filter"),
    session: AsyncSession = Depends(get_db_session),
):
    """Generate and stream Executive Safety Brief PDF."""
    cc_service = CommandCenterService(session)
    pdf_service = PDFExportService()

    overview = await cc_service.get_overview(from_date=from_date, to_date=to_date, location=location)
    sif_overview = await cc_service.get_sif_overview(from_date=from_date, to_date=to_date, location=location, lsr_code=lsr_code)
    precursor_overview = await cc_service.get_precursor_overview(from_date=from_date, to_date=to_date, location=location, lsr_code=lsr_code)
    concentration_overview = await cc_service.get_concentration_overview(from_date=from_date, to_date=to_date, location=location)
    action_overview = await cc_service.get_action_overview(from_date=from_date, to_date=to_date)
    lsr_overview = await cc_service.get_lsr_overview(from_date=from_date, to_date=to_date, location=location, lsr_code=lsr_code)

    filter_dict = {}
    if location:
        filter_dict["location"] = location
    if from_date:
        filter_dict["from_date"] = from_date.strftime("%Y-%m-%d")
    if to_date:
        filter_dict["to_date"] = to_date.strftime("%Y-%m-%d")

    pdf_bytes = pdf_service.generate_executive_safety_brief_pdf(
        overview=overview,
        sif_overview=sif_overview,
        precursor_overview=precursor_overview,
        concentration_overview=concentration_overview,
        action_overview=action_overview,
        lsr_overview=lsr_overview,
        filter_params=filter_dict,
    )

    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"OIL_SIF_Executive_Safety_Brief_{now_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


@router.get(
    "/dossier/{report_id}/pdf",
    summary="Export SIF Incident Investigation Dossier PDF",
    description="Generates a comprehensive investigation dossier PDF for a specific safety report and SIF assessment.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Generated Incident Investigation Dossier PDF stream",
        },
        404: {"description": "Report not found"},
    },
)
async def export_incident_dossier_pdf(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Generate and stream Incident Dossier PDF."""
    report_service = ReportService(session)
    report = await report_service.get_report_by_id(report_id)
    if not report:
        raise ReportNotFoundException(f"Safety report with ID '{report_id}' was not found.")

    # Fetch associated actions
    stmt_actions = select(HSEActionRecommendation).where(
        HSEActionRecommendation.source_id == str(report.id)
    )
    act_res = await session.execute(stmt_actions)
    related_actions = list(act_res.scalars().all())

    # Fetch associated case if any
    stmt_cases = (
        select(HSECase)
        .join(HSECaseSourceAssociation, HSECaseSourceAssociation.case_id == HSECase.id)
        .where(HSECaseSourceAssociation.source_id == str(report.id))
    )
    case_res = await session.execute(stmt_cases)
    related_case = case_res.scalars().first()

    pdf_service = PDFExportService()
    pdf_bytes = pdf_service.generate_incident_dossier_pdf(
        report=report,
        assessment=report.assessment,
        lsr_mappings=report.lsr_mappings,
        related_actions=related_actions,
        related_case=related_case,
    )

    report_ref = report.report_ref or str(report.id)[:8].upper()
    filename = f"OIL_SIF_Incident_Dossier_{report_ref}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


@router.get(
    "/case/{case_id}/pdf",
    summary="Export HSE Case Dossier PDF",
    description="Generates a formal investigation case dossier PDF with timeline and attached corrective actions.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Generated HSE Case Dossier PDF stream",
        },
        404: {"description": "Case not found"},
    },
)
async def export_case_dossier_pdf(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Generate and stream HSE Case Dossier PDF."""
    stmt_case = select(HSECase).where(HSECase.id == case_id)
    case_res = await session.execute(stmt_case)
    case = case_res.scalar_one_or_none()
    if not case:
        raise CaseNotFoundException(f"HSE Case with ID '{case_id}' was not found.")

    # Fetch events, actions, sources
    stmt_events = select(HSECaseEvent).where(HSECaseEvent.case_id == case_id).order_by(HSECaseEvent.created_at.asc())
    ev_res = await session.execute(stmt_events)
    events = list(ev_res.scalars().all())

    stmt_sources = select(HSECaseSourceAssociation).where(HSECaseSourceAssociation.case_id == case_id)
    src_res = await session.execute(stmt_sources)
    sources = list(src_res.scalars().all())

    action_sources = [s.source_id for s in sources if s.source_type == CaseSourceType.ACTION]
    actions = []
    if action_sources:
        act_uids = []
        act_keys = []
        for s_id in action_sources:
            try:
                act_uids.append(uuid.UUID(s_id))
            except ValueError:
                act_keys.append(s_id)
        conditions = []
        if act_uids:
            conditions.append(HSEActionRecommendation.id.in_(act_uids))
        if act_keys:
            conditions.append(HSEActionRecommendation.action_key.in_(act_keys))
        if conditions:
            stmt_actions = select(HSEActionRecommendation).where(or_(*conditions))
            act_res = await session.execute(stmt_actions)
            actions = list(act_res.scalars().all())

    pdf_service = PDFExportService()
    pdf_bytes = pdf_service.generate_case_dossier_pdf(
        case=case,
        events=events,
        actions=actions,
        sources=sources,
    )

    case_ref = str(case.id)[:8].upper()
    filename = f"OIL_HSE_Case_Dossier_{case_ref}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


@router.get(
    "/assessments/csv",
    summary="Export SIF Assessments CSV",
    description="Exports historical safety reports and SIF screening assessments to a downloadable CSV dataset.",
)
async def export_assessments_csv(
    from_date: Optional[datetime] = Query(None, description="Filter start date"),
    to_date: Optional[datetime] = Query(None, description="Filter end date"),
    location: Optional[str] = Query(None, description="Location filter"),
    session: AsyncSession = Depends(get_db_session),
):
    """Export assessments to CSV stream."""
    csv_service = CSVExportService(session)
    csv_data = await csv_service.export_assessments_csv(from_date=from_date, to_date=to_date, location=location)

    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"OIL_SIF_Assessments_{now_str}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get(
    "/actions/csv",
    summary="Export HSE Actions CSV",
    description="Exports HSE action recommendations and lifecycle resolution data to CSV.",
)
async def export_actions_csv(
    status_filter: Optional[str] = Query(None, alias="status", description="Status filter"),
    priority_filter: Optional[str] = Query(None, alias="priority", description="Priority filter"),
    session: AsyncSession = Depends(get_db_session),
):
    """Export actions to CSV stream."""
    csv_service = CSVExportService(session)
    csv_data = await csv_service.export_actions_csv(status=status_filter, priority=priority_filter)

    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"OIL_HSE_Actions_{now_str}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get(
    "/concentrations/csv",
    summary="Export Risk Concentrations CSV",
    description="Exports multi-dimensional risk concentration clusters and observed trend ratios to CSV.",
)
async def export_concentrations_csv(
    dimension: Optional[str] = Query(None, description="Dimension filter"),
    trend: Optional[str] = Query(None, description="Trend filter"),
    session: AsyncSession = Depends(get_db_session),
):
    """Export concentrations to CSV stream."""
    csv_service = CSVExportService(session)
    csv_data = await csv_service.export_concentrations_csv(dimension=dimension, trend=trend)

    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"OIL_Risk_Concentrations_{now_str}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get(
    "/cases/csv",
    summary="Export HSE Cases CSV",
    description="Exports HSE formal investigation cases to CSV.",
)
async def export_cases_csv(
    status_filter: Optional[str] = Query(None, alias="status", description="Status filter"),
    priority_filter: Optional[str] = Query(None, alias="priority", description="Priority filter"),
    session: AsyncSession = Depends(get_db_session),
):
    """Export cases to CSV stream."""
    csv_service = CSVExportService(session)
    csv_data = await csv_service.export_cases_csv(status=status_filter, priority=priority_filter)

    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"OIL_HSE_Cases_{now_str}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
