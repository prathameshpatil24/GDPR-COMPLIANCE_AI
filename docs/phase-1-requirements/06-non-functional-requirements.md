# Phase 1.6 – Non-Functional Requirements

## 1. Overview

This document defines the quality attributes GDPR AI must satisfy. These cover performance, reliability, cost, security, maintainability, and other cross-cutting concerns. Unlike functional requirements, these describe *how well* the system must behave, not *what* it must do.

Every non-functional requirement has a measurable target and a verification method.

---

## 2. Performance

### NFR-01 – End-to-End Latency

The total time from scenario input to displayed report must stay under 5 seconds for typical scenarios.

* Target: p50 ≤ 3 seconds, p95 ≤ 5 seconds
* Measured: from CLI command entry to final output render
* Verification: logged per query, aggregated weekly

### NFR-02 – Retrieval Latency

Retrieval from ChromaDB must complete in under 200 milliseconds.

* Target: p95 ≤ 200ms for hybrid dense + sparse queries
* Dependencies: local disk I/O, embedding cache in memory
* Verification: stage-level latency logging

### NFR-03 – LLM Call Latency

Each language model call must complete in under 3 seconds.

* Target: p95 ≤ 3 seconds per stage (extract, classify, reason)
* Dependencies: Anthropic API response time
* Mitigation: streaming disabled for v1 to keep validation simple

### NFR-04 – Cold Start

Running `gdpr-check` for the first time in a session must complete in under 10 seconds.

* Contributors: Python interpreter startup, embedding model load, ChromaDB open
* Target: ≤ 10 seconds p95
* Mitigation: lazy-load embedding model only when retrieval is needed

---

## 3. Cost

### NFR-05 – Per-Query Cost

The average cost of running the full pipeline on one scenario must stay under 0.05 EUR.

* Haiku calls (extract + classify): ~0.002 EUR combined
* Sonnet call (reason): ~0.015 EUR for typical chunk set
* Target: p95 ≤ 0.05 EUR
* Verification: cost tracking via token usage logs

### NFR-06 – Monthly Operating Cost

At typical personal usage (10 queries per day), monthly cost must stay under 10 EUR.

* Target: ≤ 10 EUR / month
* Components: LLM API calls, one-time translation cost amortised
* Verification: SQLite aggregation queries

### NFR-07 – One-Time Translation Cost

The one-time translation of German sources during knowledge-base build must stay under 5 EUR.

* Target: ≤ 5 EUR total
* Model: Haiku (cheapest viable for legal translation)
* Mitigation: cache translations; only re-translate changed content

---

## 4. Accuracy

### NFR-08 – Article-Level Precision

On the gold test set, the system must achieve precision ≥ 0.8.

* Definition: of all articles cited, what fraction match expected
* Target: ≥ 0.8 on gold set of 30+ scenarios
* Verification: evaluation harness runs

### NFR-09 – Article-Level Recall

On the gold test set, the system must achieve recall ≥ 0.7.

* Definition: of all expected articles, what fraction are cited
* Target: ≥ 0.7 on gold set
* Verification: evaluation harness runs

### NFR-10 – Hallucination Rate

Zero hallucinated article numbers must appear in final outputs.

* Definition: article number cited but not present in retrieved chunks
* Target: 0 occurrences after validation layer
* Verification: validation layer logs; adversarial gold scenarios

---

## 5. Reliability

### NFR-11 – Error Handling

The system must fail cleanly with actionable error messages.

* Rule: no unhandled exceptions in user-facing paths
* All errors include a suggested next step
* Verification: integration tests covering error paths

### NFR-12 – Retry Logic

Transient LLM API failures must be retried with exponential backoff.

* Rule: up to 3 retries per call with backoff 1s / 2s / 4s
* Scope: network errors, 429 rate limits, 5xx errors
* Non-retryable: 4xx auth errors, credit-balance errors

### NFR-13 – Graceful Degradation

If the language model is unavailable, the system must still respond usefully.

* Behaviour: return retrieved chunks with a clear "LLM unavailable" notice
* Purpose: allow offline retrieval inspection even when API is down

---

## 6. Security and Privacy

### NFR-14 – API Key Protection

The Anthropic API key must never be committed, logged, or transmitted to third parties.

* Storage: `.env` only, gitignored
* Logging: keys masked in all log output
* Verification: repo-wide grep for sk-ant- patterns in CI

### NFR-15 – No PII Collection

The system must not collect identifying information about the user.

* No user identity, email, or account
* Query logs stored locally only
* No external telemetry in v1

### NFR-16 – Scenario Data Handling

User scenarios may contain sensitive information; the system must treat them accordingly.

* Scenarios sent to Anthropic API (subject to their data policy)
* No retention beyond local SQLite logs
* Users can clear local logs at any time with a single command

### NFR-17 – License Compliance

The system must enforce GDPRhub's CC BY-NC-SA 4.0 requirements.

* Attribution preserved in every chunk's metadata
* Non-commercial use enforced at the project level (v1)
* Share-alike terms documented in README

---

## 7. Maintainability

### NFR-18 – Code Style Consistency

All Python code must conform to the project's style guide.

* Tooling: Ruff for linting and formatting
* Line length: 100 characters
* Verification: `ruff check .` passes with no errors

### NFR-19 – Type Safety

All public functions and class attributes must have type hints.

* Tooling: mypy in strict mode for core modules
* Exceptions: scripts/ folder may use lighter typing
* Verification: `mypy src/gdpr_ai` passes

### NFR-20 – Dependency Minimalism

New dependencies must be justified and approved before adding.

* Rule: every dependency in `pyproject.toml` has a clear purpose
* Preference: standard library over third-party where feasible
* Verification: dependency review in every PR

### NFR-21 – Prompt Versioning

All LLM prompts must be stored as separate text files, not hardcoded in Python.

* Location: `src/gdpr_ai/prompts/*.txt`
* Version control: Git tracks every change
* Purpose: enables A/B testing and rollback

---

## 8. Testability

### NFR-22 – Unit Test Coverage

Core modules must have at least 70% line coverage.

* Modules: chunker, embedder, retriever, validator, each pipeline stage
* Tooling: pytest + coverage.py
* Verification: coverage report in CI (v2) or manual runs (v1)

### NFR-23 – Mock LLM Support

All pipeline tests must be runnable without real LLM calls.

* Mock fixture: returns canned responses for integration tests
* Purpose: CI runs without API costs, deterministic results

### NFR-24 – Reproducible Evaluation

The evaluation harness must produce deterministic results for the same gold set and system state.

* Controlled: fixed random seeds where applicable
* Logged: model version, prompt version, chunk snapshot
* Purpose: ability to attribute changes to specific deltas

---

## 9. Portability

### NFR-25 – Cross-Platform Support

The system must run on macOS, Linux, and Windows (WSL).

* Python 3.11+ via uv
* No platform-specific dependencies
* Verification: manual smoke test on macOS at minimum

### NFR-26 – Local-First Operation

The system must run fully offline except for Anthropic API calls.

* ChromaDB: embedded, no server
* Embeddings: local inference
* No cloud storage or external databases required

---

## 10. Scalability (v1 Scope)

### NFR-27 – Knowledge Base Size

The system must handle at least 10,000 chunks without performance degradation.

* Expected: ~3,000 chunks in v1
* Headroom: 3× for growth
* Verification: stress test with synthetic chunks

### NFR-28 – Query Throughput

The system must handle at least 100 queries per hour on a modern laptop.

* Constraint: Anthropic API rate limits
* Target: sufficient for personal use
* v2 scope: multi-user concurrency

---

## 11. Observability

### NFR-29 – Structured Logging

All logs must be structured and queryable.

* Format: JSON lines for machine parsing, human-readable format for CLI
* Fields: timestamp, level, stage, latency, cost, query_id
* Storage: SQLite for queries, stderr for operational logs

### NFR-30 – Cost Visibility

Total and per-query costs must be visible at any time.

* Command: `gdpr-check stats` (v1) or dashboard (v2)
* Metrics: total cost today, total cost this month, cost per query average

---

## 12. Summary

GDPR AI's non-functional requirements prioritise accuracy, low cost, and grounded reasoning over feature breadth or scale. The targets are achievable on a single laptop with a modest Anthropic budget, making the system accessible to solo developers and small teams.

Quality gates — precision, recall, zero hallucinations, cost ceilings, and latency targets — form the basis for regression testing in every phase and release.

---

## v2 Non-Functional Requirements

**NFR-v2-01** — Compliance assessment (intake through assessment summary, excluding optional document generation) SHALL complete within **120 seconds** for a typical system description on a developer laptop.

**NFR-v2-02** — Document generation SHALL complete within **60 seconds per document type** under typical load (local hardware, normal KB size).

**NFR-v2-03** — API **simple** operations (health, fetch by id, list projects) SHALL respond in under **2 seconds** p95 locally.

**NFR-v2-04** — The SQLite database SHALL handle up to **10,000 projects** without unacceptable degradation for single-user local use (interactive queries remain responsive).

**NFR-v2-05** — All generated documents SHALL include **citations** to specific GDPR articles, recitals, or EDPB guidelines where a regulatory claim is made — no uncited legal claims in final outputs.

**NFR-v2-06** — The system SHALL run **entirely locally** except for calls to the language-model API; no mandatory external SaaS for core operation (see constraints doc for LLM data flow).