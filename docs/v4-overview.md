# V4 — Feature Overview

This document describes the **planned v4** product scope for GDPR AI: five major capabilities in **priority order**, with rationale, scope, dependencies, and high-level architecture notes. It is planning-only; implementation is tracked in [v4-roadmap.md](v4-roadmap.md). Detailed design for the **Retrieval Gap Tracker** is in [v4-gap-tracker.md](v4-gap-tracker.md).

---

## Priority summary

| Priority | Feature | One-line goal |
|----------|---------|---------------|
| **1** | **Near-100% Accuracy Architecture** | Deterministic article mapping, cross-reference graph, full-text assembly, verification layer, confidence scoring — similarity search as fallback only. |
| **2** | **Retrieval Gap Tracker** | Close the loop between “ungrounded” output and knowledge-base expansion — automatically learn from predictable gaps. |
| **3** | **Multilingual Retrieval** | German-first, bilingual query and retrieval while keeping English as the default response language (initially). |
| **4** | **Document Upload** | Run compliance analysis on uploaded privacy policies, DPAs, consent forms, and similar documents. |
| **5** | **Website Scanning** | Input a URL; scrape privacy/cookie signals; feed extracted text into the compliance pipeline. |

---

## Feature 1: Near-100% Accuracy Architecture (Priority 1)

### Rationale

The current retrieval pipeline (ChromaDB + BM25 hybrid search) relies on **semantic similarity** to find relevant legal content. Similarity is not the same as legal relevance — especially where overlapping terminology across articles produces false positives, and complex multi-faceted queries are compressed into single vectors that miss nuance. For a legal compliance tool, wrong answers are not only bad UX — they are a liability: a user who relies on the tool to decide whether a DPIA is required and gets “no” when “yes” is correct faces potential regulatory exposure (including fines up to €20M or 4% of global turnover under GDPR).

**The key insight:** GDPR is a **finite, known corpus** (roughly 99 articles, roughly 173 recitals, plus BDSG/TTDSG sections, EDPB guidelines). It is small enough that **deterministic mapping** can cover most queries; **embedding similarity** should be a **fallback** for edge cases, not the primary path. Target **near-100%** grounded accuracy; when the system is uncertain, it must **say so explicitly** rather than guess.

The architecture shifts from **probabilistic** retrieval (embedding similarity) to **deterministic retrieval** as the primary mechanism, with similarity search retained for novel or unmapped queries.

### Architecture — five layers

**Layer 1: Deterministic Article Mapping** (planned module: `src/gdpr_ai/retrieval/article_map.py`)

* A hand-curated YAML/JSON knowledge map that maps GDPR keywords, topics, and concepts to relevant articles, recitals, and guidance references.
* Examples (illustrative):
  * `consent` → Articles 6(1)(a), 7, 8, Recitals 32, 42, 43
  * `data_breach` → Articles 33, 34, Recitals 85, 86, 87, 88
  * `dpia` → Articles 35, 36, Recitals 89–93
  * `international_transfer` → Articles 44–49, Recitals 101–116
  * `right_to_erasure` → Article 17, Recitals 65, 66
  * `dpo` → Articles 37, 38, 39
  * `children` → Article 8, Recital 38
  * `profiling` → Article 22, Recitals 71, 72
  * `special_categories` → Article 9, Recitals 51–56
  * `security` → Article 32, Recital 83
* Estimated **200–300** mapping rules for full regulation coverage (manual curation from primary texts).
* **Properties:** Built from the regulation itself; the existing classify stage (topic taxonomy) feeds this map; **no LLM tokens** and negligible latency for this layer.
* **Product moat:** A hand-curated, exhaustive GDPR article map is hard to replicate and auditable end-to-end.

**Layer 2: Cross-Reference Graph** (planned module: `src/gdpr_ai/retrieval/cross_ref_graph.py`)

* A **directed graph** of internal cross-references in the GDPR text (and linked national law where parsed), e.g. “referred to in Article X”, “subject to Article Y”, “without prejudice to Article Z”.
* Data structure: NetworkX **or** a simple `dict[str, set[str]]` (NetworkX optional; useful for dev/visualisation, not required at runtime).
* When Layer 1 selects an article, the graph **expands** the candidate set to referenced articles (deterministic, zero tokens). Illustrative expansions:
  * Article 6 → Articles 5, 9, 13, 14, 21, 22 (among others, per actual graph)
  * Article 46 → Articles 44, 45, 47, 49
  * Article 35 → Articles 36, 9, 22
* Includes **BDSG/TTDSG** cross-references back to GDPR articles where encoded in source material.

**Layer 3: Full-Text Article Assembly** (planned module: `src/gdpr_ai/retrieval/article_store.py`)

* A **key-value store** of **complete** article (and selected recital/section) text, keyed by stable identifiers — **not** small chunks as the primary context unit for reasoning.
* GDPR articles are short enough that assembling many full articles still fits modern reasoning-model context windows.
* Storage shape: SQLite table and/or JSON files such as `{"article_6": "1. Processing shall be lawful only if...", ...}`.
* Scope: full GDPR articles, linked recitals, BDSG/TTDSG sections as needed, key EDPB guideline excerpts where included in the store.
* After Layers 1–2 (plus any fallback hits) yield an article set, this layer **assembles** full text into a **single context block** for the reasoning stage.

**Layer 4: Verification Layer** (planned module: `src/gdpr_ai/reasoning/verifier.py`)

* A **second LLM call** acting as a **legal completeness reviewer**.
* Inputs: original query, reasoning-stage output, and a **GDPR compliance checklist** (e.g. lawful basis, data-subject rights, controller obligations, cross-border processing, special categories, security, DPIA triggers, DPO duties, documentation).
* If the verifier finds gaps (e.g. “Answer covers consent but not withdrawal under Article 7(3)”), trigger **targeted retrieval** / expansion and **patch** the answer.
* **Cost:** one additional LLM call per analysis — acceptable for the accuracy target.

**Layer 5: Confidence Scoring** (schema enhancement)

* Every claim tagged with **`source_article`** (which article supports the claim) and **`confidence`**: `high` | `medium` | `low` | `uncertain`.
* Ungrounded claims → `uncertain` with explicit note that the aspect may need professional legal advice.
* **Rules (summary):**
  * **high** — Direct support from explicit article text in the retrieved/assembled set.
  * **medium** — Supported by recital or guidance, not sole explicit article phrasing.
  * **low** — Inferred from general principles without direct textual anchor.
  * **uncertain** — Cannot be grounded; system must not feign certainty.
* Output includes an **overall** confidence score for the analysis where product schema allows.

### Revised pipeline (replaces “retrieve-only” as primary path)

```
User Query
    ↓
[Extract] entities + topics (Claude Haiku) — EXISTING, no change
    ↓
[Classify] topic taxonomy mapping (Claude Haiku) — EXISTING, no change
    ↓
[Deterministic Map] topic → article set (Layer 1, rule engine; 0 tokens)
    ↓
[Graph Expand] follow cross-references (Layer 2; 0 tokens)
    ↓
[Semantic Fallback] ChromaDB + BM25 hybrid search — EXISTING stack, edge cases only
    ↓
[Merge & Deduplicate] combine article sets from all paths
    ↓
[Full-Text Assembly] load complete article text from article store (Layer 3)
    ↓
[Reason] Claude Sonnet over full articles — EXISTING prompt contract, richer context
    ↓
[Verify] completeness check (Layer 4, second LLM call)
    ↓
[Ground] every claim tagged with source article (Layer 5)
    ↓
[Confidence Score] flag uncertain claims (Layer 5)
    ↓
[Validate] hallucination guard — EXISTING, no change
    ↓
Final Output (citations, confidence markers, explicit uncertainty)
```

### What changes from the current pipeline

| Stage | Change |
|-------|--------|
| Extract / Classify | Unchanged |
| Retrieve | **Primary path** becomes deterministic map + graph expansion + full-text assembly; ChromaDB + BM25 **fallback** |
| Reason | Same LLM stage; context is **full articles** (and store content), not only chunks |
| Verify | **New** — completeness / checklist pass |
| Confidence | **New** — structured per-claim and overall scoring |
| Validate | Unchanged |

### Dependencies

* **No new required external libraries** for core behaviour — article map as YAML/JSON, graph in memory, article store as JSON/SQLite.
* **NetworkX** optional (visualisation / tooling).
* **ChromaDB** unchanged as **fallback** index.
* **API cost:** ~**one** extra LLM call per analysis (verification).

### Evaluation impact

* Re-run the **gold** scenario set before and after implementation; expect **article-level precision** to **rise materially** (planning target **95%+** on gold after full stack; exact numbers come from measurement).
* Add gold cases that historically **fail** pure similarity retrieval.
* Before/after metrics are intended for README and external communication.

### Build order (suggested milestones)

1. Deterministic article map (YAML, ~200–300 rules) — **manual curation**
2. Cross-reference graph — **parse** GDPR (semi-automated)
3. Full-text article store — **automated** from scraped corpus
4. Integrate Layers 1–3 into retrieval; keep ChromaDB as fallback
5. Gold test — measure **before/after** delta
6. Verification layer — new prompt template
7. Confidence fields on Pydantic outputs
8. Gold test again — final delta
9. README — publish accuracy comparison

See [v4-roadmap.md](v4-roadmap.md) **Milestone 0** for stepwise deliverables.

---

## Feature 2: Retrieval Gap Tracker (Priority 2)

### Rationale

The system already surfaces **retrieval gaps** in a structured way: violation mode emits **“not grounded (retrieval gap)”** style notes in `unsupported_notes`, and compliance mode can produce **`insufficient_info`** findings when the model cannot ground recommendations in retrieved chunks. Those gaps are **predictable and fixable** — the pipeline often identifies **which articles or references** are missing from the index.

An **automated feedback loop** that logs gaps, **aggregates and ranks** them, and **assists ingestion** (with human confirmation) will **continuously improve** citation quality and reduce spurious “gap” noise **without** relying on manual spreadsheet triage. This is **knowledge-base expansion**, not LLM fine-tuning.

**Interaction with deterministic mapping (v4):** The gap tracker operates **alongside** the article map. Gaps logged by the tracker inform **which topics or article references** still lack deterministic rules or store coverage; curators can **extend** `article_map` (and the article store) over time. That closes a **self-improving loop**: the map covers known topics → the tracker surfaces unknown or weakly covered topics → humans extend the map → **accuracy rises**.

### Scope

* **Gap logging** — After each analysis (violation and compliance), extract ungrounded article references from:
  * **Violation:** `unsupported_notes` (and related structured fields as defined at implementation time).
  * **Compliance:** findings where `status == insufficient_info`, using **`relevant_articles`** (and any other agreed fields).
  * Persist rows to a new **`retrieval_gaps`** table in SQLite: at minimum **`article_reference`**, **`source_scenario` / scenario text**, **`analysis_id`**, **`mode`**, **`timestamp`** (see [v4-gap-tracker.md](v4-gap-tracker.md) for full schema).

* **Gap aggregation** — New CLI command **`gdpr-check gaps`** that queries the table and returns a **ranked list** (e.g. by frequency). Output includes: article reference, how often it appeared as a gap, how often it was grounded in those rows (often **0** until resolved), **last seen** date, and an **example scenario** snippet.

* **Gap API** — **`GET /api/v1/gaps`** returning the same aggregated data for the **web UI**.

* **Frontend gaps dashboard** — A **new page or section** (e.g. under **Stats**) showing **top ungrounded articles** with a **bar chart**, so operators can see **what to ingest next**.

* **Semi-automated ingestion** — Script **`scripts/ingest_gaps.py`** that:
  * Takes the **top-N** gap articles (by frequency or priority).
  * Attempts to **scrape** from known sources (e.g. gdpr-info.eu for GDPR articles/recitals, gesetze-im-internet.de for BDSG/TTDSG, EDPB site for guidelines where URLs are stable).
  * Reuses existing **chunking** and **embedding** pipelines; writes to **ChromaDB**.
  * Requires **explicit user confirmation** before mutating the vector store (e.g. **`--confirm`**; default **dry run**).

* **Re-evaluation** — After ingestion, optionally **re-run** historical analyses that previously had gaps for those articles and verify **grounding improved**. Report e.g. *“Art. 83 — ungrounded in 23 analyses before ingestion; grounded after.”*

* **Gap reduction metrics** — Track **gap rate over time**: e.g. **(analyses with at least one gap) / (total analyses) × 100**. Surface a **trend** on the Stats dashboard alongside existing usage metrics.

### Architecture (high level)

* New SQLite table **`retrieval_gaps`** (and indexes) — see [v4-gap-tracker.md](v4-gap-tracker.md).
* **Extraction hooks** in existing **violation** and **compliance** pipelines **after** the analysis result is produced (and persisted), so **`analysis_id`** is available.
* **Ingestion** reuses **`scripts/`** scrapers, chunkers, and embedders; **no LLM retraining**.

### Dependencies

* Stable **article-reference parsing** (regex / normalisation) aligned with gap logging and `ingest_gaps.py` source resolution.
* **ChromaDB** collection strategy unchanged in principle; new chunks must preserve **attribution** metadata per project rules.
* **Alignment** with deterministic map curation (gap list drives map **priorities**).

---

## Feature 3: Multilingual Retrieval (Priority 3)

### Rationale

GDPR AI targets the **German market**, but **runtime** has been **English-only** while German legal sources (BDSG, TTDSG, Länder laws where indexed) are **translated once at index time**. **Native German retrieval** lets users **query in German** and retrieve **both German and English chunks**, improving fidelity for German-specific wording and reducing friction for local users.

### Scope

* **Bilingual indexing** — Store **both** German **original** and English **translation** (where applicable) per chunk, or equivalent dual-text representation, in the index.
* **Query language detection** — Auto-detect **German vs English** (and fallback behaviour for mixed input).
* **Cross-lingual retrieval** — A **German** query retrieves **German and English** chunks; scores are **merged** in a single ranked result set (design detail TBD).
* **Response language** — **English only** for **v4 initial** release (documented explicitly); German UI copy can evolve separately.
* **Frontend** — **Language indicator** near the analyze input (detected language).

### Dependencies

* A **multilingual embedding model** (e.g. **paraphrase-multilingual-MiniLM-L12-v2** or stronger successor) that places German and English in a **shared** vector space **without** breaking existing eval baselines — **re-evaluate** gold scenarios after migration.

---

## Feature 4: Document Upload (Priority 4)

### Rationale

Users often already have **privacy policies**, **DPAs**, **consent forms**, and **processing records**. Today the product only accepts **free-text** system descriptions. **Upload** shortens time-to-value and anchors assessment to **real** artefacts.

### Scope

* **Frontend** — **Drag-and-drop** (and file picker) on the Analyze experience, e.g. a **“Document review”** tab or mode.
* **Formats** — **PDF**, **DOCX**, **TXT** (minimum); others only if justified.
* **Backend** — **`POST /api/v1/analyze/document`** (multipart) accepting uploads.
* **Pipeline** — Extract text → run **compliance assessment** (or a document-specific variant) → return findings **grounded in** document content + KB.
* **Document types** — Policy templates: privacy policy (**Art. 13/14**), DPA (**Art. 28**), consent (**Art. 7**), cookie policy (**ePrivacy / TTDSG** themes).
* **Storage** — **Temporary** persistence for analysis; **delete after** configurable **retention**; no long-term document archive in v4 unless explicitly added.

### Dependencies

* **PDF** extraction (e.g. **pdfplumber** or **PyMuPDF**).
* **DOCX** extraction (**python-docx**).
* **Licensing** and **security** review for parsing untrusted files (size limits, malware surface).

---

## Feature 5: Website Scanning (Priority 5)

### Rationale

Many users want to **check a live site** without copying text manually. Scanning can locate **privacy policy** links, **cookie banners**, and **consent** UX and feed consolidated text into compliance assessment.

### Scope

* **Frontend** — **URL** input (e.g. **“Website scan”** tab).
* **Backend** — **`POST /api/v1/analyze/website`** with URL body.
* **Pipeline** — Fetch page(s) → discover **privacy policy** URL where possible → extract **cookie / consent** signals → compliance pipeline → structured findings.
* **Checks** — Policy completeness (**Art. 13/14**), cookie / consent (**ePrivacy / TTDSG**), **third-party** tracker surfacing where feasible.
* **Rate limiting** — e.g. **max 5 scans per hour** per key / session to limit abuse.

### Dependencies

* **HTTP** client + HTML parsing (**httpx** + **BeautifulSoup**), or **Playwright** where **JS-rendered** content is required (heavier ops).
* **Robots.txt** / **ToS** respect and legal review for automated access.

---

## Document index

| Document | Purpose |
|----------|---------|
| [v4-roadmap.md](v4-roadmap.md) | Milestones and delivery ordering |
| [v4-gap-tracker.md](v4-gap-tracker.md) | Schema, CLI, API, ingestion, metrics |
| [adr/008-deterministic-retrieval-primary.md](adr/008-deterministic-retrieval-primary.md) | ADR: deterministic primary retrieval, semantic fallback |
| [phase-0-overview/03-target-users.md](phase-0-overview/03-target-users.md) | User-facing v4 narrative |

---

## Summary

v4 prioritises a **near-100% accuracy architecture** (deterministic mapping, cross-reference expansion, full-text assembly, verification, confidence scoring) so outputs are fit for **high-stakes** compliance use, with **ChromaDB + BM25** as **fallback** only. Next: a **retrieval gap tracker** that **feeds** map and KB maintenance, then **multilingual retrieval**, **document upload**, and **website scanning**. Hosting, ToS, and commercial licensing remain aligned with earlier roadmap text but are **not** the focus of this overview.
