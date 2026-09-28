"""Application service for SIF risk concentration aggregation, temporal distribution, and intelligence."""

import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.db.models.assessment import SIFAssessment
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.domain.concentration.models import (
    ConcentrationEvidence,
    generate_concentration_key,
    normalize_dimension_identity,
)
from app.domain.concentration.trend import TrendEvaluator
from app.domain.enums import (
    ConcentrationDimension,
    ConcentrationStatus,
    ObservedTrend,
    SIFClassification,
)
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    ConcentrationListResponse,
    ConcentrationRefreshResponse,
    DimensionDistributionItem,
    DimensionDistributionResponse,
    LocationConcentrationItem,
    LSRDistributionItem,
    RiskConcentrationDTO,
    TemporalTrendItem,
    TrendsResponse,
)

logger = get_logger(__name__)


class RiskConcentrationService:
    """Service orchestrating multi-dimensional SIF risk concentration findings and temporal analysis."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    @staticmethod
    def _clean_string(text: Optional[str]) -> Optional[str]:
        """Sanitize text and reject placeholder values."""
        if text is None:
            return None
        cleaned = str(text).strip()
        if not cleaned or cleaned.upper() in ("*", "UNKNOWN", "OTHER", "N/A", "NONE", "NULL", "UNSPECIFIED"):
            return None
        return cleaned

    @classmethod
    def _format_time_bucket(cls, dt: datetime, bucket_type: str = "MONTH") -> str:
        """Format datetime into deterministic chronological string bucket (default: YYYY-MM)."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m")

    async def refresh_concentrations(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        time_bucket: Optional[str] = None,
        min_trend_periods: Optional[int] = None,
    ) -> ConcentrationRefreshResponse:
        """Aggregate SIF-eligible assessments and precursor patterns across operational dimensions."""
        run_id = uuid.uuid4()
        eff_bucket = time_bucket or self.settings.CONCENTRATION_TIME_BUCKET
        eff_min_trend = min_trend_periods or self.settings.CONCENTRATION_MIN_TREND_PERIODS
        eligible_classifications = self.settings.PATTERN_ELIGIBLE_SIF_CLASSIFICATIONS

        logger.info(
            f"Starting risk concentration aggregation run_id={run_id} "
            f"(bucket={eff_bucket}, min_trend_periods={eff_min_trend}, eligible={eligible_classifications})"
        )

        # 1. Retrieve SIF-eligible assessments joined with SafetyReport
        stmt = (
            select(SIFAssessment, SafetyReport)
            .join(SafetyReport, SIFAssessment.report_id == SafetyReport.id)
            .where(SIFAssessment.sif_classification.in_(eligible_classifications))
        )

        if start_date is not None:
            stmt = stmt.where(SafetyReport.event_timestamp >= start_date)
        if end_date is not None:
            stmt = stmt.where(SafetyReport.event_timestamp <= end_date)

        res = await self.session.execute(stmt)
        assessment_rows = res.all()

        # 2. Retrieve active recurring precursor patterns
        stmt_patterns = select(PrecursorPattern)
        res_patterns = await self.session.execute(stmt_patterns)
        pattern_rows = res_patterns.scalars().all()
        pattern_map = {p.id: p for p in pattern_rows}

        logger.info(
            f"Retrieved {len(assessment_rows)} SIF-eligible assessments and {len(pattern_rows)} precursor patterns"
        )

        # 3. Data structures for dimensional grouping
        # DimensionKey = (ConcentrationDimension, dimension_value, Optional[pattern_id], Optional[pattern_code])
        # Value = list of item dicts
        dim_aggregates: Dict[Tuple[ConcentrationDimension, str, Optional[uuid.UUID], Optional[str]], List[Dict[str, Any]]] = defaultdict(list)

        # A. Process assessments across 5 dimensions: HAZARD, BARRIER_FAILURE, ACTIVITY, LIFE_SAVING_RULE, LOCATION
        for assessment, report in assessment_rows:
            prec = assessment.structured_precursor or {}
            ts = report.event_timestamp or report.created_at or assessment.assessed_at or datetime.now(timezone.utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            loc = self._clean_string(report.reported_location)
            hazard = self._clean_string(prec.get("hazard"))
            barrier = self._clean_string(prec.get("barrier_failure"))
            activity = self._clean_string(prec.get("activity"))
            lsr = self._clean_string(prec.get("life_saving_rule"))

            item_data = {
                "report_id": report.id,
                "assessment_id": assessment.id,
                "pattern_id": assessment.pattern_id,
                "location": loc,
                "timestamp": ts,
                "lsr_code": lsr,
                "hazard": hazard,
                "barrier": barrier,
                "activity": activity,
            }

            if hazard:
                dim_aggregates[(ConcentrationDimension.HAZARD, hazard, None, None)].append(item_data)
            if barrier:
                dim_aggregates[(ConcentrationDimension.BARRIER_FAILURE, barrier, None, None)].append(item_data)
            if activity:
                dim_aggregates[(ConcentrationDimension.ACTIVITY, activity, None, None)].append(item_data)
            if lsr:
                dim_aggregates[(ConcentrationDimension.LIFE_SAVING_RULE, lsr, None, None)].append(item_data)
            if loc:
                dim_aggregates[(ConcentrationDimension.LOCATION, loc, None, None)].append(item_data)

        # B. Process recurring precursor patterns for the PATTERN dimension
        for pattern in pattern_rows:
            # Map pattern member reports
            str_rids = pattern.supporting_report_ids or []
            pattern_report_uuids = [uuid.UUID(rid) for rid in str_rids if rid]

            # Find matching assessments/reports
            matching_items = []
            for ass, rep in assessment_rows:
                if rep.id in pattern_report_uuids:
                    ts_pat = rep.event_timestamp or rep.created_at or datetime.now(timezone.utc)
                    if ts_pat.tzinfo is None:
                        ts_pat = ts_pat.replace(tzinfo=timezone.utc)
                    else:
                        ts_pat = ts_pat.astimezone(timezone.utc)

                    matching_items.append({
                        "report_id": rep.id,
                        "assessment_id": ass.id,
                        "pattern_id": pattern.id,
                        "location": self._clean_string(rep.reported_location),
                        "timestamp": ts_pat,
                        "lsr_code": pattern.lsr_code,
                        "hazard": pattern.hazard_category,
                        "barrier": pattern.failed_barrier_type,
                        "activity": pattern.activity_type,
                    })

            dim_aggregates[(ConcentrationDimension.PATTERN, pattern.title, pattern.id, pattern.pattern_code)] = matching_items

        # 4. Synthesize Concentration Findings
        findings: List[Dict[str, Any]] = []
        dimension_breakdown: Dict[str, int] = defaultdict(int)

        for (dim_type, dim_val, pat_id, pat_code), items in dim_aggregates.items():
            if not items and dim_type != ConcentrationDimension.PATTERN:
                continue

            # Deterministic stable concentration key
            if dim_type == ConcentrationDimension.PATTERN and pat_code:
                conc_key = f"CONC|PATTERN|{normalize_dimension_identity(pat_code)}"[:120]
            else:
                conc_key = generate_concentration_key(dim_type, dim_val)

            # Extract distinct reports and locations
            rep_ids = sorted(list({item["report_id"] for item in items}), key=lambda x: str(x))
            locs = sorted(list({item["location"] for item in items if item.get("location") is not None}))
            lsrs = sorted(list({item["lsr_code"] for item in items if item.get("lsr_code") is not None}))
            pat_ids = sorted(list({item["pattern_id"] for item in items if item.get("pattern_id") is not None}), key=lambda x: str(x))

            # Temporal bounds & distribution
            timestamps: List[datetime] = []
            for item in items:
                ts_item = item.get("timestamp")
                if isinstance(ts_item, datetime):
                    if ts_item.tzinfo is None:
                        ts_item = ts_item.replace(tzinfo=timezone.utc)
                    else:
                        ts_item = ts_item.astimezone(timezone.utc)
                    timestamps.append(ts_item)

            if not timestamps:
                now = datetime.now(timezone.utc)
                first_obs = now
                last_obs = now
            else:
                first_obs = min(timestamps)
                last_obs = max(timestamps)

            # Temporal distribution buckets
            temporal_dist: Dict[str, int] = defaultdict(int)
            for ts in timestamps:
                bucket_key = self._format_time_bucket(ts, eff_bucket)
                temporal_dist[bucket_key] += 1

            # Observed trend classification using descriptive engineering ratio parameters
            observed_trend = TrendEvaluator.evaluate_trend(
                dict(temporal_dist),
                min_periods=eff_min_trend,
                increase_ratio=self.settings.CONCENTRATION_TREND_INCREASE_RATIO,
                decrease_ratio=self.settings.CONCENTRATION_TREND_DECREASE_RATIO,
            )

            # Occurrence and distinct counts
            occ_count = len(items) if items else 1
            dist_rep_count = len(rep_ids) if rep_ids else 1
            dist_loc_count = len(locs)

            # Explainable evidence summary
            explanation = (
                f"Observed {occ_count} SIF-eligible occurrences for {dim_type.value} '{dim_val}' "
                f"across {dist_loc_count} operational locations ({dist_rep_count} distinct reports). "
                f"Observed trend is {observed_trend.value} across {len(temporal_dist)} chronological reporting periods."
            )

            evidence_summary = {
                "dimension": dim_type.value,
                "value": dim_val,
                "occurrence_count": occ_count,
                "distinct_report_count": dist_rep_count,
                "distinct_location_count": dist_loc_count,
                "report_ids": [str(rid) for rid in rep_ids],
                "pattern_ids": [str(pid) for pid in pat_ids],
                "locations": locs,
                "lsr_codes": lsrs,
                "first_observed_at": first_obs.isoformat(),
                "last_observed_at": last_obs.isoformat(),
                "temporal_distribution": dict(temporal_dist),
                "observed_trend": observed_trend.value,
                "explanation": explanation,
            }

            findings.append({
                "concentration_key": conc_key,
                "dimension_type": dim_type,
                "dimension_value": dim_val,
                "pattern_id": pat_id,
                "occurrence_count": occ_count,
                "distinct_report_count": dist_rep_count,
                "distinct_location_count": dist_loc_count,
                "first_observed_at": first_obs,
                "last_observed_at": last_obs,
                "observed_trend": observed_trend,
                "temporal_distribution": dict(temporal_dist),
                "supporting_report_ids": [str(rid) for rid in rep_ids],
                "supporting_pattern_ids": [str(pid) for pid in pat_ids],
                "supporting_locations": locs,
                "supporting_lsr_codes": lsrs,
                "evidence_summary": evidence_summary,
                "calculation_method": self.settings.CONCENTRATION_CALCULATION_METHOD,
                "status": ConcentrationStatus.ACTIVE,
            })
            dimension_breakdown[dim_type.value] += 1

        # 5. Persist / Upsert into risk_concentrations table
        created_count = 0
        updated_count = 0
        persisted_dtos: List[RiskConcentrationDTO] = []

        for finding_data in findings:
            conc_key = finding_data["concentration_key"]
            stmt_exist = select(RiskConcentration).where(RiskConcentration.concentration_key == conc_key)
            res_exist = await self.session.execute(stmt_exist)
            existing_record = res_exist.scalar_one_or_none()

            now_utc = datetime.now(timezone.utc)

            if existing_record:
                existing_record.dimension_value = finding_data["dimension_value"]
                existing_record.pattern_id = finding_data["pattern_id"]
                existing_record.occurrence_count = finding_data["occurrence_count"]
                existing_record.distinct_report_count = finding_data["distinct_report_count"]
                existing_record.distinct_location_count = finding_data["distinct_location_count"]
                existing_record.first_observed_at = finding_data["first_observed_at"]
                existing_record.last_observed_at = finding_data["last_observed_at"]
                existing_record.observed_trend = finding_data["observed_trend"]
                existing_record.temporal_distribution = finding_data["temporal_distribution"]
                existing_record.supporting_report_ids = finding_data["supporting_report_ids"]
                existing_record.supporting_pattern_ids = finding_data["supporting_pattern_ids"]
                existing_record.supporting_locations = finding_data["supporting_locations"]
                existing_record.supporting_lsr_codes = finding_data["supporting_lsr_codes"]
                existing_record.evidence_summary = finding_data["evidence_summary"]
                existing_record.calculation_method = finding_data["calculation_method"]
                existing_record.status = finding_data["status"]
                existing_record.updated_at = now_utc
                record_db = existing_record
                updated_count += 1
            else:
                record_db = RiskConcentration(
                    id=uuid.uuid4(),
                    concentration_key=conc_key,
                    dimension_type=finding_data["dimension_type"],
                    dimension_value=finding_data["dimension_value"],
                    pattern_id=finding_data["pattern_id"],
                    occurrence_count=finding_data["occurrence_count"],
                    distinct_report_count=finding_data["distinct_report_count"],
                    distinct_location_count=finding_data["distinct_location_count"],
                    first_observed_at=finding_data["first_observed_at"],
                    last_observed_at=finding_data["last_observed_at"],
                    observed_trend=finding_data["observed_trend"],
                    temporal_distribution=finding_data["temporal_distribution"],
                    supporting_report_ids=finding_data["supporting_report_ids"],
                    supporting_pattern_ids=finding_data["supporting_pattern_ids"],
                    supporting_locations=finding_data["supporting_locations"],
                    supporting_lsr_codes=finding_data["supporting_lsr_codes"],
                    evidence_summary=finding_data["evidence_summary"],
                    calculation_method=finding_data["calculation_method"],
                    status=finding_data["status"],
                    created_at=now_utc,
                    updated_at=now_utc,
                )
                self.session.add(record_db)
                created_count += 1

            await self.session.flush()

            dto = RiskConcentrationDTO(
                id=record_db.id,
                concentration_key=record_db.concentration_key,
                dimension_type=record_db.dimension_type,
                dimension_value=record_db.dimension_value,
                pattern_id=record_db.pattern_id,
                occurrence_count=record_db.occurrence_count,
                distinct_report_count=record_db.distinct_report_count,
                distinct_location_count=record_db.distinct_location_count,
                first_observed_at=record_db.first_observed_at,
                last_observed_at=record_db.last_observed_at,
                observed_trend=record_db.observed_trend,
                temporal_distribution=record_db.temporal_distribution,
                supporting_report_ids=[uuid.UUID(rid) for rid in record_db.supporting_report_ids if rid],
                supporting_pattern_ids=[uuid.UUID(pid) for pid in record_db.supporting_pattern_ids if pid],
                supporting_locations=record_db.supporting_locations,
                supporting_lsr_codes=record_db.supporting_lsr_codes,
                evidence_summary=record_db.evidence_summary,
                calculation_method=record_db.calculation_method,
                status=record_db.status,
                created_at=record_db.created_at,
                updated_at=record_db.updated_at,
            )
            persisted_dtos.append(dto)

        logger.info(
            f"Risk concentration aggregation completed: created={created_count}, updated={updated_count}, total={len(persisted_dtos)}"
        )

        return ConcentrationRefreshResponse(
            run_id=run_id,
            calculation_method=self.settings.CONCENTRATION_CALCULATION_METHOD,
            assessments_evaluated=len(assessment_rows),
            concentrations_created=created_count,
            concentrations_updated=updated_count,
            total_active_concentrations=len(persisted_dtos),
            dimension_breakdown=dict(dimension_breakdown),
            concentrations=persisted_dtos,
        )

    async def get_concentrations(
        self,
        dimension: Optional[ConcentrationDimension] = None,
        location: Optional[str] = None,
        lsr_code: Optional[str] = None,
        trend: Optional[ObservedTrend] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ConcentrationListResponse:
        """Query and paginate persisted SIF risk concentration findings with multi-attribute filtering."""
        stmt = select(RiskConcentration).where(RiskConcentration.status == ConcentrationStatus.ACTIVE)

        if dimension is not None:
            stmt = stmt.where(RiskConcentration.dimension_type == dimension)
        if trend is not None:
            stmt = stmt.where(RiskConcentration.observed_trend == trend)
        if location is not None:
            stmt = stmt.where(RiskConcentration.supporting_locations.contains([location]))
        if lsr_code is not None:
            stmt = stmt.where(RiskConcentration.supporting_lsr_codes.contains([lsr_code]))
        if start_date is not None:
            stmt = stmt.where(RiskConcentration.last_observed_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(RiskConcentration.first_observed_at <= end_date)

        # Count total matching
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        # Order by occurrence_count descending, then last_observed_at descending
        stmt = stmt.order_by(RiskConcentration.occurrence_count.desc(), RiskConcentration.last_observed_at.desc())
        stmt = stmt.limit(limit).offset(offset)

        res = await self.session.execute(stmt)
        rows = res.scalars().all()

        dtos = [
            RiskConcentrationDTO(
                id=r.id,
                concentration_key=r.concentration_key,
                dimension_type=r.dimension_type,
                dimension_value=r.dimension_value,
                pattern_id=r.pattern_id,
                occurrence_count=r.occurrence_count,
                distinct_report_count=r.distinct_report_count,
                distinct_location_count=r.distinct_location_count,
                first_observed_at=r.first_observed_at,
                last_observed_at=r.last_observed_at,
                observed_trend=r.observed_trend,
                temporal_distribution=r.temporal_distribution,
                supporting_report_ids=[uuid.UUID(rid) for rid in r.supporting_report_ids if rid],
                supporting_pattern_ids=[uuid.UUID(pid) for pid in r.supporting_pattern_ids if pid],
                supporting_locations=r.supporting_locations,
                supporting_lsr_codes=r.supporting_lsr_codes,
                evidence_summary=r.evidence_summary,
                calculation_method=r.calculation_method,
                status=r.status,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]

        return ConcentrationListResponse(
            total_concentrations=total,
            dimension_filter=dimension,
            trend_filter=trend,
            concentrations=dtos,
            limit=limit,
            offset=offset,
        )

    async def get_concentration_by_id(self, concentration_id: uuid.UUID) -> Optional[RiskConcentrationDTO]:
        """Retrieve a single risk concentration finding by UUID."""
        stmt = select(RiskConcentration).where(RiskConcentration.id == concentration_id)
        res = await self.session.execute(stmt)
        r = res.scalar_one_or_none()
        if not r:
            return None

        return RiskConcentrationDTO(
            id=r.id,
            concentration_key=r.concentration_key,
            dimension_type=r.dimension_type,
            dimension_value=r.dimension_value,
            pattern_id=r.pattern_id,
            occurrence_count=r.occurrence_count,
            distinct_report_count=r.distinct_report_count,
            distinct_location_count=r.distinct_location_count,
            first_observed_at=r.first_observed_at,
            last_observed_at=r.last_observed_at,
            observed_trend=r.observed_trend,
            temporal_distribution=r.temporal_distribution,
            supporting_report_ids=[uuid.UUID(rid) for rid in r.supporting_report_ids if rid],
            supporting_pattern_ids=[uuid.UUID(pid) for pid in r.supporting_pattern_ids if pid],
            supporting_locations=r.supporting_locations,
            supporting_lsr_codes=r.supporting_lsr_codes,
            evidence_summary=r.evidence_summary,
            calculation_method=r.calculation_method,
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )

    async def get_trends(self, dimension: Optional[ConcentrationDimension] = None) -> TrendsResponse:
        """Retrieve aggregate trend classifications across operational findings."""
        stmt = select(RiskConcentration).where(RiskConcentration.status == ConcentrationStatus.ACTIVE)
        if dimension is not None:
            stmt = stmt.where(RiskConcentration.dimension_type == dimension)

        res = await self.session.execute(stmt)
        rows = res.scalars().all()

        trend_summary: Dict[str, int] = defaultdict(int)
        items: List[TemporalTrendItem] = []

        for r in rows:
            trend_summary[r.observed_trend.value] += 1
            items.append(
                TemporalTrendItem(
                    dimension_type=r.dimension_type,
                    dimension_value=r.dimension_value,
                    observed_trend=r.observed_trend,
                    occurrence_count=r.occurrence_count,
                    temporal_distribution=r.temporal_distribution,
                )
            )

        items.sort(key=lambda x: x.occurrence_count, reverse=True)

        return TrendsResponse(
            time_bucket=self.settings.CONCENTRATION_TIME_BUCKET,
            total_findings=len(rows),
            trend_summary=dict(trend_summary),
            trends=items,
        )

    async def get_distribution(self, dimension: ConcentrationDimension) -> DimensionDistributionResponse:
        """Retrieve categorical occurrence distribution for a specific concentration dimension."""
        stmt = (
            select(RiskConcentration)
            .where(
                RiskConcentration.dimension_type == dimension,
                RiskConcentration.status == ConcentrationStatus.ACTIVE,
            )
            .order_by(RiskConcentration.occurrence_count.desc())
        )
        res = await self.session.execute(stmt)
        rows = res.scalars().all()

        items = [
            DimensionDistributionItem(
                dimension_value=r.dimension_value,
                occurrence_count=r.occurrence_count,
                distinct_reports=r.distinct_report_count,
                distinct_locations=r.distinct_location_count,
                observed_trend=r.observed_trend,
            )
            for r in rows
        ]

        total_occurrences = sum(i.occurrence_count for i in items)

        return DimensionDistributionResponse(
            dimension_type=dimension,
            total_occurrences=total_occurrences,
            distinct_categories=len(items),
            items=items,
        )

    async def get_analytics_summary(self) -> AnalyticsSummaryResponse:
        """Calculate factual safety summary metrics across all reports and assessments."""
        # 1. Total counts by SIF classification
        stmt_counts = select(
            SIFAssessment.sif_classification,
            func.count(SIFAssessment.id).label("count"),
        ).group_by(SIFAssessment.sif_classification)

        res_counts = await self.session.execute(stmt_counts)
        class_counts = {row[0]: row[1] for row in res_counts.all()}

        potential_sif = class_counts.get(SIFClassification.POTENTIAL_SIF, 0)
        actual_sif = class_counts.get(SIFClassification.ACTUAL_SIF, 0)
        non_sif = class_counts.get(SIFClassification.NON_SIF, 0)
        undetermined = class_counts.get(SIFClassification.UNDETERMINED, 0)
        total_analyzed = sum(class_counts.values())

        sif_pct = round((potential_sif / total_analyzed * 100.0), 2) if total_analyzed > 0 else 0.0

        # 2. Active precursor patterns and risk concentrations
        stmt_pat_count = select(func.count(PrecursorPattern.id))
        pat_count_res = await self.session.execute(stmt_pat_count)
        active_patterns = pat_count_res.scalar_one()

        stmt_conc_count = select(func.count(RiskConcentration.id)).where(RiskConcentration.status == ConcentrationStatus.ACTIVE)
        conc_count_res = await self.session.execute(stmt_conc_count)
        active_concentrations = conc_count_res.scalar_one()

        # 3. Top LSR distributions from concentration or assessment records
        stmt_lsr = (
            select(RiskConcentration)
            .where(
                RiskConcentration.dimension_type == ConcentrationDimension.LIFE_SAVING_RULE,
                RiskConcentration.status == ConcentrationStatus.ACTIVE,
            )
            .order_by(RiskConcentration.occurrence_count.desc())
            .limit(10)
        )
        res_lsr = await self.session.execute(stmt_lsr)
        lsr_rows = res_lsr.scalars().all()

        top_lsrs = [
            LSRDistributionItem(
                rule_code=r.dimension_value,
                rule_name=r.dimension_value,
                count=r.occurrence_count,
                sif_count=r.distinct_report_count,
            )
            for r in lsr_rows
        ]

        # 4. Operating location concentrations (ordered by observed occurrence count)
        stmt_loc = (
            select(RiskConcentration)
            .where(
                RiskConcentration.dimension_type == ConcentrationDimension.LOCATION,
                RiskConcentration.status == ConcentrationStatus.ACTIVE,
            )
            .order_by(RiskConcentration.occurrence_count.desc())
            .limit(10)
        )
        res_loc = await self.session.execute(stmt_loc)
        loc_rows = res_loc.scalars().all()

        location_concentrations = [
            LocationConcentrationItem(
                location=r.dimension_value,
                total_reports=r.occurrence_count,
                sif_potential_count=r.distinct_report_count,
                sif_proportion=round(r.distinct_report_count / max(1, r.occurrence_count), 2),
            )
            for r in loc_rows
        ]

        return AnalyticsSummaryResponse(
            total_reports_analyzed=total_analyzed,
            total_sif_potential_count=potential_sif,
            sif_potential_percentage=sif_pct,
            actual_sif_count=actual_sif,
            non_sif_count=non_sif,
            undetermined_count=undetermined,
            active_precursor_patterns_count=active_patterns,
            active_risk_concentrations_count=active_concentrations,
            top_life_saving_rules=top_lsrs,
            location_concentrations=location_concentrations,
        )
