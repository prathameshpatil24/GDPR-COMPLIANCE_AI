# V4 — Milestones

Ordered delivery plan for [v4-overview.md](v4-overview.md). Milestones are **sequential in priority**; parallel work is allowed where dependencies permit.

---

## Milestone 1: Retrieval Gap Tracker

**Outcome:** Gaps are logged, inspectable, ingestible, and visible in the product metrics story.

| # | Deliverable |
|---|-------------|
| 1 | **Database schema** and migration for `retrieval_gaps` |
| 2 | **Gap extraction** hooks in **violation** and **compliance** pipelines (post-result) |
| 3 | **CLI:** `gdpr-check gaps` (aggregated, ranked output) |
| 4 | **API:** `GET /api/v1/gaps` |
| 5 | **Frontend:** gaps section in **Stats** dashboard (table + bar chart) |
| 6 | **Script:** `scripts/ingest_gaps.py` (`--top N`, dry run default, `--confirm`) |
| 7 | **Re-evaluation** script (before/after grounding report) |
| 8 | **Gap rate** metric in stats output and API |

**Design detail:** [v4-gap-tracker.md](v4-gap-tracker.md)

---

## Milestone 2: Multilingual Retrieval

**Outcome:** German queries retrieve German + English chunks; responses remain English (initially); eval shows no unacceptable regression.

| # | Deliverable |
|---|-------------|
| 1 | **Multilingual embedding model** evaluation and selection |
| 2 | **Bilingual chunk indexing** pipeline (DE + EN in index) |
| 3 | **Query language detection** |
| 4 | **Cross-lingual retrieval** (merge scoring) |
| 5 | **Frontend** language indicator on analyze input |
| 6 | **Evaluation:** re-run gold scenarios; document deltas |

---

## Milestone 3: Document Upload

**Outcome:** Users upload PDF/DOCX/TXT; backend extracts text; compliance-style assessment runs with retention policy.

| # | Deliverable |
|---|-------------|
| 1 | **PDF** and **DOCX** text extraction (libraries integrated) |
| 2 | **Backend:** `POST /api/v1/analyze/document` |
| 3 | **Document-type-aware** prompts / checks (Art. 13/14, 28, 7, ePrivacy themes) |
| 4 | **Frontend:** drag-and-drop upload on Analyze (**Document review** mode/tab) |
| 5 | **Temporary storage** + configurable **retention** and deletion |

---

## Milestone 4: Website Scanning

**Outcome:** URL in; scraped signals out; rate-limited; compliance findings returned.

| # | Deliverable |
|---|-------------|
| 1 | **Scraping** pipeline (static + JS-heavy path if needed) |
| 2 | **Privacy policy** link detection |
| 3 | **Cookie banner / consent** extraction heuristics |
| 4 | **Backend:** `POST /api/v1/analyze/website` |
| 5 | **Frontend:** URL input (**Website scan** tab) |
| 6 | **Rate limiting** (e.g. 5 scans / hour per operator) |

---

## Cross-cutting

* **Documentation** and **ADRs** updated when schema or retrieval semantics change.
* **Attribution** and **licence** metadata preserved for all new chunks (project non-negotiable).

---

## See also

* [v4-overview.md](v4-overview.md)
* [v4-gap-tracker.md](v4-gap-tracker.md)
* [README.md](README.md) (version roadmap table)
