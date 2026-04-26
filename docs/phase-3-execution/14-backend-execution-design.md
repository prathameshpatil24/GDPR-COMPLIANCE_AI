# Phase 3.14 – Backend Execution Design

## 1. Overview

This document describes the implementation strategy for the backend of GDPR AI. In v1, the "backend" is the Python package `gdpr_ai` invoked by the Typer CLI. In v2, the same package is wrapped by a FastAPI layer.

The execution design covers package layout, module responsibilities, entry points, execution flow, and coding conventions.

---

## 2. Package Layout

### 2.1 Directory Structure

```
src/gdpr_ai/
├── __init__.py
├── config.py
├── models.py
│
├── cli.py                  # CLI entry point
│
├── pipeline/
│   ├── __init__.py
│   ├── orchestrator.py     # coordinates the 4 stages + validate
│   ├── extract.py
│   ├── classify.py
│   ├── retrieve.py
│   ├── reason.py
│   └── validate.py
│
├── knowledge/
│   ├── __init__.py
│   ├── chunker.py
│   ├── embedder.py
│   └── store.py            # ChromaDB interface
│
├── llm/
│   ├── __init__.py
│   └── claude_client.py    # Anthropic SDK wrapper
│
├── prompts/
│   ├── extract.txt
│   ├── classify.txt
│   └── reason.txt
│
└── observability/
    ├── __init__.py
    ├── logger.py
    └── query_log.py        # SQLite-backed log
```

### 2.2 Design Rules

* `pipeline/` modules are stateless functions. State lives in the orchestrator.
* `knowledge/` modules own the ChromaDB interface. No other module touches Chroma directly.
* `llm/` is the only module that imports the Anthropic SDK.
* `prompts/` are loaded at runtime from text files, not hardcoded.
* `observability/` is invoked by the orchestrator, not individual stages.

---

## 3. Module Responsibilities

### 3.1 `config.py`

* Loads all environment variables via Pydantic settings
* Exposes a single `settings` singleton imported across the package
* Validates required keys at import time (fails fast if `ANTHROPIC_API_KEY` missing)

### 3.2 `models.py`

* Pydantic models shared across pipeline stages
* `ExtractedEntities`, `TopicTags`, `RetrievedChunk`, `Violation`, `GDPRReport`
* No business logic, only data shapes

### 3.3 `cli.py`

* Typer app with commands: `analyse` (default), `version`, `doctor`, `logs`
* Maps CLI input to pipeline orchestrator
* Renders output with Rich
* Catches errors and presents user-friendly messages

### 3.4 `pipeline/orchestrator.py`

* Single public function: `run_pipeline(scenario: str) -> GDPRReport`
* Coordinates: extract → classify → retrieve → reason → validate
* Handles retries, logs stage timings, tracks costs
* Returns a fully validated `GDPRReport`

### 3.5 `pipeline/extract.py`

* Function: `extract_entities(scenario: str) -> ExtractedEntities`
* Calls Haiku with `prompts/extract.txt`
* Parses JSON response into Pydantic model

### 3.6 `pipeline/classify.py`

* Function: `classify_topics(scenario: str, entities: ExtractedEntities) -> TopicTags`
* Calls Haiku with `prompts/classify.txt`
* Returns 1-4 topic tags from the fixed taxonomy

### 3.7 `pipeline/retrieve.py`

* Function: `retrieve_chunks(scenario: str, entities: ExtractedEntities, topics: TopicTags, k: int = 15) -> list[RetrievedChunk]`
* No LLM calls
* Performs dense retrieval via ChromaDB + sparse retrieval via BM25
* Applies topic-tag filtering
* Combines scores and returns top-k

### 3.8 `pipeline/reason.py`

* Function: `reason_over_chunks(scenario: str, chunks: list[RetrievedChunk]) -> GDPRReport`
* Calls Sonnet with `prompts/reason.txt`
* Parses JSON response into `GDPRReport`

### 3.9 `pipeline/validate.py`

* Function: `validate_report(report: GDPRReport, chunks: list[RetrievedChunk]) -> GDPRReport`
* Checks every cited article exists in retrieved chunks
* Raises `HallucinationDetected` if validation fails
* Orchestrator catches this and retries reasoning once before failing cleanly

### 3.10 `knowledge/chunker.py`

* Functions for chunking each source type
* Produces chunks with full metadata
* Used by build-time scripts, not at query time

### 3.11 `knowledge/embedder.py`

* Wraps `sentence-transformers` with a cached singleton
* Function: `embed_texts(texts: list[str]) -> list[list[float]]`

### 3.12 `knowledge/store.py`

* Thin wrapper over ChromaDB
* Functions: `add_chunks()`, `query(...)`, `filter_by_topics(...)`
* Also maintains the BM25 index in a sidecar pickle

### 3.13 `llm/claude_client.py`

* Wraps Anthropic SDK with project-specific logic
* Function: `call_claude(model: str, messages: list, tools: list | None = None) -> ClaudeResponse`
* Handles retries, token accounting, and cost calculation

### 3.14 `observability/logger.py`

* Configures Python logging for the package
* Structured output in JSON mode
* Human-readable output in CLI mode

### 3.15 `observability/query_log.py`

* SQLite-backed query log
* Function: `log_query(query_id, scenario, entities, topics, chunk_ids, report, latencies, costs, feedback)`

---

## 4. Entry Points

### 4.1 CLI Entry

Registered in `pyproject.toml`:

```toml
[project.scripts]
gdpr-check = "gdpr_ai.cli:app"
```

Invocation:

```bash
uv run gdpr-check "<scenario>"
```

### 4.2 Programmatic Entry

For use from tests, scripts, or the v2 FastAPI layer:

```python
from gdpr_ai.pipeline.orchestrator import run_pipeline

report = run_pipeline("A German hospital accidentally emails...")
```

### 4.3 Build-Time Scripts

Separate entry points in `scripts/`:

* `scrape_gdpr.py`
* `scrape_bdsg.py`
* `scrape_ttdsg.py`
* `scrape_gdprhub.py`
* `scrape_edpb.py`
* `translate_german_sources.py`
* `chunk_and_embed.py`
* `build_index.py`
* `rebuild_knowledge_base.py`
* `verify_knowledge_base.py`

Invoked via `uv run python scripts/<name>.py`.

---

## 5. Execution Flow (Query Time)

```python
# 1. User runs: gdpr-check "..."

# 2. cli.py:
scenario = parse_arg()
report = run_pipeline(scenario)
render_with_rich(report)

# 3. orchestrator.py:
query_id = uuid4()
start_total = now()

with stage_timer("extract") as t:
    entities = extract_entities(scenario)

with stage_timer("classify") as t:
    topics = classify_topics(scenario, entities)

with stage_timer("retrieve") as t:
    chunks = retrieve_chunks(scenario, entities, topics)

with stage_timer("reason") as t:
    draft_report = reason_over_chunks(scenario, chunks)

try:
    report = validate_report(draft_report, chunks)
except HallucinationDetected:
    # retry once
    draft_report = reason_over_chunks(scenario, chunks)
    report = validate_report(draft_report, chunks)

log_query(query_id, scenario, entities, topics, chunk_ids, report, latencies, costs)
return report
```

---

## 6. Error Handling

### 6.1 Exception Hierarchy

```
GDPRAIError (base)
├── ConfigurationError          # missing API key, bad paths
├── InputValidationError        # scenario too short, too long
├── KnowledgeBaseError          # KB not built, corrupted
│   └── NoChunksRetrieved       # retrieval returned empty
├── LLMError
│   ├── CreditBalanceTooLow
│   ├── RateLimited
│   └── ModelUnavailable
├── PipelineError
│   ├── ExtractionFailed
│   ├── ClassificationFailed
│   ├── ReasoningFailed
│   └── HallucinationDetected
└── ValidationError             # schema parse failure
```

### 6.2 User-Facing Messages

CLI catches exceptions and maps each to a clear message:

| Exception | Message |
|-----------|---------|
| `ConfigurationError` | "Missing ANTHROPIC_API_KEY. Set it in .env and try again." |
| `CreditBalanceTooLow` | "Anthropic credit balance is too low. Top up at console.anthropic.com." |
| `KnowledgeBaseError` | "Knowledge base not built. Run: uv run python scripts/build_index.py" |
| `HallucinationDetected` | "Reasoning validation failed. This is unusual — please file an issue." |

---

## 7. Coding Conventions

### 7.1 Type Hints

Every function signature has type hints. Every class attribute is typed. Enforced via mypy.

### 7.2 Docstrings

Every public function has a one-line docstring, longer for complex logic:

```python
def retrieve_chunks(
    scenario: str,
    entities: ExtractedEntities,
    topics: TopicTags,
    k: int = 15,
) -> list[RetrievedChunk]:
    """Retrieve top-k chunks via hybrid dense + sparse search.

    Filters by topic tags, combines dense and BM25 scores, returns
    top-k chunks ordered by combined score.
    """
```

### 7.3 Logging vs Print

No `print` in library code. All output goes through the `logging` module except when CLI explicitly renders results.

### 7.4 No Globals

Except for `settings` (config) and cached singletons (embedding model), no module-level mutable state.

### 7.5 Small Functions

Functions longer than 40 lines are a refactor signal. Extract helpers.

---

## 8. Testing Approach

Covered in detail in [19 – Testing Strategy](../phase-3-execution/19-testing-strategy.md). Summary:

* Unit tests for each pipeline stage (mocked LLM)
* Integration tests for orchestrator end-to-end (mocked LLM)
* Gold-set evaluation (real LLM, gated behind credits)
* Retrieval quality tests (no LLM needed)

---

## 9. Deferred-to-v2 Backend Work

### 9.1 FastAPI Wrapper

Wraps `run_pipeline` in HTTP endpoints. Schema reused from `models.py`.

### 9.2 Concurrency

Currently synchronous. v2 may introduce async for parallel LLM calls (though extract → classify → retrieve → reason are mostly sequential).

### 9.3 Caching

No caching in v1. v2 may cache identical scenarios to save cost.

### 9.4 Background Indexing

v1 rebuilds the knowledge base manually. v2 may run scheduled rebuilds via cron or a worker.

---

## 10. Summary

The backend is organised into small, single-responsibility modules with clear boundaries. The orchestrator coordinates the four stages with logging, cost tracking, and validation. Build-time scripts live outside the main package. Every public function is typed, documented, and tested.

The structure is ready to accept the v2 FastAPI wrapper without internal changes.

---

## v2 Backend Modules

New packages and directories extend the layout below. v1 modules remain as implemented; paths follow the repository conventions in `CLAUDE.md`.

```
src/gdpr_ai/
├── pipeline/           # v1 — existing
│   ├── extract.py
│   ├── classify.py
│   ├── retrieve.py
│   └── reason.py
├── compliance/         # v2 — NEW
│   ├── intake.py       # System description parser → DataMap
│   ├── mapper.py       # DataMap → GDPR article mapping
│   ├── assessor.py     # Compliance posture assessment
│   └── generator.py    # Document generation from assessment
├── api/                # v2 — NEW
│   ├── app.py          # FastAPI application
│   ├── routes/
│   │   ├── analyze.py  # /analyze/violation and /analyze/compliance
│   │   ├── documents.py
│   │   └── projects.py
│   └── schemas.py      # Pydantic request/response models
├── db/                 # v2 — NEW
│   ├── database.py     # SQLite connection manager
│   ├── models.py       # SQLAlchemy or raw SQL row models
│   └── migrations.py   # Schema creation / upgrades
├── templates/          # v2 — NEW
│   ├── dpia.md.j2      # DPIA Jinja2 template
│   ├── ropa.md.j2      # RoPA template
│   ├── checklist.md.j2 # Technical checklist template
│   ├── consent.md.j2   # Consent flow template
│   └── retention.md.j2 # Data retention policy template
├── knowledge/          # v1 — existing, extended for v2 sources
│   ├── chunker.py
│   ├── embedder.py
│   └── store.py
└── cli.py              # v1 — existing, extended with v2 commands
```

FastAPI handlers depend on the same `settings` and LLM client abstractions as the CLI; they MUST NOT embed retrieval or prompt strings directly in route functions beyond thin wiring.