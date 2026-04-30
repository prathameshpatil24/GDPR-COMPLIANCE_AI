# GDPR AI

AI-powered GDPR compliance analysis tool. Describe a privacy scenario or your system architecture in plain English — get a grounded, structured report citing specific GDPR articles, recitals, and EDPB guidelines with confidence scores and source links.

Built with RAG (Retrieval-Augmented Generation) over the full GDPR text, BDSG, TTDSG, and EDPB guidance. Every cited article is backed by retrieved knowledge-base chunks, not hallucinated.

> **Not legal advice.** Output is informational only. A qualified professional must interpret the results.

---

## Features

### Violation Analysis
Describe a scenario; get a severity rating, violated articles with confidence scores, actionable recommendations, and honest "retrieval gap" notes when something is relevant but ungrounded.

```bash
uv run gdpr-check analyze "A company sends marketing emails to users without getting consent"
```

### Compliance Assessment
Describe your system; get an auto-generated data map, risk level, and findings across 10+ compliance areas (legal basis, transparency, international transfers, processor agreements, security, retention, DPIA, data subject rights, and more).

```bash
uv run gdpr-check assess "SaaS collecting emails via web form, sends newsletters via Mailchimp, data in PostgreSQL on AWS eu-central-1"
```

### REST API
Same analysis engines exposed via FastAPI:

```bash
uv run gdpr-check serve
# POST /api/v1/analyze/violation
# POST /api/v1/analyze/compliance
# GET  /health
```

### Observability
```bash
uv run gdpr-check stats      # aggregated cost, latency, token usage
uv run gdpr-check history     # recent analysis runs
```

---

## Example Outputs

**Simple scenario** — marketing emails without consent:
- Severity: **HIGH**
- Articles flagged: Art. 6 (0.95), Art. 7 (0.93), Art. 21 (0.97), Art. 13 (0.80), Art. 14 (0.72), Art. 17 (0.75)
- Includes 10 actionable recommendations and retrieval gap notes for ePrivacy Directive, Art. 83 fines, Art. 5 principles

**Complex scenario** — healthcare CRM with genetic data, children's data, AI/automated decisions, 5 third-party processors, multi-region AWS, transfers to US/UK/Japan:
- Severity: **CRITICAL**
- 15 findings across: special category data, consent validity, automated decision-making, DPIA, transparency, retention, international transfers (split by US processors vs research universities), processor contracts, security, data protection by design, children's data, data subject rights, breach notification readiness, ROPA

**Minimal scenario** — offline calculator app with no data collection:
- Severity: **LOW**
- All areas compliant, with a scope verification note to audit for inadvertent SDK telemetry

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| LLM | Anthropic Claude API (Claude 4 Sonnet) |
| Vector store | ChromaDB with sentence-transformers embeddings |
| Retrieval | Dense + BM25 hybrid search |
| API | FastAPI |
| CLI | Typer + Rich |
| Database | SQLite (analysis persistence + query telemetry) |
| Language | Python 3.11+ |

---

## Architecture

**Five-stage pipeline** with validation:

1. **Extract** — Structured entities from natural language (actors, data types, processing activities, jurisdiction, special categories)
2. **Classify** — Topic tags (consent, transfers, security, children, AI/automated decisions, etc.) to steer retrieval
3. **Retrieve** — Hybrid dense + BM25 search over ChromaDB; topic-aware routing pulls from main GDPR collection plus specialized v2 collections (DPIA, RoPA, TOM, consent guidance, EDPB guidelines)
4. **Reason** — LLM generates structured JSON report grounded only in retrieved chunks
5. **Validate** — Second pass removes or corrects citations not provable from retrieved context

### Compliance mode (v2) adds:

1. **Intake** — Free text or JSON DataMap → normalized DataMap (LLM parses prose into structured data categories, flows, third parties, storage)
2. **Map** — Hybrid retrieval across main + v2 collections based on classified topics and data map signals
3. **Assess** — LLM produces ComplianceAssessment with findings per compliance area, relevant articles, remediation, and technical guidance
4. **API / Persistence** — FastAPI routes; projects, analyses, and documents stored in SQLite

---

## Getting Started

**Prerequisites:** Python 3.11+, [uv](https://github.com/astral-sh/uv), Anthropic API key

1. **Clone and install**
   ```bash
   git clone https://github.com/prathameshpatil7/gdpr-ai.git
   cd gdpr-ai
   uv sync
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Set ANTHROPIC_API_KEY and optional paths (CHROMA_PATH, LOG_DB_PATH, etc.)
   ```

3. **Build the knowledge base** (one-time, no API calls)
   ```bash
   uv run python scripts/scrape_gdpr.py
   uv run python scripts/scrape_bdsg.py
   uv run python scripts/scrape_ttdsg.py
   uv run python scripts/translate_sources.py
   uv run python scripts/chunk_and_embed.py
   ```

4. **Run an analysis**
   ```bash
   uv run gdpr-check analyze "Your scenario here"
   uv run gdpr-check assess "Your system description here"
   ```

---

## Frontend (v3)

The web UI provides a visual interface for both analysis modes.

### Running locally

Start the backend and frontend:

```bash
# Terminal 1: Backend
uv run gdpr-check serve

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

### Pages

- **Analyze** — run violation analysis or compliance assessment with live results
- **History** — browse, filter, and search past analyses
- **Dashboard** — usage stats, cost tracking, severity distribution charts
- **Settings** — theme toggle, connection status, about info

---

## API Usage

Start the server:
```bash
uv run gdpr-check serve
```

**Violation analysis:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/violation \
  -H "Content-Type: application/json" \
  -d '{"scenario": "A German hospital accidentally emails patient test results to the wrong patient."}'
```

**Compliance assessment:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/compliance \
  -H "Content-Type: application/json" \
  -d '{"system_description": "Mobile fitness app tracking location and heart rate, stored on AWS eu-central-1, anonymized analytics shared with US research partner."}'
```

---

## Evaluation Framework

Gold-standard test scenarios with automated scoring:

```bash
uv run python tests/run_eval.py --scenarios SC-V-001,SC-C-001
uv run python tests/run_eval.py --mode violation_analysis --dry-run
```

**Metrics:**
- **Article recall** — % of expected GDPR articles found
- **Article precision** — % of flagged articles that are expected (recitals excluded from penalty)
- **Finding coverage** — % of expected compliance areas addressed
- **Law recall** — % of expected legal instruments cited

**Filters:** `--mode`, `--scenarios`, `--difficulty`, `--category`

**Regression detection:** `--check-baseline` warns on >5pp drops, exits 1 on >10pp drops.

**Gold set:** 30 violation scenarios (`SC-V-*`) + 20 compliance scenarios (`SC-C-*`) in `gold/test_scenarios.yaml`

---

## Knowledge Base Sources

| Source | Usage | License |
|--------|-------|---------|
| EU GDPR (consolidated) | Articles + recitals, chunked and embedded | EU law (public) |
| BDSG / TTDSG | Scraped from gesetze-im-internet.de, translated at index time | German public law |
| EDPB guidelines | Chunked guidance (breach notification, transfers, consent) | EDPB reuse policy |
| gdpr-info.eu | Fallback HTML source | Unofficial consolidation |

Every chunk carries `source`, `source_url`, and `license` metadata for traceability.

---

## Cost

| Operation | Approximate cost |
|-----------|-----------------|
| Single violation analysis | €0.02–0.08 |
| Single compliance assessment | €0.08–0.17 |
| Complex compliance (healthcare CRM) | ~€0.17 |
| Offline calculator (minimal) | ~€0.03 |

---

## Limitations

- **Not legal advice** — requires professional interpretation
- **English runtime** — German legal sources translated at index time
- **Indexed law only** — if an article isn't in the knowledge base, you'll see "retrieval gap" notes instead of hallucinated citations
- **ePrivacy gaps** — cookie/electronic marketing scenarios may be incomplete unless TTDSG chunks cover the pattern
- **Latency** — full runs are typically **20–190s** depending on mode and complexity (multi-stage LLM pipeline)

## Retrieval (v4 accuracy path)

Violation analysis now defaults to **deterministic article mapping** (`data/gdpr_article_map.yaml`) plus **cross-reference expansion** (`data/gdpr_cross_references.yaml`), then a **single assembled full-text context chunk** when `data/gdpr_articles_fulltext.yaml` is populated (otherwise text is filled from `data/raw/gdpr_articles.json` after scraping). Hybrid Chroma + BM25 still runs as a **fallback** merge. Set `DETERMINISTIC_RETRIEVAL=false` to use legacy semantic-only retrieval. After scraping, run `uv run python scripts/export_gdpr_fulltext_yaml.py` to build the YAML article store. Eval baselines: run `uv run python tests/run_eval.py` before/after and compare with `uv run python tests/compare_eval.py`.

### Retrieval accuracy

Evaluated on 5 core scenarios (3 violation analysis, 2 compliance assessment). SC-C-002 previously errored during `DataMap` validation when the LLM returned `crosses_border: null` on a data flow (see `DataFlow` model); null is now coerced to `false` so intake completes. Figures below are **order-of-magnitude targets** after that fix; regenerate `gold/baseline_v3_semantic.json` with `DETERMINISTIC_RETRIEVAL=false` for exact percentages.

| Metric | v3 (semantic retrieval) |
|--------|-------------------------|
| Article recall | ~95% |
| Article precision | ~96% |
| Finding coverage | ~100% |
| Pass / warn / fail | 5 / 0 / 0 |
| Errors | 0 |
| Avg cost per run | ~€0.88 |

Hand-maintained regression targets also live in `gold/baseline.json`. Reproduce the v3 baseline (semantic retrieval, 5 default scenarios):

```bash
DETERMINISTIC_RETRIEVAL=false uv run python tests/run_eval.py --output gold/baseline_v3_semantic.json --yes
```

Default eval (5 core scenarios, ~€0.40):

```bash
uv run python tests/run_eval.py --output gold/eval_results.json --yes
```

Full suite (all 50 scenarios, ~€3.84):

```bash
uv run python tests/run_eval.py --all --output gold/eval_full.json --yes
```

Compare two JSON reports (overall + per-scenario deltas):

```bash
uv run python tests/compare_eval.py gold/baseline_v3_semantic.json gold/eval_v4_accuracy.json
```

Deterministic (v4) run for side-by-side comparison:

```bash
DETERMINISTIC_RETRIEVAL=true VERIFICATION_ENABLED=true uv run python tests/run_eval.py --output gold/eval_v4_accuracy.json --yes
```

After each eval run, read `violation_analysis_summary` and `compliance_assessment_summary` in the output JSON for mode-specific averages.

---

## Product roadmap

| Release | Focus |
|---------|--------|
| **v1** | Violation analysis CLI |
| **v2** | Compliance assessment, local REST API, eval framework, SQLite persistence *(current)* |
| **v3** | Web UI (React dashboard), auth, rate limits, feedback, PDF export |
| **v4** | Near-100% accuracy architecture (deterministic retrieval, verification, confidence), gap tracker, German-first multilingual retrieval, document upload, website scanning, ToS/privacy, optional commercial path |

Details: [docs/README.md](docs/README.md) and [docs/phase-0-overview/03-target-users.md](docs/phase-0-overview/03-target-users.md).

---

## License

Copyright © 2026 Prathamesh Patil. All rights reserved.

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

You may view, fork, and modify the code for personal and educational purposes. However:

- **Any use of this software in a networked service (SaaS, API, web app)** requires you to release your complete source code under AGPL-3.0
- **Commercial use** without open-sourcing your derivative work is prohibited under this license
- **For commercial licensing** (closed-source use, enterprise deployment, white-labeling): contact prathamesh.p9594@gmail.com

See [LICENSE](LICENSE) for the full license text.

## Attribution

Retain all `source`, `source_url`, and `license` fields when exporting or redistributing chunks. Third-party datasets with specific license constraints (e.g., CC BY-NC-SA) must keep their original attribution.