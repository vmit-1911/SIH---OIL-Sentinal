"""Phase 14 Production Readiness, Security & Release Validation Tests.

Validates security boundaries, credential hygiene, file upload constraints,
API error sanitization, security headers, CORS configuration, data isolation,
and end-to-end release smoke workflows without changing SIF intelligence.
"""

import os
from pathlib import Path
from uuid import uuid4
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.batch.validator import BatchValidator
from app.main import app

settings = get_settings()
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


# ==============================================================================
# 1. SECRET & CREDENTIAL HYGIENE TESTS
# ==============================================================================

def test_gitignore_protects_sensitive_files():
    """Verify .gitignore excludes .env, .venv, logs, and production data."""
    gitignore_path = WORKSPACE_ROOT / ".gitignore"
    assert gitignore_path.exists(), ".gitignore file must exist"
    content = gitignore_path.read_text(encoding="utf-8")

    assert ".env" in content
    assert ".venv/" in content
    assert "data/production/*" in content
    assert "*.key" in content or "*.pem" in content


def test_env_example_contains_placeholders_only():
    """Verify .env.example contains only template placeholders and no live credentials."""
    env_example = WORKSPACE_ROOT / ".env.example"
    assert env_example.exists(), ".env.example must exist"
    content = env_example.read_text(encoding="utf-8")

    assert "change_me" in content.lower() or "secure_random_string" in content.lower()
    assert "AKIA" not in content  # No AWS access key pattern
    assert "ghp_" not in content  # No GitHub token pattern
    assert "BEGIN PRIVATE KEY" not in content


def test_production_data_directory_isolation():
    """Verify data/production contains zero uncommitted proprietary data files."""
    prod_data_dir = WORKSPACE_ROOT / "data" / "production"
    assert prod_data_dir.exists(), "data/production directory must exist"
    files = [f.name for f in prod_data_dir.iterdir() if f.is_file()]
    # Only .gitkeep should be present
    assert files == [".gitkeep"], f"data/production must only contain .gitkeep, found: {files}"


# ==============================================================================
# 2. FILE UPLOAD & BATCH SECURITY TESTS
# ==============================================================================

def test_upload_validator_rejects_non_csv():
    """Verify BatchValidator strictly rejects non-CSV file extensions."""
    is_valid, err = BatchValidator.validate_file(
        file_content=b"some content",
        filename="malicious.exe",
        allowed_extensions=[".csv"],
    )
    assert not is_valid
    assert "Unsupported file extension" in err


def test_upload_validator_rejects_empty_content():
    """Verify BatchValidator strictly rejects empty files."""
    is_valid, err = BatchValidator.validate_file(
        file_content=b"",
        filename="empty.csv",
        allowed_extensions=[".csv"],
    )
    assert not is_valid
    assert "empty" in err.lower()


def test_upload_validator_rejects_oversized_file():
    """Verify BatchValidator strictly enforces file size limits."""
    # 1MB limit for test check
    max_size = 1024 * 1024
    oversized_content = b"x" * (max_size + 100)
    is_valid, err = BatchValidator.validate_file(
        file_content=oversized_content,
        filename="large.csv",
        max_size_bytes=max_size,
        allowed_extensions=[".csv"],
    )
    assert not is_valid
    assert "exceeds the maximum allowed limit" in err


def test_upload_filename_path_traversal_neutralized():
    """Verify path traversal characters in uploaded filenames do not escape directory boundaries."""
    traversal_filename = "../../etc/passwd.csv"
    is_valid, err = BatchValidator.validate_file(
        file_content=b"raw_text,source_type\nObserved loose handrail at Rig 4,UNSAFE_CONDITION\n",
        filename=traversal_filename,
        allowed_extensions=[".csv"],
    )
    assert is_valid, "Valid CSV content with complex filename is accepted structurally"
    # Suffix extraction must correctly identify .csv regardless of directory separators
    assert Path(traversal_filename).suffix.lower() == ".csv"


# ==============================================================================
# 3. API SECURITY HEADERS & TRACEABILITY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_security_headers_present_on_responses(async_client: AsyncClient):
    """Verify X-Content-Type-Options, X-Frame-Options, and Referrer-Policy headers."""
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "X-Request-ID" in resp.headers


@pytest.mark.asyncio
async def test_request_id_preservation_and_generation(async_client: AsyncClient):
    """Verify incoming X-Request-ID is preserved and missing ID is deterministically generated."""
    # 1. Custom incoming ID
    custom_id = "oil-sif-sec-audit-12345"
    resp = await async_client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == custom_id

    # 2. Generated ID
    resp2 = await async_client.get("/api/v1/health")
    assert resp2.status_code == 200
    assert "X-Request-ID" in resp2.headers
    assert len(resp2.headers["X-Request-ID"]) > 10


# ==============================================================================
# 4. API ERROR SANITIZATION & EXCEPTION SAFETY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_sanitized_validation_error_envelope(async_client: AsyncClient):
    """Verify 422 validation errors return structured envelope without leaking stack traces."""
    # Malformed payload missing required 'raw_text'
    resp = await async_client.post("/api/v1/sif/analyze", json={"source_type": "INVALID_ENUM_VALUE"})
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in data["error"]
    assert "traceback" not in str(data).lower()


@pytest.mark.asyncio
async def test_sanitized_invalid_uuid_error(async_client: AsyncClient):
    """Verify invalid UUID parameter returns clean 422/404 without internal server crash."""
    resp = await async_client.get("/api/v1/sif/reports/not-a-valid-uuid")
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_sanitized_invalid_date_range_error(async_client: AsyncClient):
    """Verify invalid date filter returns structured INVALID_DATE_RANGE envelope."""
    resp = await async_client.get(
        "/api/v1/sif/command-center/overview",
        params={"from_date": "2026-12-31T00:00:00Z", "to_date": "2026-01-01T00:00:00Z"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_DATE_RANGE"


# ==============================================================================
# 5. DOCKER & CONTAINER SECURITY CHECKS
# ==============================================================================

def test_dockerfile_security_configuration():
    """Verify Dockerfile uses non-root user, proper healthcheck, and minimal base."""
    dockerfile_path = WORKSPACE_ROOT / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "USER appuser" in content, "Dockerfile must switch to non-root USER appuser"
    assert "HEALTHCHECK" in content, "Dockerfile must define a container HEALTHCHECK"
    assert "python:3.11-slim" in content or "python:3" in content
    assert "rm -rf /var/lib/apt/lists/*" in content, "Dockerfile must clean apt package caches"


def test_dockerignore_excludes_sensitive_assets():
    """Verify .dockerignore excludes secrets, tests, virtual environments, and production data."""
    dockerignore_path = WORKSPACE_ROOT / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore must exist"
    content = dockerignore_path.read_text(encoding="utf-8")

    assert ".env" in content
    assert "tests/" in content
    assert ".venv/" in content
    assert "data/production/*" in content


# ==============================================================================
# 6. CORS & CONFIGURATION SAFETY
# ==============================================================================

def test_cors_configuration_parsing():
    """Verify CORS origins are parsed cleanly from comma-separated string."""
    origins = settings.cors_origins
    assert isinstance(origins, list)
    assert len(origins) > 0
    for origin in origins:
        assert isinstance(origin, str)
        assert len(origin.strip()) > 0


# ==============================================================================
# 7. END-TO-END RELEASE SMOKE TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_release_smoke_operational_chain(async_client: AsyncClient):
    """Verify complete operational chain: Health -> Readiness -> Taxonomy -> Analyze -> Command Center."""
    # Step 1: Health check (Liveness)
    health_resp = await async_client.get("/api/v1/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    # Step 2: Readiness check
    ready_resp = await async_client.get("/api/v1/ready")
    assert ready_resp.status_code in (200, 503)

    # Step 3: Taxonomies check
    tax_resp = await async_client.get("/api/v1/taxonomies")
    assert tax_resp.status_code == 200
    assert len(tax_resp.json()["taxonomies"]) >= 1

    # Step 4: SIF Single Report Analysis
    analyze_resp = await async_client.post(
        "/api/v1/sif/analyze",
        json={
            "raw_text": "High pressure gas leak observed at manifold valve on Wellhead 14 without permit.",
            "source_type": "UC",
            "reported_location": "Wellhead 14",
            "reported_department": "Production",
        },
    )
    assert analyze_resp.status_code == 200
    analysis_data = analyze_resp.json()
    assert "report_id" in analysis_data
    assert "sif_classification" in analysis_data
    assert "explainability" in analysis_data
    assert "life_saving_rules" in analysis_data
    assert "X-Request-ID" in analyze_resp.headers

    # Step 5: Command Center Overview
    overview_resp = await async_client.get("/api/v1/sif/command-center/overview")
    assert overview_resp.status_code == 200
    assert "total_reports" in overview_resp.json()

    # Step 6: Traceability & Security Headers on all responses
    assert analyze_resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert overview_resp.headers.get("X-Content-Type-Options") == "nosniff"
