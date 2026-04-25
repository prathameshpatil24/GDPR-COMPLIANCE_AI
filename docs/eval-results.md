# Evaluation results

**Last updated:** 2026-04-25

## How to refresh this document

Run the gold harness (charges the configured LLM API):

```bash
uv run python tests/run_eval.py --yes
```

Results are written to `logs/eval_results.json` (gitignored). Copy aggregate figures below after each formal eval run.

## Latest aggregate metrics

| Metric | Value |
|--------|-------|
| Precision | *Run eval to populate* |
| Recall | *Run eval to populate* |
| F1 | *Run eval to populate* |
| Total hallucinated citations | *Run eval to populate* |
| Scenarios | 30 |

## Worst-performing scenarios (by F1)

*Run `tests/run_eval.py` and list the bottom five scenario ids from `per_scenario` sorted by `f1`.*

1. —
2. —
3. —
4. —
5. —

## Known retrieval gaps

- **ePrivacy / cookies:** Scenario SC-018 flags a gap for the ePrivacy framework; the index focuses on GDPR + national implementations (e.g. TTDSG) and EDPB guidance, not the full ePrivacy Directive text.
- **Thin index:** If Chroma is empty or stale, run `scripts/scrape_*.py`, `scripts/translate_sources.py`, and `scripts/chunk_and_embed.py` before eval.

## Improvement notes

- Tighten retrieval (chunking, `TOP_K`, topic hints) when recall on medium/hard scenarios lags.
- Expand gold expected sets only when the knowledge base reliably contains supporting chunks.
- Re-run eval after any prompt or retriever change; keep this file in sync for release notes.
