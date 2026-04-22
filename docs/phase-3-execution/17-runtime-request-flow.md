# Phase 3.17 – Runtime Request Flow

## 1. Overview

This document traces what happens inside GDPR AI when a user runs a query, from the moment they press Enter on the CLI to the moment the report is rendered. It is intended as a debugging and onboarding reference.

Every step is annotated with latency expectations, side effects, and failure paths.

---

## 2. End-to-End Flow Diagram

```
User types: gdpr-check "scenario text here"
                │
                ▼
        ┌──────────────────┐
        │  1. CLI startup  │  ~400ms
        └────────┬─────────┘
                 ▼
        ┌──────────────────────────────┐
        │  2. Input validation         │  <1ms
        └────────┬─────────────────────┘
                 ▼
        ┌──────────────────────────────┐
        │  3. Orchestrator generates   │  <1ms
        │     query_id, starts timer   │
        └────────┬─────────────────────┘
                 ▼
        ┌──────────────────────────────┐
        │  4. Extract (Haiku)          │  ~800ms
        │     scenario → entities      │
        └────────┬─────────────────────┘
                 ▼
        ┌──────────────────────────────┐
        │  5. Classify (Haiku)         │  ~600ms
        │     scenario → topic tags    │
        └────────┬─────────────────────┘
                 ▼
        ┌──────────────────────────────┐
        │  6. Retrieve (local)         │  ~150ms
        │     ChromaDB + BM25 hybrid   │
        └────────┬─────────────────────┘
                 ▼
        ┌──────────────────────────────┐
        │  7. Reason (Sonnet)          │  ~2500ms
        │     chunks → GDPRReport      │
        └────────┬─────────────────────┘
                 ▼
        ┌──────────────────────────────┐
        │  8. Validate (local)         │  <10ms
        │     hallucination guard      │
        └────────┬─────────────────────┘
                 ▼
        ┌──────────────────────────────┐
        │  9. Log to SQLite            │  <20ms
        └────────┬─────────────────────┘
                 ▼
        ┌──────────────────────────────┐
        │ 10. Render with Rich         │  ~100ms
        └────────┬─────────────────────┘
                 ▼
        User sees the report

Total expected latency: ~4500ms
```

---

## 3. Step-by-Step Detail

### 3.1 Step 1 – CLI Startup

**Triggered by**: Shell executing `gdpr-check "..."` entry point.

**What happens**:

* Python interpreter loads
* `gdpr_ai.cli` module imports
* Typer app initialises
* `config.py` loads `.env` and validates `ANTHROPIC_API_KEY` is set

**Latency**: 300-500ms cold, 50-100ms warm

**Side effects**: None

**Failure modes**:

* Missing `.env` → `ConfigurationError`, message tells user to set up `.env`
* Invalid API key format → `ConfigurationError`, message tells user how to fix

### 3.2 Step 2 – Input Validation

**What happens**:

* Scenario length checked (10-2000 chars)
* Scenario stripped of leading/trailing whitespace
* Empty scenario rejected

**Latency**: <1ms

**Failure modes**:

* Too short → `InputValidationError` with specific minimum
* Too long → `InputValidationError` with specific maximum
* Empty → `InputValidationError`

### 3.3 Step 3 – Orchestrator Setup

**What happens**:

* Orchestrator generates UUID for `query_id`
* Starts total-latency timer
* Logs query intent (query_id + truncated scenario) at DEBUG level

**Latency**: <1ms

### 3.4 Step 4 – Extract Stage

**What happens**:

1. Orchestrator loads `prompts/extract.txt`
2. Constructs messages: system + user (scenario)
3. Calls `llm.claude_client.call_claude(model=HAIKU, ...)`
4. Claude client sends request to Anthropic API
5. Response JSON is parsed into `ExtractedEntities`
6. On JSON parse failure, retry once
7. On persistent failure, raise `ExtractionFailed`

**Latency**: 500-1200ms (dominated by Anthropic API)

**Tokens**: ~300 input, ~150 output typically

**Cost**: ~0.0005 EUR

**Side effects**:

* Stage latency logged
* Token counts recorded for cost tracking

**Failure modes**:

* API unreachable → retry with backoff, then fail
* Rate limited (429) → retry after suggested delay
* Credit too low → `CreditBalanceTooLow`, clear CLI message
* Malformed JSON → retry once, then `ExtractionFailed`

### 3.5 Step 5 – Classify Stage

**What happens**:

1. Orchestrator loads `prompts/classify.txt`
2. Constructs messages with scenario + entities + full taxonomy
3. Calls Haiku
4. Parses response into `TopicTags`
5. Filters any invalid tag names (not in taxonomy)
6. If zero tags remain, defaults to `["legal-basis"]`

**Latency**: 400-800ms

**Tokens**: ~400 input, ~100 output

**Cost**: ~0.0004 EUR

**Failure modes**:

* Same as extract stage
* No relevant tags → graceful default, no error

### 3.6 Step 6 – Retrieve Stage

**What happens**:

1. Orchestrator passes scenario + entities + topics to `retrieve_chunks`
2. Pre-filter: ChromaDB metadata query to get chunks whose `topic_tags` intersect with `topics.primary`
3. If fewer than 30 candidates, expand to include parent taxonomy tags
4. Dense retrieval:
   * Embed scenario with bge-m3 (local, ~50ms)
   * ChromaDB similarity search within candidates
   * Get top 30 with dense scores
5. Sparse retrieval:
   * BM25 scoring of scenario against candidate chunk texts
   * Get top 30 with BM25 scores
6. Combine:
   * Normalise both score sets to [0, 1]
   * Apply boost rules (Germany, special categories)
   * Sum weighted scores
7. Return top 15

**Latency**: 100-200ms total

**Side effects**:

* Embedding model loaded into memory on first call (adds ~2s on cold start)
* Subsequent calls are fast

**Failure modes**:

* ChromaDB not initialised → `KnowledgeBaseError` with build instructions
* Zero candidates after filter → fall back to unfiltered retrieval
* Zero chunks returned → orchestrator produces "no violation" report

### 3.7 Step 7 – Reason Stage

**What happens**:

1. Orchestrator loads `prompts/reason.txt`
2. Constructs messages: system + user (scenario + chunks)
3. Chunks are formatted as numbered list with metadata
4. Calls Sonnet with `max_tokens=2048`, `temperature=0.0`
5. Parses response into `GDPRReport`

**Latency**: 1500-3500ms (dominated by Sonnet)

**Tokens**: ~2500 input (scenario + 15 chunks), ~700 output

**Cost**: ~0.018 EUR

**Failure modes**:

* JSON parse failure → retry once, then `ReasoningFailed`
* Missing required fields → `ReasoningFailed`
* Hallucinated article numbers → caught by validate stage

### 3.8 Step 8 – Validate Stage

**What happens**:

1. Check every `Violation.article` against chunk metadata
2. Check every `source_url` against chunk metadata
3. Check schema integrity via Pydantic
4. On any failure, raise `HallucinationDetected`
5. Orchestrator catches, retries step 7 once
6. If second attempt also fails, raise to CLI

**Latency**: <10ms

**Side effects**: Validation failure logged

**Failure modes**:

* Invalid article cited → retry
* Invalid URL → retry
* Schema violation → retry

### 3.9 Step 9 – Log Query

**What happens**:

1. Compose full query log row
2. INSERT into SQLite `query_log` table
3. Commit transaction

**Latency**: 5-20ms

**Side effects**: `data/gdpr_ai.db` grows by ~5KB per query

### 3.10 Step 10 – Render with Rich

**What happens**:

1. CLI receives `GDPRReport`
2. Rich renders scenario summary
3. Rich renders violations table
4. Rich renders similar cases
5. Rich renders disclaimer footer
6. Output goes to stdout

**Latency**: 50-150ms

---

## 4. Expected Latency Budget

| Stage | p50 | p95 |
|-------|-----|-----|
| CLI startup | 300ms | 500ms |
| Input validation | <1ms | <1ms |
| Extract | 700ms | 1200ms |
| Classify | 500ms | 800ms |
| Retrieve | 130ms | 200ms |
| Reason | 2200ms | 3500ms |
| Validate | <5ms | <10ms |
| Log | 10ms | 30ms |
| Render | 80ms | 150ms |
| **Total** | **~3900ms** | **~6400ms** |

The p95 can exceed the 5-second target under Anthropic API latency spikes. This is logged for analysis.

---

## 5. Cost Budget per Query

| Stage | Tokens (input/output) | Cost |
|-------|----------------------|------|
| Extract (Haiku) | 300 / 150 | 0.0005 EUR |
| Classify (Haiku) | 400 / 100 | 0.0004 EUR |
| Reason (Sonnet) | 2500 / 700 | 0.0180 EUR |
| **Total** | | **~0.019 EUR** |

Well under the 0.05 EUR per-query target.

---

## 6. Error Paths

### 6.1 User Errors

| Error | Where | User Message |
|-------|-------|--------------|
| Empty scenario | Step 2 | "Scenario cannot be empty. Please provide a description." |
| Too short | Step 2 | "Scenario is too short (min 10 characters)." |
| Too long | Step 2 | "Scenario exceeds 2000 characters. Please shorten." |

### 6.2 System Errors

| Error | Where | User Message |
|-------|-------|--------------|
| Missing API key | Step 1 | "Missing ANTHROPIC_API_KEY. Set it in .env." |
| Credit low | Step 4/5/7 | "Anthropic credit balance is too low. Top up at console.anthropic.com." |
| API down | Step 4/5/7 | "Anthropic API is unreachable. Try again in a moment." |
| KB not built | Step 6 | "Knowledge base not found. Run: uv run python scripts/build_index.py" |
| Hallucination retried | Step 8 | "Unable to produce a grounded report for this scenario. Please refine." |

All error paths log the error to SQLite for later analysis.

---

## 7. Observability Per Request

Every query produces one row in the `query_log` SQLite table with:

* `query_id`
* `timestamp`
* `scenario` (full text)
* `entities_json` (pretty-printed)
* `topics_json`
* `retrieved_chunk_ids` (comma-separated)
* `report_json` (full output)
* Per-stage latencies (ms)
* Per-stage token counts
* Total cost (EUR)
* Outcome status

This enables offline analysis: "Which scenarios failed validation?", "What's the p95 reason latency this week?", "Which chunks are most frequently retrieved?".

---

## 8. Retry Policy

### 8.1 LLM Call Retries

Automatic retries for:

* Network errors (DNS, connection timeout, read timeout)
* 5xx server errors
* 429 rate limit (respect `Retry-After` header)

Max 3 retries with exponential backoff (1s, 2s, 4s).

No retries for:

* 400-level errors (bad request, auth failure, credit balance)
* 401 Unauthorized
* 402 Payment Required

### 8.2 Pipeline-Level Retries

Only one pipeline-level retry — for hallucination on reason stage. If the second attempt also fails validation, the error surfaces to the CLI.

---

## 9. Concurrency (Future)

V1 runs one query at a time. No concurrency.

V2 may introduce:

* Async Anthropic SDK calls for parallel extract + classify (currently sequential)
* Connection pooling for ChromaDB under higher query volume
* Background workers for long-running tasks (e.g., bulk evaluation)

---

## 10. Summary

The runtime flow is sequential, well-instrumented, and bounded in latency and cost. Every stage has defined inputs, outputs, failure modes, and observability. The p50 latency fits comfortably under the 5-second target, with the p95 occasionally exceeding it under API slowdowns.

The observability contract — one SQLite row per query with full context — is sufficient for both debugging and long-term quality analysis.