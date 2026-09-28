"""API v1 master router aggregator."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    action,
    alerts,
    analytics,
    analyze,
    batch,
    case,
    command_center,
    export,
    health,
    intelligence,
    patterns,
    reports,
    review,
    taxonomies,
)

api_router = APIRouter()

# Health & Readiness
api_router.include_router(health.router, tags=["Health & Telemetry"])

# Taxonomies
api_router.include_router(taxonomies.router, tags=["Life-Saving Rules Taxonomies"])

# SIF Inference & Triage
api_router.include_router(analyze.router, tags=["SIF Inference Engine"])
api_router.include_router(batch.router, tags=["Batch Ingestion"])
api_router.include_router(reports.router, tags=["Safety Reports"])
api_router.include_router(review.router, tags=["Human Triage & Review"])
api_router.include_router(patterns.router, tags=["Precursor Intelligence"])
api_router.include_router(analytics.router, tags=["Analytics & KPIs"])
api_router.include_router(intelligence.router, tags=["HSE Intelligence & Evidence"])
api_router.include_router(action.router, tags=["HSE Action & Recommendations"])
api_router.include_router(case.router, tags=["HSE Case Management & Follow-up"])
api_router.include_router(command_center.router, tags=["HSE Command Center"])
api_router.include_router(export.router, tags=["Intelligence Exports"])
api_router.include_router(alerts.router, tags=["Alerts & Webhooks"])


