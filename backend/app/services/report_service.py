"""Report service coordinating report persistence and retrieval."""

from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.assessment import SIFAssessment
from app.db.models.report import SafetyReport
from app.schemas.report import ReportFilterParams


class ReportService:
    """Service for managing safety report persistence and queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_report_by_id(self, report_id: UUID) -> Optional[SafetyReport]:
        """Fetch report with its assessment and mappings by ID."""
        stmt = (
            select(SafetyReport)
            .where(SafetyReport.id == report_id)
            .options(
                selectinload(SafetyReport.assessment),
                selectinload(SafetyReport.lsr_mappings),
                selectinload(SafetyReport.reviews),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_reports(
        self,
        params: ReportFilterParams,
    ) -> Tuple[list[SafetyReport], int]:
        """Query paginated reports with optional filtering."""
        query = select(SafetyReport).options(selectinload(SafetyReport.assessment))
        count_query = select(func.count(SafetyReport.id))

        if params.source_type:
            query = query.where(SafetyReport.source_type == params.source_type)
            count_query = count_query.where(SafetyReport.source_type == params.source_type)

        if params.location:
            query = query.where(SafetyReport.reported_location.ilike(f"%{params.location}%"))
            count_query = count_query.where(SafetyReport.reported_location.ilike(f"%{params.location}%"))

        # Total count
        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        # Pagination
        offset = (params.page - 1) * params.page_size
        query = query.order_by(SafetyReport.created_at.desc()).offset(offset).limit(params.page_size)

        result = await self.session.execute(query)
        reports = list(result.scalars().all())

        return reports, total
