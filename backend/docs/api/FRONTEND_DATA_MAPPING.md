# OIL SIF Sentinel — Frontend Data Mapping Contract

## Document Version
- **API Version**: `1.0`
- **Phase**: Phase 11 — HSE Intelligence Delivery & Frontend Contract
- **Target Audience**: Frontend UI/UX Engineers, Dashboard Developers, Client Consumers

---

## 1. Executive Summary

This document specifies the exact mapping between the backend Phase 10 Command Center API responses and the frontend UI views/components.

All data exposed through these endpoints is **persisted and deterministic** (Phases 1–9). The frontend layer should consume these DTOs directly without requiring client-side computation or heuristic re-scoring.

---

## 2. Endpoint to UI View Mapping Table

| Endpoint | Target Frontend View / Component | Key Metrics / Visualizations |
| :--- | :--- | :--- |
| `GET /api/v1/sif/command-center/overview` | **Executive Overview Dashboard** | KPI metric cards (Total Reports, SIF Breakdown, Open Actions, Active Cases, Queue Depth). |
| `GET /api/v1/sif/command-center/sif` | **SIF Severity & Outcomes View** | Donut charts (Classification & Severity splits), Monthly Trend Line Chart, LSR Distribution. |
| `GET /api/v1/sif/command-center/precursors` | **Recurring Precursors Intelligence** | Top recurring patterns list, Hazard/Barrier/Activity cluster charts, Affected locations. |
| `GET /api/v1/sif/command-center/concentrations` | **Risk Concentration Matrix** | Heatmap/Table across 6 canonical dimensions, Temporal trend badges (Increasing/Decreasing/Stable). |
| `GET /api/v1/sif/command-center/lsr` | **Life-Saving Rules Compliance View** | LSR rule cards with assessment volume, potential SIF counts, reviewed ratios, and open actions. |
| `GET /api/v1/sif/command-center/actions` | **HSE Action Workload Tracker** | Status Kanban/Bar charts, Priority breakdown, Category distribution, Action aging buckets. |
| `GET /api/v1/sif/command-center/cases` | **HSE Investigation Case Hub** | Case status pipeline, Type breakdown, Owner workload, Recently updated case table. |
| `GET /api/v1/sif/command-center/reviews` | **Human Triage & Review Queue** | Review progress gauge, Decision distribution, Feedback categorizations, Review age histogram. |
| `GET /api/v1/sif/command-center/investigation-snapshot` | **Investigation Drill-Down / Traceability** | Interactive multi-node graph linking Reports, Assessments, Patterns, Actions, and Cases. |

---

## 3. View-by-View Detailed Mapping Specifications

### 3.1 Executive Overview Dashboard
**Endpoint**: `GET /api/v1/sif/command-center/overview`

#### Component Mapping:
- **Header Card**:
  - `generated_at`: Display "Report generated at [formatted timestamp]".
  - `data_as_of`: Display "Data as of [formatted timestamp]".
- **KPI Cards**:
  - `total_reports`: Total Incidents & Near-Misses.
  - `total_assessments`: SIF Screening Volume.
  - `potential_sif_count`: High-visibility badge (POTENTIAL_SIF).
  - `non_sif_count`: Standard badge (NON_SIF).
  - `undetermined_count`: Warning badge (UNDETERMINED).
  - `open_action_count`: Total Open Actions requiring HSE intervention.
  - `active_case_count`: Active Formal Investigations.
  - `unreviewed_count`: Pending Human Triage Reviews.
  - `recurring_pattern_count`: Discovered Precursor Patterns ($N \ge 3$).
  - `concentration_count`: Active Risk Concentrations.

---

### 3.2 SIF Severity & Outcomes View
**Endpoint**: `GET /api/v1/sif/command-center/sif`

#### Component Mapping:
- **SIF Classification Donut**:
  - `classification_counts["POTENTIAL_SIF"]` (Red/Amber)
  - `classification_counts["NON_SIF"]` (Green/Gray)
  - `classification_counts["UNDETERMINED"]` (Yellow/Orange)
- **Potential Outcome Severity Breakdown**:
  - `potential_severity_counts["FATALITY"]`
  - `potential_severity_counts["PERMANENT_DISABLING_INJURY"]`
  - `potential_severity_counts["LOST_TIME_INJURY"]`
  - `potential_severity_counts["MEDICAL_TREATMENT"]`
  - `potential_severity_counts["FIRST_AID"]`
- **Monthly Assessment Trend Chart**:
  - X-Axis: `assessment_trend_by_month[].period` (e.g. `2026-03`)
  - Series 1: `potential_sif_count`
  - Series 2: `non_sif_count`
  - Series 3: `undetermined_count`

---

### 3.3 Precursor Intelligence View
**Endpoint**: `GET /api/v1/sif/command-center/precursors`

#### Component Mapping:
- **Top Precursor Patterns Table**:
  - Columns: `pattern_code`, `title`, `hazard_category`, `activity_type`, `failed_barrier_type`, `occurrence_count`, `supporting_report_count`, `first_detected_at`.
- **Dimensional Aggregates (Bar Charts)**:
  - `top_hazard_dimensions`: Hazard frequency distribution.
  - `top_barrier_failure_dimensions`: Failed barrier breakdown.
  - `top_activity_dimensions`: Operational activities with highest recurrence.
  - `supporting_locations`: Top affected facilities/rigs.

---

### 3.4 Risk Concentration Matrix
**Endpoint**: `GET /api/v1/sif/command-center/concentrations`

#### Component Mapping:
- **6 Canonical Dimension Filters**:
  - `PATTERN`, `HAZARD`, `BARRIER_FAILURE`, `ACTIVITY`, `LIFE_SAVING_RULE`, `LOCATION`.
- **Concentration Cards / Grid**:
  - `dimension_value`: e.g. "Work at Height", "Rig-04", "Pressure Isolation".
  - `occurrence_count`: Total occurrences.
  - `distinct_report_count`: Supporting distinct reports.
  - `observed_trend`: Trend indicator:
    - `INCREASING` $\rightarrow$ Red arrow up $\uparrow$
    - `DECREASING` $\rightarrow$ Green arrow down $\downarrow$
    - `STABLE` $\rightarrow$ Blue horizontal arrow $\rightarrow$
    - `INSUFFICIENT_DATA` $\rightarrow$ Gray dashed line $-$
- **Pagination Controls**:
  - Bound to `limit`, `offset`, and `total_concentrations`.

---

### 3.5 Life-Saving Rules Compliance View
**Endpoint**: `GET /api/v1/sif/command-center/lsr`

#### Component Mapping:
- **LSR Rule Cards**:
  - `rule_code`: e.g. `BYPASS_SAFETY_CONTROLS`, `CONFINED_SPACE`, `ENERGY_ISOLATION`.
  - `rule_name`: Full IOGP rule description.
  - `assessment_count`: Total events mapped to this rule.
  - `potential_sif_count`: High-risk SIF events mapped.
  - `reviewed_count`: Human-validated events.
  - `open_action_count`: Actions currently targeting this rule.

---

### 3.6 HSE Action Workload Tracker
**Endpoint**: `GET /api/v1/sif/command-center/actions`

#### Component Mapping:
- **Status Distribution**:
  - `status_counts["OPEN"]`, `status_counts["ACKNOWLEDGED"]`, `status_counts["IN_PROGRESS"]`, `status_counts["COMPLETED"]`, `status_counts["DISMISSED"]`.
- **Priority Matrix**:
  - `priority_distribution["CRITICAL"]`, `HIGH`, `MEDIUM`, `LOW`.
- **Action Aging Histogram**:
  - `< 7 days`, `7-30 days`, `> 30 days`.

---

### 3.7 HSE Case Hub
**Endpoint**: `GET /api/v1/sif/command-center/cases`

#### Component Mapping:
- **Case Pipeline Stages**:
  - `status_counts["OPEN"]`, `TRIAGE`, `INVESTIGATING`, `ACTION_REQUIRED`, `PENDING_VERIFICATION`, `CLOSED`, `CANCELLED`.
- **Case Type Split**:
  - `case_type_distribution["SIF_INVESTIGATION"]`, `NEAR_MISS_REVIEW`, etc.
- **Recently Updated Cases Table**:
  - `case_key`, `title`, `status`, `priority`, `owner`, `updated_at`.

---

### 3.8 Human Triage & Review Queue View
**Endpoint**: `GET /api/v1/sif/command-center/reviews`

#### Component Mapping:
- **Review Status Summary**:
  - `pending_reviews`: Unclaimed reviews in queue.
  - `in_review_count`: Actively claimed reviews.
  - `reviewed_count`: Completed reviews.
- **Decision Breakdown**:
  - `decision_distribution["CONFIRMED"]` (Human confirmed AI assessment)
  - `decision_distribution["CORRECTED"]` (Human updated classification)
  - `decision_distribution["OVERRIDDEN"]` (Human rejected AI classification)
- **Pending Review Aging**:
  - `< 7 days`, `7-30 days`, `> 30 days`.

---

### 3.9 Investigation Snapshot / Traceability Drill-Down
**Endpoint**: `GET /api/v1/sif/command-center/investigation-snapshot`

#### Component Mapping:
- **Target Query**: `report_ref`, `case_key`, `pattern_code`, or `concentration_key`.
- **Multi-Node Visual Graph**:
  - **Reports Node**: `reports[]` (ID, ref, source type, location, created_at).
  - **Assessments Node**: `assessments[]` (Classification, potential severity, evidence score, precursor signature).
  - **Patterns Node**: `patterns[]` (Pattern code, title, occurrences).
  - **Concentrations Node**: `concentrations[]` (Key, dimension type/value, occurrences).
  - **Reviews Node**: `reviews[]` (Status, human decision, reviewer ID).
  - **Actions Node**: `actions[]` (Action key, title, status, priority).
  - **Cases Node**: `cases[]` (Case key, title, status, priority).
- **Summary Badge Count**:
  - `summary["report_count"]`, `assessment_count`, `pattern_count`, `concentration_count`, `review_count`, `action_count`, `case_count`.

---

## 4. Error Handling & Traceability in UI

When an API call returns a non-2xx status, the client should extract `X-Request-ID` and display structured user guidance:

```typescript
interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: any;
    request_id?: string;
  };
}

function handleApiError(response: Response, payload: ApiErrorPayload) {
  const reqId = payload.error?.request_id || response.headers.get("X-Request-ID");
  console.error(`API Error [${payload.error?.code}] (Trace ID: ${reqId}): ${payload.error?.message}`);
  // Render user-friendly toast or banner displaying message and Trace ID
}
```
