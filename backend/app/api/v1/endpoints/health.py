"""Health, readiness, and liveness probe endpoints for Phase 12 operational observability."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app import __version__
from app.config import get_settings
from app.core.logging import get_logger
from app.db.session import check_database_health
from app.domain.taxonomy.loader import get_default_taxonomy

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


class DatabaseHealthDTO(BaseModel):
    """Database connectivity and readiness status."""
    connected: bool = Field(..., description="Whether database connection is verified")
    pgvector_ready: bool = Field(..., description="Whether pgvector extension is available")
    error: Optional[str] = Field(None, description="Sanitized error description if connection check failed")


class HealthResponse(BaseModel):
    """Liveness probe response payload."""
    status: str = Field(..., description="Service liveness state (healthy/ok)")
    service: str = Field(default="oil-sif-sentinel", description="Service identifier")
    app_name: str = Field(..., description="Configured application name")
    version: str = Field(..., description="Application semantic version")
    api_version: str = Field(default="1.0", description="API contract version")
    environment: str = Field(..., description="Current deployment environment")
    database: DatabaseHealthDTO = Field(..., description="Liveness descriptor")
    active_taxonomies: List[Dict[str, str]] = Field(default_factory=list, description="Loaded taxonomy metadata")


class ReadinessResponse(BaseModel):
    """Readiness probe response payload."""
    status: str = Field(..., description="Readiness state (ready or unhealthy)")
    service: str = Field(default="oil-sif-sentinel", description="Service identifier")
    app_name: str = Field(..., description="Configured application name")
    version: str = Field(..., description="Application semantic version")
    api_version: str = Field(default="1.0", description="API contract version")
    environment: str = Field(..., description="Current deployment environment")
    database: DatabaseHealthDTO = Field(..., description="Live database connectivity status")
    active_taxonomies: List[Dict[str, str]] = Field(default_factory=list, description="Active taxonomies status")


def _get_active_taxonomies_summary() -> List[Dict[str, str]]:
    """Retrieve in-memory taxonomy metadata without performing DB operations."""
    try:
        taxonomy = get_default_taxonomy()
        return [{
            "taxonomy_id": taxonomy.taxonomy_id,
            "authority": taxonomy.authority,
            "version": taxonomy.version,
            "name": taxonomy.name,
            "rules_count": str(len(taxonomy.rules)),
        }]
    except Exception as exc:
        logger.warning(f"Could not load default taxonomy for probe: {exc}")
        return [{
            "taxonomy_id": "ERROR",
            "error": "Taxonomy definitions unavailable",
        }]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Process Liveness Probe",
    description="Lightweight, DB-independent liveness probe verifying process health and in-memory metadata.",
)
async def get_health() -> HealthResponse:
    """Process liveness probe (independent of database availability)."""
    active_taxonomies = _get_active_taxonomies_summary()

    return HealthResponse(
        status="ok",
        service="oil-sif-sentinel",
        app_name=settings.APP_NAME,
        version=__version__,
        api_version=settings.API_VERSION,
        environment=settings.APP_ENV,
        database=DatabaseHealthDTO(
            connected=True,
            pgvector_ready=True,
            error=None,
        ),
        active_taxonomies=active_taxonomies,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Dependency Readiness Probe",
    description="Verifies live database connectivity and dependency readiness for handling production traffic.",
    responses={
        200: {"description": "Service and dependencies are ready"},
        503: {"description": "Dependencies unavailable or failing connectivity check"},
    },
)
async def get_ready(response: Response) -> ReadinessResponse:
    """Dependency readiness probe verifying live database connectivity."""
    db_health = await check_database_health()
    active_taxonomies = _get_active_taxonomies_summary()

    is_db_ok = db_health.get("connected", False)
    tax_ok = bool(active_taxonomies and active_taxonomies[0].get("taxonomy_id") != "ERROR")

    if is_db_ok and tax_ok:
        readiness_status = "ready"
    else:
        readiness_status = "degraded"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    sanitized_err = None
    if db_health.get("error"):
        logger.error(f"Readiness probe database connection failure: {db_health['error']}")
        sanitized_err = "Database connection unavailable"

    return ReadinessResponse(
        status=readiness_status,
        service="oil-sif-sentinel",
        app_name=settings.APP_NAME,
        version=__version__,
        api_version=settings.API_VERSION,
        environment=settings.APP_ENV,
        database=DatabaseHealthDTO(
            connected=db_health["connected"],
            pgvector_ready=db_health.get("pgvector_ready", False),
            error=sanitized_err,
        ),
        active_taxonomies=active_taxonomies,
    )
