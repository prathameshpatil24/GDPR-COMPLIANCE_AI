# V4 — Milestones

Ordered delivery plan for [v4-overview.md](v4-overview.md). Milestones are **sequential in priority**; parallel work is allowed where dependencies permit.

---

## Milestone 0: Near-100% Accuracy Architecture

**Outcome:** Primary retrieval is **deterministic** (article map + cross-reference graph + full-text store); hybrid vector search remains **fallback**; outputs gain **verification** and **confidence** signalling.

| Sub-milestone | Deliverable |
|---------------|-------------|
| **0a** | **GDPR Article Map** — `data/article_map.yaml` (hand-curated topic → article/recital/guidance mapping, ~200–300 rules) |
| **0b** | **Cross-Reference Graph** — `src/gdpr_ai/retrieval/cross_ref_graph.py`: parse and build directed graph of GDPR internal references (plus linked national refs as available) |
| **0c** | **Full-Text Article Store** — `data/articles/` and/or SQLite: complete text per article/recital/key sections (BDSG/TTDSG as scoped) |
| **0d** | **Pipeline integration** — wire Layers 1–3 into retrieval; **merge/dedupe** with semantic fallback |
| **0e** | **Gold baseline run** — capture “before” metrics on unified gold set |
| **0f** | **Verification layer** — `src/gdpr_ai/reasoning/verifier.py` + completeness checklist prompt |
| **0g** | **Confidence scoring** — Pydantic / output schema: `source_article`, `confidence` per claim, overall score |
| **0h** | **Gold final run** — “after” metrics and improvement delta |
| **0i** | **Documentation** — README accuracy comparison; architecture diagrams updated (see [architecture.md](architecture.md), [v4-overview.md](v4-overview.md)) |

**Design detail:** [v4-overview.md](v4-overview.md) (Feature 1), [adr/008-deterministic-retrieval-primary.md](adr/008-deterministic-retrieval-primary.md)

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
