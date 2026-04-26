# Phase 2.11 – API Design

## 1. Overview

GDPR AI v2 exposes a **local REST API** (FastAPI) alongside the CLI. The API provides two modes: **violation analysis** (v1 pipeline) and **compliance assessment** (v2 pipeline). Behaviour matches the shared Python pipelines; the HTTP layer is thin validation, orchestration, and persistence.

All paths are served from a single process on the developer machine. There is **no** hosting or domain requirement in v2.

---

## 2. Design Principles

### 2.1 Thin HTTP Layer

Handlers call the same orchestration functions as the CLI. No duplicated business logic.

### 2.2 REST-style resources

Resources are **projects**, **analyses**, and **documents**. Analysis operations that run longer than a few seconds use **async** acceptance and polling.

### 2.3 JSON bodies

Request and response bodies are JSON unless downloading raw markdown (optional `Accept` or dedicated field).

### 2.4 Versioned base path

**Base URL:** `http://localhost:8000/api/v1`

All endpoints below are relative to this base (for example, `GET /health` → `http://localhost:8000/api/v1/health`).

### 2.5 Consistent errors

Errors use a single JSON envelope (see section 8).

---

## 3. Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness and dependency checks |
| `POST` | `/analyze/violation` | v1 — scenario text → violation report |
| `POST` | `/analyze/compliance` | v2 — system description → compliance assessment (async-capable) |
| `GET` | `/analyze/{analysis_id}` | Fetch one analysis result by id |
| `POST` | `/documents/generate` | Generate markdown documents from a completed analysis |
| `GET` | `/documents/{document_id}` | Fetch one generated document |
| `POST` | `/projects` | Create a project |
| `GET` | `/projects` | List projects for the local user |
| `GET` | `/projects/{project_id}` | Project detail including analyses |
| `PUT` | `/projects/{project_id}` | Update project system description / metadata |

---

## 4. Pydantic schemas (shared)

### 4.1 Enums

```python
from enum import StrEnum


class AnalysisMode(StrEnum):
    violation_analysis = "violation_analysis"
    compliance_assessment = "compliance_assessment"


class AnalysisStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class DocumentType(StrEnum):
    dpia = "dpia"
    ropa = "ropa"
    checklist = "checklist"
    consent_flow = "consent_flow"
    retention_policy = "retention_policy"
    violation_report = "violation_report"


class PostureClass(StrEnum):
    compliant = "compliant"
    at_risk = "at-risk"
    non_compliant = "non-compliant"
    insufficient_information = "insufficient-information"
```

### 4.2 Citation

```python
from pydantic import BaseModel, Field


class LegalCitation(BaseModel):
    """Single grounded reference returned to clients."""

    instrument: str = Field(..., description="e.g. GDPR, BDSG, EDPB guideline id")
    article: str = Field(..., description="Article or section label, paragraph-level where possible")
    title: str | None = None
    source_url: str = Field(..., description="Authoritative or indexed URL")
    excerpt_id: str | None = Field(None, description="Internal chunk id if available")
```

### 4.3 Violation report (v1-shaped)

```python
class ViolationItem(BaseModel):
    article: str
    paragraph: str | None = None
    title: str | None = None
    short_definition: str | None = None
    scenario_explanation: str
    source_url: str


class SimilarCase(BaseModel):
    case_name: str
    fine_amount_eur: int | None = None
    url: str


class ViolationReportBody(BaseModel):
    scenario_summary: str
    violations: list[ViolationItem]
    similar_cases: list[SimilarCase]
    disclaimer: str
    citations: list[LegalCitation]
```

### 4.4 Compliance assessment (v2-shaped)

```python
class ComplianceFinding(BaseModel):
    topic: str
    posture: PostureClass
    summary: str
    remediation: str | None = None
    technical_steps: list[str] = Field(default_factory=list)
    citations: list[LegalCitation]


class ComplianceAssessmentBody(BaseModel):
    system_summary: str
    findings: list[ComplianceFinding]
    risks: list[str]
    recommendations: list[str]
    ai_act_notes: list[str] = Field(default_factory=list)
    disclaimer: str
    citations: list[LegalCitation]
```

### 4.5 DataMap (intake)

The full **DataMap** and nested models match [10 – Data and Knowledge Model](10-data-knowledge-model.md) (`DataCategory`, `ProcessingPurpose`, `DataFlow`, `ThirdParty`, `StorageInfo`, `DataMap`). The API imports the same models from `src/gdpr_ai` package code.

---

## 5. Request and response models by endpoint

### 5.1 `GET /health`

**Response 200**

```python
class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    version: str
    knowledge_base_ready: bool
    sqlite_ready: bool
```

**Example**

```json
{
  "status": "ok",
  "version": "2.0.0",
  "knowledge_base_ready": true,
  "sqlite_ready": true
}
```

---

### 5.2 `POST /analyze/violation`

**Request**

```python
class ViolationAnalyzeRequest(BaseModel):
    scenario: str = Field(..., min_length=10, max_length=2000)
    project_id: str | None = Field(None, description="Optional; attach run to a project")
    options: dict = Field(default_factory=dict, description="e.g. include_similar_cases")
```

**Example**

```json
{
  "scenario": "A German hospital accidentally emails patient test results to the wrong patient.",
  "project_id": null,
  "options": { "include_similar_cases": true }
}
```

**Response 200**

```python
class AnalysisEnvelope(BaseModel):
    analysis_id: str
    project_id: str | None
    mode: AnalysisMode
    status: AnalysisStatus
    started_at: str
    completed_at: str | None
    llm_cost_usd: float | None
    result: ViolationReportBody
```

**Example (abridged)**

```json
{
  "analysis_id": "a1b2c3d4-...",
  "project_id": null,
  "mode": "violation_analysis",
  "status": "completed",
  "started_at": "2026-04-26T12:00:00Z",
  "completed_at": "2026-04-26T12:00:04Z",
  "llm_cost_usd": 0.017,
  "result": {
    "scenario_summary": "...",
    "violations": [],
    "similar_cases": [],
    "disclaimer": "Not legal advice.",
    "citations": []
  }
}
```

---

### 5.3 `POST /analyze/compliance`

Supports **structured** `data_map` or **raw** `system_description_text` (server normalises to `DataMap`).

**Request**

```python
class ComplianceAnalyzeRequest(BaseModel):
    project_id: str
    data_map: DataMap | None = None
    system_description_text: str | None = Field(None, max_length=32000)
    async_mode: bool = Field(True, description="If true, return 202 with analysis_id for polling")
```

**Validation rule:** at least one of `data_map` or non-empty `system_description_text` MUST be provided (enforce with a Pydantic field validator in implementation).

**Example (structured)**

```json
{
  "project_id": "p-001",
  "async_mode": true,
  "data_map": {
    "system_name": "Example SaaS",
    "system_description": "B2B analytics dashboard with EU customers.",
    "data_categories": [
      {
        "name": "work email",
        "sensitivity": "standard",
        "volume": "medium",
        "subjects": ["customers"]
      }
    ],
    "processing_purposes": [
      {
        "purpose": "product analytics",
        "legal_basis_claimed": "legitimate_interest",
        "data_categories": ["work email"]
      }
    ],
    "data_flows": [],
    "third_parties": [],
    "storage": [],
    "has_automated_decision_making": false,
    "processes_children_data": false,
    "uses_ai_ml": true
  }
}
```

**Response 202** (when `async_mode` is true)

```python
class ComplianceAnalyzeAccepted(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    poll_url: str
```

**Example**

```json
{
  "analysis_id": "e5f6-...",
  "status": "queued",
  "poll_url": "/api/v1/analyze/e5f6-..."
}
```

**Response 200** (when `async_mode` is false and run finishes within server timeout)

Same envelope as violation response but `mode` is `compliance_assessment` and `result` is `ComplianceAssessmentBody`.

---

### 5.4 `GET /analyze/{analysis_id}`

**Response 200**

```python
class AnalysisGetResponse(BaseModel):
    analysis_id: str
    project_id: str | None
    mode: AnalysisMode
    status: AnalysisStatus
    error: str | None = None
    started_at: str
    completed_at: str | None
    llm_cost_usd: float | None
    result: ViolationReportBody | ComplianceAssessmentBody | None
```

---

### 5.5 `POST /documents/generate`

**Request**

```python
class DocumentGenerateRequest(BaseModel):
    analysis_id: str
    doc_types: list[DocumentType]
```

**Example**

```json
{
  "analysis_id": "e5f6-...",
  "doc_types": ["dpia", "ropa", "checklist", "consent_flow", "retention_policy"]
}
```

**Response 200**

```python
class GeneratedDocumentRef(BaseModel):
    document_id: str
    doc_type: DocumentType
    path: str | None = Field(None, description="Local path if persisted to disk")
    citation_count: int


class DocumentGenerateResponse(BaseModel):
    analysis_id: str
    documents: list[GeneratedDocumentRef]
```

---

### 5.6 `GET /documents/{document_id}`

**Response 200**

```python
class DocumentGetResponse(BaseModel):
    document_id: str
    analysis_id: str
    doc_type: DocumentType
    format: str  # "markdown"
    content: str
    created_at: str
```

---

### 5.7 `POST /projects`

**Request**

```python
class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    system_description: dict = Field(..., description="Raw JSON blob; often a serialised DataMap")
```

**Example**

```json
{
  "name": "EU expansion CRM",
  "system_description": { "system_name": "Internal CRM", "system_description": "..." }
}
```

**Response 201**

```python
class ProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    created_at: str
    updated_at: str
```

---

### 5.8 `GET /projects`

**Response 200**

```python
class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
```

---

### 5.9 `GET /projects/{project_id}`

**Response 200**

```python
class ProjectDetailResponse(BaseModel):
    project: ProjectResponse
    system_description: dict
    data_map: dict | None
    analyses: list[AnalysisGetResponse]
```

---

### 5.10 `PUT /projects/{project_id}`

**Request**

```python
class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    system_description: dict | None = None
    data_map: dict | None = None
```

**Response 200** — `ProjectDetailResponse` (optional analyses omitted or truncated per query params).

---

## 6. Async processing semantics

* **Violation analysis** typically completes inline (response 200).
* **Compliance assessment** defaults to **async**: `202 Accepted` with `analysis_id`, then `GET /analyze/{analysis_id}` until `status` is `completed` or `failed`.
* Long **document generation** may return immediately with document ids and fill content asynchronously; clients poll `GET /documents/{document_id}` until `content` is non-empty or status in metadata indicates completion (implementation detail: optional `generation_status` field may be added on the document record).

---

## 7. Rate limiting (local)

Even on localhost, handlers apply **token-bucket** rate limits to prevent accidental tight loops against the language-model API. Limits are configurable via environment settings (see config module).

---

## 8. Error shape

```python
class APIError(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: APIError
```

**Example**

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Scenario is too short to analyse.",
    "details": { "min_length": 10, "provided_length": 5 }
  }
}
```

| Code | HTTP | Meaning |
|------|------|---------|
| `INVALID_INPUT` | 400 | Validation failed (Pydantic / business rules) |
| `NOT_FOUND` | 404 | Unknown project, analysis, or document |
| `PIPELINE_ERROR` | 500 | Pipeline or template failure |
| `LLM_UNAVAILABLE` | 503 | Reasoning engine unreachable |
| `KNOWLEDGE_BASE_NOT_READY` | 503 | Chroma index missing or empty |

---

## 9. CLI and API parity

* Shared Pydantic models for **reports**, **assessments**, and **DataMap**.
* Shared pipeline orchestrators for **violation** and **compliance** modes.
* Integration tests assert identical structured outputs for the same inputs (with mocked reasoning engine).

---

## 10. Summary

The v2 API is a **local**, **versioned** FastAPI surface at `http://localhost:8000/api/v1`. It exposes **violation** and **compliance** analyses, **async** compliance jobs, **document** generation to markdown, and **SQLite-backed** projects — without introducing hosting, domains, or frontend scope in v2.
