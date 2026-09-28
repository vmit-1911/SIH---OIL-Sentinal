"""Safety dashboard analytics, KPI summaries, and SIF risk concentration endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.domain.enums import ConcentrationDimension, ObservedTrend
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    ConcentrationListResponse,
    ConcentrationRefreshResponse,
    DimensionDistributionResponse,
    RiskConcentrationDTO,
    TrendsResponse,
)
from app.schemas.common import ErrorResponse
from app.services.risk_concentration_service import RiskConcentrationService

router = APIRouter()


@router.get(
    "/sif/analytics/concentrations",
    response_model=ConcentrationListResponse,
    summary="List SIF Risk Concentrations",
    description="Retrieves aggregated, explainable SIF risk concentrations across operational dimensions.",
)
async def list_concentrations(
    dimension: Optional[ConcentrationDimension] = Query(
        None,
        description="Filter by concentration dimension (PATTERN, HAZARD, BARRIER_FAILURE, ACTIVITY, LIFE_SAVING_RULE, LOCATION)",
    ),
    location: Optional[str] = Query(
        None,
        description="Filter by operational location string",
    ),
    lsr_code: Optional[str] = Query(
        None,
        description="Filter by supporting Life-Saving Rule code",
    ),
    trend: Optional[ObservedTrend] = Query(
        None,
        description="Filter by observed trend (STABLE, INCREASING, DECREASING, INSUFFICIENT_DATA)",
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Filter observations after start date (ISO 8601)",
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter observations before end date (ISO 8601)",
    ),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db_session),
) -> ConcentrationListResponse:
    """Retrieve filtered and paginated SIF risk concentrations."""
    service = RiskConcentrationService(db)
    return await service.get_concentrations(
        dimension=dimension,
        location=location,
        lsr_code=lsr_code,
        trend=trend,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/sif/analytics/concentrations/{concentration_id}",
    response_model=RiskConcentrationDTO,
    responses={
        404: {"model": ErrorResponse, "description": "Risk concentration finding not found"},
    },
    summary="Get Risk Concentration Details",
    description="Retrieve details, temporal distributions, supporting reports, and explainable evidence for a specific concentration finding.",
)
async def get_concentration_detail(
    concentration_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> RiskConcentrationDTO:
    """Retrieve details of an individual risk concentration finding."""
    service = RiskConcentrationService(db)
    result = await service.get_concentration_by_id(concentration_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk concentration finding '{concentration_id}' was not found.",
        )
    return result


@router.post(
    "/sif/analytics/concentrations/refresh",
    response_model=ConcentrationRefreshResponse,
    summary="Refresh SIF Risk Concentrations",
    description="Executes deterministic aggregation and observed trend evaluation across all SIF-eligible reports and precursor patterns.",
)
async def refresh_concentrations(
    start_date: Optional[datetime] = Query(
        None,
        description="Optional start date boundary for observations",
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Optional end date boundary for observations",
    ),
    time_bucket: Optional[str] = Query(
        None,
        description="Override time bucket aggregation (default: 'MONTH')",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> ConcentrationRefreshResponse:
    """Trigger on-demand concentration aggregation run."""
    service = RiskConcentrationService(db)
    return await service.refresh_concentrations(
        start_date=start_date,
        end_date=end_date,
        time_bucket=time_bucket,
    )


@router.get(
    "/sif/analytics/trends",
    response_model=TrendsResponse,
    summary="Get Observed Precursor Trends",
    description="Returns aggregate counts of observed historical trends across operational dimensions.",
)
async def get_trends(
    dimension: Optional[ConcentrationDimension] = Query(
        None,
        description="Filter trends by concentration dimension",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> TrendsResponse:
    """Retrieve observed trends across operational dimensions."""
    service = RiskConcentrationService(db)
    return await service.get_trends(dimension=dimension)


@router.get(
    "/sif/analytics/distribution",
    response_model=DimensionDistributionResponse,
    summary="Get Dimension Occurrence Distribution",
    description="Returns categorical occurrence counts, distinct reports, and observed trends for a requested dimension.",
)
async def get_distribution(
    dimension: ConcentrationDimension = Query(
        ConcentrationDimension.HAZARD,
        description="Concentration dimension (PATTERN, HAZARD, BARRIER_FAILURE, ACTIVITY, LIFE_SAVING_RULE, LOCATION)",
    ),
    db: AsyncSession = Depends(get_db_session),
) -> DimensionDistributionResponse:
    """Retrieve categorical distribution for a concentration dimension."""
    service = RiskConcentrationService(db)
    return await service.get_distribution(dimension=dimension)


@router.get(
    "/sif/analytics/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Get Safety Dashboard Analytics Summary",
    description="Returns factual aggregate SIF metrics, Life-Saving Rule distributions, and location concentration summaries.",
)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db_session),
) -> AnalyticsSummaryResponse:
    """Retrieve safety dashboard aggregated analytics summary."""
    service = RiskConcentrationService(db)
    return await service.get_analytics_summary()
