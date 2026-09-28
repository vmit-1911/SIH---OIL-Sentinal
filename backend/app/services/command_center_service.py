"""Service layer for Phase 10 HSE Command Center / Operational Intelligence API.

Aggregates already-persisted intelligence from Phases 1–9 into read-oriented command-center views.
Strictly read-only; does NOT mutate underlying records or execute AI/ML inference.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.action import HSEActionRecommendation
from app.db.models.assessment import SIFAssessment
from app.db.models.case import HSECase, HSECaseSourceAssociation
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.review import TriageReview
from app.db.models.taxonomy import LSRReportMapping, LSRTaxonomy
from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
    ActualOutcome,
    CasePriority,
    CaseSourceType,
    CaseStatus,
    CaseType,
    ConcentrationDimension,
    ConcentrationStatus,
    ObservedTrend,
    PatternStatus,
    PotentialOutcome,
    ReviewDecision,
    ReviewFeedbackCategory,
    ReviewState,
    SIFClassification,
    SourceType,
)
from app.schemas.command_center import (
    ActionOverviewDTO,
    CaseOverviewDTO,
    CaseSummaryItemDTO,
    CommandCenterOverview,
    ConcentrationOverviewDTO,
    ConcentrationSummaryDTO,
    DimensionMetricDTO,
    InvestigationSnapshotDTO,
    LSRDetailOverviewDTO,
    LSROverviewDTO,
    MonthlyAssessmentTrendDTO,
    PatternSummaryDTO,
    PrecursorOverviewDTO,
    ReportingPeriodDTO,
    ReviewQueueOverviewDTO,
    SIFOverviewDTO,
    SnapshotActionNode,
    SnapshotAssessmentNode,
    SnapshotCaseNode,
    SnapshotConcentrationNode,
    SnapshotPatternNode,
    SnapshotReportNode,
    SnapshotReviewNode,
)


class CommandCenterService:
    """Service providing read-only aggregated operational views for the HSE Command Center."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==========================================================================
    # 1. COMMAND CENTER OVERVIEW
    # ==========================================================================

    async def get_overview(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        location: Optional[str] = None,
    ) -> CommandCenterOverview:
        """Aggregate high-level descriptive counts across safety reports, SIF assessments, reviews, actions, and cases."""
        now = datetime.now(timezone.utc)
        reporting_period = ReportingPeriodDTO(from_date=from_date, to_date=to_date) if (from_date or to_date) else None

        # 1. Total reports
        rep_query = select(func.count(SafetyReport.id))
        if from_date:
            rep_query = rep_query.where(SafetyReport.created_at >= from_date)
        if to_date:
            rep_query = rep_query.where(SafetyReport.created_at <= to_date)
        if location:
            rep_query = rep_query.where(SafetyReport.reported_location.ilike(f"%{location}%"))
        total_reports = (await self.session.execute(rep_query)).scalar_one() or 0

        # 2. SIF Assessments breakdown
        asm_query = (
            select(
                SIFAssessment.sif_classification,
                func.count(SIFAssessment.id),
            )
            .join(SafetyReport, SIFAssessment.report_id == SafetyReport.id)
            .group_by(SIFAssessment.sif_classification)
        )
        if from_date:
            asm_query = asm_query.where(SafetyReport.created_at >= from_date)
        if to_date:
            asm_query = asm_query.where(SafetyReport.created_at <= to_date)
        if location:
            asm_query = asm_query.where(SafetyReport.reported_location.ilike(f"%{location}%"))
        
        asm_rows = (await self.session.execute(asm_query)).all()
        classification_map = {row[0]: row[1] for row in asm_rows}
        
        potential_sif_count = classification_map.get(SIFClassification.POTENTIAL_SIF, 0)
        non_sif_count = classification_map.get(SIFClassification.NON_SIF, 0)
        undetermined_count = classification_map.get(SIFClassification.UNDETERMINED, 0)
        total_assessments = sum(classification_map.values())

        # 3. Human Reviews breakdown
        rev_query = (
            select(
                TriageReview.status,
                func.count(TriageReview.id),
            )
            .join(SafetyReport, TriageReview.report_id == SafetyReport.id)
            .group_by(TriageReview.status)
        )
        if from_date:
            rev_query = rev_query.where(SafetyReport.created_at >= from_date)
        if to_date:
            rev_query = rev_query.where(SafetyReport.created_at <= to_date)
        if location:
            rev_query = rev_query.where(SafetyReport.reported_location.ilike(f"%{location}%"))

        rev_rows = (await self.session.execute(rev_query)).all()
        rev_map = {row[0]: row[1] for row in rev_rows}
        unreviewed_count = rev_map.get(ReviewState.PENDING, 0) + rev_map.get(ReviewState.IN_REVIEW, 0)
        reviewed_count = rev_map.get(ReviewState.REVIEWED, 0)

        # 4. Open Actions count (OPEN, ACKNOWLEDGED, IN_PROGRESS)
        act_query = (
            select(func.count(HSEActionRecommendation.id))
            .where(
                HSEActionRecommendation.status.in_([
                    ActionStatus.OPEN,
                    ActionStatus.ACKNOWLEDGED,
                    ActionStatus.IN_PROGRESS,
                ])
            )
        )
        if from_date:
            act_query = act_query.where(HSEActionRecommendation.created_at >= from_date)
        if to_date:
            act_query = act_query.where(HSEActionRecommendation.created_at <= to_date)
        open_action_count = (await self.session.execute(act_query)).scalar_one() or 0

        # 5. Active Cases count (not CLOSED or CANCELLED)
        case_query = (
            select(func.count(HSECase.id))
            .where(
                HSECase.status.in_([
                    CaseStatus.OPEN,
                    CaseStatus.TRIAGE,
                    CaseStatus.INVESTIGATING,
                    CaseStatus.ACTION_REQUIRED,
                    CaseStatus.PENDING_VERIFICATION,
                ])
            )
        )
        if from_date:
            case_query = case_query.where(HSECase.created_at >= from_date)
        if to_date:
            case_query = case_query.where(HSECase.created_at <= to_date)
        active_case_count = (await self.session.execute(case_query)).scalar_one() or 0

        # 6. Active Precursor Patterns count
        pat_query = select(func.count(PrecursorPattern.id)).where(PrecursorPattern.status == PatternStatus.ACTIVE)
        if from_date:
            pat_query = pat_query.where(PrecursorPattern.first_detected_at >= from_date)
        if to_date:
            pat_query = pat_query.where(PrecursorPattern.first_detected_at <= to_date)
        recurring_pattern_count = (await self.session.execute(pat_query)).scalar_one() or 0

        # 7. Active Risk Concentrations count
        conc_query = select(func.count(RiskConcentration.id)).where(RiskConcentration.status == ConcentrationStatus.ACTIVE)
        if from_date:
            conc_query = conc_query.where(RiskConcentration.created_at >= from_date)
        if to_date:
            conc_query = conc_query.where(RiskConcentration.created_at <= to_date)
        concentration_count = (await self.session.execute(conc_query)).scalar_one() or 0

        return CommandCenterOverview(
            generated_at=now,
            data_as_of=now,
            reporting_period=reporting_period,
            total_reports=total_reports,
            total_assessments=total_assessments,
            potential_sif_count=potential_sif_count,
            non_sif_count=non_sif_count,
            undetermined_count=undetermined_count,
            reviewed_count=reviewed_count,
            unreviewed_count=unreviewed_count,
            open_action_count=open_action_count,
            active_case_count=active_case_count,
            recurring_pattern_count=recurring_pattern_count,
            concentration_count=concentration_count,
        )

    # ==========================================================================
    # 2. SIF OVERVIEW
    # ==========================================================================

    async def get_sif_overview(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        location: Optional[str] = None,
        lsr_code: Optional[str] = None,
    ) -> SIFOverviewDTO:
        """Descriptive aggregation of SIF assessments, severities, LSR mappings, and monthly trends."""
        now = datetime.now(timezone.utc)
        reporting_period = ReportingPeriodDTO(from_date=from_date, to_date=to_date) if (from_date or to_date) else None

        # Build base join of SIFAssessment and SafetyReport
        base_stmt = (
            select(
                SIFAssessment.sif_classification,
                SafetyReport.actual_severity,
                SIFAssessment.potential_severity,
                SafetyReport.created_at,
            )
            .join(SafetyReport, SIFAssessment.report_id == SafetyReport.id)
        )

        if from_date:
            base_stmt = base_stmt.where(SafetyReport.created_at >= from_date)
        if to_date:
            base_stmt = base_stmt.where(SafetyReport.created_at <= to_date)
        if location:
            base_stmt = base_stmt.where(SafetyReport.reported_location.ilike(f"%{location}%"))
        if lsr_code:
            base_stmt = (
                base_stmt.join(LSRReportMapping, LSRReportMapping.report_id == SafetyReport.id)
                .where(LSRReportMapping.rule_code == lsr_code)
            )

        rows = (await self.session.execute(base_stmt)).all()

        classification_counts: Dict[str, int] = defaultdict(int)
        actual_severity_counts: Dict[str, int] = defaultdict(int)
        potential_severity_counts: Dict[str, int] = defaultdict(int)
        monthly_map: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for row in rows:
            sif_cls, act_sev, pot_sev, cr_at = row
            if sif_cls:
                classification_counts[sif_cls.value if hasattr(sif_cls, "value") else str(sif_cls)] += 1
            if act_sev:
                actual_severity_counts[act_sev.value if hasattr(act_sev, "value") else str(act_sev)] += 1
            if pot_sev:
                potential_severity_counts[pot_sev.value if hasattr(pot_sev, "value") else str(pot_sev)] += 1
            
            if cr_at:
                period_key = cr_at.strftime("%Y-%m")
                monthly_map[period_key]["total"] += 1
                if sif_cls == SIFClassification.POTENTIAL_SIF:
                    monthly_map[period_key]["potential_sif"] += 1
                elif sif_cls == SIFClassification.NON_SIF:
                    monthly_map[period_key]["non_sif"] += 1
                elif sif_cls == SIFClassification.UNDETERMINED:
                    monthly_map[period_key]["undetermined"] += 1

        total_assessments = len(rows)

        # Reviews breakdown for the filtered set
        rev_stmt = (
            select(TriageReview.status, func.count(TriageReview.id))
            .join(SafetyReport, TriageReview.report_id == SafetyReport.id)
            .group_by(TriageReview.status)
        )
        if from_date:
            rev_stmt = rev_stmt.where(SafetyReport.created_at >= from_date)
        if to_date:
            rev_stmt = rev_stmt.where(SafetyReport.created_at <= to_date)
        if location:
            rev_stmt = rev_stmt.where(SafetyReport.reported_location.ilike(f"%{location}%"))
        
        rev_rows = (await self.session.execute(rev_stmt)).all()
        rev_map = {r[0]: r[1] for r in rev_rows}
        unreviewed_count = rev_map.get(ReviewState.PENDING, 0) + rev_map.get(ReviewState.IN_REVIEW, 0)
        reviewed_count = rev_map.get(ReviewState.REVIEWED, 0)

        # LSR Distribution
        lsr_stmt = (
            select(LSRReportMapping.rule_code, func.count(LSRReportMapping.id))
            .join(SafetyReport, LSRReportMapping.report_id == SafetyReport.id)
            .group_by(LSRReportMapping.rule_code)
            .order_by(func.count(LSRReportMapping.id).desc())
        )
        if from_date:
            lsr_stmt = lsr_stmt.where(SafetyReport.created_at >= from_date)
        if to_date:
            lsr_stmt = lsr_stmt.where(SafetyReport.created_at <= to_date)
        if location:
            lsr_stmt = lsr_stmt.where(SafetyReport.reported_location.ilike(f"%{location}%"))
        
        lsr_rows = (await self.session.execute(lsr_stmt)).all()
        lsr_distribution = {row[0]: row[1] for row in lsr_rows}

        # Monthly trends ordered chronologically
        assessment_trend_by_month: List[MonthlyAssessmentTrendDTO] = [
            MonthlyAssessmentTrendDTO(
                period=p,
                total_assessments=counts["total"],
                potential_sif_count=counts["potential_sif"],
                non_sif_count=counts["non_sif"],
                undetermined_count=counts["undetermined"],
            )
            for p, counts in sorted(monthly_map.items(), key=lambda x: x[0])
        ]

        return SIFOverviewDTO(
            generated_at=now,
            reporting_period=reporting_period,
            total_assessments=total_assessments,
            classification_counts=dict(classification_counts),
            actual_severity_counts=dict(actual_severity_counts),
            potential_severity_counts=dict(potential_severity_counts),
            reviewed_count=reviewed_count,
            unreviewed_count=unreviewed_count,
            lsr_distribution=lsr_distribution,
            assessment_trend_by_month=assessment_trend_by_month,
        )

    # ==========================================================================
    # 3. PRECURSOR INTELLIGENCE OVERVIEW
    # ==========================================================================

    async def get_precursor_overview(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        location: Optional[str] = None,
        lsr_code: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> PrecursorOverviewDTO:
        """Overview of recurring precursor patterns and multi-dimensional cluster distributions."""
        now = datetime.now(timezone.utc)
        reporting_period = ReportingPeriodDTO(from_date=from_date, to_date=to_date) if (from_date or to_date) else None

        # Base query for patterns
        query = select(PrecursorPattern).where(PrecursorPattern.status == PatternStatus.ACTIVE)
        if from_date:
            query = query.where(PrecursorPattern.first_detected_at >= from_date)
        if to_date:
            query = query.where(PrecursorPattern.first_detected_at <= to_date)
        if lsr_code:
            query = query.where(PrecursorPattern.lsr_code == lsr_code)

        all_patterns = (await self.session.execute(query.order_by(PrecursorPattern.occurrence_count.desc(), PrecursorPattern.pattern_code.asc()))).scalars().all()

        # Filter by location if specified
        if location:
            filtered_patterns = [
                p for p in all_patterns
                if any(location.lower() in loc.lower() for loc in (p.affected_locations or []))
            ]
        else:
            filtered_patterns = list(all_patterns)

        total_patterns = len(filtered_patterns)
        paged_patterns = filtered_patterns[offset: offset + limit]

        top_patterns = [
            PatternSummaryDTO(
                id=p.id,
                pattern_code=p.pattern_code,
                title=p.title,
                description=p.description,
                hazard_category=p.hazard_category,
                activity_type=p.activity_type,
                failed_barrier_type=p.failed_barrier_type,
                lsr_code=p.lsr_code,
                occurrence_count=p.occurrence_count,
                affected_locations=p.affected_locations or [],
                supporting_report_count=len(p.supporting_report_ids or []),
                first_detected_at=p.first_detected_at,
            )
            for p in paged_patterns
        ]

        # Aggregate dimension metrics across all filtered patterns
        hazard_counts: Dict[str, int] = defaultdict(int)
        barrier_counts: Dict[str, int] = defaultdict(int)
        activity_counts: Dict[str, int] = defaultdict(int)
        location_counts: Dict[str, int] = defaultdict(int)
        lsr_counts: Dict[str, int] = defaultdict(int)

        for p in filtered_patterns:
            if p.hazard_category:
                hazard_counts[p.hazard_category] += p.occurrence_count
            if p.failed_barrier_type:
                barrier_counts[p.failed_barrier_type] += p.occurrence_count
            if p.activity_type:
                activity_counts[p.activity_type] += p.occurrence_count
            if p.lsr_code:
                lsr_counts[p.lsr_code] += p.occurrence_count
            for loc in (p.affected_locations or []):
                location_counts[loc] += p.occurrence_count

        return PrecursorOverviewDTO(
            generated_at=now,
            reporting_period=reporting_period,
            total_patterns=total_patterns,
            top_patterns=top_patterns,
            top_hazard_dimensions=[
                DimensionMetricDTO(name=k, count=v)
                for k, v in sorted(hazard_counts.items(), key=lambda x: (-x[1], x[0]))
            ],
            top_barrier_failure_dimensions=[
                DimensionMetricDTO(name=k, count=v)
                for k, v in sorted(barrier_counts.items(), key=lambda x: (-x[1], x[0]))
            ],
            top_activity_dimensions=[
                DimensionMetricDTO(name=k, count=v)
                for k, v in sorted(activity_counts.items(), key=lambda x: (-x[1], x[0]))
            ],
            supporting_locations=[
                DimensionMetricDTO(name=k, count=v)
                for k, v in sorted(location_counts.items(), key=lambda x: (-x[1], x[0]))
            ],
            supporting_lsrs=[
                DimensionMetricDTO(name=k, count=v)
                for k, v in sorted(lsr_counts.items(), key=lambda x: (-x[1], x[0]))
            ],
        )

    # ==========================================================================
    # 4. CONCENTRATION OVERVIEW
    # ==========================================================================

    async def get_concentration_overview(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        dimension_type: Optional[ConcentrationDimension] = None,
        trend: Optional[ObservedTrend] = None,
        location: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ConcentrationOverviewDTO:
        """Expose existing Phase 3 concentration intelligence across canonical dimensions."""
        now = datetime.now(timezone.utc)
        reporting_period = ReportingPeriodDTO(from_date=from_date, to_date=to_date) if (from_date or to_date) else None

        query = select(RiskConcentration).where(RiskConcentration.status == ConcentrationStatus.ACTIVE)
        if from_date:
            query = query.where(RiskConcentration.created_at >= from_date)
        if to_date:
            query = query.where(RiskConcentration.created_at <= to_date)
        if dimension_type:
            query = query.where(RiskConcentration.dimension_type == dimension_type)
        if trend:
            query = query.where(RiskConcentration.observed_trend == trend)

        all_concs = (
            await self.session.execute(
                query.order_by(RiskConcentration.occurrence_count.desc(), RiskConcentration.concentration_key.asc())
            )
        ).scalars().all()

        if location:
            filtered = [
                c for c in all_concs
                if any(location.lower() in loc.lower() for loc in (c.supporting_locations or []))
                or (c.dimension_type == ConcentrationDimension.LOCATION and location.lower() in c.dimension_value.lower())
            ]
        else:
            filtered = list(all_concs)

        total_concentrations = len(filtered)
        paged = filtered[offset: offset + limit]

        dimension_counts: Dict[str, int] = {dim.value: 0 for dim in ConcentrationDimension}
        for c in filtered:
            dim_key = c.dimension_type.value if hasattr(c.dimension_type, "value") else str(c.dimension_type)
            dimension_counts[dim_key] = dimension_counts.get(dim_key, 0) + 1

        items = [
            ConcentrationSummaryDTO(
                id=c.id,
                concentration_key=c.concentration_key,
                dimension_type=c.dimension_type,
                dimension_value=c.dimension_value,
                occurrence_count=c.occurrence_count,
                distinct_report_count=c.distinct_report_count,
                distinct_location_count=c.distinct_location_count,
                observed_trend=c.observed_trend,
                supporting_locations=c.supporting_locations or [],
                first_observed_at=c.first_observed_at,
                last_observed_at=c.last_observed_at,
            )
            for c in paged
        ]

        return ConcentrationOverviewDTO(
            generated_at=now,
            reporting_period=reporting_period,
            total_concentrations=total_concentrations,
            dimension_counts=dimension_counts,
            items=items,
            limit=limit,
            offset=offset,
        )

    # ==========================================================================
    # 5. LSR OVERVIEW
    # ==========================================================================

    async def get_lsr_overview(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        location: Optional[str] = None,
        lsr_code: Optional[str] = None,
    ) -> LSROverviewDTO:
        """Expose descriptive LSR distributions across assessments, SIF potential, reviews, and actions."""
        now = datetime.now(timezone.utc)
        reporting_period = ReportingPeriodDTO(from_date=from_date, to_date=to_date) if (from_date or to_date) else None

        # 1. Fetch active LSR rules
        tax_stmt = select(LSRTaxonomy).where(LSRTaxonomy.active == True)
        taxonomies = (await self.session.execute(tax_stmt)).scalars().all()

        rule_names: Dict[str, str] = {}
        for tax in taxonomies:
            for r in (tax.rules or []):
                code = r.get("rule_code") or r.get("code")
                name = r.get("rule_name") or r.get("name") or code
                if code:
                    rule_names[code] = name

        # 2. Query LSR report mappings joined to SafetyReport, SIFAssessment, TriageReview
        mapping_stmt = (
            select(
                LSRReportMapping.rule_code,
                LSRReportMapping.rule_name,
                SIFAssessment.sif_classification,
                TriageReview.status,
            )
            .join(SafetyReport, LSRReportMapping.report_id == SafetyReport.id)
            .outerjoin(SIFAssessment, SIFAssessment.report_id == SafetyReport.id)
            .outerjoin(TriageReview, TriageReview.report_id == SafetyReport.id)
        )

        if from_date:
            mapping_stmt = mapping_stmt.where(SafetyReport.created_at >= from_date)
        if to_date:
            mapping_stmt = mapping_stmt.where(SafetyReport.created_at <= to_date)
        if location:
            mapping_stmt = mapping_stmt.where(SafetyReport.reported_location.ilike(f"%{location}%"))
        if lsr_code:
            mapping_stmt = mapping_stmt.where(LSRReportMapping.rule_code == lsr_code)

        rows = (await self.session.execute(mapping_stmt)).all()

        # 3. Actions linked to LSR rules (via pattern/assessment rule_id or source)
        act_stmt = (
            select(HSEActionRecommendation.rule_id, func.count(HSEActionRecommendation.id))
            .where(
                HSEActionRecommendation.status.in_([
                    ActionStatus.OPEN,
                    ActionStatus.ACKNOWLEDGED,
                    ActionStatus.IN_PROGRESS,
                ])
            )
            .group_by(HSEActionRecommendation.rule_id)
        )
        act_rows = (await self.session.execute(act_stmt)).all()
        act_map = {r[0]: r[1] for r in act_rows if r[0]}

        # Aggregate counts per rule
        lsr_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "name": "",
            "assessment_count": 0,
            "potential_sif_count": 0,
            "reviewed_count": 0,
            "open_actions": 0,
        })

        for row in rows:
            code, name, sif_cls, rev_status = row
            if not code:
                continue
            stat = lsr_stats[code]
            if not stat["name"]:
                stat["name"] = name or rule_names.get(code, code)
            stat["assessment_count"] += 1
            if sif_cls == SIFClassification.POTENTIAL_SIF:
                stat["potential_sif_count"] += 1
            if rev_status == ReviewState.REVIEWED:
                stat["reviewed_count"] += 1

        # Also populate any rule present in rule_names even if count is 0
        for code, name in rule_names.items():
            if code not in lsr_stats and (not lsr_code or lsr_code == code):
                lsr_stats[code] = {
                    "name": name,
                    "assessment_count": 0,
                    "potential_sif_count": 0,
                    "reviewed_count": 0,
                    "open_actions": 0,
                }

        # Match open action counts
        for code, stat in lsr_stats.items():
            stat["open_actions"] = act_map.get(code, 0)

        rules_list = [
            LSRDetailOverviewDTO(
                rule_code=code,
                rule_name=stat["name"] or code,
                assessment_count=stat["assessment_count"],
                potential_sif_count=stat["potential_sif_count"],
                reviewed_count=stat["reviewed_count"],
                open_action_count=stat["open_actions"],
            )
            for code, stat in sorted(lsr_stats.items(), key=lambda x: (-x[1]["assessment_count"], x[0]))
        ]

        return LSROverviewDTO(
            generated_at=now,
            reporting_period=reporting_period,
            total_lsr_rules=len(rules_list),
            rules=rules_list,
        )

    # ==========================================================================
    # 6. ACTION OVERVIEW
    # ==========================================================================

    async def get_action_overview(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        status: Optional[ActionStatus] = None,
        priority: Optional[ActionPriority] = None,
        category: Optional[ActionCategory] = None,
        source_type: Optional[ActionSourceType] = None,
    ) -> ActionOverviewDTO:
        """Expose Phase 8 action recommendations state, category, priority, and age distribution."""
        now = datetime.now(timezone.utc)
        reporting_period = ReportingPeriodDTO(from_date=from_date, to_date=to_date) if (from_date or to_date) else None

        query = select(HSEActionRecommendation)
        if from_date:
            query = query.where(HSEActionRecommendation.created_at >= from_date)
        if to_date:
            query = query.where(HSEActionRecommendation.created_at <= to_date)
        if status:
            query = query.where(HSEActionRecommendation.status == status)
        if priority:
            query = query.where(HSEActionRecommendation.priority == priority)
        if category:
            query = query.where(HSEActionRecommendation.action_category == category)
        if source_type:
            query = query.where(HSEActionRecommendation.source_type == source_type)

        actions = (await self.session.execute(query.order_by(HSEActionRecommendation.created_at.desc()))).scalars().all()

        total_actions = len(actions)
        status_counts: Dict[str, int] = {s.value: 0 for s in ActionStatus}
        category_counts: Dict[str, int] = defaultdict(int)
        priority_counts: Dict[str, int] = defaultdict(int)
        source_type_counts: Dict[str, int] = defaultdict(int)
        
        open_age_buckets: Dict[str, int] = {
            "< 7 days": 0,
            "7-30 days": 0,
            "> 30 days": 0,
        }

        for act in actions:
            # Status
            st_key = act.status.value if hasattr(act.status, "value") else str(act.status)
            status_counts[st_key] = status_counts.get(st_key, 0) + 1

            # Category
            cat_key = act.action_category.value if hasattr(act.action_category, "value") else str(act.action_category)
            category_counts[cat_key] += 1

            # Priority
            prio_key = act.priority.value if hasattr(act.priority, "value") else str(act.priority)
            priority_counts[prio_key] += 1

            # Source Type
            src_key = act.source_type.value if hasattr(act.source_type, "value") else str(act.source_type)
            source_type_counts[src_key] += 1

            # Age of open / in-progress actions
            if act.status in (ActionStatus.OPEN, ActionStatus.ACKNOWLEDGED, ActionStatus.IN_PROGRESS):
                age_days = (now - act.created_at.replace(tzinfo=timezone.utc if act.created_at.tzinfo is None else act.created_at.tzinfo)).total_seconds() / 86400.0
                if age_days < 7:
                    open_age_buckets["< 7 days"] += 1
                elif age_days <= 30:
                    open_age_buckets["7-30 days"] += 1
                else:
                    open_age_buckets["> 30 days"] += 1

        return ActionOverviewDTO(
            generated_at=now,
            reporting_period=reporting_period,
            total_actions=total_actions,
            status_counts=status_counts,
            category_distribution=dict(category_counts),
            priority_distribution=dict(priority_counts),
            source_type_distribution=dict(source_type_counts),
            open_actions_by_age=open_age_buckets,
        )

    # ==========================================================================
    # 7. CASE OVERVIEW
    # ==========================================================================

    async def get_case_overview(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        status: Optional[CaseStatus] = None,
        priority: Optional[CasePriority] = None,
        case_type: Optional[CaseType] = None,
        owner: Optional[str] = None,
    ) -> CaseOverviewDTO:
        """Expose Phase 9 HSE case management state, type, priority, and recent activity."""
        now = datetime.now(timezone.utc)
        reporting_period = ReportingPeriodDTO(from_date=from_date, to_date=to_date) if (from_date or to_date) else None

        query = select(HSECase)
        if from_date:
            query = query.where(HSECase.created_at >= from_date)
        if to_date:
            query = query.where(HSECase.created_at <= to_date)
        if status:
            query = query.where(HSECase.status == status)
        if priority:
            query = query.where(HSECase.priority == priority)
        if case_type:
            query = query.where(HSECase.case_type == case_type)
        if owner:
            query = query.where(HSECase.owner == owner)

        cases = (await self.session.execute(query.order_by(HSECase.updated_at.desc()))).scalars().all()

        total_cases = len(cases)
        status_counts: Dict[str, int] = {s.value: 0 for s in CaseStatus}
        type_counts: Dict[str, int] = defaultdict(int)
        priority_counts: Dict[str, int] = defaultdict(int)
        owner_counts: Dict[str, int] = defaultdict(int)
        active_case_count = 0

        for c in cases:
            st_key = c.status.value if hasattr(c.status, "value") else str(c.status)
            status_counts[st_key] = status_counts.get(st_key, 0) + 1

            if c.status not in (CaseStatus.CLOSED, CaseStatus.CANCELLED):
                active_case_count += 1

            tp_key = c.case_type.value if hasattr(c.case_type, "value") else str(c.case_type)
            type_counts[tp_key] += 1

            pr_key = c.priority.value if hasattr(c.priority, "value") else str(c.priority)
            priority_counts[pr_key] += 1

            if c.owner:
                owner_counts[c.owner] += 1

        recent_cases = [
            CaseSummaryItemDTO(
                id=c.id,
                case_key=c.case_key,
                title=c.title,
                case_type=c.case_type,
                status=c.status,
                priority=c.priority,
                owner=c.owner,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in cases[:10]
        ]

        return CaseOverviewDTO(
            generated_at=now,
            reporting_period=reporting_period,
            total_cases=total_cases,
            status_counts=status_counts,
            case_type_distribution=dict(type_counts),
            priority_distribution=dict(priority_counts),
            owner_distribution=dict(owner_counts),
            active_case_count=active_case_count,
            recently_updated_cases=recent_cases,
        )

    # ==========================================================================
    # 8. REVIEW QUEUE OVERVIEW
    # ==========================================================================

    async def get_review_queue_overview(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> ReviewQueueOverviewDTO:
        """Expose Phase 5 human review queue workload and decision statistics."""
        now = datetime.now(timezone.utc)
        reporting_period = ReportingPeriodDTO(from_date=from_date, to_date=to_date) if (from_date or to_date) else None

        query = select(TriageReview)
        if from_date:
            query = query.where(TriageReview.created_at >= from_date)
        if to_date:
            query = query.where(TriageReview.created_at <= to_date)

        reviews = (await self.session.execute(query.order_by(TriageReview.created_at.desc()))).scalars().all()

        total_reviews = len(reviews)
        pending_reviews = 0
        in_review_count = 0
        reviewed_count = 0
        decision_counts: Dict[str, int] = defaultdict(int)
        feedback_category_counts: Dict[str, int] = defaultdict(int)
        pending_age_buckets: Dict[str, int] = {
            "< 7 days": 0,
            "7-30 days": 0,
            "> 30 days": 0,
        }

        for r in reviews:
            if r.status == ReviewState.PENDING:
                pending_reviews += 1
                age_days = (now - r.created_at.replace(tzinfo=timezone.utc if r.created_at.tzinfo is None else r.created_at.tzinfo)).total_seconds() / 86400.0
                if age_days < 7:
                    pending_age_buckets["< 7 days"] += 1
                elif age_days <= 30:
                    pending_age_buckets["7-30 days"] += 1
                else:
                    pending_age_buckets["> 30 days"] += 1
            elif r.status == ReviewState.IN_REVIEW:
                in_review_count += 1
            else:
                reviewed_count += 1

            if r.decision:
                dec_key = r.decision.value if hasattr(r.decision, "value") else str(r.decision)
                decision_counts[dec_key] += 1

            if r.feedback_category:
                fb_key = r.feedback_category.value if hasattr(r.feedback_category, "value") else str(r.feedback_category)
                feedback_category_counts[fb_key] += 1

        return ReviewQueueOverviewDTO(
            generated_at=now,
            reporting_period=reporting_period,
            total_reviews=total_reviews,
            pending_reviews=pending_reviews,
            in_review_count=in_review_count,
            reviewed_count=reviewed_count,
            decision_distribution=dict(decision_counts),
            feedback_category_distribution=dict(feedback_category_counts),
            age_of_pending_reviews=pending_age_buckets,
        )

    # ==========================================================================
    # 9. INVESTIGATION SNAPSHOT
    # ==========================================================================

    async def get_investigation_snapshot(
        self,
        report_ref: Optional[str] = None,
        case_key: Optional[str] = None,
        pattern_code: Optional[str] = None,
        concentration_key: Optional[str] = None,
    ) -> InvestigationSnapshotDTO:
        """Compact operational chain: Reports -> Assessments -> Precursor -> Pattern -> Concentration -> Review -> Actions -> Cases."""
        now = datetime.now(timezone.utc)
        query_target = {
            "report_ref": report_ref,
            "case_key": case_key,
            "pattern_code": pattern_code,
            "concentration_key": concentration_key,
        }

        matched_report_ids: Set[uuid.UUID] = set()
        matched_assessment_ids: Set[uuid.UUID] = set()
        matched_pattern_ids: Set[uuid.UUID] = set()
        matched_concentration_ids: Set[uuid.UUID] = set()
        matched_review_ids: Set[uuid.UUID] = set()
        matched_action_ids: Set[uuid.UUID] = set()
        matched_case_ids: Set[uuid.UUID] = set()

        # Target 1: report_ref
        if report_ref:
            rep_stmt = select(SafetyReport).where(SafetyReport.report_ref == report_ref)
            rep = (await self.session.execute(rep_stmt)).scalar_one_or_none()
            if rep:
                matched_report_ids.add(rep.id)

        # Target 2: case_key
        if case_key:
            case_stmt = select(HSECase).where(HSECase.case_key == case_key)
            c = (await self.session.execute(case_stmt)).scalar_one_or_none()
            if c:
                matched_case_ids.add(c.id)
                assoc_stmt = select(HSECaseSourceAssociation).where(HSECaseSourceAssociation.case_id == c.id)
                assocs = (await self.session.execute(assoc_stmt)).scalars().all()
                for a in assocs:
                    if a.source_type == CaseSourceType.REPORT:
                        # Find report by ref or id
                        r = (await self.session.execute(select(SafetyReport).where((SafetyReport.report_ref == a.source_id) | (SafetyReport.id == self._parse_uuid(a.source_id))))).scalar_one_or_none()
                        if r:
                            matched_report_ids.add(r.id)
                    elif a.source_type == CaseSourceType.ASSESSMENT:
                        u = self._parse_uuid(a.source_id)
                        if u:
                            matched_assessment_ids.add(u)
                    elif a.source_type == CaseSourceType.PATTERN:
                        pat = (await self.session.execute(select(PrecursorPattern).where((PrecursorPattern.pattern_code == a.source_id) | (PrecursorPattern.id == self._parse_uuid(a.source_id))))).scalar_one_or_none()
                        if pat:
                            matched_pattern_ids.add(pat.id)
                    elif a.source_type == CaseSourceType.CONCENTRATION:
                        conc = (await self.session.execute(select(RiskConcentration).where((RiskConcentration.concentration_key == a.source_id) | (RiskConcentration.id == self._parse_uuid(a.source_id))))).scalar_one_or_none()
                        if conc:
                            matched_concentration_ids.add(conc.id)
                    elif a.source_type == CaseSourceType.REVIEW:
                        u = self._parse_uuid(a.source_id)
                        if u:
                            matched_review_ids.add(u)
                    elif a.source_type == CaseSourceType.ACTION:
                        act = (await self.session.execute(select(HSEActionRecommendation).where((HSEActionRecommendation.action_key == a.source_id) | (HSEActionRecommendation.id == self._parse_uuid(a.source_id))))).scalar_one_or_none()
                        if act:
                            matched_action_ids.add(act.id)

        # Target 3: pattern_code
        if pattern_code:
            pat = (await self.session.execute(select(PrecursorPattern).where(PrecursorPattern.pattern_code == pattern_code))).scalar_one_or_none()
            if pat:
                matched_pattern_ids.add(pat.id)
                for rid in (pat.supporting_report_ids or []):
                    r_uuid = self._parse_uuid(rid)
                    if r_uuid:
                        matched_report_ids.add(r_uuid)
                    else:
                        r = (await self.session.execute(select(SafetyReport).where(SafetyReport.report_ref == rid))).scalar_one_or_none()
                        if r:
                            matched_report_ids.add(r.id)

        # Target 4: concentration_key
        if concentration_key:
            conc = (await self.session.execute(select(RiskConcentration).where(RiskConcentration.concentration_key == concentration_key))).scalar_one_or_none()
            if conc:
                matched_concentration_ids.add(conc.id)
                if conc.pattern_id:
                    matched_pattern_ids.add(conc.pattern_id)
                for rid in (conc.supporting_report_ids or []):
                    r_uuid = self._parse_uuid(rid)
                    if r_uuid:
                        matched_report_ids.add(r_uuid)

        # Expand operational chain from matched reports
        if matched_report_ids:
            # Assessments
            asm_rows = (await self.session.execute(select(SIFAssessment).where(SIFAssessment.report_id.in_(matched_report_ids)))).scalars().all()
            for asm in asm_rows:
                matched_assessment_ids.add(asm.id)
                if asm.pattern_id:
                    matched_pattern_ids.add(asm.pattern_id)

            # Reviews
            rev_rows = (await self.session.execute(select(TriageReview).where(TriageReview.report_id.in_(matched_report_ids)))).scalars().all()
            for rev in rev_rows:
                matched_review_ids.add(rev.id)

        # Expand actions from matched assessments / patterns / concentrations
        action_source_ids = [str(uid) for uid in (matched_assessment_ids | matched_pattern_ids | matched_concentration_ids | matched_report_ids)]
        if action_source_ids:
            act_rows = (await self.session.execute(select(HSEActionRecommendation).where(HSEActionRecommendation.source_id.in_(action_source_ids)))).scalars().all()
            for act in act_rows:
                matched_action_ids.add(act.id)

        # Fetch concrete objects for response DTOs
        reports = []
        if matched_report_ids:
            rep_objs = (await self.session.execute(select(SafetyReport).where(SafetyReport.id.in_(matched_report_ids)).order_by(SafetyReport.created_at.desc()))).scalars().all()
            reports = [
                SnapshotReportNode(
                    id=r.id,
                    report_ref=r.report_ref,
                    source_type=r.source_type,
                    reported_location=r.reported_location,
                    created_at=r.created_at,
                )
                for r in rep_objs
            ]

        assessments = []
        if matched_assessment_ids:
            asm_objs = (await self.session.execute(select(SIFAssessment).where(SIFAssessment.id.in_(matched_assessment_ids)).order_by(SIFAssessment.evidence_score.desc()))).scalars().all()
            assessments = [
                SnapshotAssessmentNode(
                    id=a.id,
                    report_id=a.report_id,
                    sif_classification=a.sif_classification,
                    potential_severity=a.potential_severity,
                    evidence_score=a.evidence_score,
                    precursor_signature=a.precursor_signature,
                )
                for a in asm_objs
            ]

        patterns = []
        if matched_pattern_ids:
            pat_objs = (await self.session.execute(select(PrecursorPattern).where(PrecursorPattern.id.in_(matched_pattern_ids)).order_by(PrecursorPattern.first_detected_at.desc()))).scalars().all()
            patterns = [
                SnapshotPatternNode(
                    id=p.id,
                    pattern_code=p.pattern_code,
                    title=p.title,
                    occurrence_count=p.occurrence_count,
                )
                for p in pat_objs
            ]

        concentrations = []
        if matched_concentration_ids:
            conc_objs = (await self.session.execute(select(RiskConcentration).where(RiskConcentration.id.in_(matched_concentration_ids)).order_by(RiskConcentration.created_at.desc()))).scalars().all()
            concentrations = [
                SnapshotConcentrationNode(
                    id=c.id,
                    concentration_key=c.concentration_key,
                    dimension_type=c.dimension_type,
                    dimension_value=c.dimension_value,
                    occurrence_count=c.occurrence_count,
                )
                for c in conc_objs
            ]

        reviews = []
        if matched_review_ids:
            rev_objs = (await self.session.execute(select(TriageReview).where(TriageReview.id.in_(matched_review_ids)).order_by(TriageReview.created_at.desc()))).scalars().all()
            reviews = [
                SnapshotReviewNode(
                    id=rv.id,
                    report_id=rv.report_id,
                    status=rv.status,
                    decision=rv.decision,
                    reviewer_id=rv.reviewer_id,
                )
                for rv in rev_objs
            ]

        actions = []
        if matched_action_ids:
            act_objs = (await self.session.execute(select(HSEActionRecommendation).where(HSEActionRecommendation.id.in_(matched_action_ids)).order_by(HSEActionRecommendation.created_at.desc()))).scalars().all()
            actions = [
                SnapshotActionNode(
                    id=ac.id,
                    action_key=ac.action_key,
                    action_title=ac.action_title,
                    status=ac.status,
                    priority=ac.priority,
                )
                for ac in act_objs
            ]

        cases = []
        if matched_case_ids:
            case_objs = (await self.session.execute(select(HSECase).where(HSECase.id.in_(matched_case_ids)).order_by(HSECase.created_at.desc()))).scalars().all()
            cases = [
                SnapshotCaseNode(
                    id=cs.id,
                    case_key=cs.case_key,
                    title=cs.title,
                    status=cs.status,
                    priority=cs.priority,
                )
                for cs in case_objs
            ]

        summary = {
            "report_count": len(reports),
            "assessment_count": len(assessments),
            "pattern_count": len(patterns),
            "concentration_count": len(concentrations),
            "review_count": len(reviews),
            "action_count": len(actions),
            "case_count": len(cases),
        }

        return InvestigationSnapshotDTO(
            generated_at=now,
            query_target=query_target,
            reports=reports,
            assessments=assessments,
            patterns=patterns,
            concentrations=concentrations,
            reviews=reviews,
            actions=actions,
            cases=cases,
            summary=summary,
        )

    def _parse_uuid(self, val: Any) -> Optional[uuid.UUID]:
        """Safely parse string to UUID without throwing."""
        if isinstance(val, uuid.UUID):
            return val
        try:
            return uuid.UUID(str(val))
        except (ValueError, TypeError, AttributeError):
            return None
