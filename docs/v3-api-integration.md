# V3 Frontend — API Integration Plan

How the React SPA integrates with the **existing FastAPI** application (`src/gdpr_ai/api/`). All request/response shapes below reflect **current** Pydantic models unless noted.

---

## Base URLs and transport

| Environment | Frontend | API |
|-------------|----------|-----|
| Development | `http://localhost:5173` (Vite) | `http://localhost:8000` |

**Recommendation:** Configure Vite `server.proxy` so:

- `/api` → `http://localhost:8000`
- `/health` → `http://localhost:8000`

The browser then calls **`/api/v1/...`** and **`/health`** as **same-origin**, avoiding CORS preflight during local dev.

### CORS (current backend)

`src/gdpr_ai/api/app.py` **does not** register `CORSMiddleware` today. Relying on the **Vite proxy** avoids CORS for local development. If you ever hit the API **directly** from the browser (different origin), you must add CORS allowing `http://localhost:5173` — treat that as a **small backend change** when needed.

---

## Endpoints to consume

| Endpoint | Method | Purpose | Primary UI |
|----------|--------|---------|------------|
| `/health` | GET | Liveness + version string | Header, Settings |
| `/api/v1/analyze/violation` | POST | Run violation pipeline | Analyze (violation mode) |
| `/api/v1/analyze/compliance` | POST | Run compliance assessment | Analyze (compliance mode) |
| `/api/v1/analyze/{analysis_id}` | GET | Fetch one stored analysis | History detail, refresh |
| `/api/v1/projects` | GET | List projects (includes analysis id lists) | History composition (interim) |
| `/api/v1/projects/{project_id}` | GET | One project + analysis ids | History |

**Documents (optional v3):**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/documents/generate` | POST | Generate markdown docs from `analysis_id` |
| `/api/v1/documents/{document_id}` | GET | Fetch generated doc body |

### Gaps vs product spec (recommended backend additions)

The **Stats** page calls for aggregates and **time series** similar to CLI `gdpr-check stats` / query log data:

- Today, **`get_stats()`** in `src/gdpr_ai/logger.py` aggregates **`query_logs`** (SQLite) but is **not** exposed over HTTP.
- There is **no** `GET /api/v1/analyses` listing endpoint; **`list_analyses_for_project`** exists on `AppRepository` but only surfaces as **`analyses: list[str]`** inside project responses.

**Recommended for v3 (small FastAPI additions):**

1. **`GET /api/v1/stats/summary`** — JSON mirroring `get_stats()` keys: `total_queries`, `avg_latency_ms`, `avg_cost_eur`, `total_cost_eur`, `total_tokens`, `avg_violations_per_query`.
2. **`GET /api/v1/stats/timeseries?bucket=day`** — optional; if omitted initially, Stats charts can use **client-side** bucketing after fetching many analyses (heavy) or ship Milestone 4 charts after the endpoint exists.
3. **`GET /api/v1/analyses?project_id=&limit=&offset=`** — returns **summary rows** (`id`, `mode`, `created_at`, `input_text` snippet, `duration_seconds`, `llm_cost_usd`, optional derived `severity` from parsed `result_json`) to avoid N+1 `GET /analyze/{id}` calls.

Until (3) exists, History can **prototype** by: `GET /projects` → pick default project → `GET /analyze/{id}` for each id (poor scalability; acceptable for dogfood only).

---

## Request / response schemas

### `GET /health`

**Response** (`dict`):

```json
{ "status": "ok", "version": "2.0.0" }
```

Source: `app.py` `health()`.

---

### `POST /api/v1/analyze/violation`

**Request body** — `ViolationAnalyzeRequest` (`api/schemas.py`):

| Field | Type | Constraints |
|-------|------|-------------|
| `scenario` | `string` | required, length **10–8000** |
| `project_id` | `string \| null` | optional; default project used if empty |

**Response** — `AnalysisRunResponse`:

| Field | Type | Description |
|-------|------|-------------|
| `analysis_id` | `string` | Query log id / correlation id |
| `mode` | `"violation_analysis"` | constant for this route |
| `result` | `object` | **`AnalysisReport.model_dump()`** |

**`result` shape** — `AnalysisReport` (`models.py`):

| Field | Type |
|-------|------|
| `scenario_summary` | `string` |
| `extracted_entities` | object (`ExtractedEntities`) |
| `classified_topics` | object (`ClassifiedTopics`) |
| `violations` | array of `{ article_reference, description, confidence, supporting_chunk_ids, source_url }` |
| `severity_level` | `"low" \| "medium" \| "high" \| "critical" \| "unknown"` |
| `severity_rationale` | `string` |
| `recommendations` | `string[]` |
| `citations` | `string[]` |
| `similar_cases` | `object[]` |
| `unsupported_notes` | `string[]` |
| `disclaimer` | `string` |

**Errors:**

- **404** — `detail: "Project not found"` if `project_id` invalid.
- **422** — validation (body too short, etc.).
- **500** — pipeline exception; `detail` may be stringified exception message.

---

### `POST /api/v1/analyze/compliance`

**Request body** — `ComplianceAnalyzeRequest`:

| Field | Type | Rules |
|-------|------|--------|
| `system_description` | `string \| null` | max 32000 chars if set |
| `data_map` | `object \| null` | structured `DataMap`-compatible JSON |
| `project_id` | `string \| null` | optional |

**Validation:** **Exactly one** of `system_description` (non-empty) or `data_map` must be provided (`model_validator`).

**Response** — `AnalysisRunResponse`:

| Field | Type |
|-------|------|
| `analysis_id` | `string` |
| `mode` | `"compliance_assessment"` |
| `result` | `object` — **`ComplianceAssessment.model_dump()`** |

**`result` shape** — `ComplianceAssessment` + nested models (`compliance/schemas.py`):

| Field | Type |
|-------|------|
| `system_name` | `string` |
| `overall_risk_level` | `string` (e.g. low/medium/high/critical — treat as display string) |
| `findings` | array of `Finding` |
| `summary` | `string` |
| `data_map` | `DataMap` object |

**`Finding`:**

| Field | Type |
|-------|------|
| `area` | `string` |
| `status` | `"compliant" \| "at_risk" \| "non_compliant" \| "insufficient_info"` |
| `relevant_articles` | `string[]` |
| `description` | `string` |
| `remediation` | `string \| null` |
| `technical_guidance` | `string \| null` |

**`DataMap`** includes `data_categories`, `processing_purposes`, `data_flows`, `third_parties`, `storage`, flags for AI/children/automated decisions, etc.

**Errors:** same pattern as violation (404 project, 422 validation, 500 runtime).

---

### `GET /api/v1/analyze/{analysis_id}`

**Response** — `AnalysisGetResponse`:

| Field | Type |
|-------|------|
| `analysis_id` | `string` |
| `mode` | `string \| null` |
| `result` | `object` (parsed JSON from DB or query log) |
| `scenario_text` | `string` |
| `created_at` | `string \| null` (ISO timestamp) |

**404** if not in app DB and not in query log with `report_json`.

---

### `GET /api/v1/projects` and `GET /api/v1/projects/{project_id}`

**Response** — `ProjectListResponse` / `ProjectResponse`:

- `ProjectResponse` includes `analyses: string[]` (ids only), not full payloads.

Use to discover **analysis ids** per project for History until a dedicated list endpoint exists.

---

## Latency and UX expectations

| Mode | Typical wall time (observed / planned UI copy) |
|------|-----------------------------------------------|
| Violation | ~**20–120 s** depending on scenario |
| Compliance | ~**60–190 s** for full assessment + persistence |

The frontend **must**:

- Keep the request **in flight** (no silent timeout below ~3–5 minutes unless configurable).
- Show **non-blocking** loading UI (skeleton + indeterminate progress + copy).
- Allow **cancel** only if backend supports abort (today: closing tab aborts fetch; optional `AbortController`).

---

## Error handling

| Class | HTTP | Frontend behavior |
|-------|------|-------------------|
| Validation | **422** | Show field/message from FastAPI `detail` (array or string). |
| Not found | **404** | Toast + inline message (“Project or analysis not found”). |
| Server / pipeline | **500** | Toast + retry; show `detail` string if safe (no stack traces in UI). |
| Network | fetch failed | Offline/toast; retry button. |

**JSON / LLM truncation:** Backend pipelines include hardening for malformed or truncated model output; failures still surface as **500** with a message. The UI should **not** assume partial JSON — always handle failed analyze as a full error.

---

## Authentication and API keys

- **Today:** The FastAPI app does **not** require an API key from the client. The **Anthropic** key is read from **server** environment (`.env`).
- **Settings page “API key”:** For v3 local MVP, implement as either:
  - **Informational only** (“Key is configured on the server”), optionally probing a non-secret **health** flag in future, or
  - **Placeholder** for a future **BYOK** header — requires backend support (out of v3 doc scope unless added).

Do **not** commit secrets into frontend `localStorage` without an explicit security review.

---

## Default `project_id`

The backend resolves empty `project_id` to **`DEFAULT_PROJECT_ID`** (`db/database.py`). The UI may omit `project_id` on requests to use the default project for single-user local use.

---

## References

- `src/gdpr_ai/api/app.py`
- `src/gdpr_ai/api/routes/analyze.py`
- `src/gdpr_ai/api/schemas.py`
- `src/gdpr_ai/models.py` — `AnalysisReport`
- `src/gdpr_ai/compliance/schemas.py` — `ComplianceAssessment`, `Finding`
- `src/gdpr_ai/logger.py` — `get_stats`, query log schema
- [v3-overview.md](v3-overview.md)
- [v3-roadmap.md](v3-roadmap.md)
