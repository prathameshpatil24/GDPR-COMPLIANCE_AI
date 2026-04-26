# Phase 1.5 – Functional Requirements

## 1. Overview

This document defines what GDPR AI must do from a user-facing and system-facing perspective. Every functional requirement has a clear owner (CLI, pipeline stage, knowledge base, or logging subsystem) and a verifiable acceptance criterion.

Functional requirements are numbered with an `FR-` prefix for traceability in tests, commits, and future documentation updates.

---

## 2. Input Requirements

### FR-01 – Scenario Input via CLI

The system must accept a free-text scenario as a command-line argument or via interactive prompt.

* Input length: up to 2000 characters
* Input language: English only (v1)
* Input format: plain text, no markdown parsing
* Acceptance: `gdpr-check "<scenario>"` produces a report

### FR-02 – Interactive Mode

The system must support an interactive mode when no scenario argument is provided.

* Command: `gdpr-check` (no arguments)
* Behaviour: prompt the user to enter a scenario, then process it
* Exit: standard terminal controls (Ctrl+C, Ctrl+D)

### FR-03 – Scenario Validation

The system must reject invalid input with a clear error message before running the pipeline.

* Empty string → `Error: scenario cannot be empty`
* Fewer than 10 characters → `Error: scenario too short to analyse`
* More than 2000 characters → `Error: scenario exceeds maximum length`

---

## 3. Processing Requirements

### FR-04 – Entity Extraction

The system must extract structured entities from the free-text scenario before retrieval.

* Entities: data subject, data type, controller role, processing purpose, legal basis claimed, jurisdiction, special categories flag
* Output format: structured JSON
* Failure mode: if extraction fails, the system must return a clear error rather than guessing

### FR-05 – Topic Classification

The system must classify the scenario into one or more GDPR topic areas from a fixed taxonomy.

* Taxonomy: legal basis, consent, data subject rights, controller/processor duties, security and breaches, DPIA and DPO, international transfers, employment context, children, automated decisions, direct marketing
* Output: 1 to 4 topic tags per scenario
* Purpose: scope the retrieval to relevant knowledge-base partitions

### FR-06 – Hybrid Retrieval

The system must retrieve relevant knowledge chunks using both dense and sparse retrieval methods.

* Dense: cosine similarity over bge-m3 embeddings
* Sparse: BM25 over chunk text
* Filter: by topic tags from FR-05
* Output: top 15 chunks, ranked by combined score

### FR-07 – Grounded Reasoning

The system must produce its final report by reasoning only over retrieved chunks.

* Input to reasoning stage: scenario + retrieved chunks only
* Forbidden: citing articles not present in retrieved set
* Behaviour: if no relevant articles are retrieved, return a clear "no violation identified" response rather than fabricating

### FR-08 – Hallucination Validation

The system must validate that every article number in the final output exists in the retrieved chunks.

* Check: every cited article matches a retrieved chunk's metadata
* Action on failure: reject the output, retry reasoning once, then fail cleanly if still invalid
* Logging: all validation failures are logged for analysis

---

## 4. Output Requirements

### FR-09 – Structured Report Format

The system must produce output conforming to a defined Pydantic schema.

* Fields: `scenario_summary`, `violations[]`, `similar_cases[]`, `disclaimer`, `metadata`
* Each violation includes: `article`, `paragraph`, `title`, `short_definition`, `scenario_explanation`, `source_url`
* Format: JSON internally, Rich-formatted text for CLI display

### FR-10 – Article-Level Citations

Every cited article must include its full identifier with paragraph.

* Example: `Article 6(1)(a)` not `Article 6`
* Example: `BDSG §26(1)` not `BDSG §26`
* Recitals cited separately when relevant

### FR-11 – Source Attribution

Every violation output must reference the source document and URL.

* GDPR chunks → EUR-Lex URL
* BDSG / TTDSG chunks → gesetze-im-internet.de URL
* GDPRhub chunks → GDPRhub case URL + CC BY-NC-SA attribution

### FR-12 – Enforcement Case Anchoring

When retrievable, the system must include references to similar enforcement cases.

* Include: case name, DPA or court, fine amount, articles cited
* Source: GDPRhub and Enforcement Tracker chunks
* Limit: top 3 most relevant cases per report

### FR-13 – Legal Disclaimer

Every output must include an informational-only disclaimer.

* Placement: footer of every report
* Language: clear, non-legalese
* Content: not legal advice, machine translations may be imperfect, consult qualified counsel

---

## 5. Knowledge Base Requirements

### FR-14 – Legal Text Coverage

The knowledge base must contain the full text of GDPR, BDSG, and TTDSG.

* GDPR: all 99 articles + 173 recitals in English
* BDSG: all articles relevant to common scenarios, translated to English
* TTDSG: full text, translated to English

### FR-15 – Guidance Coverage

The knowledge base must contain core regulatory guidance.

* EDPB Guidelines: at least 20 core guidelines
* DSK Kurzpapiere: at least 15 core papers, translated
* BfDI / BayLDA / LfDI BW: key guidance, translated

### FR-16 – Enforcement Case Coverage

The knowledge base must contain German enforcement decisions.

* GDPRhub: top 50-100 German cases
* Enforcement Tracker: structured fine data
* Landmark cases: Deutsche Wohnen, 1&1, H&M Nürnberg, Notebooksbilliger, Vodafone

### FR-17 – Metadata on Every Chunk

Every knowledge-base chunk must carry complete metadata.

* Required fields: `source`, `article_or_section`, `paragraph`, `topic_tags`, `language`, `jurisdiction`, `url`, `license`
* Purpose: traceability, filtering, attribution

### FR-18 – Refresh Cadence

The system must support re-running scraping and re-embedding incrementally.

* Legal text: quarterly re-scrape
* Enforcement cases: monthly re-scrape
* Delta detection: only new or changed content is re-embedded

---

## 6. Evaluation Requirements

### FR-19 – Gold Test Set

The system must maintain a gold test set of at least 30 scenarios with expected article citations.

* Storage: `tests/gold_set.json`
* Format: scenario + expected articles + expected laws + notes
* Growth: new scenarios added whenever a real query reveals a gap

### FR-20 – Evaluation Harness

The system must provide a script to run the full pipeline against the gold set.

* Output: precision and recall per article
* Metrics: article-level precision, recall, F1
* Logging: per-scenario result with retrieved chunks and final output

### FR-21 – Regression Gate

Every change that touches prompts, retrieval, or chunking must be measured against the gold set.

* Rule: precision and recall must not drop below the previous baseline
* Enforcement: manual for v1 (documented in commit message), CI-enforced in v2

---

## 7. Observability Requirements

### FR-22 – Query Logging

Every query must be logged to SQLite with full context.

* Fields: `timestamp`, `scenario`, `entities`, `topics`, `retrieved_chunk_ids`, `final_output`, `latency_per_stage`, `token_usage`, `cost`
* Storage: local SQLite, no external transmission

### FR-23 – Cost Tracking

The system must compute and log the cost of every LLM call.

* Input and output tokens separately
* Per-model cost rates (Haiku vs Sonnet)
* Aggregated daily totals queryable via SQLite

### FR-24 – Feedback Capture

The system must support thumbs-up / thumbs-down feedback on each output.

* Interface: CLI prompt after report display
* Storage: linked to query log row
* Purpose: weak-chunk identification, prompt iteration

---

## 8. CLI Requirements

### FR-25 – Primary Commands

The CLI must support the following commands.

| Command | Behaviour |
|---------|-----------|
| `gdpr-check "<scenario>"` | Run the pipeline on a scenario and print the report |
| `gdpr-check` | Enter interactive mode |
| `gdpr-check version` | Print the version |
| `gdpr-check doctor` | Check environment and knowledge-base health |

### FR-26 – Output Formatting

CLI output must be rendered with syntax colouring and clear structure.

* Library: Rich (Python)
* Sections: scenario summary, violations table, similar cases, disclaimer
* Truncation: long explanations collapsed with an "expand" hint

---

## 9. Non-Functional Crossover

Some functional requirements rely on non-functional guarantees. These are listed here as a cross-reference only. Details are in [06 – Non-Functional Requirements](06-non-functional-requirements.md).

* Latency: FR-06 (retrieval) and FR-07 (reasoning) together must complete within 5 seconds
* Cost: FR-07 must stay under 0.05 EUR per query on average
* Accuracy: FR-20 must demonstrate precision >= 0.8 on the gold set

---

## 10. Summary

GDPR AI's functional requirements cover input handling, pipeline processing, structured output, knowledge base completeness, evaluation, observability, and CLI interaction. Every requirement has a verifiable acceptance criterion and a clear owner in the system architecture.

The requirements are intentionally scoped for v1 simplicity — single-shot scenario analysis with a CLI interface — with explicit deferral of multi-turn conversation, document upload, and website scanning to later versions.

---

## v2 Functional Requirements

The following requirements extend v1. They cover **system intake**, **compliance analysis**, **document generation**, **REST API**, and **persistence** for compliance assessment mode.

### System Intake

**FR-v2-01** — The system SHALL accept a structured system description via a documented JSON schema (Pydantic models), validated at the API and CLI boundaries.

**FR-v2-02** — The system SHALL extract and normalise, from that description: data categories collected; processing purposes; legal-basis candidates; data flows (who sends what where); third-party processors; storage locations and jurisdictions; retention periods.

**FR-v2-03** — The system SHALL produce a standardised **DataMap** object from intake (see [10 – Data and Knowledge Model](../phase-2-architecture/10-data-knowledge-model.md)).

**FR-v2-04** — The system SHALL support both **structured** (JSON) and **conversational** (free-text) intake; free-text SHALL be normalised into the same DataMap schema (via the reasoning engine where needed).

### Compliance Analysis

**FR-v2-05** — The system SHALL identify which GDPR articles, BDSG sections, and EDPB guidelines are relevant to the described system.

**FR-v2-06** — The system SHALL classify each assessed aspect of the system as one of: **compliant**, **at-risk**, **non-compliant**, or **insufficient-information**.

**FR-v2-07** — The system SHALL provide specific remediation guidance for each at-risk or non-compliant finding, including technical implementation steps where applicable.

**FR-v2-08** — When the system description involves AI/ML processing of personal data, the system SHALL cross-reference EU AI Act requirements relevant to data protection (GDPR-adjacent scope only; not full AI Act product compliance).

### Document Generation

**FR-v2-09** — The system SHALL generate a draft DPIA document following EDPB-oriented structure (template + grounded content).

**FR-v2-10** — The system SHALL generate a pre-filled RoPA template derived from the DataMap.

**FR-v2-11** — The system SHALL generate a technical requirements checklist (encryption, access controls, breach notification, DSAR handling, and related controls).

**FR-v2-12** — The system SHALL generate consent-flow recommendations specifying what needs explicit consent versus legitimate interest (and gaps where basis is unclear).

**FR-v2-13** — The system SHALL generate a data retention policy draft with proposed retention periods per data category.

**FR-v2-14** — All generated documents SHALL be persisted and exposed as **markdown** outputs (files and/or API body fields).

### API

**FR-v2-15** — The system SHALL expose REST API endpoints for both **violation analysis** (v1 mode) and **compliance assessment** (v2 mode), in addition to the CLI.

**FR-v2-16** — The API SHALL support **asynchronous** processing for long-running compliance assessments (accept job, poll or fetch by id).

**FR-v2-17** — The API SHALL return structured JSON responses whose findings and generated text include **citations** to specific GDPR articles (and related sources), consistent with grounding rules.

### Persistence

**FR-v2-18** — The system SHALL store user projects and generated documents in **SQLite**.

**FR-v2-19** — The system SHALL support **multiple projects** per user (local user identity).

**FR-v2-20** — The system SHALL allow re-running analysis on a **modified** system description and **comparing** results to a prior run for the same project (at minimum: retrieve prior analysis records side-by-side).