# Phase 0.4 – Production-Ready Implementation Plan

## 1. Overview

This document provides a step-by-step implementation plan for GDPR AI, from empty repository to shipped v1. It defines the phase boundaries, the artefacts produced at each phase, and the dependencies between phases.

The plan is optimised for a solo developer working part-time, with an aggressive but realistic target of a 2-to-3-week v1 delivery.

---

## 2. Guiding Principles

### 2.1 Credit-Free Foundation First

The entire knowledge base, retrieval layer, and offline testing can be built without any language model API credits. This work is scheduled first, ensuring that budget constraints never block progress on the infrastructure.

### 2.2 Evaluation Before Generation

A gold test set of 30+ scenarios with expected article citations is created before any pipeline prompts are written. Every subsequent change is measured against this set. This prevents regression and ensures that progress is measurable rather than subjective.

### 2.3 One Feature Branch per Deliverable

Every meaningful unit of work lives on its own feature branch. This keeps `main` clean, creates a clear review surface, and provides natural rollback points if a direction turns out to be wrong.

### 2.4 Ship Narrow Before Ship Wide

Version 1 is the simplest possible end-to-end system that delivers the core value proposition: scenario in, grounded report out. Frontend, multi-turn reasoning, and document analysis are explicitly deferred.

---

## 3. Phase Breakdown

### 3.1 Phase A – Foundation (Day 1)

**Goal**: Working project skeleton with all tooling configured.

**Deliverables**

* Project directory structure per the architecture specification
* `pyproject.toml` with all v1 dependencies declared
* Python 3.11 pinned via uv
* Dependencies installed and locked via `uv.lock`
* Working CLI entry point that prints the version
* `.env` documented in README (not committed); no committed `.env.example`
* `.gitignore` covering Python, data, logs, IDE, and local notes
* MIT License committed
* Comprehensive README with architecture, stack, docs pointers, and licensing
* GitHub repository initialised with `main` and `develop` branches

**Success criteria**: `uv run gdpr-check version` prints the correct version, repository is visible on GitHub, no sensitive files committed.

### 3.2 Phase B – Knowledge Base Construction (Days 2–3)

**Goal**: All primary legal sources scraped, structured, and stored locally.

**Deliverables**

* `scripts/scrape_gdpr.py` — parses EUR-Lex into structured JSON
* `scripts/scrape_bdsg.py` — parses gesetze-im-internet.de for BDSG
* `scripts/scrape_ttdsg.py` — parses gesetze-im-internet.de for TTDSG
* `scripts/scrape_gdprhub.py` — parses 50–100 landmark cases
* `scripts/scrape_edpb.py` — parses core EDPB guidelines
* `data/raw/*.json` — structured source data with metadata
* Source URL, license, and attribution preserved for every item

**Success criteria**: All scripts run end-to-end without errors. Output JSON files are valid and contain expected counts (approximately 99 articles for GDPR, 50+ cases for GDPRhub, etc.). No language model API calls used.

### 3.3 Phase C – Chunking and Embedding (Day 4)

**Goal**: Raw data transformed into retrieval-ready chunks with embeddings.

**Deliverables**

* `src/gdpr_ai/knowledge/chunker.py` — produces paragraph-level chunks with metadata
* `src/gdpr_ai/knowledge/embedder.py` — wraps sentence-transformers for bge-m3
* `scripts/chunk_and_embed.py` — end-to-end chunk + embed pipeline
* `data/processed/chunks.jsonl` — structured chunks with metadata
* `data/chroma/` — populated ChromaDB collection

**Success criteria**: ChromaDB contains all expected chunks. Manual sanity queries return relevant results. No language model API calls used.

### 3.4 Phase D – Retrieval and Validation (Day 5)

**Goal**: Hybrid retrieval working and tested against hand-crafted queries.

**Deliverables**

* `src/gdpr_ai/pipeline/retrieve.py` — hybrid dense + BM25 retrieval
* `src/gdpr_ai/pipeline/validate.py` — hallucination guards
* `tests/gold_set.json` — 30 hand-curated scenarios with expected citations
* `tests/test_retrieval.py` — validates retrieval quality on gold set

**Success criteria**: Retrieval returns relevant chunks for 90%+ of gold set queries. Validation layer rejects fake article numbers. No language model API calls used.

### 3.5 Phase E – Translation of German Sources (Day 6)

**Goal**: German-origin content (BDSG, TTDSG, DSK) translated to English once.

**Deliverables**

* `scripts/translate_german_sources.py` — Claude Haiku translation pipeline
* `data/processed/translated/*.json` — translated English versions
* Spot-check log for legal-term accuracy

**Success criteria**: All German sources present in English form. Key legal terms verified against authoritative translations. First language model API usage.

**Note**: Phase E requires language model credits. If credits are not yet available, Phase E is deferred until credits land, but Phases B–D can proceed without it. The translated content is added to the knowledge base as a separate indexing step.

### 3.6 Phase F – Pipeline Implementation (Days 7–8)

**Goal**: End-to-end pipeline from scenario to structured report.

**Deliverables**

* `src/gdpr_ai/pipeline/extract.py` — Haiku entity extraction
* `src/gdpr_ai/pipeline/classify.py` — Haiku topic classification
* `src/gdpr_ai/pipeline/reason.py` — Sonnet grounded reasoning
* `src/gdpr_ai/prompts/*.txt` — versioned prompt files
* `src/gdpr_ai/models.py` — Pydantic output schema
* `src/gdpr_ai/cli.py` — connected end-to-end CLI
* `src/gdpr_ai/llm/claude_client.py` — Anthropic SDK wrapper

**Success criteria**: `gdpr-check "<scenario>"` produces a structured report in under 5 seconds. Pipeline runs end-to-end for all 30 gold scenarios. Cost per query stays under 0.05 EUR.

### 3.7 Phase G – Evaluation and Iteration (Days 9–10)

**Goal**: Measured quality against gold set and at least one iteration of improvements.

**Deliverables**

* `tests/run_eval.py` — runs pipeline on gold set and reports metrics
* Precision and recall figures per article
* At least one round of prompt or retrieval tuning based on results
* `docs/eval-results.md` — recorded baseline and iteration deltas

**Success criteria**: Article-level precision >= 0.8 and recall >= 0.7 on the gold set. Zero hallucinated article numbers detected.

### 3.8 Phase H – Observability and Logging (Day 11)

**Goal**: Every query is logged, measurable, and traceable.

**Deliverables**

* SQLite-backed query log
* Per-query cost tracking from token usage
* Latency breakdown per pipeline stage
* Simple feedback capture (thumbs up/down)

**Success criteria**: All queries produce a log row. Running totals of tokens, cost, and latency are queryable via SQLite.

### 3.9 Phase I – Documentation and Polish (Days 12–13)

**Goal**: Repository is ready for portfolio presentation.

**Deliverables**

* Phase-by-phase design documentation (this docs folder)
* Architecture diagram
* Sample report output committed to docs
* README refined with Getting Started and Quick Demo sections
* Screenshots or CLI asciinema if useful

**Success criteria**: A third-party developer can clone the repo and run their first query in under 30 minutes.

### 3.10 Phase J – v1 Release (Day 14)

**Goal**: Tag v1 and merge to main.

**Deliverables**

* Git tag `v1.0.0`
* Merge `develop` into `main` with comprehensive release notes
* GitHub release entry
* v2 roadmap document committed

**Success criteria**: `main` contains a clean, documented, tested, runnable v1 of GDPR AI.

---

## 4. Dependency Graph

```
Phase A (Foundation)
    └── Phase B (Knowledge Base)
            └── Phase C (Chunking + Embedding)
                    └── Phase D (Retrieval + Validation)
                            ├── Phase E (Translation)      [needs API credits]
                            └── Phase F (Pipeline)         [needs API credits]
                                    └── Phase G (Evaluation)
                                            └── Phase H (Observability)
                                                    └── Phase I (Documentation)
                                                            └── Phase J (Release)
```

Phases A through D can proceed entirely without API credits. Phases E onward require language model access. This ordering is deliberate — it ensures that payment or billing friction cannot block early progress.

---

## 5. Branching and Commit Strategy

### 5.1 Branch Model

* `main` — stable, only updated by merging from `develop` at release points
* `develop` — default working branch
* `feature/<short-name>` — branches from `develop` for each feature

### 5.2 Branch Naming Convention

* `feature/scrape-gdpr`
* `feature/chunking`
* `feature/retrieval`
* `feature/translation`
* `feature/extract-stage`
* `feature/classify-stage`
* `feature/reason-stage`
* `feature/eval-harness`
* `feature/logging`

### 5.3 Commit Message Convention

Conventional Commits format:

* `feat:` new feature
* `fix:` bug fix
* `docs:` documentation only
* `chore:` tooling, configs, scaffolding
* `refactor:` code restructure, no behaviour change
* `test:` tests only

One logical change per commit. Prefer small commits over large ones.

---

## 6. Testing Strategy Timeline

### 6.1 Test Deliverables by Phase

| Phase | Tests Added |
|-------|-------------|
| A | Smoke test: CLI version command |
| B | Unit tests for each scraper's parsing logic |
| C | Unit tests for chunker boundary conditions |
| D | Integration tests for retrieval against gold set |
| E | Translation round-trip spot-checks |
| F | Unit tests for each pipeline stage, integration tests for end-to-end |
| G | Evaluation harness runs against gold set |
| H | Log schema validation tests |

### 6.2 Minimum Coverage Targets

* Scraper parsing logic: 70%+
* Chunker: 80%+
* Retrieval: 70%+
* Pipeline stages (mocked LLM): 70%+

---

## 7. Risk Register

### 7.1 Identified Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API credit payment delayed | Medium | Medium | Phases A-D are credit-free; schedule allows flexibility |
| Source website structure changes during scraping | Medium | Low | Store raw HTML for re-parsing; pin parsers to specific URL patterns |
| Retrieval quality insufficient for gold set | Low | High | Hybrid retrieval + filtering fallback; iterate on chunking |
| Translation quality issues on legal terms | Medium | Medium | Spot-check against known translations; manual override for key terms |
| LLM output format drift | Medium | Medium | Strict Pydantic schema + validation retry loop |
| GDPRhub structure changes | Low | Medium | Scheduled monthly refresh identifies breakage early |

### 7.2 Non-Risks

* Running out of API credits during normal development (monitored via cost tracking)
* Running out of disk space (knowledge base fits in under 100MB)
* ChromaDB performance (embedded mode handles 10K+ chunks trivially)

---

## 8. Definition of Done for v1

Version 1 is considered shipped when all of the following are true:

* All 10 phases (A–J) are complete
* Gold test set has at least 30 scenarios with a precision >= 0.8 and recall >= 0.7
* Zero hallucinated article numbers on gold set
* README is accurate and Getting Started section is validated
* MIT License committed, all attributions in place
* `main` branch contains the tagged v1.0.0 release
* At least one end-to-end demo (CLI recording or screenshots) is available

---

## 9. Post-v1 Considerations

### 9.1 What Is Explicitly Deferred to v2

* Web UI and FastAPI HTTP layer
* Multi-turn reasoning
* Document upload (privacy policies, DPAs)
* Website scanning
* Multilingual retrieval and UI
* Cross-encoder re-ranking
* Cloud hosting
* CI/CD pipeline
* Knowledge graph layer

### 9.2 What Is Deferred Beyond v2

* Jurisdictions outside GDPR and German law
* Commercial licensing path (requires CC BY-NC-SA negotiation)
* Enterprise audit workflow features

---

## 10. Summary

The implementation plan is staged to maximise low-cost, credit-free progress early, concentrate paid language model usage in the value-delivering pipeline stages, and reach a shippable v1 within two to three weeks of part-time effort. Evaluation-first development, strict grounding, and small atomic commits provide the quality guardrails throughout.

---

## v2 Implementation Phases

The following phases build on the completed v1 (Phases A–J). They add **compliance assessment**, **document generation**, **local REST API**, and **SQLite** persistence while **preserving** the v1 violation pipeline.

| Phase | Name | Description | Depends On |
|-------|------|-------------|------------|
| K | Knowledge Base Expansion | Add DPIA templates, RoPA structure, TOM catalog, consent-flow best practices, legitimate-interest assessment guidance, and EU AI Act (data-protection-relevant) sources to ChromaDB | v1 complete |
| L | System Intake Engine | Structured input parser: accepts system description (JSON schema), extracts data categories, processing purposes, legal-basis candidates, data flows, third parties, storage locations, retention; outputs a normalised **DataMap** | K |
| M | Compliance Analysis Pipeline | New pipeline: **intake → map → assess → generate**. Takes **DataMap**, runs against expanded KB, flags applicable articles, compliant vs risky vs missing areas; reuses v1 retrieval with **compliance-posture** prompts | K, L |
| N | Document Generation Service | From analysis output: DPIA draft (markdown), RoPA pre-filled template, technical checklist, consent-flow recommendations, retention policy draft — all markdown | M |
| O | REST API Layer | FastAPI exposes **v1** (violation analysis) and **v2** (compliance assessment); endpoint detail in [11 – API Design](../phase-2-architecture/11-api-design.md) | M, N |
| P | User and Project Persistence | SQLite: users (local identity), projects (multiple systems per user), analyses, generated documents | O |
| Q | v2 Evaluation | Gold set: **20** compliance scenarios (SaaS, mobile, AI product, e-commerce, health, etc.); metrics: articles, DPIA completeness, actionability of technical guidance | M, N |