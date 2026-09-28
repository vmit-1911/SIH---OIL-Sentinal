"""CSV Generation Service for SIF Assessments, HSE Actions, Risk Concentrations, and Cases (Phase 15).

Generates RFC 4180-compliant CSV datasets with deterministic columns,
proper escaping, and sanitized field representations.
"""

import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.action import HSEActionRecommendation
from app.db.models.assessment import SIFAssessment
from app.db.models.case import HSECase
from app.db.models.concentration import RiskConcentration
from app.db.models.report import SafetyReport
from app.schemas.command_center import CommandCenterOverview


class CSVExportService:
    """Service generating CSV exports for all intelligence data models."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def export_assessments_csv(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        location: Optional[str] = None,
    ) -> str:
        """Export safety reports with SIF assessments to CSV."""
        stmt = select(SafetyReport).options(selectinload(SafetyReport.assessment))
        if from_date:
            stmt = stmt.where(SafetyReport.event_timestamp >= from_date)
        if to_date:
            stmt = stmt.where(SafetyReport.event_timestamp <= to_date)
        if location:
            stmt = stmt.where(SafetyReport.reported_location.ilike(f"%{location}%"))

        stmt = stmt.order_by(SafetyReport.created_at.desc())
        result = await self.session.execute(stmt)
        reports = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            "Report ID",
            "Report Reference",
            "Event Timestamp",
            "Reported Location",
            "Source Type",
            "Actual Severity",
            "SIF Classification",
            "Evidence Score",
            "Potential Severity",
            "Rule Screening Score",
            "Primary Reasoning",
            "Hazard Source",
            "Barrier Failure",
            "Activity",
            "Equipment",
            "Created At",
        ])

        for r in reports:
            a = r.assessment
            sif_cls = a.sif_classification.value if (a and hasattr(a.sif_classification, 'value')) else (str(a.sif_classification) if a else "N/A")
            ev_score = f"{a.evidence_score:.2f}" if a else "0.00"
            pot_sev = a.potential_severity.value if (a and hasattr(a.potential_severity, 'value')) else (str(a.potential_severity) if a else "N/A")
            rule_score = f"{a.rule_based_screening_score:.2f}" if a else "0.00"
            reason = a.primary_reasoning if (a and a.primary_reasoning) else ""
            
            sp = a.structured_precursor if (a and a.structured_precursor) else {}
            hazard = sp.get("hazard_source", "") if isinstance(sp, dict) else ""
            barrier = sp.get("barrier_failure", "") if isinstance(sp, dict) else ""
            activity = sp.get("activity", "") if isinstance(sp, dict) else ""
            equip = sp.get("equipment", "") if isinstance(sp, dict) else ""

            event_dt_str = r.event_timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.event_timestamp else ""

            writer.writerow([
                str(r.id),
                r.report_ref or "",
                event_dt_str,
                r.reported_location or "",
                r.source_type.value if hasattr(r.source_type, 'value') else str(r.source_type),
                r.actual_severity.value if hasattr(r.actual_severity, 'value') else str(r.actual_severity),
                sif_cls,
                ev_score,
                pot_sev,
                rule_score,
                reason,
                hazard,
                barrier,
                activity,
                equip,
                r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            ])

        return output.getvalue()

    async def export_actions_csv(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> str:
        """Export HSE action recommendations to CSV."""
        stmt = select(HSEActionRecommendation)
        if status:
            stmt = stmt.where(HSEActionRecommendation.status == status)
        if priority:
            stmt = stmt.where(HSEActionRecommendation.priority == priority)

        stmt = stmt.order_by(HSEActionRecommendation.created_at.desc())
        result = await self.session.execute(stmt)
        actions = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            "Action ID",
            "Action Key",
            "Title",
            "Description",
            "Category",
            "Priority",
            "Status",
            "Source Type",
            "Source ID",
            "Assigned To",
            "Rule ID",
            "Created At",
        ])

        for a in actions:
            writer.writerow([
                str(a.id),
                a.action_key,
                a.action_title,
                a.action_description,
                a.action_category.value if hasattr(a.action_category, 'value') else str(a.action_category),
                a.priority.value if hasattr(a.priority, 'value') else str(a.priority),
                a.status.value if hasattr(a.status, 'value') else str(a.status),
                a.source_type.value if hasattr(a.source_type, 'value') else str(a.source_type),
                a.source_id,
                a.assigned_to or "",
                a.rule_id or "",
                a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else "",
            ])

        return output.getvalue()

    async def export_concentrations_csv(
        self,
        dimension: Optional[str] = None,
        trend: Optional[str] = None,
    ) -> str:
        """Export Risk Concentrations to CSV."""
        stmt = select(RiskConcentration)
        if dimension:
            stmt = stmt.where(RiskConcentration.dimension_type == dimension)
        if trend:
            stmt = stmt.where(RiskConcentration.observed_trend == trend)

        stmt = stmt.order_by(RiskConcentration.last_observed_at.desc())
        result = await self.session.execute(stmt)
        concentrations = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            "Concentration ID",
            "Concentration Key",
            "Dimension Type",
            "Dimension Value",
            "Occurrence Count",
            "Distinct Report Count",
            "Distinct Location Count",
            "Observed Trend",
            "Status",
            "First Observed At",
            "Last Observed At",
        ])

        for c in concentrations:
            dim_str = c.dimension_type.value if hasattr(c.dimension_type, 'value') else str(c.dimension_type)
            trend_str = c.observed_trend.value if hasattr(c.observed_trend, 'value') else str(c.observed_trend)
            stat_str = c.status.value if hasattr(c.status, 'value') else str(c.status)
            first_str = c.first_observed_at.strftime("%Y-%m-%d %H:%M:%S") if c.first_observed_at else ""
            last_str = c.last_observed_at.strftime("%Y-%m-%d %H:%M:%S") if c.last_observed_at else ""

            writer.writerow([
                str(c.id),
                c.concentration_key,
                dim_str,
                c.dimension_value,
                c.occurrence_count,
                c.distinct_report_count,
                c.distinct_location_count,
                trend_str,
                stat_str,
                first_str,
                last_str,
            ])

        return output.getvalue()

    async def export_cases_csv(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> str:
        """Export HSE Cases to CSV."""
        stmt = select(HSECase)
        if status:
            stmt = stmt.where(HSECase.status == status)
        if priority:
            stmt = stmt.where(HSECase.priority == priority)

        stmt = stmt.order_by(HSECase.created_at.desc())
        result = await self.session.execute(stmt)
        cases = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            "Case ID",
            "Title",
            "Case Type",
            "Status",
            "Priority",
            "Assigned To",
            "Description",
            "Created At",
            "Updated At",
        ])

        for c in cases:
            writer.writerow([
                str(c.id),
                c.title,
                c.case_type.value if hasattr(c.case_type, 'value') else str(c.case_type),
                c.status.value if hasattr(c.status, 'value') else str(c.status),
                c.priority.value if hasattr(c.priority, 'value') else str(c.priority),
                c.owner or "",
                c.description or "",
                c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
                c.updated_at.strftime("%Y-%m-%d %H:%M:%S") if c.updated_at else "",
            ])

        return output.getvalue()

    @staticmethod
    def export_command_center_summary_csv(overview: CommandCenterOverview) -> str:
        """Export top-level Command Center KPI overview to CSV."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow(["Metric Name", "Value", "Description"])
        writer.writerow(["Total Reports", overview.total_reports, "Total safety events ingested"])
        writer.writerow(["Total Assessments", overview.total_assessments, "Total SIF screened reports"])
        writer.writerow(["Potential SIF Count", overview.potential_sif_count, "Events classified as POTENTIAL_SIF"])
        writer.writerow(["Non-SIF Count", overview.non_sif_count, "Routine low-energy events"])
        writer.writerow(["Undetermined Count", overview.undetermined_count, "Inconclusive narrative context"])
        writer.writerow(["Open Actions Count", overview.open_action_count, "Actions requiring resolution"])
        writer.writerow(["Active Cases Count", overview.active_case_count, "Formal investigation cases open"])
        writer.writerow(["Pending Review Count", overview.unreviewed_count, "Pending human triage reviews"])
        writer.writerow(["Discovered Precursor Patterns", overview.recurring_pattern_count, "Recurring pattern clusters (N >= 3)"])
        writer.writerow(["Active Risk Concentrations", overview.concentration_count, "Identified statistical risk clusters"])
        writer.writerow(["Generated At", overview.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC"), "Report generation timestamp"])
        writer.writerow(["Data Baseline As Of", overview.data_as_of.strftime("%Y-%m-%d %H:%M:%S UTC"), "Data currency timestamp"])

        return output.getvalue()
