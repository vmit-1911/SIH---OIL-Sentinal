"""Unit tests for configuration loading and validation."""

from app.config import Settings, get_settings


def test_settings_defaults():
    """Verify default settings initialization."""
    settings = get_settings()
    assert settings.APP_NAME == "OIL SIF Sentinel"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert "postgresql+asyncpg://" in settings.DATABASE_URL
    assert settings.DEFAULT_TAXONOMY_ID == "IOGP_REPORT_459"
    assert settings.PRECURSOR_SIMILARITY_CANDIDATE_THRESHOLD == 0.65
    assert settings.SIMILARITY_THRESHOLD == 0.65


def test_candidate_threshold_override():
    """Verify PRECURSOR_SIMILARITY_CANDIDATE_THRESHOLD can be configured and alias reflects it."""
    settings = Settings(PRECURSOR_SIMILARITY_CANDIDATE_THRESHOLD=0.75)
    assert settings.PRECURSOR_SIMILARITY_CANDIDATE_THRESHOLD == 0.75
    assert settings.SIMILARITY_THRESHOLD == 0.75


def test_cors_origins_parsing():
    """Verify comma-separated origins are parsed to list."""
    settings = Settings(ALLOWED_ORIGINS="http://localhost:3000, http://example.com ")
    assert settings.cors_origins == ["http://localhost:3000", "http://example.com"]
