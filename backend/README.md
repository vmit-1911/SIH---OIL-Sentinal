# OIL SIF Sentinel — Backend & AI Engine

AI/NLP Engine to Detect Serious Injury & Fatality (SIF) Precursors in Oil India Limited's Unsafe-Act/Unsafe-Condition and Near-Miss Reports.

---

## 1. Project Purpose & Problem Statement

Oil India Limited (OIL) collects large volumes of free-text Unsafe Act (UA), Unsafe Condition (UC), near-miss, and incident reports across drilling rigs, production facilities (EPS/GGS), gas pipelines, terminals, and workshops. 

Manual triage is periodic and resource-intensive. Traditional safety pyramids often equate actual injury outcome with hazard severity, creating a blind spot: **a near-miss with zero injuries can carry genuine fatality or catastrophic event potential (a SIF Precursor) if high-energy hazards were present and critical barriers failed or were bypassed.**

**OIL SIF Sentinel** is a production-oriented backend and AI/NLP engine designed to:
- Distinguish **Actual Outcome** from **Potential Outcome / SIF Potential**.
- Screen free-text reports using configurable multi-factor evidence heuristics.
- Map reports to versioned **IOGP Life-Saving Rules (Report 459 - 2018 Edition)**.
- Extract a structured **7-dimensional Precursor Object** (Hazard, Activity, Barrier Failure, Exposure, Potential Consequence, LSR, Location).
- Discover recurring precursor patterns across operations using weighted hybrid similarity (structural + semantic).
- Expose stable, frontend-ready REST API contracts.

---

## 2. Architecture Overview

The system follows **Hexagonal (Clean) Architecture**:

```
[Frontend / Client Application]
             │
             ▼ REST API / JSON (FastAPI)
┌─────────────────────────────────────────────────────────────┐
│ 1. API Layer: DTOs, Validation, Middleware, Error Handlers  │
├─────────────────────────────────────────────────────────────┤
│ 2. Application Services: Triage, Batch, Pattern, Analytics  │
├─────────────────────────────────────────────────────────────┤
│ 3. Domain Core:                                             │
│    - ActualOutcome vs PotentialOutcome Enums                │
│    - SIFClassification & Scoring Evidence Breakdown        │
│    - Structured Precursor (7 Dimensions)                    │
│    - Versioned IOGP Report 459 (2018) Taxonomy Engine       │
│    - Abstract AI/NLP & Matcher Interfaces                   │
├─────────────────────────────────────────────────────────────┤
│ 4. Persistence Layer:                                       │
│    - PostgreSQL 16 + pgvector                               │
│    - SQLAlchemy 2.x Async Engine + Alembic                  │
│    - JSONB Structured Precursor Indexing                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Prerequisites & Environment

- **Python:** `3.11+` (Compatible with Python 3.11, 3.12, 3.13, 3.14)
- **Database:** PostgreSQL `15+` or `16+` with `pgvector` extension enabled.
- **Operating System:** Linux, macOS, or Windows.

---

## 4. Local Setup & Installation

### Step 1: Clone & Navigate to Workspace
```bash
cd "SIH- SIF Detection OIL"
```

### Step 2: Create and Activate Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements-dev.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env` and configure your database credentials:
```bash
cp .env.example .env
```

Key configuration variables:
```ini
APP_NAME="OIL SIF Sentinel"
APP_ENV="development"
DEBUG=true
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/oil_sif_sentinel"
DATABASE_URL_SYNC="postgresql://postgres:postgres@localhost:5432/oil_sif_sentinel"
DEFAULT_TAXONOMY_ID="IOGP_REPORT_459"
TAXONOMY_DEFINITIONS_PATH="app/domain/taxonomy/iogp_report_459.json"
```

---

## 5. Database Setup & Alembic Migrations

Ensure PostgreSQL is running and the database exists:
```sql
CREATE DATABASE oil_sif_sentinel;
\c oil_sif_sentinel
CREATE EXTENSION IF NOT EXISTS vector;
```

Run Alembic migrations to create all tables:
```bash
alembic upgrade head
```

To rollback migrations:
```bash
alembic downgrade base
```

---

## 6. Running the Application

Start the development server with Uvicorn:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Interactive API Documentation:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 7. Running the Test Suite

Execute all unit and integration tests with pytest:
```bash
pytest -v
```

Run tests with coverage reporting:
```bash
pytest --cov=app -v
```

---

## 8. Data Separation & Proprietary Data Boundary

To prevent accidental contamination or leakage of real operational data:
- `data/synthetic/`: Contains synthetic mock safety reports strictly for development and unit testing (`sample_safety_reports.json`).
- `data/evaluation/`: Reserved for labeled benchmark evaluation datasets.
- `data/production/`: Reserved for actual operational OIL datasets (strictly excluded from git via `.gitignore`).

---

## 9. Pipeline Architecture & Verified Phases (Phases 1A – 6)

The OIL SIF Sentinel backend is a **production-oriented deterministic backend pipeline** integrating domain NLP extraction, rule-based screening, precursor synthesis, hybrid similarity, pattern discovery, concentration analytics, batch processing, and human-in-the-loop expert validation.

```
Safety Narrative (Raw Text)
    ↓
Phase 1A — Domain-Aware Safety Event Extraction (RuleBasedSafetyExtractor)
    ↓
Phase 1B — SIF Screening & IOGP LSR Mapping (SIFScreeningEngine + LSRMapper)
    ↓
Phase 1C — End-to-End Analysis Persistence (SafetyReport + SIFAssessment)
    ↓
Phase 1D — Structured Precursor Synthesis (7-Dimensional Precursor Object)
    │
    ├───────────────────────────────────────────────────────┐
    ▼ (Explicitly Triggered)                                ▼ (Explicitly Triggered)
Phase 2A & 2B — Hybrid Similarity & Pattern Discovery   Phase 3 — Multi-Dimensional Risk Concentrations
(Cosine + Structured Weights → Cohesion Grouping)       (Temporal Distributions & Descriptive Trends)
    │                                                       │
    └───────────────────────┬───────────────────────────────┘
                            ▼
Phase 5 — Human-in-the-Loop HSE Expert Review & Triage
(Claim Locking, Audit Trails, AI Preservation, Human Overrides)
```

### Architectural Decoupling & Boundaries:
1. **Batch / Analytics Boundary (Phase 4 vs 2B/3)**:
   - Ingestion of CSV batch files persists `SafetyReport` and `SIFAssessment` records deterministically.
   - Batch completion **MUST NOT and DOES NOT** automatically trigger pattern discovery or risk concentration refresh.
   - Pattern discovery (`POST /api/v1/sif/patterns/discover`) and concentration aggregation (`POST /api/v1/sif/analytics/concentrations/refresh`) are independently invoked.
2. **AI Assessment Preservation Boundary (Phase 5)**:
   - Original AI assessments (`SIFAssessment`) are immutable audit baselines.
   - Expert human review decisions (`CONFIRM_AI`, `CORRECT`, `REJECT_AI`, `MARK_UNDETERMINED`) and corrected precursors/classifications are stored in separate `TriageReview` records.
   - `ACTUAL_SIF` is never automatically inferred from narrative text; it is strictly an authoritative or human review outcome.
3. **Deterministic Engineering Parameters**:
   - Trend classifications (`INCREASING`, `DECREASING`, `STABLE`) are descriptive ratio evaluations (1.25x / 0.80x) across chronological buckets.
   - They represent engineering observability metrics, not calibrated statistical significance or predictive risk probabilities.

---

---

## 10. Database Schema & Alembic Migration Chain

The PostgreSQL schema is managed via linear Alembic migrations:
- `0001_initial_schema`: `safety_reports`, `sif_assessments`, `lsr_taxonomies`, `lsr_report_mappings`
- `0002_make_structured_precursor_nullable`: Schema refinement for initial assessment staging
- `0003_phase2b_pattern_discovery_fields`: `precursor_patterns` table and assessment pattern foreign keys
- `0004_phase3_risk_concentration_tables`: `risk_concentrations` table and dimension indexing
- `0005_phase4_batch_pipeline_tables`: `batch_jobs` and `batch_row_errors` tables
- `0006_phase5_human_in_the_loop_review_tables`: `triage_reviews` and `review_audit_events` tables
- `0007_phase8_hse_action_recommendations`: `hse_action_recommendations` table for auditable HSE action lifecycle

---

## 11. Phase 7 — HSE Intelligence & Evidence Layer

Phase 7 exposes read-only deterministic intelligence, explainability, and evidence traceability across the entire lifecycle:

```
SafetyReport
    │
    └── SIFAssessment
          │
          ├── EvidenceSpans (Character offsets, normalized concepts, negation)
          ├── StructuredPrecursor (7 dimensions with field-level provenance)
          ├── LSR Mapping (IOGP Report 459 primary and secondary rules)
          ├── Similar Assessments (Ranked hybrid similarity scores)
          ├── PrecursorPattern (Recurring pattern membership and co-member traceability)
          ├── RiskConcentration (Multi-dimensional descriptive trend findings)
          └── TriageReview
                  │
                  ├── Human Decision & Rationale
                  ├── Precursor & Classification Corrections
                  └── Immutable Audit Trail
```

### Intelligence Endpoints:
- `GET /api/v1/sif/reports/{report_id}/evidence`: Factual extracted narrative spans, character offsets, negation, and provenance.
- `GET /api/v1/sif/reports/{report_id}/explanation`: SIF screening factor breakdown, triggered rules, and 7D precursor provenance.
- `GET /api/v1/sif/reports/{report_id}/investigation-context`: Consolidated 10-dimension investigation model.
- `GET /api/v1/sif/assessments/{assessment_id}/evidence`: Assessment-level evidence spans and dimension mappings.
- `GET /api/v1/sif/assessments/{assessment_id}/similarity`: Ranked historical similar reports with dimension breakdown.
- `GET /api/v1/sif/assessments/{assessment_id}/pattern`: Precursor pattern membership and co-member reports.
- `GET /api/v1/sif/patterns/{pattern_id}/evidence`: Traceable supporting reports and assessments for a pattern.
- `GET /api/v1/sif/concentrations/{concentration_key}/evidence`: Traceable supporting reports and observed trends for a concentration.

---

## 12. Phase 8 — HSE Action & Recommendation Intelligence

Phase 8 converts existing persisted SIF intelligence into targeted, explainable, and auditable HSE action recommendations without altering underlying source-of-truth records:

```
Safety Report
    ↓
SIF Assessment + LSR + Structured Precursor (Phases 1A–1D)
    ↓
Similarity + Recurring Pattern (Phases 2A–2B)
    ↓
Risk Concentration & Trends (Phase 3)
    ↓
Human Triage Review & Audit (Phase 5)
    ↓
Investigation Context & Evidence (Phase 7)
    ↓
Action Rule Engine (Deterministic Rule Evaluation)
    ↓
HSE Action Recommendations (Idempotent Persistence & Lifecycle)
```

### Architectural Principles:
1. **Deterministic Rule Engine**: All action recommendations are generated through deterministic rule evaluations (`ACT-R01` through `ACT-R13`). No LLMs, ML models, or predictive risk scoring are used.
2. **Read-Only Intelligence Model**: Recommendations consume existing intelligence and never recalculate SIF classifications, similarity scores, or pattern groupings.
3. **Human Review Authority**:
   - `CONFIRM_AI`: Preserves and elevates recommendation priority (e.g. `CRITICAL_REVIEW` for confirmed fatality potential).
   - `CORRECT`: Follows authoritative human-corrected precursor dimensions and LSR codes.
   - `REJECT_AI`: Suppresses SIF-driven actions based on the rejected AI assessment.
   - `MARK_UNDETERMINED`: Suppresses definitive SIF follow-up actions pending resolution.
4. **Idempotency & Deduplication**: Stable composite keys (`ACTION|<source_type>|<source_id>|<category>|<rule_id>`) ensure re-running action generation is 100% idempotent.
5. **Auditable Lifecycle**: Explicit state machine (`OPEN` → `ACKNOWLEDGED` → `IN_PROGRESS` → `COMPLETED` / `DISMISSED`) requiring mandatory rationale on terminal transitions.

### Action Categories:
- `BARRIER_VERIFICATION`, `ENERGY_ISOLATION_VERIFICATION`, `FALL_PROTECTION_VERIFICATION`, `LIFTING_CONTROL_VERIFICATION`
- `LINE_OF_FIRE_CONTROL_REVIEW`, `CONFINED_SPACE_CONTROL_REVIEW`, `HOT_WORK_CONTROL_REVIEW`, `DRIVING_CONTROL_REVIEW`
- `PROCEDURE_REVIEW`, `WORK_AUTHORIZATION_REVIEW`, `TREND_INVESTIGATION`, `PATTERN_INVESTIGATION`
- `SITE_FOCUSED_REVIEW`, `IMMEDIATE_REVIEW`, `MANAGEMENT_ATTENTION`

### Action REST Endpoints:
- `GET /api/v1/sif/actions`: Filterable and paginated list of recommendations (`source_type`, `status`, `priority`, `action_category`, `rule_id`, `lsr_code`).
- `GET /api/v1/sif/actions/{action_id}`: Detailed recommendation with evidence links and rule provenance.
- `GET /api/v1/sif/reports/{report_id}/actions`: Recommendations generated for a specific safety report.
- `GET /api/v1/sif/assessments/{assessment_id}/actions`: Recommendations for an assessment.
- `GET /api/v1/sif/patterns/{pattern_id}/actions`: Recommendations for a recurring pattern.
- `GET /api/v1/sif/concentrations/{concentration_key}/actions`: Recommendations for a risk concentration finding.
- `POST /api/v1/sif/actions/generate`: Idempotent on-demand action generation.
- `POST /api/v1/sif/actions/{action_id}/acknowledge`: Acknowledge and assign an action item.
- `POST /api/v1/sif/actions/{action_id}/status`: Audited status transition (`IN_PROGRESS`, `COMPLETED`, `DISMISSED`) with mandatory rationale.

---

---

## 13. Phase 9 — HSE Case Management & Operational Follow-Up

Phase 9 establishes an operational investigation and case management layer grouping related safety intelligence into an auditable investigation lifecycle:

```
Existing SIF Intelligence (Phases 1A–1D, 2A–2B, 3, 5, 7)
    ↓
HSE Action Recommendations (Phase 8)
    ↓
HSE Case / Investigation Lifecycle (Phase 9)
    ↓
Operational Follow-Up & Verification
    ↓
Auditable Case Closure (With Mandatory Rationale & Action Resolution)
```

### Architectural Principles:
1. **Operational Workflow Layer**: Phase 9 is strictly a case management and audit orchestration layer. It introduces **no new inference engine, no predictive risk scoring, no probability estimates, and no AI-generated narrative summaries**.
2. **Immutable Source Intelligence**: Attached safety reports, SIF assessments, precursor patterns, risk concentrations, human reviews, and action recommendations remain 100% authoritative and unmutated.
3. **Deterministic State Machine**: Strict lifecycle progression (`OPEN` → `TRIAGE` → `INVESTIGATING` → `ACTION_REQUIRED` → `PENDING_VERIFICATION` → `CLOSED` or `CANCELLED`).
4. **Append-Only Case Timeline**: Every lifecycle change, owner assignment, source attachment, and source detachment is recorded in an immutable audit event trail (`HSECaseEvent`).
5. **Deterministic Case Summary**: Aggregate metrics (`report_count`, `assessment_count`, `pattern_count`, `concentration_count`, `review_count`, `open_action_count`, `completed_action_count`, `evidence_count`) are calculated directly from persisted records via efficient SQL queries.
6. **Controlled Closure & Reopening**: Case closure enforces an explicit rationale and verifies that all attached actions are completed or dismissed. Reopening a closed case transitions it back to `INVESTIGATING` with mandatory justification.
7. **Idempotency**: Case creation accepts an optional `idempotency_key` / `case_key` preventing duplicate case generation.

### Case Types & Priorities:
- **Case Types**: `SIF_INVESTIGATION`, `PATTERN_INVESTIGATION`, `LOCATION_REVIEW`, `ACTIVITY_REVIEW`, `BARRIER_REVIEW`, `HSE_FOLLOW_UP`
- **Case Priorities**: `CRITICAL_REVIEW`, `HIGH`, `MEDIUM`, `INFORMATIONAL`
- **Case Statuses**: `OPEN`, `TRIAGE`, `INVESTIGATING`, `ACTION_REQUIRED`, `PENDING_VERIFICATION`, `CLOSED`, `CANCELLED`

### Case Management REST Endpoints:
- `POST /api/v1/sif/cases`: Explicitly create an HSE investigation case with optional initial source links and idempotency key.
- `GET /api/v1/sif/cases`: Query and filter cases by status, priority, type, owner, or date ranges with pagination.
- `GET /api/v1/sif/cases/{case_id}`: Retrieve detailed case information and attached source references.
- `PATCH /api/v1/sif/cases/{case_id}`: Update case title, description, or priority.
- `POST /api/v1/sif/cases/{case_id}/assign`: Assign an investigator/owner to the case with an audit record.
- `POST /api/v1/sif/cases/{case_id}/status`: Transition case lifecycle status (enforces validation and closure rationale).
- `POST /api/v1/sif/cases/{case_id}/sources`: Attach a source intelligence reference (`REPORT`, `ASSESSMENT`, `PATTERN`, `CONCENTRATION`, `REVIEW`, `ACTION`).
- `DELETE /api/v1/sif/cases/{case_id}/sources/{source_id}`: Detach an associated source intelligence reference.
- `GET /api/v1/sif/cases/{case_id}/timeline`: Retrieve the append-only chronological audit event timeline.
- `GET /api/v1/sif/cases/{case_id}/summary`: Compute and retrieve aggregate statistical case metrics.
- `POST /api/v1/sif/cases/{case_id}/reopen`: Reopen a previously closed case with mandatory justification (CANCELLED cases remain strictly terminal).

---

## 14. Phase 10 — HSE Command Center / Operational Intelligence API

Phase 10 provides the backend aggregation and read API for the HSE Command Center, presenting frontend clients with a coherent, multi-dimensional operational view of already-persisted SIF intelligence:

```
Existing Persisted Intelligence (Phases 1–9)
(Reports, Assessments, Precursors, Patterns, Concentrations, Reviews, Actions, Cases)
    ↓
Read-Only Aggregation Layer (Phase 10)
    ↓
HSE Command Center APIs
    ↓
Frontend Operational Dashboard Visualization
```

### Architectural Principles:
1. **Pure Aggregation Layer**: Phase 10 is strictly a read-only aggregation interface. It introduces **no new AI/ML inference, no embeddings, no predictive risk scoring, no probability estimates, and no forecasting**.
2. **Authoritative Intelligence Consumption**: Consumes existing persisted outputs from Phases 1–9 without redefining SIF classifications, thresholds, LSR mappings, precursor syntheses, similarity clusters, concentrations, reviews, actions, or cases.
3. **Descriptive Analytics Only**: Counts and distributions represent historical, persisted observation activity and operational follow-up workload; they do not represent future risk estimates.
4. **Performance Optimized**: Uses database-side SQL aggregations, grouped projections, and indexed lookups to prevent N+1 queries.
5. **Deterministic Filtering & Pagination**: Supports filtering by date ranges (`from_date`, `to_date`), operational locations, Life-Saving Rules (`lsr_code`), and entity statuses with deterministic sorting.
6. **Graceful Empty State**: Gracefully returns zeros and empty collections without error or fabricated data.
7. **Multi-Phase Investigation Snapshot**: Provides a compact operational chain linking Reports → Assessments → Precursors → Patterns → Concentrations → Reviews → Actions → Cases.

### Command Center REST Endpoints:
- `GET /api/v1/sif/command-center/overview`: Executive summary of reports, assessments, potential SIFs, reviews, open actions, active cases, patterns, and concentrations.
- `GET /api/v1/sif/command-center/sif`: Detailed breakdown of SIF assessments, actual vs potential severities, LSR distributions, and chronological monthly trends.
- `GET /api/v1/sif/command-center/precursors`: Overview of recurring precursor patterns, top hazards, barrier failures, activities, and affected locations.
- `GET /api/v1/sif/command-center/concentrations`: Exposes Phase 3 concentration intelligence across the 6 canonical dimensions (`PATTERN`, `HAZARD`, `BARRIER_FAILURE`, `ACTIVITY`, `LIFE_SAVING_RULE`, `LOCATION`).
- `GET /api/v1/sif/command-center/lsr`: Descriptive distribution and statistics across all configured Life-Saving Rules.
- `GET /api/v1/sif/command-center/actions`: Overview of Phase 8 HSE action recommendations by status, priority, category, and age.
- `GET /api/v1/sif/command-center/cases`: Overview of Phase 9 HSE investigation cases by status, priority, type, owner, and recently updated items.
- `GET /api/v1/sif/command-center/reviews`: Overview of Phase 5 human review workloads, decisions, feedback categories, and age.
- `GET /api/v1/sif/command-center/investigation-snapshot`: Compact operational chain linking related reports, assessments, patterns, concentrations, reviews, actions, and cases.

---

## 15. Phase 11 — HSE Intelligence Delivery & Frontend Contract

Phase 11 establishes a robust, hardened API Delivery Layer and Frontend Contract on top of the Phase 10 Command Center API:

```
Command Center Aggregations (Phase 10)
    ↓
API Delivery Layer & Contract Hardening (Phase 11)
├── Request Traceability (X-Request-ID Header & Injected Request Context)
├── Standardized Error Envelopes (ApiErrorResponse, ApiError with canonical codes)
├── Reusable Metadata & Pagination Envelopes (ApiMetadata, PaginationMetadata)
├── Documented Frontend Filter & Data Mapping (COMMAND_CENTER_CONTRACT.md, FRONTEND_DATA_MAPPING.md)
└── OpenAPI Contract Verification Suite (400 Total Passing Tests)
    ↓
Frontend Operational Dashboard (Untouched & Ready for Integration)
```

### Architectural Principles & Hardening Guarantees:
1. **API Delivery & Contract Hardening Only**: Phase 11 does **not** create new intelligence, predictive scoring, risk forecasts, autonomous actions, or AI/ML inference.
2. **Deterministic Request Traceability**: Every incoming request is tracked via `X-Request-ID` HTTP headers and structured error/metadata payloads without storing IDs in the database.
3. **Unified Error Contract**: All API exceptions (`SIFSentinelException`, `RequestValidationError`, `HTTPException`, unhandled errors) return structured `ApiError` payloads containing machine-readable error codes (`INVALID_DATE_RANGE`, `VALIDATION_ERROR`, `RESOURCE_NOT_FOUND`, `INTERNAL_SERVER_ERROR`, `CONFLICT`) while suppressing internal stack traces and secrets.
4. **Stable Frontend Mapping & Filter Contracts**: Documented in `docs/api/COMMAND_CENTER_CONTRACT.md` and `docs/api/FRONTEND_DATA_MAPPING.md`.
5. **No Database Schema Changes**: Zero new database tables, models, or Alembic migrations.
6. **Frontend Untouched**: Zero changes made to frontend source files.
7. **Read-Only Invariant**: Guarantees zero mutation of underlying Phase 1–10 source tables during inspection or aggregation.

---

## 16. Phase 12 — Deployment, Observability & Diagnostic Hardening

Phase 12 hardens the OIL SIF Sentinel backend for enterprise deployment, diagnostic observability, and operational resilience:

```
Runtime Hardening & Observability (Phase 12)
├── Configuration Hardening (Pydantic BaseSettings, .env.example, environment precedence)
├── Decoupled Probes (GET /api/v1/health for Liveness, GET /api/v1/ready for DB Readiness)
├── Request Traceability (Preserve/Generate UUID4 X-Request-ID, header injection, access logs)
├── Structured JSON Logging (Standardized JSON logs with component, latency, status, IDs)
├── Exception Hardening & Error Sanitization (Zero stack traces/DB internals leaked in HTTP)
├── Database & Session Resilience (Strict rollback on failure, pool management, clean teardown)
├── Batch Failure Recovery (Structured error logs, fatal failure catch, deterministic FAILED status)
├── Minimal Containerization (Multi-stage Dockerfile, non-root user, .dockerignore, docker-compose.yml)
└── Graceful Shutdown (Database engine disposal on SIGTERM/SIGINT)
```

### Key Capabilities:
1. **Liveness vs Readiness Probes**:
   - `GET /api/v1/health`: Lightweight, process-level liveness probe running in $<1\text{ms}$ with zero DB I/O.
   - `GET /api/v1/ready`: Dependency readiness probe verifying live PostgreSQL connectivity and `pgvector` extension readiness with sanitized 503 error handling.
2. **Standardized Structured Logging**: Emits single-line JSON logs containing `timestamp`, `level`, `component`, `request_id`, `method`, `route`, `status`, `duration_ms`, and `batch_id`.
3. **Containerization & Deployment Support**: Production-ready `Dockerfile` running as non-root `appuser` with container healthchecks and a complete `docker-compose.yml` stack.
4. **Comprehensive Documentation**: Complete operational and deployment runbook available at `docs/operations/DEPLOYMENT_AND_OPERABILITY.md`.

---

## 17. Phase 13 — Production Validation, Performance & Reliability Hardening

Phase 13 validates and hardens the existing OIL SIF Sentinel backend under realistic operational workloads without altering SIF intelligence algorithms, API schemas, frontend interfaces, or database models:

```
Operational Hardening & Validation (Phase 13)
├── Performance Benchmarking (Sub-35ms median single-report analysis, sub-15ms Command Center endpoints)
├── Batch Throughput Validation (10, 100, 300 rows CSV ingestion with strict counter invariants)
├── Concurrency Testing (2, 5, 10, 20 concurrent workers; 100% success rate, 0 connection leaks)
├── Database Pool Resilience (Checked in/out tracking, clean rollback on failure, zero session leaks)
├── Embedding Singleton Performance (Cold start ~29s isolated to startup; warm inference ~13ms median)
├── Failure & Recovery Diagnostics (Sanitized 503 on DB down, automatic recovery on DB restore)
├── Large Input & Boundary Stress (4,650-character narrative processing, high-duplicate handling)
└── Performance Regression Protection (8 automated performance & reliability integration tests)
```

### Key Validation Outcomes:
1. **Zero Database Migrations**: Alembic head remains at `0008_phase9_hse_case_management.py` with 0 schema changes.
2. **Deterministic Accounting Invariants**: `total_rows == accepted_rows + rejected_rows + duplicate_rows` and `accepted_rows == processed_rows + failed_rows` verified across all batch sizes.
3. **Comprehensive Performance Report**: Detailed metrics, methodology, and engineering observations documented in `docs/performance/PHASE_13_PERFORMANCE_REPORT.md`.

---

## 18. Phase 14 — Production Readiness, Security & Release Validation

Phase 14 verifies security hygiene, credential protection, containerization posture, API contract freezes, and production release readiness without altering SIF intelligence algorithms, API schemas, frontend interfaces, or database models:

```
Production Readiness & Release Validation (Phase 14)
├── Secret & Credential Audit (Zero committed credentials, sanitized .env.example)
├── Ingestion Security (Strict CSV validation, 10MB file limit, path traversal neutralization)
├── API Error Sanitization (Zero stack traces/SQL leaks in HTTP responses, structured error codes)
├── Security Headers Injection (X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Referrer-Policy)
├── CORS Configuration Safety (Explicit allowed origin parsing, configurable domain restrictions)
├── Docker Container Hardening (Non-root appuser UID 10001, container healthchecks, .dockerignore)
├── Data Isolation Boundary (Proprietary data/production directory protected and excluded from VCS)
├── OpenAPI Contract Freeze (Full OpenAPI schema validated across all 12 API modules)
└── Release Smoke Testing (Verified end-to-end chain: Startup → Health → Readiness → Analyze → Command Center)
```

### Key Validation Outcomes:
1. **Zero Database Migrations**: Alembic head remains at `0008_phase9_hse_case_management.py` with 0 schema changes.
2. **Security & Release Checklist**: Comprehensive verification and deployment runbook documented in `docs/security/SECURITY_AND_RELEASE_CHECKLIST.md`.
3. **API Contract Compatibility**: No breaking API contract changes detected; OpenAPI routes, methods, DTOs, and error envelopes remain compatible with the established Phase 1–13 contract.

---

## 19. Verification & Testing

Complete regression and integration suite execution:
```bash
.venv\Scripts\pytest --cov=app --cov-report=term-missing -v
```

- **Regression Suite:** 434 tests (100% pass rate)
- **Application Coverage:** 93%
- **Deterministic Scenarios Verified:**
  - Scenario A: Suspended Load / Line of Fire → `CONFIRM_AI` review audit
  - Scenario B: Working at Height → `CORRECT` review with AI preservation
  - Scenario C: Energy Isolation / LOTO failure pipeline
  - Scenario D: Housekeeping low-severity observation (`NON_SIF` exclusion)
  - Scenario E: Semantically related reports recurring pattern discovery
  - Scenario F: Unrelated reports pattern exclusion
  - Scenario G: Multi-location pattern with representative location normalization
  - Scenario H: Batch ingestion with decoupled pattern/concentration refresh
  - Phase 7 Scenarios: Full evidence graph traceability, factor explanations, similarity ranking, and consolidated investigation context.
  - Phase 8 Scenarios: Full deterministic action generation, barrier verification, LSR controls, human review integration, idempotency, lifecycle state transitions, and invalid transition rejection.
  - Phase 9 Scenarios: Complete HSE case lifecycle management, multiple source intelligence attachment/detachment, append-only audit event timeline, case ownership assignment, controlled closure with action resolution verification, justified case reopening, duplicate protection, and deterministic aggregate summaries.
  - Phase 10 Scenarios: Command Center executive overview, SIF severity breakdown, precursor pattern distribution, 6 canonical concentration dimensions, LSR statistics, action & case workloads, human review queue metrics, date/location/LSR filters, pagination, deterministic sorting, multi-phase investigation snapshot chain, read-only source integrity, and OpenAPI contract validation.
  - Phase 11 Scenarios: All 9 Command Center endpoints verified (Scenarios A–T), valid empty states, populated DTO parsing, date/location/LSR/concentration/action/case filtering, pagination invariants, invalid date range 400 error schema, invalid enum 422 error schema, missing resource 404 error schema, request ID traceability headers, read-only non-mutation of underlying tables, and full OpenAPI contract compliance.
  - Phase 12 Scenarios: Liveness endpoint (/health) zero-DB execution, readiness endpoint (/ready) DB connectivity & pgvector validation, readiness 503 failure handling on DB down, request ID preservation & generation, structured JSON logging format & field extraction, sanitized 500 error boundary, session rollback safety on failure, batch unhandled exception recovery & FAILED status recording, and graceful shutdown lifecycle.
  - Phase 13 Scenarios: Single-report sub-stage latency profiling, Command Center read-only sub-15ms latency verification, CSV batch ingestion accounting invariants across 10/100/300 rows, concurrent request handling (2-20 workers) with zero 5xx errors, database session pool lifecycle and leak prevention, embedding singleton lifecycle, DB outage and recovery lifecycle with sanitized error envelopes, and large narrative input processing boundary validation.
  - Phase 14 Scenarios: Secret scanning and .gitignore credential protection, template hygiene (.env.example), production data isolation, CSV upload boundary validation (file type, size limits, path traversal neutralization), API security headers (nosniff, DENY, Referrer-Policy), sanitized error responses on invalid UUIDs/dates/payloads, CORS configuration parsing, Dockerfile non-root execution and healthcheck validation, and end-to-end release smoke workflow verification.



