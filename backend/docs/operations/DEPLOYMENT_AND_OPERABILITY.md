# OIL SIF Sentinel — Deployment, Observability & Diagnostic Hardening Guide

## 1. Overview & Operational Principles

Phase 12 hardens the **OIL SIF Sentinel backend** for enterprise deployment, diagnostic observability, and operational resilience.
It introduces zero database schema changes, preserves all Phase 1–11 deterministic algorithms and API contracts, and operates without external distributed queue infrastructure (Redis, Celery, Kafka).

### Core Operational Principles
- **Liveness vs Readiness Distinction**: Process liveness (`/api/v1/health`) is strictly decoupled from external dependencies. Readiness (`/api/v1/ready`) verifies live database connectivity.
- **Traceability**: All requests carry a unique `X-Request-ID` header (preserving incoming IDs or generating a UUID4) that propagates through structured logs.
- **Sanitized Failures**: Internal exceptions, SQLAlchemy engine errors, and stack traces are never exposed in HTTP response envelopes; detailed diagnostics are captured in server-side structured logs.
- **Session & Transaction Safety**: All database transactions follow strict `try -> commit` / `except -> rollback` / `finally -> close` semantics with connection pooling and graceful teardown on SIGTERM/SIGINT.
- **Observable Background Tasks**: Asynchronous batch ingestion runs in isolated database sessions, logging lifecycle stages and deterministically recording `FAILED` states on unexpected crashes.

---

## 2. Configuration & Environment Variables

Configuration is managed via Pydantic `BaseSettings` (`app.config.Settings`) with environment variable overrides.

### Supported Environment Variables

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | String | `development` | Runtime environment: `development`, `testing`, `staging`, `production` |
| `DEBUG` | Boolean | `true` | Debug mode flag (Must be `false` in production) |
| `LOG_LEVEL` | String | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | String | `JSON` | Log format: `JSON` (structured) or `TEXT` (human-readable) |
| `HOST` | String | `0.0.0.0` | Bind host address |
| `PORT` | Integer | `8000` | Bind HTTP port |
| `API_VERSION` | String | `1.0` | API version string |
| `DATABASE_URL` | String | *PostgreSQL Async URL* | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `DATABASE_URL_SYNC` | String | *PostgreSQL Sync URL* | `postgresql://user:pass@host:5432/dbname` (Alembic) |
| `DB_POOL_SIZE` | Integer | `5` | Database connection pool base size |
| `DB_MAX_OVERFLOW` | Integer | `10` | Database connection pool max overflow |
| `DB_POOL_TIMEOUT` | Integer | `30` | Connection checkout timeout in seconds |
| `DB_ECHO` | Boolean | `false` | Echo raw SQL queries to stdout (debug only) |
| `CORS_ALLOWED_ORIGINS` | String / List | `*` | Comma-separated list or JSON array of allowed CORS origins |
| `BATCH_MAX_FILE_SIZE_BYTES` | Integer | `10485760` | Maximum batch upload size in bytes (10MB default) |
| `BATCH_CHUNK_SIZE` | Integer | `50` | Row chunk size for batch database processing |

### Production vs Development Expectations

- **Development**: `DEBUG=true`, `CORS_ALLOWED_ORIGINS=*`, `LOG_FORMAT=TEXT` or `JSON`, default local PostgreSQL credentials.
- **Production**:
  - `APP_ENV=production`
  - `DEBUG=false`
  - `LOG_FORMAT=JSON` (for ingestion into log aggregators such as Datadog, CloudWatch, or ELK)
  - `CORS_ALLOWED_ORIGINS` explicitly restricted to frontend domains (e.g. `https://sif-sentinel.oilindia.in`)
  - `DATABASE_URL` configured via environment variables / secret manager without hardcoded source credentials.

---

## 3. Health & Readiness Probes

### 3.1 Liveness Probe (`GET /api/v1/health`)
- **Purpose**: Process-level liveness probe for orchestrators (Docker, systemd, Kubernetes).
- **Behavior**: Executes in memory in $<1\text{ms}$ with **zero database I/O**.
- **Guarantee**: Always returns `200 OK` as long as the Python process and ASGI event loop are responsive, even if PostgreSQL is unreachable.

**Response Schema (`200 OK`)**:
```json
{
  "status": "ok",
  "service": "oil-sif-sentinel",
  "api_version": "1.0"
}
```

### 3.2 Readiness Probe (`GET /api/v1/ready`)
- **Purpose**: Dependency readiness check to determine if the backend can serve DB-dependent traffic.
- **Behavior**: Executes a lightweight `SELECT 1` ping against the database pool and checks for the `pgvector` extension.
- **Status Codes**:
  - `200 OK`: Database is connected and operational.
  - `503 Service Unavailable`: Database is unreachable, connection timed out, or database error occurred.

**Healthy Response (`200 OK`)**:
```json
{
  "status": "ready",
  "database": {
    "connected": true,
    "pgvector_ready": true
  }
}
```

**Degraded Response (`503 Service Unavailable`)**:
```json
{
  "status": "degraded",
  "database": {
    "connected": false,
    "pgvector_ready": false,
    "error": "Database connection unavailable"
  }
}
```
*(Underlying stack traces and SQLAlchemy exceptions are sanitized from the HTTP response and logged server-side).*

---

## 4. Request Traceability & Request IDs

1. **Header**: Every incoming HTTP request is inspected for the `X-Request-ID` header.
2. **Preservation & Generation**:
   - If present and non-empty, the incoming ID is preserved.
   - If omitted or empty, a new UUID4 string is generated.
3. **Response Header**: The active `request_id` is always returned in the `X-Request-ID` response header.
4. **Error Envelope**: Returned in `error.request_id` for all `4xx` and `500` error responses.
5. **Logs**: Embedded in every structured log line produced during that request's execution lifecycle.

---

## 5. Structured JSON Logging

All logs in `LOG_FORMAT=JSON` mode are emitted as single-line JSON objects to `sys.stdout`.

### Standard Structured Fields

| Field | Type | Example | Description |
| :--- | :--- | :--- | :--- |
| `timestamp` | ISO-8601 UTC | `2026-09-24T12:00:00.000000+00:00` | Log event timestamp |
| `level` | String | `INFO`, `WARNING`, `ERROR` | Log level |
| `logger` | String | `app.main` | Logger module name |
| `message` | String | `POST /api/v1/sif/analyze 200 (14.2ms)` | Human-readable log message |
| `component` | String | `api`, `batch_processor`, `db` | Architectural component |
| `request_id` | String | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` | Request traceability ID |
| `method` | String | `POST` | HTTP method |
| `route` | String | `/api/v1/sif/analyze` | Request route |
| `status` | Integer | `200` | HTTP status code |
| `duration_ms` | Float | `14.2` | Processing duration in milliseconds |
| `batch_id` | String | `...` | Batch job UUID (for batch operations) |
| `exception_category` | String | `IntegrityError` | Category of unhandled/caught exception |

### Sensitive Data Protection
Passwords, database URLs with embedded credentials, raw authentication tokens, and full file byte streams are strictly suppressed from structured log payloads.

---

## 6. Exception Boundary & Error Sanitization

All unhandled exceptions are caught by FastAPI global exception handlers and mapped to standardized JSON envelopes:

```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An internal server error occurred.",
    "details": null,
    "request_id": "8fa538c2-4a7b-40fa-9860-9d0d35d212b0"
  },
  "detail": "An internal server error occurred."
}
```

### Standard Error Codes
- `400`: `BAD_REQUEST`, `INVALID_DATE_RANGE`, domain validation codes.
- `404`: `RESOURCE_NOT_FOUND`.
- `409`: `CONFLICT`, `REVIEW_CONFLICT`.
- `422`: `VALIDATION_ERROR` (with pydantic validation details).
- `500`: `INTERNAL_SERVER_ERROR` (sanitized).
- `501`: `NOT_IMPLEMENTED`.

---

## 7. Deployment Instructions

### 7.1 Running Locally (Bare Metal)

```powershell
# 1. Activate virtual environment
.venv\Scripts\Activate.ps1

# 2. Configure environment
cp .env.example .env

# 3. Run database migrations
alembic upgrade head

# 4. Start Uvicorn server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7.2 Running via Docker Compose (Recommended for Full Stack)

```bash
# Build and start application + pgvector database
docker compose up --build -d

# Check service logs
docker compose logs -f app

# Run healthcheck verification
curl -f http://localhost:8000/api/v1/health
curl -f http://localhost:8000/api/v1/ready
```

### 7.3 Building Standalone Container Image

```bash
docker build -t oil-sif-sentinel:latest .
docker run -p 8000:8000 --env-file .env oil-sif-sentinel:latest
```

---

## 8. Troubleshooting Playbook

| Symptom | Probable Cause | Diagnostic & Resolution |
| :--- | :--- | :--- |
| `/api/v1/ready` returns `503 Degraded` | PostgreSQL container is stopped or network unreachable | 1. Check DB host/port in `DATABASE_URL`.<br>2. Ensure PostgreSQL is accepting connections (`pg_isready`).<br>3. Verify `pgvector` extension is installed (`CREATE EXTENSION IF NOT EXISTS vector;`). |
| Application startup hangs or fails | Port collision or invalid database configuration | 1. Verify `PORT=8000` is free.<br>2. Check `alembic current` to ensure database schema is at migration head.<br>3. Check structured logs for startup exceptions. |
| API returns `500 INTERNAL_SERVER_ERROR` | Unhandled backend exception | 1. Note the `request_id` from the response header or body.<br>2. Search application logs for `request_id="..."` and examine the full server-side stack trace. |
| Background batch job marked `FAILED` | Malformed file content or unhandled exception during processing | 1. Search logs for `component="batch_processor"` and `batch_id="<id>"`.<br>2. Inspect `GET /api/v1/batch/jobs/{batch_id}/errors` for row-level validation issues. |
| DB connection pool exhaustion | Long-running queries or connection leak | 1. Check `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` settings.<br>2. Verify that all async database calls utilize `async with AsyncSessionLocal()` context manager. |
