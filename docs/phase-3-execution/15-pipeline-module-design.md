# Phase 3.15 – Pipeline Module Design

## 1. Overview

This document specifies each pipeline module in detail: its inputs, outputs, prompts, error modes, and testing approach. These modules collectively implement the four-stage RAG pipeline defined in [08 – High-Level Architecture](../phase-2-architecture/08-high-level-architecture.md).

Every module is designed to be independently testable, with a clear data contract at its boundary.

---

## 2. Module: `pipeline.extract`

### 2.1 Purpose

Convert a free-text scenario into a structured entity object.

### 2.2 Contract

```python
def extract_entities(scenario: str) -> ExtractedEntities: ...

class ExtractedEntities(BaseModel):
    data_subject: str                     # e.g., "employee", "patient", "customer"
    data_type: list[str]                  # e.g., ["contact info", "health data"]
    controller_role: str                  # e.g., "employer", "service provider"
    purpose: str                          # e.g., "marketing", "safety monitoring"
    legal_basis_claimed: str | None       # e.g., "consent", "legitimate interest"
    jurisdiction: str                     # e.g., "Germany", "EU", "unspecified"
    special_categories_present: bool
    summary: str                          # 1-2 sentence plain summary
```

### 2.3 LLM Call

**Model**: `claude-haiku-4-5-20251001`

**Prompt**: `src/gdpr_ai/prompts/extract.txt`

**Prompt structure**:

* System: "You extract structured entities from GDPR scenarios. Output only valid JSON matching the schema."
* User: "Scenario: <scenario>\n\nExtract entities."

**Response handling**: Parsed into `ExtractedEntities` via Pydantic. Malformed JSON → retry once, then raise `ExtractionFailed`.

### 2.4 Failure Modes

| Failure | Response |
|---------|----------|
| JSON parse error | Retry once with stricter prompt; else `ExtractionFailed` |
| Required field missing | `ExtractionFailed` |
| API unreachable | `LLMUnavailable` |
| Credit exhausted | `CreditBalanceTooLow` |

### 2.5 Testing

* Unit tests with mocked Claude responses for typical scenarios
* Tests for malformed JSON responses
* Tests for edge-case scenarios (very short, very long, non-GDPR topics)

---

## 3. Module: `pipeline.classify`

### 3.1 Purpose

Map the scenario to 1-4 topic tags from the fixed taxonomy. These tags scope retrieval to the relevant knowledge-base partitions.

### 3.2 Contract

```python
def classify_topics(
    scenario: str,
    entities: ExtractedEntities,
) -> TopicTags: ...

class TopicTags(BaseModel):
    primary: list[str]       # 1-4 tags from taxonomy
    rationale: str            # 1-2 sentences explaining the choice
```

### 3.3 Taxonomy Reference

See [10 – Data and Knowledge Model](../phase-2-architecture/10-data-knowledge-model.md#5-topic-taxonomy). The prompt includes the full taxonomy list.

### 3.4 LLM Call

**Model**: Haiku

**Prompt**: `src/gdpr_ai/prompts/classify.txt`

**Prompt structure**:

* Full taxonomy embedded as a list
* Scenario and entities provided
* "Select 1-4 tags. Return JSON."

### 3.5 Failure Modes

| Failure | Response |
|---------|----------|
| Tag not in taxonomy | Drop the invalid tag; if all invalid, default to `legal-basis` |
| Zero tags returned | Default to `legal-basis` |
| More than 4 tags | Truncate to top 4 by order given |

### 3.6 Testing

* Unit tests for scenarios covering each taxonomy branch
* Test that invalid tag names are filtered
* Test default behaviour when classifier returns nothing useful

---

## 4. Module: `pipeline.retrieve`

### 4.1 Purpose

Find the top-k most relevant chunks from the knowledge base, given the scenario, entities, and topic tags.

### 4.2 Contract

```python
def retrieve_chunks(
    scenario: str,
    entities: ExtractedEntities,
    topics: TopicTags,
    k: int = 15,
) -> list[RetrievedChunk]: ...

class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    dense_score: float
    bm25_score: float
    combined_score: float
```

### 4.3 Retrieval Algorithm

1. **Pre-filter**: From all chunks, keep only those whose `topic_tags` intersect with `topics.primary`. If the filter produces fewer than 30 chunks, expand to include parent taxonomy nodes.

2. **Dense retrieval**: Embed the scenario with bge-m3. Cosine similarity against filtered chunks. Keep top 30.

3. **Sparse retrieval**: BM25 scoring of the scenario against the same filtered set. Keep top 30.

4. **Combine**: Merge dense and sparse results. Normalise both scores to [0, 1] within the candidate set. Compute combined score:

   ```
   combined_score = 0.5 * dense_normalised + 0.5 * bm25_normalised
   ```

5. **Boost rules**:

   * If `jurisdiction == "Germany"` → boost BDSG and TTDSG chunks by +0.1
   * If `special_categories_present == True` → boost Art. 9 chunks by +0.15

6. **Return**: Top k (default 15) by combined score.

### 4.4 Failure Modes

| Failure | Response |
|---------|----------|
| ChromaDB not built | `KnowledgeBaseError` with build instructions |
| Filter produces zero chunks | Fall back to unfiltered retrieval |
| Retrieval returns zero chunks | `NoChunksRetrieved` — orchestrator produces "no violation" output |

### 4.5 Testing

* Unit tests against a small test ChromaDB with known chunks
* Tests for each boost rule
* Tests for fallback behaviour
* Integration test: gold-set queries should retrieve expected chunks in top 15

---

## 5. Module: `pipeline.reason`

### 5.1 Purpose

Produce the final structured report by reasoning over retrieved chunks.

### 5.2 Contract

```python
def reason_over_chunks(
    scenario: str,
    chunks: list[RetrievedChunk],
) -> GDPRReport: ...

class GDPRReport(BaseModel):
    scenario_summary: str
    violations: list[Violation]
    similar_cases: list[SimilarCase]
    disclaimer: str
    metadata: ReportMetadata

class Violation(BaseModel):
    article: str                     # "Article 32"
    paragraph: str | None            # "1"
    title: str                       # "Security of processing"
    short_definition: str            # one-line summary
    scenario_explanation: str        # why this applies to this scenario
    source_url: str                  # from chunk metadata

class SimilarCase(BaseModel):
    case_name: str
    dpa_or_court: str
    fine_amount_eur: int | None
    articles_cited: list[str]
    source_url: str

class ReportMetadata(BaseModel):
    query_id: str
    latency_ms: int
    cost_eur: float
    model_used: str
    knowledge_base_version: str
```

### 5.3 LLM Call

**Model**: `claude-sonnet-4-6`

**Prompt**: `src/gdpr_ai/prompts/reason.txt`

**Prompt structure**:

* System: explains the task, forbids citing articles not in retrieved chunks
* User: scenario + numbered list of retrieved chunks with metadata
* Output format: JSON matching `GDPRReport` schema

**Key instructions in prompt**:

* "Only cite articles that appear in the retrieved chunks. Do not cite anything else."
* "If no chunk supports a violation claim, do not include that claim."
* "Include the source URL for every article cited, copied from the chunk metadata."
* "For each violation, explain how it specifically applies to this scenario."

### 5.4 Failure Modes

| Failure | Response |
|---------|----------|
| JSON parse error | Retry once; else `ReasoningFailed` |
| Required field missing | `ReasoningFailed` |
| Hallucinated article | Caught by validate stage, not here |

### 5.5 Testing

* Unit tests with mocked Sonnet responses
* Tests for empty chunk list → should produce "no violation" output
* Tests for scenarios where multiple articles apply

---

## 6. Module: `pipeline.validate`

### 6.1 Purpose

Catch hallucinations before the report reaches the user.

### 6.2 Contract

```python
def validate_report(
    report: GDPRReport,
    chunks: list[RetrievedChunk],
) -> GDPRReport: ...  # raises HallucinationDetected on failure
```

### 6.3 Validation Rules

1. **Article presence**: For each `Violation`, the cited article (e.g., "Article 32") must match `chunk.metadata.article_or_section` of at least one retrieved chunk.

2. **URL traceability**: `violation.source_url` must equal one of the retrieved chunks' `source_url`. No invented URLs.

3. **Schema integrity**: Full Pydantic re-validation of the report. Any schema violation → `ValidationError`.

4. **Similar cases traceability**: If `SimilarCase` is included, its URL must come from a chunk (case or fine-tracker chunk) in the retrieved set.

### 6.4 Failure Behaviour

* Validation failure raises `HallucinationDetected`
* Orchestrator catches it and retries the reason stage once
* If retry also fails validation, the orchestrator raises the error to the CLI, which shows a clear message

### 6.5 Testing

* Tests for each rule with adversarial reports
* Test that valid reports pass unchanged
* Test retry behaviour in orchestrator

---

## 7. Module: `pipeline.orchestrator`

### 7.1 Purpose

Run the full pipeline end-to-end, coordinating stages, logging, and error handling.

### 7.2 Contract

```python
def run_pipeline(scenario: str) -> GDPRReport: ...
```

### 7.3 Execution Order

1. Validate scenario input (length, emptiness)
2. Generate `query_id`
3. Call `extract.extract_entities(scenario)`
4. Call `classify.classify_topics(scenario, entities)`
5. Call `retrieve.retrieve_chunks(scenario, entities, topics)`
6. Call `reason.reason_over_chunks(scenario, chunks)`
7. Call `validate.validate_report(report, chunks)`
8. On `HallucinationDetected`, retry step 6-7 once
9. Attach `ReportMetadata` (query_id, total latency, total cost)
10. Log the full query to SQLite
11. Return the report

### 7.4 Timing and Cost Tracking

Each stage wrapped in a context manager that records:

* Start time
* End time
* Tokens used (from LLM client return value)
* Cost in EUR

Totals aggregated into `ReportMetadata`.

### 7.5 Testing

* Integration tests mocking LLM calls, verifying full orchestration
* Tests for retry behaviour on hallucination detection
* Tests for timing capture accuracy

---

## 8. Prompts Management

### 8.1 Location

All prompts live in `src/gdpr_ai/prompts/` as `.txt` files.

### 8.2 Loading

Loaded at module import time:

```python
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
EXTRACT_PROMPT = (PROMPTS_DIR / "extract.txt").read_text()
```

### 8.3 Versioning

Prompt changes are Git-tracked. Each prompt file includes a version comment in its header:

```
# prompt: extract
# version: 1.0
# last_updated: 2026-04-25
```

### 8.4 A/B Testing (v2)

v1 uses a single prompt per stage. v2 may introduce A/B testing with prompt variants and comparison against the gold set.

---

## 9. LLM Client

### 9.1 Module: `llm.claude_client`

Wraps the Anthropic SDK with:

* Retry logic (exponential backoff, max 3 retries on transient errors)
* Token counting (from SDK response metadata)
* Cost calculation (per-model rate constants)
* Cost tracking (adds to SQLite-backed running total)

### 9.2 Contract

```python
class ClaudeResponse(BaseModel):
    content: str
    input_tokens: int
    output_tokens: int
    cost_eur: float
    model: str
    latency_ms: int

def call_claude(
    model: str,
    messages: list[dict],
    system_prompt: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> ClaudeResponse: ...
```

### 9.3 Rate Constants

```python
RATES_PER_MTOKEN = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6":         {"input": 3.00, "output": 15.00},
}
```

(Updated as Anthropic pricing changes.)

---

## 10. Configuration

### 10.1 Tuning Knobs

| Setting | Default | Where |
|---------|---------|-------|
| `k` (retrieved chunks) | 15 | `retrieve.retrieve_chunks` |
| `max_tokens` (reason) | 2048 | `reason.reason_over_chunks` |
| `temperature` | 0.0 | all LLM calls |
| `dense_weight` | 0.5 | `retrieve` scoring |
| `bm25_weight` | 0.5 | `retrieve` scoring |
| `german_boost` | 0.1 | `retrieve` boost rule |
| `special_categories_boost` | 0.15 | `retrieve` boost rule |

These are constants in v1; tunable via config file in v2.

---

## 11. Summary

Each pipeline module has a single responsibility, a clear input-output contract, well-defined failure modes, and isolated testing. The orchestrator composes them into the end-to-end flow with logging and cost tracking. Prompts are file-based and version-controlled. The LLM client encapsulates retry logic and cost accounting so higher-level modules stay clean.

This design supports iteration: changing a prompt, tuning retrieval weights, or swapping a model can be done in one place without cascading changes.

---

## v2 Compliance Pipeline

The v2 path is **intake → map → assess → generate**. It reuses **retrieval** and **grounding** machinery from v1 with different prompts and output schemas. Each module below is independently testable.

### `compliance.intake`

* **Input:** Structured JSON conforming to **DataMap**, or **free-text** system description.
* **Behaviour:** If JSON, validate with Pydantic. If free text, call the reasoning engine with a structured-extraction prompt to populate **DataMap** fields (with explicit unknowns rather than invention).
* **Output:** `DataMap` instance persisted on the project row when applicable.

### `compliance.mapper`

* **Input:** `DataMap`.
* **Behaviour:** For each data category, processing purpose, flow, and third party, query ChromaDB (including v2 collections) for applicable GDPR articles, BDSG sections, and EDPB guidelines.
* **Output:** **ArticleMap** — mapping from system elements to cited legal bases and chunk ids (implementation detail: Pydantic model shared with assessor).

### `compliance.assessor`

* **Input:** `DataMap` + **ArticleMap** + retrieved chunk texts (same grounding contract as v1: no citation without retrieval path).
* **Behaviour:** Single or multi-call reasoning with a **compliance posture** prompt: "what is missing, what is risky, what is needed?" — not "what went wrong in an incident?"
* **Output:** **ComplianceAssessment** — findings with posture `compliant` | `at-risk` | `non-compliant` | `insufficient-information`, remediation text, technical steps, citations.

### `compliance.generator`

* **Input:** **ComplianceAssessment** (+ **DataMap** for RoPA context).
* **Behaviour:** Render Jinja2 templates (`templates/*.md.j2`) per document type. Templates encode regulatory **structure** (EDPB-oriented DPIA sections, Article 30 RoPA fields); the reasoning engine fills **case-specific** narrative fields where needed, still subject to citation rules.
* **Output:** Markdown strings stored in SQLite `documents` and returned via API/CLI.

Prompt files for v2 live alongside v1 under `src/gdpr_ai/prompts/` (for example `compliance_extract.txt`, `compliance_assess.txt`) and are versioned in Git the same way as v1 prompts.