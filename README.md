# GDPR Violation Analyzer (gdpr-ai)

**gdpr-ai** turns short natural-language privacy scenarios into a **grounded** list of likely GDPR-related breaches: every cited article must be supported by retrieved knowledge-base chunks, not invented.

## What it does

The tool is aimed at **German-market** contexts: EU GDPR plus English translations of BDSG and TTDSG, and EDPB-style guidance where indexed. You describe a situation in English; the pipeline extracts facts, classifies legal topics, retrieves relevant sources from a local vector database, and produces a structured report with confidence scores and source URLs.

It does **not** provide legal advice; it assists analysis and documentation.

## Quick demo

```bash
uv run gdpr-check analyze "A company emails marketing without consent."
```

Typical output includes a severity assessment, a table of articles with confidence and source links, and optional “not grounded” notes when something seems relevant but no chunk supported it. See [`docs/sample-output.md`](docs/sample-output.md) for a trimmed example.

## Architecture

High-level flow (extract → classify → retrieve → reason → validate) and the knowledge-base build path are in [`docs/architecture.md`](docs/architecture.md).

## Getting started

**Prerequisites:** Python 3.11+, [uv](https://github.com/astral-sh/uv), and an API key for your LLM provider (set in `.env`).

1. **Clone and install**

   ```bash
   git clone <repository-url>
   cd gdpr-ai
   uv sync
   ```

2. **Configure environment**

   Create `.env` in the project root (see `src/gdpr_ai/config.py` for variable names). At minimum set the API key and optional paths (`CHROMA_PATH`, `LOG_DB_PATH`, etc.).

3. **Build the knowledge base** (one-time; no API calls in scrapers)

   ```bash
   uv run python scripts/scrape_gdpr.py
   uv run python scripts/scrape_bdsg.py
   uv run python scripts/scrape_ttdsg.py
   # … other scrapers as needed
   uv run python scripts/translate_sources.py
   uv run python scripts/chunk_and_embed.py
   ```

4. **Smoke-test retrieval** (optional)

   ```bash
   uv run python scripts/verify_retrieval.py
   ```

5. **Run an analysis**

   ```bash
   uv run gdpr-check analyze "Your scenario here."
   ```

**Observability**

- `uv run gdpr-check stats` — aggregates from the SQLite query log (`LOG_DB_PATH`, default `logs/gdpr_ai.db`).
- `uv run gdpr-check history --last 10` — recent runs; `gdpr-check history --id <uuid>` for detail.
- `uv run gdpr-check feedback --id <uuid> --rating up|down` — store quick feedback.

A motivated developer can complete steps 1–5 in well under 30 minutes once raw data and embeddings are already built; a cold build depends on network speed and translation throughput.

## Knowledge base sources

| Source | How it is used | License / terms |
|--------|----------------|-------------------|
| EU GDPR (consolidated) | Articles + recitals, chunked and embedded | EU law (public) |
| gdpr-info.eu mirror | Fallback HTML when EUR-Lex blocks automated fetches | Unofficial consolidation; check site terms |
| BDSG / TTDSG (gesetze-im-internet.de) | Scraped, translated to English at index time | German public law |
| EDPB guidelines (as scraped) | Chunked guidance | EDPB reuse policy |
| Enforcement / secondary sources | As added to `data/raw` per project rules | Per-file attribution in chunk metadata |

Every chunk carries `source`, `source_url`, `license`, and related metadata for traceability.

## How it works (four stages + validation)

1. **Extract** — Structured entities (who, what data, which processing, jurisdiction).
2. **Classify** — Topic tags (consent, transfers, employment, etc.) to steer retrieval.
3. **Retrieve** — Dense + BM25 hybrid search over ChromaDB (sentence-transformer embeddings).
4. **Reason** — Draft JSON report from retrieved context only.
5. **Validate** — Second pass removes or corrects citations that are not provable from retrieved chunks.

## Evaluation

- **Gold set:** `gold/test_scenarios.yaml` (30 hand-written scenarios).
- **Harness:** `uv run python tests/run_eval.py` (live API calls; use `--scenarios SC-001,SC-002` for a subset, `--yes` to skip the cost prompt).
- **Reported metrics:** See [`docs/eval-results.md`](docs/eval-results.md) (update after each formal eval).

## Cost

Rough order of magnitude (depends on provider pricing and scenario length):

- **Single analysis:** on the order of **€0.02–€0.08** for a typical scenario with the default models in `config`.
- **Full gold eval (30 scenarios):** use the cost line printed by `tests/run_eval.py` before confirming.

## Limitations

- **Not legal advice** — Output is informational; a qualified professional must interpret it.
- **English runtime** — User-facing text is English; German sources are translated at index time.
- **Indexed law only** — If an article or statute is not in the database, the tool will not invent it; you may see “retrieval gap” notes instead.
- **ePrivacy** — Cookie-only scenarios may be incomplete unless TTDSG / guidance chunks cover the fact pattern (see gold scenario SC-018).

## License

This project is released under the **MIT License** — see [`LICENSE`](LICENSE).

## Attribution

Retain all `source`, `source_url`, and `license` fields when exporting or redistributing chunks. Third-party datasets (e.g. CC BY-NC-SA material such as GDPRhub, if used) must keep their original attribution and licence constraints.
