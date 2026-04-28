# V4 — Retrieval Gap Tracker (Technical Design)

This document specifies the **Retrieval Gap Tracker**: SQLite schema, extraction rules, CLI/API surfaces, ingestion script behaviour, re-evaluation, and **gap rate** metrics. It implements **Feature 1** from [v4-overview.md](v4-overview.md).

---

## 1. Goals

1. **Log** every *actionable* ungrounded reference after violation and compliance runs.
2. **Aggregate** and **rank** gaps so operators know what to ingest first.
3. **Expose** the same data via **CLI** and **HTTP API** for automation and the **Stats / gaps UI**.
4. **Semi-automate ingestion** from known sources with **`--confirm`** safety and **dry run** by default.
5. **Measure** gap rate over time and optionally **re-evaluate** historical runs after KB updates.

---

## 2. Database schema

New table in the **application** SQLite database (alongside `analyses` / projects), not necessarily the query-log DB — final placement is an implementation choice; the foreign key below assumes the **`analyses`** table used for persisted runs.

```sql
CREATE TABLE retrieval_gaps (
    id TEXT PRIMARY KEY,
    article_reference TEXT NOT NULL,
    article_type TEXT NOT NULL,  -- 'gdpr_article', 'gdpr_recital', 'bdsg', 'ttdsg', 'edpb', 'other'
    analysis_id TEXT NOT NULL,
    mode TEXT NOT NULL,           -- 'violation_analysis', 'compliance_assessment'
    scenario_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,       -- set when chunk coverage is considered resolved for this row
    FOREIGN KEY (analysis_id) REFERENCES analyses(id)
);

CREATE INDEX idx_gaps_article ON retrieval_gaps (article_reference);
CREATE INDEX idx_gaps_resolved ON retrieval_gaps (resolved_at);
```

**Notes**

* **`article_type`** is **derived** at insert time from `article_reference` (regex / taxonomy) to drive `ingest_gaps.py` source selection.
* **`resolved_at`** is set when ingestion (or manual KB fix) is recorded; **aggregation** treats unresolved rows as active gaps.
* **Deduplication:** before insert, if **`(article_reference, analysis_id)`** already exists for the same logical gap event, **skip** (or use upsert policy documented at implementation time).

---

## 3. Extraction logic

### 3.1 Violation mode

* Parse the **`unsupported_notes`** list (and any sibling fields the pipeline uses for “retrieval gap” messaging).
* Extract **article references** using patterns consistent with the rest of the product, e.g.:
  * `Art. X` / `Article X`
  * `Recital X`
  * `§ X BDSG`
  * `EDPB Guideline X` / guideline ids
* Normalise to a canonical **`article_reference`** string for aggregation (trim, consistent spacing).

### 3.2 Compliance mode

* Filter findings where **`status == 'insufficient_info'`**.
* Take **`relevant_articles`** (array of strings); each entry becomes one candidate gap row **if** it is attributed to insufficient grounding (implementation may require an extra flag from the LLM schema — document when added).

### 3.3 Insert rules

* One row per **(analysis_id, article_reference)** per extraction pass, or finer granularity if the same article appears in multiple notes — **product decision**: prefer **dedupe per analysis per reference**.
* **`scenario_text`**: store a **redacted or truncated** system/scenario text for the example column (privacy: respect configurable max length).

---

## 4. CLI: `gdpr-check gaps`

**Behaviour**

* Query **`retrieval_gaps`** where **`resolved_at IS NULL`** (default), or include resolved with **`--all`** if needed.
* **Group by** `article_reference` (and optionally `article_type`).
* **Sort** by **frequency** descending, then **last seen** descending.

**Example output** (Rich table or plain text):

```text
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Article                ┃ Frequency ┃ Last seen   ┃ Status          ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ Art. 83 GDPR           │ 23        │ 2026-04-28  │ unresolved      │
│ Art. 5 GDPR            │ 18        │ 2026-04-28  │ unresolved      │
│ ePrivacy Directive     │ 12        │ 2026-04-27  │ unresolved      │
│ Art. 77 GDPR           │ 8         │ 2026-04-26  │ unresolved      │
│ Art. 82 GDPR           │ 5         │ 2026-04-28  │ unresolved      │
└────────────────────────┴───────────┴─────────────┴─────────────────┘
```

**Columns (minimum)**

* Article (reference)
* **Frequency** (row count)
* **Last seen** (`MAX(created_at)`)
* **Status** (`unresolved` / `resolved` when `--all`)

Optional: **example scenario** (first or most recent `scenario_text` snippet).

---

## 5. API: `GET /api/v1/gaps`

* Returns **JSON** with the same aggregated structure as the CLI (machine-readable).
* Suitable for the **frontend gaps dashboard** (bar chart + table).
* **Auth / rate limits** follow whatever v3+ API policy applies when this ships.

---

## 6. Ingestion script: `scripts/ingest_gaps.py`

### 6.1 Flags

* **`--top N`** — Process the **N** most frequent unresolved gaps (default **5**).
* **`--dry-run`** — Default: **no writes** to ChromaDB; print planned URLs and actions.
* **`--confirm`** — Required to **embed and insert** chunks into ChromaDB and to **mark** matching `retrieval_gaps` rows **`resolved_at = now`**.

### 6.2 Per-gap workflow

1. Resolve **source URL** from **`article_type`** + **`article_reference`** (gdpr-info.eu, gesetze-im-internet.de, EDPB, etc.).
2. **Scrape** (reuse existing scrapers where possible).
3. **Chunk** using existing chunking utilities.
4. **Embed** using the **current** embedding model.
5. **Upsert** into the appropriate **ChromaDB** collection with full **metadata** (source, URL, license).
6. On success for that reference, **`UPDATE retrieval_gaps SET resolved_at = CURRENT_TIMESTAMP WHERE article_reference = ? AND resolved_at IS NULL`** (or narrower scope if only partial coverage).

### 6.3 Output

* Summary: **articles processed**, **chunks added**, **rows marked resolved**, **failures** (with reasons).

---

## 7. Re-evaluation script

* **Input:** list of **`analysis_id`** values (or query “all analyses that had gap for Art. X before date D”).
* **Action:** re-run **retrieval + reason** stages (or full pipeline) using **current** Chroma state; compare **`unsupported_notes` / insufficient_info** before vs after.
* **Report:** tabular or markdown: *“Art. 83 — ungrounded in 23 analyses pre-ingestion; 0 post-ingestion”* (example).

---

## 8. Gap rate metric

**Definition**

\[
\text{gap rate} = \frac{\text{analyses with} \geq 1\ \text{unresolved gap event}}{\text{total analyses}} \times 100
\]

* **Implementation detail:** whether “gap” is derived from **`retrieval_gaps`** inserts vs on-the-fly flags in the result JSON should be **one source of truth** (prefer **`retrieval_gaps`** for consistency).

**Targets**

* Record **baseline** when the feature ships.
* **Product goal:** drive gap rate **below 10%** over time (tune as data arrives).

**Surfacing**

* Add to **`gdpr-check stats`** and **Stats API** as a **time series** or rolling window if volume allows.

---

## 9. Non-goals (v4 tracker scope)

* **LLM fine-tuning** — out of scope.
* **Automatic ingestion without confirmation** — out of scope for the first milestone.
* **Public multi-tenant gap sharing** — local / single-operator first.

---

## 10. References

* [v4-overview.md](v4-overview.md)
* [v4-roadmap.md](v4-roadmap.md)
* [ADR 005 — Strict Grounding](adr/005-strict-grounding.md)
