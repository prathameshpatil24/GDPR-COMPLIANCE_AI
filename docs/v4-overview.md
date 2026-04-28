# V4 — Feature Overview

This document describes the **planned v4** product scope for GDPR AI: four major capabilities in **priority order**, with rationale, scope, dependencies, and high-level architecture notes. It is planning-only; implementation is tracked in [v4-roadmap.md](v4-roadmap.md). Detailed design for the **Retrieval Gap Tracker** is in [v4-gap-tracker.md](v4-gap-tracker.md).

---

## Priority summary

| Priority | Feature | One-line goal |
|----------|---------|----------------|
| **1** | **Retrieval Gap Tracker** | Close the loop between “ungrounded” output and knowledge-base expansion — automatically learn from predictable gaps. |
| **2** | **Multilingual Retrieval** | German-first, bilingual query and retrieval while keeping English as the default response language (initially). |
| **3** | **Document Upload** | Run compliance analysis on uploaded privacy policies, DPAs, consent forms, and similar documents. |
| **4** | **Website Scanning** | Input a URL; scrape privacy/cookie signals; feed extracted text into the compliance pipeline. |

---

## Feature 1: Retrieval Gap Tracker (Priority 1)

### Rationale

The system already surfaces **retrieval gaps** in a structured way: violation mode emits **“not grounded (retrieval gap)”** style notes in `unsupported_notes`, and compliance mode can produce **`insufficient_info`** findings when the model cannot ground recommendations in retrieved chunks. Those gaps are **predictable and fixable** — the pipeline often identifies **which articles or references** are missing from the index.

An **automated feedback loop** that logs gaps, **aggregates and ranks** them, and **assists ingestion** (with human confirmation) will **continuously improve** citation quality and reduce spurious “gap” noise **without** relying on manual spreadsheet triage. This is **knowledge-base expansion**, not LLM fine-tuning.

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

---

## Feature 2: Multilingual Retrieval (Priority 2)

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

## Feature 3: Document Upload (Priority 3)

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

## Feature 4: Website Scanning (Priority 4)

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
| [phase-0-overview/03-target-users.md](phase-0-overview/03-target-users.md) | User-facing v4 narrative |

---

## Summary

v4 prioritises a **closed-loop retrieval gap tracker** to make grounding **measurable and improvable**, then **multilingual retrieval** for the German market, then **document** and **URL** inputs. Hosting, ToS, and commercial licensing remain aligned with earlier roadmap text but are **not** the focus of this overview.
