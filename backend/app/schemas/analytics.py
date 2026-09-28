"""Pydantic schemas for SIF risk concentration findings and aggregated analytics."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import ConcentrationDimension, ConcentrationStatus, ObservedTrend


class RiskConcentrationDTO(BaseModel):
    """Data transfer object for an explainable SIF risk concentration finding."""
    id: uuid.UUID
    concentration_key: str
    dimension_type: ConcentrationDimension
    dimension_value: str
    pattern_id: Optional[uuid.UUID] = None
    occurrence_count: int = Field(..., ge=1)
    distinct_report_count: int = Field(..., ge=1)
    distinct_location_count: int = Field(..., ge=0)
    first_observed_at: datetime
    last_observed_at: datetime
    observed_trend: ObservedTrend
    temporal_distribution: Dict[str, int] = Field(default_factory=dict)
    supporting_report_ids: List[uuid.UUID] = Field(default_factory=list)
    supporting_pattern_ids: List[uuid.UUID] = Field(default_factory=list)
    supporting_locations: List[str] = Field(default_factory=list)
    supporting_lsr_codes: List[str] = Field(default_factory=list)
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)
    calculation_method: str
    status: ConcentrationStatus
    created_at: datetime
    updated_at: datetime


class ConcentrationListResponse(BaseModel):
    """Paginated response containing SIF risk concentration findings."""
    total_concentrations: int = Field(..., ge=0)
    dimension_filter: Optional[ConcentrationDimension] = None
    trend_filter: Optional[ObservedTrend] = None
    concentrations: List[RiskConcentrationDTO] = Field(default_factory=list)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)


class ConcentrationRefreshResponse(BaseModel):
    """Response returned when refreshing / recalculating risk concentrations."""
    run_id: uuid.UUID
    calculation_method: str
    assessments_evaluated: int = Field(..., ge=0)
    concentrations_created: int = Field(..., ge=0)
    concentrations_updated: int = Field(..., ge=0)
    total_active_concentrations: int = Field(..., ge=0)
    dimension_breakdown: Dict[str, int] = Field(default_factory=dict)
    concentrations: List[RiskConcentrationDTO] = Field(default_factory=list)


class TemporalTrendItem(BaseModel):
    """Trend item for a specific operational finding."""
    dimension_type: ConcentrationDimension
    dimension_value: str
    observed_trend: ObservedTrend
    occurrence_count: int = Field(..., ge=0)
    temporal_distribution: Dict[str, int] = Field(default_factory=dict)


class TrendsResponse(BaseModel):
    """Aggregate observed trends across operational dimensions."""
    time_bucket: str
    total_findings: int = Field(..., ge=0)
    trend_summary: Dict[str, int] = Field(default_factory=dict)
    trends: List[TemporalTrendItem] = Field(default_factory=list)


class DimensionDistributionItem(BaseModel):
    """Occurrence metrics for a category within a concentration dimension."""
    dimension_value: str
    occurrence_count: int = Field(..., ge=0)
    distinct_reports: int = Field(..., ge=0)
    distinct_locations: int = Field(..., ge=0)
    observed_trend: ObservedTrend


class DimensionDistributionResponse(BaseModel):
    """Categorical distribution breakdown for a requested concentration dimension."""
    dimension_type: ConcentrationDimension
    total_occurrences: int = Field(..., ge=0)
    distinct_categories: int = Field(..., ge=0)
    items: List[DimensionDistributionItem] = Field(default_factory=list)


class LSRDistributionItem(BaseModel):
    """Distribution count for a specific Life-Saving Rule."""
    rule_code: str
    rule_name: str
    count: int
    sif_count: int


class LocationConcentrationItem(BaseModel):
    """Factual concentration summary for a specific operating location or facility ordered by observed occurrences."""
    location: str = Field(..., description="Operating facility or location name")
    total_reports: int = Field(..., description="Total observed SIF occurrences at this location")
    sif_potential_count: int = Field(..., description="Distinct SIF-eligible reports at this location")
    sif_proportion: float = Field(default=1.0, description="Factual proportion of SIF reports (0.0 to 1.0), not a predictive risk score")


# Backward compatible alias for legacy imports
LocationRiskItem = LocationConcentrationItem


class AnalyticsSummaryResponse(BaseModel):
    """High-level safety dashboard analytics payload."""
    total_reports_analyzed: int = Field(..., ge=0)
    total_sif_potential_count: int = Field(..., ge=0)
    sif_potential_percentage: float = Field(..., ge=0.0, le=100.0)
    actual_sif_count: int = Field(..., ge=0)
    non_sif_count: int = Field(..., ge=0)
    undetermined_count: int = Field(..., ge=0)
    active_precursor_patterns_count: int = Field(default=0, ge=0)
    active_risk_concentrations_count: int = Field(default=0, ge=0)
    top_life_saving_rules: List[LSRDistributionItem] = Field(default_factory=list)
    location_concentrations: List[LocationConcentrationItem] = Field(
        default_factory=list,
        description="Observed location occurrence concentrations ordered by frequency (descriptive occurrence ordering, not risk ranking)",
    )

