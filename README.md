# 🛡️ OIL SIF Sentinel — Enterprise AI Safety Intelligence Platform

> **AI/NLP Engine to Detect Serious Injury & Fatality (SIF) Precursors in Oil India Limited (OIL) Unsafe-Act / Unsafe-Condition and Near-Miss Field Reports.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.122-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6.svg?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=flat&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg?style=flat&logo=postgresql)](https://github.com/pgvector/pgvector)
[![IOGP Report 459](https://img.shields.io/badge/Standard-IOGP%20Report%20459%20(2018)-E02424.svg)](https://www.iogp.org)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20OIL-blue.svg)](#)

---

## 📑 Table of Contents
1. [Problem Statement (PS)](#1-problem-statement-ps)
2. [Executive Solution](#2-executive-solution)
3. [What We Developed](#3-what-we-developed)
4. [Unique Features & Innovations](#4-unique-features--innovations)
5. [Complete Technology Stack](#5-complete-technology-stack)
6. [Internal Pipelines & Core Engine](#6-internal-pipelines--core-engine)
7. [The AI & NLP Subsystem](#7-the-ai--nlp-subsystem)
8. [End-to-End System Architecture](#8-end-to-end-system-architecture)
9. [Frontend Mission Control Views](#9-frontend-mission-control-views)
10. [REST API Contract & Endpoints](#10-rest-api-contract--endpoints)
11. [Installation & Local Setup](#11-installation--local-setup)
12. [Verification & Testing](#12-verification--testing)

---

## 1. Problem Statement (PS)

### Context & Operational Challenges
Oil India Limited (OIL) oversees vast operational infrastructure across the Assam Basin, Rajasthan Project, KG Offshore Basin, and extensive pipeline networks. Operating units—including exploratory drilling rigs, workover rigs, Early Production Systems (EPS), Gas Gathering Stations (GGS), crude oil processing plants, and compressor stations—generate thousands of daily field observation reports.

These reports capture:
* **Unsafe Acts (UA)**: Behavioral non-compliances (e.g., bypassing double block and bleed, improper fall arrest tethering).
* **Unsafe Conditions (UC)**: Physical asset anomalies (e.g., corroded flange gaskets, passing bleed-off valves, passing gas seals).
* **Near-Miss Events (NM)**: Incidents where an uncontrolled energy release occurred but resulted in zero casualties due to fortunate timing or secondary barriers.

### The Fatal Flaw of the Traditional Safety Pyramid
Conventional industrial HSE relies on Heinrich/Bird safety pyramids, which evaluate safety risk primarily on **Actual Outcome Severity** (Fatalities > Lost Time Injuries > First Aid > Near Misses). This methodology introduces a dangerous blind spot:
> **An event resulting in zero harm (e.g., a pressurized gas leak during flange servicing) often shares identical causal mechanisms and failed barriers with a catastrophic explosion or fatality.**

### Core Deficiencies in Existing Workflows
1. **Manual Triage Bottlenecks:** Periodic manual review of high-volume text logs leads to cognitive fatigue, backlogs, and delayed hazard mitigation.
2. **Conflation of Actual vs. Potential Severity:** High-hazard near-misses with broken barriers are misclassified as routine "minor observations" simply because nobody was struck.
3. **Failure to Detect Recurring Precursors:** Weak signals dispersed across different drilling rigs or workover stations remain isolated, hiding widespread systemic failure patterns.
4. **Lack of Explainability:** Black-box machine learning models cannot provide the audit-grade evidentiary provenance needed for high-stakes oil & gas HSE sign-offs.

---

## 2. Executive Solution

**OIL SIF Sentinel** is a dual-engine safety intelligence platform engineered specifically for oil, gas, and energy operations. It automatically screens, classifies, links, and visualizes high-energy hazards and failed barriers embedded in free-text safety narratives.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   OIL SIF SENTINEL                                     │
├──────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│  1. SIF Screening Engine │ 2. IOGP 459 Standard Mapper │ 3. Precursor Topology Cluster │
│  Separates actual harm   │ Maps field narratives to    │ Discovers recurring weak      │
│  from potential fatality │ 9 versioned Life-Saving     │ signals across multiple rigs  │
│  severity deterministics │ Rules with zero hallu-      │ and production assets using   │
│  using stored energy.    │ cinations.                  │ hybrid vector similarity.     │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

The system provides:
1. **Immediate SIF Potential Identification:** Automated triage classifying reports into `POTENTIAL_SIF`, `ACTUAL_SIF`, `NON_SIF`, or `UNDETERMINED`.
2. **Deterministic Standard Alignment:** Direct rule mapping against the internationally recognized **IOGP Report 459 (2018 Edition) Life-Saving Rules**.
3. **Structured 7-Dimensional Precursor Synthesis:** Extracts structured safety entities (Hazard, Activity, Barrier Failure, Worker Exposure, Potential Consequence, LSR, Location).
4. **Semantic & Structural Precursor Clustering:** Uses dense vector embeddings (`all-MiniLM-L6-v2`) and cosine distance search via `pgvector` to correlate recurring risks across geographical operating assets.
5. **Executive Mission Control & Explainable AI Dossiers:** A mission-critical, human-in-the-loop dashboard providing word-level evidence spans, synthesis equations, and audit-grade verification workflows.

---

## 3. What We Developed

### Unified Full-Stack Architecture
We developed a complete production-grade application comprising two tightly integrated layers:

```
[React 19 Mission Control UI] <───(Vite Proxy / HTTP REST)───> [FastAPI Backend & NLP Core]
              │                                                              │
              ├── TopUtilityBar & Navigation Rail                            ├── SIF Inference Engine
              ├── SIF Command Center Dashboard                               ├── 7D Precursor Synthesizer
              ├── Precursor Path & Barrier Topology                          ├── IOGP 459 Rule Engine
              ├── Interactive AI Report Analyzer                             ├── pgvector Hybrid Matcher
              ├── Site & Asset Spatial Exposure Grid                         ├── Risk Concentration Engine
              ├── IOGP Life-Saving Rules Matrix                              ├── Case Management & Review
              └── Explainable Evidence Dossier Modal                         └── Batch CSV Ingestion
```

### 1. Interactive Frontend Application (`src/`)
* **State-of-the-Art Mission Control Interface:** Built with React 19, TypeScript, and custom CSS design tokens. Optimized for control room displays with glassmorphic dark-mode styling, industrial typography, responsive data grids, and real-time polling.
* **Bi-directional Live API Bridge (`apiBridge.ts`):** Directly queries live backend endpoints for health, single-report inference, command center KPIs, and CSV ingestion, featuring automatic fallback to local simulated telemetry for offline resilience.
* **Auditable Evidence Dossier Modal:** Displays word-level highlighting of hazard vectors, energy sources, failed barriers, and rule provenance tags.

### 2. Scalable Backend & AI Core (`backend/`)
* **FastAPI Enterprise Engine:** Asynchronous Python API adhering to clean Hexagonal (Ports & Adapters) architecture with request-level UUID traceability, structured JSON logging, and deterministic exception handling.
* **Multi-stage SIF Screening & Context Extractor:** Comprehensive deterministic NLP engine equipped with an oil & gas safety lexicon, multi-energy screening heuristics, and negation detection.
* **Vector Semantic Store:** PostgreSQL 16 database accelerated by `pgvector` for candidate retrieval, hybrid precursor clustering, and persistent historical triage records.

---

## 4. Unique Features & Innovations

### 1. Actual vs. Potential Decoupling
Traditional HSE tools record `Actual Outcome = No Injury` and categorize the report as low priority. SIF Sentinel evaluates stored energy levels (e.g., >1000 psi hydraulic pressure, toxic H2S presence, work at >2m height) against barrier status: if a critical barrier failed or was bypassed, the event is escalated to `POTENTIAL_SIF` regardless of whether an injury occurred.

### 2. Structured 7-Dimensional Precursor Representation
Rather than storing vague text summaries, every screened report is synthesized into a standardized, indexable 7-dimensional object:
1. **Hazard:** Physical stored energy or toxic hazard (e.g., `High-Pressure Gas`).
2. **Activity:** Operational context (e.g., `Wellhead Flange Servicing`).
3. **Barrier Failure:** Primary safeguard compromised (e.g., `Double Block and Bleed`).
4. **Worker Exposure:** Human presence in trajectory (e.g., `Line of Fire`).
5. **Potential Consequence:** Worst-case plausible harm (e.g., `Fatal Blast / Projectile Impact`).
6. **Life-Saving Rule:** Standardized code (e.g., `LSR_04_ENERGY_ISOLATION`).
7. **Operational Asset:** Geographical location (e.g., `Duliajan Rig #14`).

### 3. Explainability & Transparent Provenance (Zero Hallucination)
Generative LLMs can hallucinate safety facts. SIF Sentinel uses a **deterministic extraction and scoring profile**. Every classification provides:
* Word-level evidence spans with start/end character offsets.
* Rule provenance IDs (e.g., `LSR_RULE_ENERGY_ISOLATION_004`, `LEXICON_HAZARD_PRESSURE`).
* A mathematical synthesis equation showing how factors contributed to the final evidence score.

### 4. Hybrid Precursor Similarity (50% Semantic + 50% Structural)
To identify precursor trends across disparate reports, SIF Sentinel calculates a weighted similarity score combining:
* **Structural Match (50%):** Exact and hierarchical overlaps in hazard types, broken barriers, and activities.
* **Semantic Vector Match (50%):** Cosine distance between 384-dimensional dense embeddings generated by `all-MiniLM-L6-v2`.

### 5. Resilient Offline Operation
The frontend incorporates a self-healing API Bridge. If the FastAPI backend or PostgreSQL database is offline or initializing, the frontend gracefully transitions to an internal deterministic screening model without blank screens or thrown exceptions, accompanied by real-time status telemetry in the top utility bar.

---

## 5. Complete Technology Stack

### Frontend Architecture
* **Framework:** React 19.2 (Functional Components + Hooks)
* **Language:** TypeScript 5.x (Strict type compliance, zero `any` leaks)
* **Build Tool:** Vite 8.3 with Hot Module Replacement (HMR) and reverse proxy
* **Styling:** Custom Vanilla CSS Design System (HSL design tokens, glassmorphism, responsive grid, micro-animations)
* **Icons:** Lucide React (Clean industrial iconography)
* **Quality Assurance:** Oxlint + TypeScript Compiler (`tsc -b`)

### Backend Architecture
* **Core Framework:** FastAPI 0.122+ (Async ASGI runtime)
* **Web Server:** Uvicorn (UVLoop event loop implementation)
* **Validation & Settings:** Pydantic v2 & Pydantic-Settings
* **ORM & Database Layer:** SQLAlchemy 2.0 (Async Engine) with Alembic migration manager
* **Database:** PostgreSQL 16 + `pgvector` extension for dense vector storage
* **Export Engines:** ReportLab (Audit-grade PDF dossiers) & Pandas/CSV

### AI, NLP & Embedding Stack
* **Dense Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional embeddings)
* **Deep Learning Framework:** PyTorch 2.14+ (CPU/CUDA optimized inference)
* **Text Processing:** Custom rule-based NLP parser, tokenization, regular expression lexicon, negation scopes
* **Taxonomy Engine:** Official IOGP Report 459 (2018 Edition) definition mapper

---

## 6. Internal Pipelines & Core Engine

```
[Raw Narrative Text]
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ PIPELINE 1: Context Extraction (Phase 1A)              │
│ - Lexicon Pattern Matching (Energy, Equipment, Actions)│
│ - Negation Scope Detection ("no leak", "was inspected")│
│ - Extraction of SafetyEventContext                     │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ PIPELINE 2: Multi-Factor SIF Screening (Phase 1B)      │
│ - Multi-factor Stored Energy Assessment                │
│ - Critical Physical Barrier Status Evaluation          │
│ - Mathematical Evidence Scoring [0.0 - 1.0]            │
│ - Classification: POTENTIAL_SIF, NON_SIF, UNDETERMINED │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ PIPELINE 3: IOGP Life-Saving Rules Mapping (Phase 1C)  │
│ - Mapping against 9 IOGP Report 459 Rules              │
│ - Primary & Secondary Rule Association                 │
│ - Provenance Tracking with Trigger Evidence Validation │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ PIPELINE 4: Structured Precursor Synthesis (Phase 1D)  │
│ - Formats 7-Dimensional Structured SIF Precursor       │
│ - Generates Unique Deterministic Precursor Signature   │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ PIPELINE 5: Semantic Embedding & Vector Search (Ph. 2A)│
│ - SentenceTransformer (all-MiniLM-L6-v2) 384d Vector   │
│ - pgvector Cosine Candidate Retrieval                  │
│ - Hybrid Similarity Scoring (50% Struct + 50% Semantic)│
│ - Similar Historical Incident Association              │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ PIPELINE 6: Persistence, Triage & Verification (Ph. 9) │
│ - Atomic DB Transaction (SafetyReport, SIFAssessment)  │
│ - HSE Officer Review Queue Integration                 │
│ - Audit Trail & Case Follow-up Generation              │
└────────────────────────────────────────────────────────┘
```

---

## 7. The AI & NLP Subsystem

### 1. Safety Event Context Extraction
The system screens free-text narratives using a specialized oilfield lexicon encompassing:
* **High-Energy Vectors:** Pressure (>100 psi, hydraulic, gas kick), Electrical (high voltage, arc flash), Mechanical/Rotating (top drive, rotary table), Gravitational/Suspended Loads (drilling line, pipe racks), Chemical/Thermal (pyrophoric scale, crude vapor, H2S).
* **Barrier Integrity Indicators:** Defeated interlocks, missing lockout/tagout (LOTO), bypassed gas detectors, valve misalignment, single isolation valves.
* **Negation Awareness:** Differentiates between *"valve failed to isolate"* and *"valve was inspected and verified closed without failure"*.

### 2. Multi-Factor SIF Scoring Formula
The SIF Screening Engine computes an aggregate evidence score:

$$\text{Evidence Score} = w_h \cdot H + w_b \cdot B + w_e \cdot E + w_a \cdot A$$

Where:
* $H$: Stored Energy Presence Factor
* $B$: Critical Barrier Invalidation Factor
* $E$: Direct Worker Exposure / Line of Fire Factor
* $A$: High-Hazard Operational Activity Factor
* If $\text{Score} \ge 0.65$ and $H \land B = \text{True}$, the event is deterministically escalated to `POTENTIAL_SIF`.

### 3. Dense Semantic Embeddings (`all-MiniLM-L6-v2`)
Precursor signatures are transformed into normalized text vectors:
```
"Hazard: High Pressure Hydrocarbon Gas | Activity: Flange Maintenance | Barrier Failure: Isolation Valve Passed | Rule: Energy Isolation"
  ───▶ [ 0.0421, -0.1189, 0.0832, ..., -0.0125 ] (384 dimensions)
```
Stored in PostgreSQL using `pgvector` indexed with cosine distance:
```sql
SELECT report_id, 1 - (text_embedding <=> target_vector) AS cosine_similarity
FROM sif_assessments
WHERE 1 - (text_embedding <=> target_vector) > 0.65
ORDER BY cosine_similarity DESC LIMIT 5;
```

---

## 8. End-to-End System Architecture

```
                                  USER BROWSER / MISSION CONTROL
                                                │
                                 ┌──────────────┴──────────────┐
                                 │ http://localhost:5173       │
                                 │ React 19 Frontend           │
                                 └──────────────┬──────────────┘
                                                │
                                         HTTP / REST API
                               (Proxied or Direct via API Bridge)
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │ http://127.0.0.1:8000           │
                               │ FastAPI Application Server      │
                               ├─────────────────────────────────┤
                               │ • Request Traceability & CORS   │
                               │ • Endpoint Routers (/api/v1)    │
                               │ • Application Services          │
                               │ • Deterministic NLP Screener    │
                               │ • SentenceTransformer Embedder  │
                               └────────────────┬────────────────┘
                                                │
                                      SQLAlchemy 2.0 Async
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │ PostgreSQL 16 + pgvector        │
                               ├─────────────────────────────────┤
                               │ • safety_reports                │
                               │ • sif_assessments (with Vector) │
                               │ • lsr_taxonomies & mappings     │
                               │ • precursor_patterns            │
                               │ • triage_reviews                │
                               │ • risk_concentrations           │
                               │ • hse_cases & actions           │
                               └─────────────────────────────────┘
```

---

## 9. Frontend Mission Control Views

| Module | Navigation Key | Key Capabilities |
| :--- | :--- | :--- |
| **SIF Command Center** | `command-center` | High-level operational intelligence: SIF exposure density, high-risk operational assets, active precursor clusters, live trends, and immediate triage actions. |
| **Precursor Path Topology** | `precursors` | Deep-dive root causal analysis visualizing the trajectory from weak signal to failed barrier, affected rigs, and evidence logs. |
| **AI Report Analyzer** | `analyzer` | Interactive field report screener with simulated typing, multi-factor analysis, word-level evidence tagging, and HSE review sign-off. |
| **Site & Asset Exposure** | `sites` | Spatial operational risk grid across Assam operational fields (Duliajan, Moran, Digboi, Naharkatiya), ranking assets by SIF potential concentration. |
| **IOGP Life-Saving Rules** | `lsr` | Real-time compliance and violation matrix across all 9 IOGP Report 459 rules, tracking recurring barrier breakdowns. |
| **Report Explorer** | `explorer` | Paginated search, faceted filtering (SIF Potential, Rule, Site, Source Type), semantic phrase highlighting, and HSE verification status editor. |
| **Evidence Dossier Modal** | Modal Overlay | Complete explainable AI audit sheet detailing stored energy vectors, barrier classifications, synthesis equations, and audit trail logs. |

---

## 10. REST API Contract & Endpoints

All backend routes are versioned under `/api/v1`:

### Health & Observability
* `GET /api/v1/health` — Probe service status, database connectivity, and pgvector readiness.
* `GET /api/v1/readiness` — Deep probe confirming system dependencies and taxonomy tables.

### SIF Analysis & Inference Engine
* `POST /api/v1/sif/analyze` — Synchronous single report inference: performs context extraction, multi-factor SIF screening, IOGP mapping, and structured precursor synthesis.
* `POST /api/v1/batch/upload` — Multipart CSV ingestion for enterprise safety datasets.

### Command Center & Operational Telemetry
* `GET /api/v1/sif/command-center/overview` — High-level KPI aggregations for executive dashboards.
* `GET /api/v1/sif/command-center/sif` — Categorical SIF assessment and severity breakdowns.
* `GET /api/v1/sif/analytics/concentration` — Temporal and spatial risk concentration matrices.

### Safety Reports & Human Triage
* `GET /api/v1/sif/reports` — Paginated, filtered historical report queries.
* `GET /api/v1/sif/reports/{id}` — Full report detail with assessment and evidence breakdown.
* `POST /api/v1/sif/reviews` — Human-in-the-loop review creation (HSE Verified, Overridden).

### Taxonomies & Precursor Patterns
* `GET /api/v1/taxonomies` — Active Life-Saving Rules taxonomies (IOGP Report 459).
* `GET /api/v1/sif/patterns` — Automatically discovered recurring precursor pattern groups.

---

## 11. Installation & Local Setup

### Prerequisites
* **Node.js:** `v18+` or `v20+`
* **Python:** `3.10+` or `3.11+`
* **Database (Optional for local testing, required for persistence):** PostgreSQL 15+ with `pgvector`
* **Git**

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/vmit-1911/SIH---OIL-Sentinal.git
cd SIH---OIL-Sentinal
```

---

### Step 2: Set Up Backend
```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
# source .venv/bin/activate

# Install all backend and AI dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Start the FastAPI backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend will be available at **`http://127.0.0.1:8000`**.  
Interactive Swagger docs: **`http://127.0.0.1:8000/docs`**.

---

### Step 3: Set Up Frontend
Open a new terminal in the project root:
```bash
# Install frontend dependencies
npm install

# Start Vite development server
npm run dev
```
The frontend will be available at **`http://localhost:5173`**.

---

## 12. Verification & Testing

### Test Backend Health
```bash
curl http://127.0.0.1:8000/api/v1/health
```
**Expected Response:**
```json
{
  "status": "ok",
  "service": "oil-sif-sentinel",
  "app_name": "OIL SIF Sentinel",
  "version": "0.1.0",
  "api_version": "1.0",
  "environment": "development",
  "database": {
    "connected": true,
    "pgvector_ready": true,
    "error": null
  },
  "active_taxonomies": [
    {
      "taxonomy_id": "IOGP_REPORT_459",
      "authority": "IOGP",
      "version": "2018",
      "name": "IOGP Life-Saving Rules (Report 459 - 2018 Edition)",
      "rules_count": "9"
    }
  ]
}
```

### Test Live SIF Inference Endpoint
```bash
curl -X POST http://127.0.0.1:8000/api/v1/sif/analyze \
  -H "Content-Type: application/json" \
  -d '{"raw_text": "During well servicing, crew noticed bleed-off valve passing high pressure gas with no positive mechanical isolation locked out."}'
```

### Run Frontend Production Build & Linting
```bash
npm run build
```
Build output completes in < 1 second with 0 TypeScript errors.

---

## 👥 Contributors & Acknowledgements
* **Team:** Smart India Hackathon Team (`vmit-1911`)
* **Standard Guidance:** [International Association of Oil & Gas Producers (IOGP) Report 459](https://www.iogp.org)
* **Domain Context:** Oil India Limited (OIL) Operational Safety Guidelines

---
*Developed for Oil India Limited (OIL) — Smart India Hackathon.*
