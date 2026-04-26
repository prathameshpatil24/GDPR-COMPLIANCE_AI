# Phase 2.8 – High-Level Architecture

## 1. Overview

GDPR AI is a retrieval-augmented reasoning system. It takes a natural-language scenario, retrieves relevant legal knowledge, and produces a grounded report identifying violated articles.

This document describes the top-level system design, the four-stage processing pipeline, the major components, and how they interact.

---

## 2. Design Goals

### 2.1 Primary Goals

* Accurate article identification with strict grounding
* Sub-5-second response time for typical scenarios
* Low per-query cost (under 0.05 EUR average)
* German-market specialisation (GDPR + BDSG + TTDSG)
* Local-first execution with minimal external dependencies

### 2.2 Non-Goals for v1

* Multi-turn conversation
* Document upload and analysis
* Website scanning
* Web UI
* Multilingual input and output

---

## 3. System Context

```
┌─────────────────────────────────────────────────────────────┐
│                        User's Machine                        │
│                                                              │
│  ┌────────────┐      ┌──────────────────────────────────┐   │
│  │    CLI     │◄────►│         GDPR AI Pipeline         │   │
│  │ (Typer +   │      │                                  │   │
│  │   Rich)    │      │  Extract → Classify → Retrieve   │   │
│  └────────────┘      │              ↓                   │   │
│                      │      Reason → Validate           │   │
│                      └──────────────────────────────────┘   │
│                                    │                         │
│  ┌──────────────┐    ┌─────────────┴──────────┐             │
│  │   ChromaDB   │◄───┤    Local Knowledge     │             │
│  │  (embedded)  │    │         Base           │             │
│  └──────────────┘    └────────────────────────┘             │
│                                                              │
│  ┌──────────────┐                                           │
│  │   SQLite     │◄── query logs, feedback, costs            │
│  │  (local)     │                                           │
│  └──────────────┘                                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │  HTTPS (TLS)
                  ▼
        ┌──────────────────────┐
        │   Anthropic API      │
        │  (Haiku + Sonnet)    │
        └──────────────────────┘
```

---

## 4. The Four-Stage Pipeline

The core processing pipeline has four stages, each with a single responsibility.

### 4.1 Stage 1 – Extract

**Purpose**: Convert free-text scenario into structured entities.

**Model**: Claude Haiku (cheap, fast)

**Inputs**: Raw scenario text

**Outputs**: Structured entity object with:

* `data_subject` — e.g., employee, customer, patient, child
* `data_type` — e.g., contact, biometric, health, financial
* `controller_role` — employer, service provider, etc.
* `purpose` — e.g., marketing, security, record-keeping
* `legal_basis_claimed` — if the scenario mentions one
* `jurisdiction` — country context (Germany-specific flag)
* `special_categories` — flags sensitive data presence

### 4.2 Stage 2 – Classify

**Purpose**: Map the scenario to GDPR topic areas.

**Model**: Claude Haiku

**Inputs**: Scenario + extracted entities

**Outputs**: Topic tags from fixed taxonomy:

* Legal basis (Art. 6, 9)
* Consent (Art. 7, 8)
* Data subject rights (Art. 12-22)
* Controller and processor duties (Art. 24-31)
* Security and breaches (Art. 32-34)
* DPIA and DPO (Art. 35-39)
* International transfers (Art. 44-50)
* Employment context (BDSG §26)
* Children (Art. 8)
* Automated decisions (Art. 22)
* Direct marketing (Art. 21, ePrivacy)

1 to 4 tags per scenario.

### 4.3 Stage 3 – Retrieve

**Purpose**: Find relevant knowledge chunks.

**No LLM call** — pure local retrieval.

**Inputs**: Scenario + entities + topic tags

**Process**:

1. Filter knowledge base by topic tags
2. Dense retrieval: cosine similarity over bge-m3 embeddings
3. Sparse retrieval: BM25 over chunk text
4. Combine scores (weighted)
5. Return top 15 chunks

**Outputs**: List of 15 chunks, each with:

* `text` — the actual content
* `metadata` — source, article, paragraph, topic tags, URL, license
* `score` — combined retrieval score

### 4.4 Stage 4 – Reason

**Purpose**: Produce the structured report.

**Model**: Claude Sonnet

**Inputs**: Scenario + retrieved chunks

**Process**:

1. Prompt explicitly constrains reasoning to retrieved chunks only
2. Claude identifies which chunks describe violations
3. Claude produces scenario-specific explanations
4. Claude links to similar cases when retrievable

**Outputs**: Structured report in Pydantic schema.

### 4.5 Validation Layer

**Purpose**: Catch hallucinations before output.

**No LLM call** — pure Python logic.

**Inputs**: Draft report + retrieved chunks

**Checks**:

1. Every cited article number exists in retrieved chunks
2. Every citation has a source URL
3. Schema is valid (Pydantic parse succeeds)

**Failure handling**: Retry reasoning stage once. If still invalid, fail cleanly with error.

---

## 5. Major Components

### 5.1 CLI Layer (`src/gdpr_ai/cli.py`)

Built with Typer. Handles:

* Argument parsing
* Interactive mode
* Rich-formatted output rendering
* Error presentation

### 5.2 Pipeline Orchestrator (`src/gdpr_ai/pipeline/`)

Coordinates the four stages. Each stage is a separate module:

* `extract.py`
* `classify.py`
* `retrieve.py`
* `reason.py`
* `validate.py`

### 5.3 Knowledge Base (`data/chroma/` + `src/gdpr_ai/knowledge/`)

* `chunker.py` — splits source text into retrievable chunks
* `embedder.py` — wraps sentence-transformers for bge-m3
* `store.py` — ChromaDB interface (add, query, filter)

### 5.4 LLM Client (`src/gdpr_ai/llm/claude_client.py`)

Thin wrapper around Anthropic SDK. Handles:

* Model selection (Haiku vs Sonnet)
* Token counting
* Retry logic
* Cost tracking

### 5.5 Prompts (`src/gdpr_ai/prompts/*.txt`)

Prompts stored as plain text files:

* `extract.txt`
* `classify.txt`
* `reason.txt`

Versioned in Git. Never hardcoded in Python.

### 5.6 Configuration (`src/gdpr_ai/config.py`)

Pydantic settings loaded from `.env`:

* `ANTHROPIC_API_KEY`
* Model IDs
* Paths to ChromaDB and SQLite
* Log level

### 5.7 Observability (SQLite + logging)

* Query log in SQLite
* Per-query cost tracking
* Stage-level latency tracking
* Feedback capture

---

## 6. Data Flow

### 6.1 Build-Time Data Flow (one-time)

```
Raw source websites
    ↓ (scripts/scrape_*.py)
data/raw/*.json
    ↓ (scripts/translate_german_sources.py) [Haiku]
data/processed/*.json
    ↓ (scripts/chunk_and_embed.py)
data/chroma/ (ChromaDB collection)
```

### 6.2 Query-Time Data Flow

```
User scenario
    ↓
CLI (Typer)
    ↓
Extract [Haiku API call]
    ↓
Classify [Haiku API call]
    ↓
Retrieve [local, ChromaDB + BM25]
    ↓
Reason [Sonnet API call]
    ↓
Validate [local, regex + schema]
    ↓
CLI render [Rich]
    ↓
Query log [SQLite]
```

---

## 7. Trust Boundaries

### 7.1 Trusted

* Local filesystem (ChromaDB, SQLite)
* Python process memory
* Environment variables loaded from `.env`

### 7.2 Untrusted

* User-provided scenarios (treated as untrusted input; no command execution derived from them)
* Scraped HTML from external websites (parsed defensively)

### 7.3 External

* Anthropic API (trusted counterparty, but data transmission considered; users are warned in README)

---

## 8. Failure Modes and Responses

| Failure | Stage | Response |
|---------|-------|----------|
| Invalid scenario input | CLI | Clear error, no pipeline invocation |
| Haiku API down | Extract or Classify | Retry with backoff, then fail with suggestion |
| ChromaDB empty | Retrieve | Explain KB not built yet, suggest build commands |
| No relevant chunks | Retrieve | Return "no violation identified" output |
| Sonnet hallucinates | Validate | Retry once, then fail cleanly |
| Network offline | Any LLM stage | Allow retrieval-only mode with clear notice |

---

## 9. Cross-Cutting Concerns

### 9.1 Logging

Every stage logs:

* Start and end timestamps
* Inputs (truncated)
* Outputs (truncated)
* Latency
* Token usage and cost (where applicable)

### 9.2 Cost Tracking

Every LLM call:

* Counts input and output tokens
* Applies model-specific rates
* Logs per-query subtotal
* Aggregates into daily and monthly totals

### 9.3 Attribution

Every chunk carries:

* Source document name
* Original URL
* License identifier
* Publisher

Every report output includes attribution in the footer.

---

## 10. Extension Points

The architecture is designed to accept these v2 extensions without rework:

* Replace CLI with FastAPI layer (same pipeline)
* Replace ChromaDB with Qdrant (same interface)
* Add re-ranker stage between Retrieve and Reason
* Add clarifying-question stage before Extract (multi-turn)
* Add document-parsing stage before Extract (document upload)
* Swap Anthropic for any other LLM provider via the llm/ abstraction

Each extension is isolated to a single component, minimising ripple effects.

---

## 11. Summary

The architecture is intentionally simple: one pipeline, four stages, one vector store, one LLM provider. This simplicity is the primary design virtue. Every choice is optimised for accuracy, cost, and developer understandability rather than feature breadth.

The clean stage boundaries and explicit data contracts make every component independently testable and replaceable, setting up a straightforward path to v2 extensions.

---

## v2 Architecture Extension

Version 2 adds **compliance assessment** alongside the existing **violation analysis** pipeline. Both modes share the **same ChromaDB knowledge base** (extended with v2 collections) and the **same language-model reasoning engine**; they differ in **intake shape**, **prompt objective**, and **output artefacts**.

### v2 system diagram (local)

```
┌─────────────────────────────────────────────────────────────┐
│                        GDPR AI v2                           │
│                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────┐   │
│  │   REST API   │    │           CLI (v1 + v2)          │   │
│  │  (FastAPI)   │    │                                  │   │
│  └──────┬───────┘    └──────────────┬───────────────────┘   │
│         │                           │                       │
│         ▼                           ▼                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Router / Mode Selector                 │    │
│  │         (violation_analysis | compliance_assessment)│    │
│  └──────────┬──────────────────────┬───────────────────┘    │
│             │                      │                        │
│     ┌───────▼───────┐    ┌────────▼────────────┐           │
│     │ v1 Pipeline   │    │   v2 Pipeline       │           │
│     │ extract →     │    │   intake →          │           │
│     │ classify →    │    │   map →             │           │
│     │ retrieve →    │    │   assess →          │           │
│     │ reason        │    │   generate          │           │
│     └───────┬───────┘    └────────┬────────────┘           │
│             │                      │                        │
│             ▼                      ▼                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           Shared Knowledge Base (ChromaDB)          │    │
│  │  GDPR Articles | Recitals | BDSG | TTDSG | EDPB    │    │
│  │  + v2: DPIA templates | RoPA | TOM | AI Act        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Document Generation Service                 │    │
│  │  DPIA Draft | RoPA Template | Checklist |           │    │
│  │  Consent Flow | Retention Policy                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         SQLite (User Projects & Documents)          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         LLM API (Reasoning Engine)                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Shared vs mode-specific behaviour

| Aspect | Shared | v1-specific | v2-specific |
|--------|--------|-------------|-------------|
| Vector store | ChromaDB corpus + embeddings | Topic-tagged violation retrieval | Article mapping per DataMap elements |
| Reasoning engine | Same client and grounding rules | Prompts: **what went wrong** | Prompts: **posture, gaps, remediation** |
| Intake | — | Free-text scenario | JSON DataMap and/or conversational normalisation |
| Outputs | Citations and disclaimers | Violation report | Compliance assessment + markdown documents |
| Persistence | SQLite | Query/analytics logs (existing) | Projects, analyses, document bodies |

This preserves v1 behaviour while adding a **second pipeline** behind an explicit **mode selector** in CLI and API.