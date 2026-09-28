"""Application settings and configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application Information
    APP_NAME: str = "OIL SIF Sentinel"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    API_VERSION: str = "1.0"
    SECRET_KEY: str = "development_secret_key_change_in_production"

    # Server Host & Port
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "JSON"

    # PostgreSQL + pgvector Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/oil_sif_sentinel"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/oil_sif_sentinel"

    # Database Pool Settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # Life-Saving Rules Taxonomy Settings
    DEFAULT_TAXONOMY_ID: str = "IOGP_REPORT_459"
    TAXONOMY_DEFINITIONS_PATH: str = "app/domain/taxonomy/iogp_report_459.json"

    # Precursor Embedding & Similarity Settings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    SIMILARITY_STRUCTURED_WEIGHT: float = 0.5
    SIMILARITY_SEMANTIC_WEIGHT: float = 0.5
    # Engineering candidate-retrieval/filtering parameter. It is not calibrated and must not be interpreted as probability, SIF severity, recurrence, or official OIL/IOGP guidance.
    PRECURSOR_SIMILARITY_CANDIDATE_THRESHOLD: float = 0.65
    SIMILARITY_TOP_K: int = 5

    # Phase 2B Recurring Precursor Pattern Discovery Settings
    # Engineering pattern-discovery parameter specifying the minimum number of supporting reports
    # required before creating an automatically discovered recurring-pattern candidate.
    # It is NOT an official safety threshold, nor does it indicate an official SIF risk level.
    MIN_PATTERN_REPORT_COUNT: int = 3
    PATTERN_DISCOVERY_METHOD: str = "HYBRID_SIMILARITY_GROUPING_V1"

    # Engineering pattern-discovery cohesion parameter. Not an official OIL/IOGP threshold and not a probability.
    PATTERN_MIN_GROUP_COHESION: float = 0.65

    # SIF-eligible classifications for recurring precursor pattern discovery.
    # Pattern discovery explicitly groups SIF-eligible classifications (POTENTIAL_SIF, ACTUAL_SIF).
    # NON_SIF and UNDETERMINED events are strictly excluded before candidate grouping.
    PATTERN_ELIGIBLE_SIF_CLASSIFICATIONS: List[str] = ["POTENTIAL_SIF", "ACTUAL_SIF"]

    # Phase 3 Risk Concentration & SIF Intelligence Settings
    # Configurable temporal aggregation bucket ("MONTH", "QUARTER", "WEEK")
    CONCENTRATION_TIME_BUCKET: str = "MONTH"
    # Minimum populated historical time periods required to evaluate an observed directional trend
    CONCENTRATION_MIN_TREND_PERIODS: int = 2
    # Descriptive engineering parameters for observed trend classification.
    # They are NOT: OIL safety thresholds, IOGP thresholds, calibrated statistical significance thresholds, SIF probabilities, or predictive risk thresholds.
    # Trend classification is purely descriptive of historical reporting distributions and does NOT perform prediction or forecasting.
    CONCENTRATION_TREND_INCREASE_RATIO: float = 1.25
    CONCENTRATION_TREND_DECREASE_RATIO: float = 0.80
    CONCENTRATION_CALCULATION_METHOD: str = "EXPLAINABLE_OBSERVED_CONCENTRATION_V1"

    # Phase 9 HSE Case Management & Follow-up Settings
    # Configurable case closure policy regarding attached action resolution.
    # Case closure currently requires all attached actions to be COMPLETED or DISMISSED as an application workflow rule; this is not an OIL policy or regulatory requirement.
    CASE_CLOSURE_REQUIRES_ACTION_RESOLUTION: bool = True

    # Phase 4 Batch Pipeline & Enterprise Ingestion Settings
    BATCH_MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    BATCH_MAX_FILE_SIZE: Optional[int] = None
    BATCH_ALLOWED_EXTENSIONS: List[str] = [".csv"]
    BATCH_DEFAULT_IMPORT_SCHEMA_VERSION: str = "OIL_SAFETY_REPORT_CSV_V1"
    BATCH_CHUNK_SIZE: int = 100  # Database persistence transaction chunk size

    # Phase 15 Alerting & Export Pipeline Settings
    ALERTING_ENABLED: bool = True
    ALERTING_DISPATCH_MODE: str = "mock"  # Options: "mock", "smtp", "webhook"
    ALERTING_SMTP_HOST: str = "localhost"
    ALERTING_SMTP_PORT: int = 587
    ALERTING_SMTP_USER: str = ""
    ALERTING_SMTP_PASSWORD: str = ""
    ALERTING_SMTP_FROM: str = "sif-sentinel@oilindia.in"
    ALERTING_DEFAULT_RECIPIENTS: str = "hse-alerts@oilindia.in"
    ALERTING_WEBHOOK_TIMEOUT_SECONDS: float = 5.0
    ALERTING_WEBHOOK_MAX_RETRIES: int = 3
    ALERTING_WEBHOOK_SECRET: str = "oil-sif-sentinel-webhook-secret-key"

    @property
    def alert_recipient_list(self) -> List[str]:
        """Parse comma-separated alert recipients into a list."""
        return [r.strip() for r in self.ALERTING_DEFAULT_RECIPIENTS.split(",") if r.strip()]

    @property
    def SIMILARITY_THRESHOLD(self) -> float:
        """Backward-compatible alias for candidate retrieval threshold."""
        return self.PRECURSOR_SIMILARITY_CANDIDATE_THRESHOLD

    # CORS Settings
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    CORS_ALLOWED_ORIGINS: Optional[str] = None

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated allowed origins into a list."""
        origins_str = self.CORS_ALLOWED_ORIGINS or self.ALLOWED_ORIGINS
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]

    @property
    def batch_max_file_size(self) -> int:
        """Resolve effective max batch upload file size in bytes."""
        return self.BATCH_MAX_FILE_SIZE or self.BATCH_MAX_FILE_SIZE_BYTES

    @property
    def taxonomy_file_path(self) -> Path:
        """Resolve the path to the active taxonomy JSON file."""
        base_dir = Path(__file__).resolve().parent.parent
        resolved = base_dir / self.TAXONOMY_DEFINITIONS_PATH
        if not resolved.exists():
            # Try relative to current working directory
            fallback = Path(self.TAXONOMY_DEFINITIONS_PATH)
            if fallback.exists():
                return fallback
        return resolved


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
