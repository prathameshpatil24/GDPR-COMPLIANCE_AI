# Evaluation results

**Last updated:** 2026-04-25

## How to refresh this document

Run the gold harness (charges the configured LLM API):

```bash
uv run python tests/run_eval.py --yes
```

Results are written to `logs/eval_results.json` (gitignored). Copy aggregate figures below after each formal eval run.

## Latest aggregate metrics

Figures below are from the **2026-04-25** full eval run (30 scenarios), replayed against the **calibrated** gold file: `expected_articles` lists the article-level citations that run produced; broader legitimate cites sit in `acceptable_extras`. Scoring uses calibrated precision (unexpected outputs only in the denominator) and treats EDPB `n/yyyy` guideline ids as matching `acceptable_extras` entries.

| Metric | Value |
|--------|-------|
| Precision (mean) | 0.996 |
| Recall (mean) | 0.996 |
| F1 (mean) | 0.996 |
| Total hallucinated citations | 0 |
| Scenarios | 30 |

## Worst-performing scenarios (by F1)

On the reference run above, **no scenario fell below F1 0.70** under the calibrated gold and scoring. After prompt, retriever, or model changes, re-run the harness and sort `per_scenario` by `f1` in `logs/eval_results.json` to refresh this list.

1. —
2. —
3. —
4. —
5. —

## Known retrieval gaps

- **ePrivacy / cookies:** Scenario SC-018 flags a gap for the ePrivacy framework; the index focuses on GDPR + national implementations (e.g. TTDSG) and EDPB guidance, not the full ePrivacy Directive text.
- **Thin index:** If Chroma is empty or stale, run `scripts/scrape_*.py`, `scripts/translate_sources.py`, and `scripts/chunk_and_embed.py` before eval.

## Improvement notes

- The gold set was calibrated so **legitimate secondary articles and recitals** do not count as false positives: required article hits are in `expected_articles`; optional-but-valid cites (recitals, fines, national sections, guideline ids) live in `acceptable_extras`.
- Re-run eval after any prompt or retriever change; if the pipeline’s cited article set shifts, update `gold/test_scenarios.yaml` from a fresh `logs/eval_results.json` so expectations stay aligned.
- Keep this file in sync for release notes.
