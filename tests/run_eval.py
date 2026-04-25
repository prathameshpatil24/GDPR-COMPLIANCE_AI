#!/usr/bin/env python3
"""Gold-set evaluation harness: live pipeline (API) or ``--replay`` (no API)."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from gdpr_ai.config import settings
from gdpr_ai.evaluation import (
    estimate_eval_run_cost_eur,
    load_gold_scenarios,
    load_indexed_article_keys,
    normalize_article_ref,
)
from gdpr_ai.pipeline import run_pipeline

console = Console()
ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "gold" / "test_scenarios.yaml"
OUT_PATH = ROOT / "logs" / "eval_results.json"
REPLAY_OUT_PATH = ROOT / "logs" / "eval_replay.json"


def _article_key(label: str) -> str:
    """Normalize a citation for scoring (EDPB ``n/yyyy`` ids, then GDPR helpers)."""
    s = (label or "").strip()
    m_edpb = re.search(r"\b(\d{1,2}/\d{4})\b", s)
    if m_edpb:
        return m_edpb.group(1)
    return normalize_article_ref(s)


def _calibrated_metrics_from_acts(
    expected: list[str],
    acceptable_extras: list[str],
    act: set[str],
) -> dict[str, Any]:
    """Precision/recall/F1 from normalized citation keys (no hallucination check)."""
    exp = {_article_key(x) for x in expected}
    acc = {_article_key(x) for x in acceptable_extras}
    act_n = {_article_key(str(k)) for k in act}
    correct = act_n & exp
    unexpected = act_n - exp - acc

    denom = len(correct) + len(unexpected)
    if denom == 0:
        precision = 1.0
    else:
        precision = len(correct) / denom

    if not exp:
        recall = 1.0
    else:
        recall = len(correct) / len(exp)

    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "hallucinations": 0,
        "expected_keys": sorted(exp),
        "actual_keys": sorted(act_n),
        "acceptable_keys": sorted(acc),
        "unexpected_keys": sorted(unexpected),
    }


def _calibrated_metrics(
    expected: list[str],
    acceptable_extras: list[str],
    violations: list[Any],
    kb_keys: set[str],
) -> dict[str, Any]:
    """Precision/recall/F1 with extras that count neither as TP nor as FP.

    Precision uses only unexpected citations (output minus expected minus acceptable)
    in the denominator so legitimate secondary hits are not penalised.
    """
    act = {_article_key(v.article_reference) for v in violations}
    out = _calibrated_metrics_from_acts(expected, acceptable_extras, act)
    exp = {_article_key(x) for x in expected}
    acc = {_article_key(x) for x in acceptable_extras}
    hallucinations = 0
    for v in violations:
        raw_cite = v.article_reference.strip()
        key = _article_key(raw_cite)
        if key in exp or key in acc:
            continue
        if raw_cite in kb_keys or raw_cite.lower() in kb_keys or key in kb_keys:
            continue
        hallucinations += 1
    out["hallucinations"] = hallucinations
    return out


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run gold scenarios against the full pipeline.")
    p.add_argument(
        "--scenarios",
        type=str,
        default="",
        help="Comma-separated scenario ids (default: all), e.g. SC-001,SC-002",
    )
    p.add_argument(
        "--replay",
        type=Path,
        default=None,
        metavar="PATH",
        help="Recompute metrics from a saved eval JSON plus current gold (no API calls).",
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
        acceptable = list(row.get("acceptable_extras") or [])
        m = _calibrated_metrics(
            list(row.get("expected_articles", [])),
            acceptable,
            report.violations,
            kb_keys,
        )
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
                "acceptable_keys": m["acceptable_keys"],
                "unexpected_keys": m["unexpected_keys"],
                "violations_count": len(report.violations),
            }
        )
    return out


def _run_replay(replay_path: Path, rows: list[dict]) -> int:
    """Score current gold against citation keys stored from an earlier eval run."""
    if not replay_path.is_file():
        console.print(f"[red]Replay file not found: {replay_path}[/red]")
        return 2
    data = json.loads(replay_path.read_text(encoding="utf-8"))
    by_id = {str(p["id"]): p for p in data.get("per_scenario", [])}
    per: list[dict] = []
    for row in rows:
        sid = str(row["id"])
        if sid not in by_id:
            console.print(f"[red]Missing scenario {sid} in replay JSON.[/red]")
            return 2
        prev = by_id[sid]
        act = set(prev["actual_keys"])
        acceptable = list(row.get("acceptable_extras") or [])
        m = _calibrated_metrics_from_acts(
            list(row.get("expected_articles", [])),
            acceptable,
            act,
        )
        per.append(
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
                "acceptable_keys": m["acceptable_keys"],
                "unexpected_keys": m["unexpected_keys"],
                "violations_count": len(act),
            }
        )
    return _aggregate_print_save(
        per,
        replay_source=replay_path.resolve(),
        out_path=REPLAY_OUT_PATH,
    )


def _aggregate_print_save(
    per: list[dict],
    *,
    replay_source: Path | None,
    out_path: Path,
) -> int:
    """Write eval JSON, print the table, apply exit thresholds."""
    precs = [p["precision"] for p in per]
    recs = [p["recall"] for p in per]
    f1s = [p["f1"] for p in per]
    agg_prec = sum(precs) / len(precs)
    agg_rec = sum(recs) / len(recs)
    agg_f1 = sum(f1s) / len(f1s)
    total_hallu = sum(int(p["hallucinations"]) for p in per)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(tz=UTC).isoformat()
    payload: dict[str, Any] = {
        "run_id": run_id,
        "scenario_count": len(per),
        "scoring": "calibrated_precision_with_acceptable_extras",
        "aggregate": {
            "precision": agg_prec,
            "recall": agg_rec,
            "f1": agg_f1,
            "hallucinations": total_hallu,
        },
        "per_scenario": per,
    }
    if replay_source is not None:
        payload["replay_source"] = str(replay_source)
        payload["replay_note"] = (
            "No API usage; citation keys taken from replay file. "
            "Hallucination count is not recomputed (always zero in replay)."
        )

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

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
    console.print(f"Wrote {out_path}")

    if replay_source is not None:
        if agg_prec < 0.8 or agg_rec < 0.7:
            console.print(
                "[red]Threshold breach: need precision ≥0.8, recall ≥0.7 "
                "(replay skips hallucination gate).[/red]"
            )
            return 1
        console.print(
            "[cyan]Replay: zero API cost; hallucination threshold skipped.[/cyan]"
        )
        return 0

    if agg_prec < 0.8 or agg_rec < 0.7 or total_hallu > 0:
        console.print(
            "[red]Threshold breach: need precision ≥0.8, recall ≥0.7, "
            "zero hallucinations.[/red]"
        )
        return 1
    return 0


async def _amain() -> int:
    args = _parse_args()
    rows = load_gold_scenarios(GOLD_PATH)
    wanted = {s.strip() for s in args.scenarios.split(",") if s.strip()}
    rows = _filter_rows(rows, wanted)
    if not rows:
        console.print("[red]No scenarios matched the filter.[/red]")
        return 2

    if args.replay is not None:
        return _run_replay(args.replay, rows)

    if not settings.anthropic_api_key:
        console.print("[red]ANTHROPIC_API_KEY missing — cannot run eval.[/red]")
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
        console.print(
            "[yellow]Warning: empty Chroma index — hallucination counts may be unreliable.[/yellow]"
        )

    per = await _eval_rows(rows, kb_keys)
    return _aggregate_print_save(per, replay_source=None, out_path=OUT_PATH)


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
