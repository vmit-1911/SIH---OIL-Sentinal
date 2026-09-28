# OIL SIF Sentinel — HSE Command Center API Contract

## Specification Version
- **API Version**: `1.0`
- **Base URL**: `/api/v1`
- **Phase**: Phase 11 — HSE Intelligence Delivery & Frontend Contract
- **Contract Type**: Authoritative REST JSON Interface (Read-Only)

---

## 1. Architectural Principles & Guarantees

1. **Strictly Read-Only**: The Command Center endpoints perform SQL-level aggregation and projection over persisted Phase 1–9 data models. They execute zero mutations or state updates.
2. **No Autonomous Intelligence Creation**: No new SIF classifications, risk concentrations, pattern discoveries, or action recommendations are generated in this layer. All metrics reflect persisted source-of-truth tables (`SafetyReport`, `SIFAssessment`, `PrecursorPattern`, `RiskConcentration`, `TriageReview`, `HSEActionRecommendation`, `HSECase`, `HSECaseEvent`).
3. **Deterministic Aggregation**: Responses are reproducible and deterministic based strictly on database state and requested filter parameters.
4. **Request Traceability**: Every request is assigned a deterministic request identifier (via `X-Request-ID` HTTP header and response error/metadata payloads).
5. **No Synthetic / Fake Data**: Empty states return explicit zeros and empty arrays. No fake or placeholder records are ever injected.

---

## 2. Authentication & Authorization

> [!NOTE]
> **Authentication Placeholder**: Authentication is outside Phase 11 scope. Endpoints currently execute without credential headers. Centralized OAuth2/JWT and Role-Based Access Control (RBAC) are scheduled for future production infrastructure phases.

---

## 3. Endpoints Overview

All Command Center endpoints reside under `/api/v1/sif/command-center`:

| Method | Path | Response Model | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/sif/command-center/overview` | `CommandCenterOverview` | High-level executive KPI metrics across all operational entities. |
| `GET` | `/api/v1/sif/command-center/sif` | `SIFOverviewDTO` | SIF assessment distributions, severity breakdowns, and monthly trends. |
| `GET` | `/api/v1/sif/command-center/precursors` | `PrecursorOverviewDTO` | Top recurring precursor patterns and multi-dimensional cluster distributions. |
| `GET` | `/api/v1/sif/command-center/concentrations` | `ConcentrationOverviewDTO` | Risk concentration findings across the 6 canonical dimensions with pagination. |
| `GET` | `/api/v1/sif/command-center/lsr` | `LSROverviewDTO` | Descriptive statistics and activity distribution across Life-Saving Rules. |
| `GET` | `/api/v1/sif/command-center/actions` | `ActionOverviewDTO` | HSE action recommendations workload by status, priority, category, and age. |
| `GET` | `/api/v1/sif/command-center/cases` | `CaseOverviewDTO` | HSE investigation cases by status, priority, type, owner, and recently updated items. |
| `GET` | `/api/v1/sif/command-center/reviews` | `ReviewQueueOverviewDTO` | Human triage review workload, decision breakdowns, feedback categories, and age. |
| `GET` | `/api/v1/sif/command-center/investigation-snapshot` | `InvestigationSnapshotDTO` | Operational graph linking related entities for drill-down investigation context. |

---

## 4. Query Filter Contract

### 4.1 Filter Parameters Matrix

| Filter Parameter | Type | Allowed Values / Constraints | Supported Endpoints |
| :--- | :--- | :--- | :--- |
| `from_date` | `datetime` (ISO-8601) | e.g. `2026-01-01T00:00:00Z` | All 8 aggregation endpoints |
| `to_date` | `datetime` (ISO-8601) | Must be $\ge$ `from_date` | All 8 aggregation endpoints |
| `location` | `string` | Substring match against reported/affected location | `overview`, `sif`, `precursors`, `concentrations`, `lsr` |
| `lsr_code` | `string` | e.g. `LSR-01`, `BYPASS_SAFETY_CONTROLS` | `sif`, `precursors`, `lsr` |
| `dimension` | `string` (enum) | `PATTERN`, `HAZARD`, `BARRIER_FAILURE`, `ACTIVITY`, `LIFE_SAVING_RULE`, `LOCATION` | `concentrations` |
| `trend` | `string` (enum) | `STABLE`, `INCREASING`, `DECREASING`, `INSUFFICIENT_DATA` | `concentrations` |
| `status` | `string` (enum) | `OPEN`, `ACKNOWLEDGED`, `IN_PROGRESS`, `COMPLETED`, `DISMISSED` | `actions` |
| `priority` | `string` (enum) | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | `actions`, `cases` |
| `category` | `string` (enum) | `PREVENTIVE_MAINTENANCE`, `PROCEDURE_UPDATE`, `TRAINING_COMPLIANCE`, `ENGINEERING_CONTROL`, `BARRIER_REINFORCEMENT`, `MANAGEMENT_REVIEW` | `actions` |
| `source_type` | `string` (enum) | `ASSESSMENT`, `PATTERN`, `CONCENTRATION`, `CASE`, `MANUAL` | `actions` |
| `status` | `string` (enum) | `OPEN`, `TRIAGE`, `INVESTIGATING`, `ACTION_REQUIRED`, `PENDING_VERIFICATION`, `CLOSED`, `CANCELLED` | `cases` |
| `case_type` | `string` (enum) | `SIF_INVESTIGATION`, `NEAR_MISS_REVIEW`, `PATTERN_FOLLOW_UP`, `CONCENTRATION_MITIGATION`, `AUDIT_ACTION` | `cases` |
| `owner` | `string` | Substring match against case owner name/email | `cases` |
| `limit` | `integer` | Precursors: $[1, 100]$ (default 10); Concentrations: $[1, 200]$ (default 50) | `precursors`, `concentrations` |
| `offset` | `integer` | $\ge 0$ (default 0) | `precursors`, `concentrations` |
| `report_ref` | `string` | Exact or prefix match (e.g. `OIL-REP-001`) | `investigation-snapshot` |
| `case_key` | `string` | Exact case key (e.g. `CASE-01J...`) | `investigation-snapshot` |
| `pattern_code` | `string` | Exact pattern code (e.g. `PAT-01J...`) | `investigation-snapshot` |
| `concentration_key` | `string` | Exact concentration key | `investigation-snapshot` |

### 4.2 Date Validation Rule
If both `from_date` and `to_date` are provided, the condition `from_date <= to_date` MUST hold. Otherwise, HTTP 400 with error code `INVALID_DATE_RANGE` is returned:
```json
{
  "error": {
    "code": "INVALID_DATE_RANGE",
    "message": "Invalid date range: 'from_date' cannot be greater than 'to_date'.",
    "details": null,
    "request_id": "c1f76d49-4113-4318-971c-3b0d2d3856e1"
  }
}
```

---

## 5. Standardized Error Contract

All error responses adhere to the unified `ApiErrorResponse` envelope:

```json
{
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human-readable description of error.",
    "details": {},
    "request_id": "uuid-v4-string"
  }
}
```

### Canonical Error Codes & HTTP Status Codes

| HTTP Status | Error Code | Trigger Condition |
| :--- | :--- | :--- |
| `400 Bad Request` | `INVALID_DATE_RANGE` | `from_date` is later than `to_date` |
| `400 Bad Request` | `BAD_REQUEST` | Malformed query arguments or invalid state transition |
| `400 Bad Request` | `CASE_CLOSURE_BLOCKED` | Attempted closure of case with unresolved blocking actions |
| `400 Bad Request` | `REVIEW_RATIONALE_REQUIRED` | Override of AI assessment without mandatory rationale |
| `404 Not Found` | `RESOURCE_NOT_FOUND` | Target entity (Report, Assessment, Case, Action, Review) not found |
| `409 Conflict` | `CONFLICT` / `REVIEW_CONFLICT` | Concurrency conflict or duplicate source attachment |
| `422 Unprocessable` | `VALIDATION_ERROR` | Request payload or query param failed Pydantic schema validation |
| `500 Internal Error` | `INTERNAL_SERVER_ERROR` | Unexpected server fault (stack traces and credentials suppressed) |
| `501 Not Implemented` | `NOT_IMPLEMENTED` | Explicit placeholder for future phases |

---

## 6. Pagination Contract

Paginated list responses (e.g. `/concentrations`, `/precursors`) return deterministic pagination metadata:

```json
{
  "total_concentrations": 42,
  "limit": 20,
  "offset": 0,
  "items": [ ... ]
}
```

### Invariants:
1. `offset` specifies 0-based starting index.
2. `limit` specifies page size.
3. Pagination does NOT mutate aggregate totals (`total_concentrations`, `total_patterns`).
4. Stable deterministic ordering is maintained using primary keys and creation timestamps.

---

## 7. Timestamp & As-Of Semantics

- `generated_at`: ISO-8601 UTC timestamp indicating exactly when the API response was evaluated.
- `data_as_of`: ISO-8601 UTC timestamp representing the latest relevant persisted record timestamp in the queried tables. When the database is empty, it reflects `generated_at`.

---

## 8. Empty States

When the database contains zero matching records, the API returns a structured empty response with 0 counts and empty arrays:

```json
{
  "total_reports": 0,
  "total_assessments": 0,
  "potential_sif_count": 0,
  "non_sif_count": 0,
  "undetermined_count": 0,
  "reviewed_count": 0,
  "unreviewed_count": 0,
  "open_action_count": 0,
  "active_case_count": 0,
  "recurring_pattern_count": 0,
  "concentration_count": 0
}
```

Zero counts are returned as `0` (never `null`). List fields are returned as `[]` (never `null`).
