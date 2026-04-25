#!/usr/bin/env python3
"""Gold-set evaluation harness (live pipeline; incurs API usage)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from gdpr_ai.config import settings
from gdpr_ai.evaluation import (
    estimate_eval_run_cost_eur,
    load_gold_scenarios,
    scenario_metrics,
    load_indexed_article_keys,
)
from gdpr_ai.pipeline import run_pipeline

console = Console()
ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "gold" / "test_scenarios.yaml"
OUT_PATH = ROOT / "logs" / "eval_results.json"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run gold scenarios against the full pipeline.")
    p.add_argument(
        "--scenarios",
        type=str,
        default="",
        help="Comma-separated scenario ids (default: all), e.g. SC-001,SC-002",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive cost confirmation prompt.",
    )
    return p.parse_args()


def _filter_rows(rows: list[dict], wanted: set[str]) -> list[dict]:
    if not wanted:
        return rows
    return [r for r in rows if str(r.get("id", "")) in wanted]


async def _eval_rows(rows: list[dict], kb_keys: set[str]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        sid = row["id"]
        console.print(f"Evaluating {sid} …")
        report = await run_pipeline(str(row["scenario"]))
        m = scenario_metrics(list(row.get("expected_articles", [])), report.violations, kb_keys)
        out.append(
            {
                "id": sid,
                "title": row.get("title", ""),
                "difficulty": row.get("difficulty", ""),
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "hallucinations": m["hallucinations"],
                "expected_keys": m["expected_keys"],
                "actual_keys": m["actual_keys"],
                "violations_count": len(report.violations),
            }
        )
    return out


async def _amain() -> int:
    args = _parse_args()
    if not settings.anthropic_api_key:
        console.print("[red]ANTHROPIC_API_KEY missing — cannot run eval.[/red]")
        return 2

    rows = load_gold_scenarios(GOLD_PATH)
    wanted = {s.strip() for s in args.scenarios.split(",") if s.strip()}
    rows = _filter_rows(rows, wanted)
    if not rows:
        console.print("[red]No scenarios matched the filter.[/red]")
        return 2

    est = estimate_eval_run_cost_eur(len(rows))
    usd = est * 1.08
    console.print(
        f"[bold]Estimated cost (order of magnitude):[/bold] €{est:.2f} (~${usd:.2f}). "
        f"{len(rows)} scenario(s), assuming ~4 reasoning-class calls each."
    )
    if not args.yes:
        console.print("Press Enter to continue, or Ctrl+C to abort.")
        input()

    kb_keys = load_indexed_article_keys()
    if not kb_keys:
        console.print("[yellow]Warning: empty Chroma index — hallucination counts may be unreliable.[/yellow]")

    per = await _eval_rows(rows, kb_keys)

    precs = [p["precision"] for p in per]
    recs = [p["recall"] for p in per]
    f1s = [p["f1"] for p in per]
    agg_prec = sum(precs) / len(precs)
    agg_rec = sum(recs) / len(recs)
    agg_f1 = sum(f1s) / len(f1s)
    total_hallu = sum(int(p["hallucinations"]) for p in per)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(tz=UTC).isoformat()
    OUT_PATH.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "scenario_count": len(per),
                "aggregate": {
                    "precision": agg_prec,
                    "recall": agg_rec,
                    "f1": agg_f1,
                    "hallucinations": total_hallu,
                },
                "per_scenario": per,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    table = Table(
        "ID",
        "Title",
        "Precision",
        "Recall",
        "F1",
        "Hallucinated",
    )
    for p in sorted(per, key=lambda x: x["id"]):
        table.add_row(
            p["id"],
            (p.get("title") or "")[:36],
            f"{p['precision']:.2f}",
            f"{p['recall']:.2f}",
            f"{p['f1']:.2f}",
            str(p["hallucinations"]),
        )
    table.add_row(
        "AGGREGATE",
        "",
        f"{agg_prec:.2f}",
        f"{agg_rec:.2f}",
        f"{agg_f1:.2f}",
        str(total_hallu),
    )
    console.print(table)
    console.print(f"Wrote {OUT_PATH}")

    if agg_prec < 0.8 or agg_rec < 0.7 or total_hallu > 0:
        console.print("[red]Threshold breach: need precision ≥0.8, recall ≥0.7, zero hallucinations.[/red]")
        return 1
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
