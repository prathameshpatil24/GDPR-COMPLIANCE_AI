#!/usr/bin/env python3
"""Unified gold evaluation: violation_analysis (v1) and compliance_assessment (v2)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from gdpr_ai.compliance.generator import generate_documents
from gdpr_ai.compliance.intake import parse_structured_input
from gdpr_ai.compliance.orchestrator import run_compliance_assessment_logged
from gdpr_ai.config import settings
from gdpr_ai.evaluation import (
    estimate_eval_run_cost_eur,
    filter_unified_scenarios,
    load_gold_scenarios,
    load_indexed_article_keys,
    normalize_article_ref,
)
from gdpr_ai.logger import get_query
from gdpr_ai.pipeline import run_pipeline_logged

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from eval_models import EvalReport, ScenarioResult  # noqa: E402
from eval_scoring import (  # noqa: E402
    article_recall_precision_violation,
    article_sets_violation,
    compliance_article_metrics,
    document_completeness_score,
    finding_area_coverage,
    finding_status_accuracy,
    law_recall_from_keys,
    law_recall_score,
    legacy_replay_ids,
    outcome_label,
    violation_hallucination_count,
    violation_recall_precision_from_act_keys,
    without_recital_keys,
)

console = Console()
GOLD_PATH = ROOT / "gold" / "test_scenarios.yaml"
DEFAULT_OUT = ROOT / "logs" / "eval_results.json"
REPLAY_OUT_PATH = ROOT / "logs" / "eval_replay.json"
BASELINE_PATH = ROOT / "gold" / "baseline.json"


def load_scenarios(path: Path = GOLD_PATH) -> list[dict[str, Any]]:
    """Load all unified gold scenarios from YAML."""
    return load_gold_scenarios(path)


def filter_scenarios(
    scenarios: list[dict[str, Any]],
    *,
    mode: str | None = None,
    ids: list[str] | None = None,
    difficulty: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Filter scenarios by mode, ids, difficulty, or category."""
    return filter_unified_scenarios(
        scenarios,
        mode=mode,
        ids=ids,
        difficulty=difficulty,
        category=category,
    )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unified gold eval (violation + compliance).")
    p.add_argument(
        "--mode",
        type=str,
        default="",
        help="violation_analysis | compliance_assessment",
    )
    p.add_argument("--scenarios", type=str, default="", help="Comma-separated ids")
    p.add_argument("--difficulty", type=str, default="", help="easy | medium | hard")
    p.add_argument("--category", type=str, default="", help="Category label")
    p.add_argument("--dry-run", action="store_true", help="Validate YAML only; no LLM")
    p.add_argument("--yes", action="store_true", help="Skip cost confirmation")
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write EvalReport JSON (default: logs/eval_results.json)",
    )
    p.add_argument(
        "--replay",
        type=Path,
        default=None,
        metavar="PATH",
        help="Violation-only: recompute metrics from saved eval JSON",
    )
    p.add_argument(
        "--check-baseline",
        action="store_true",
        help="Compare run aggregates to gold/baseline.json",
    )
    return p.parse_args()


def _validate_row(row: dict[str, Any]) -> None:
    sid = str(row.get("id", ""))
    mode = str(row.get("mode", ""))
    if mode not in {"violation_analysis", "compliance_assessment"}:
        raise ValueError(f"{sid}: invalid mode {mode!r}")
    if mode == "violation_analysis":
        if "scenario" not in row or not str(row["scenario"]).strip():
            raise ValueError(f"{sid}: violation_analysis requires scenario")
        if "expected_articles" not in row:
            raise ValueError(f"{sid}: violation_analysis requires expected_articles")
    else:
        if "system_description" not in row or not str(row["system_description"]).strip():
            raise ValueError(f"{sid}: compliance_assessment requires system_description")
        if "expected_findings" not in row:
            raise ValueError(f"{sid}: compliance_assessment requires expected_findings")
        if "expected_documents" not in row:
            raise ValueError(f"{sid}: compliance_assessment requires expected_documents")


def dry_run_all(rows: list[dict[str, Any]]) -> None:
    """Structural validation and compliance DataMap skeleton parse."""
    seen: set[str] = set()
    for row in rows:
        sid = str(row["id"])
        if sid in seen:
            raise ValueError(f"duplicate id {sid}")
        seen.add(sid)
        _validate_row(row)
        if row["mode"] == "compliance_assessment":
            dm = {
                "system_name": str(row.get("title", sid)),
                "system_description": str(row.get("system_description", "")).strip(),
                "data_categories": [],
                "processing_purposes": [],
                "data_flows": [],
                "third_parties": [],
                "storage": [],
            }
            parse_structured_input(dm)


async def _run_violation_row(row: dict[str, Any], kb_keys: set[str]) -> ScenarioResult:
    sid = str(row["id"])
    title = str(row.get("title", ""))
    try:
        report, qid = await run_pipeline_logged(str(row["scenario"]))
        log = get_query(qid)
        cost = float(log.estimated_cost_eur) if log else 0.0
        dur = (log.latency_total_ms / 1000.0) if log else 0.0
        exp = list(row.get("expected_articles") or [])
        acc = list(row.get("acceptable_extras") or [])
        rec, prec = article_recall_precision_violation(exp, acc, report.violations)
        law_r = law_recall_score(list(row.get("expected_laws") or []), report.violations)
        hallu = violation_hallucination_count(exp, acc, report.violations, kb_keys)
        _, act_keys, missing, extra = article_sets_violation(exp, acc, report.violations)
        st = outcome_label(article_recall=rec, article_precision=prec, finding_coverage=None)
        if hallu > 0:
            st = "fail"
        return ScenarioResult(
            id=sid,
            mode="violation_analysis",
            title=title,
            status=st,
            article_recall=rec,
            article_precision=prec,
            law_recall=law_r,
            finding_coverage=None,
            finding_accuracy=None,
            document_completeness=None,
            expected_articles=exp,
            found_article_keys=sorted(act_keys),
            missing_article_keys=sorted(missing),
            extra_article_keys=sorted(extra),
            cost_eur=cost,
            duration_seconds=dur,
            hallucinations=hallu,
        )
    except Exception as exc:  # noqa: BLE001
        return ScenarioResult(
            id=sid,
            mode="violation_analysis",
            title=title,
            status="error",
            error=str(exc),
            expected_articles=list(row.get("expected_articles") or []),
        )


def _normalize_finding_specs(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw[0], str):
        return [{"area": s, "min_status": "at_risk"} for s in raw]
    return [dict(x) for x in raw]


async def _run_compliance_row(row: dict[str, Any]) -> ScenarioResult:
    sid = str(row["id"])
    title = str(row.get("title", ""))
    try:
        text = str(row["system_description"]).strip()
        assessment, qid = await run_compliance_assessment_logged(text)
        log = get_query(qid)
        cost = float(log.estimated_cost_eur) if log else 0.0
        dur = (log.latency_total_ms / 1000.0) if log else 0.0
        exp_art = [str(x) for x in (row.get("expected_articles") or [])]
        rec, prec, found_l, miss_l, ext_l = compliance_article_metrics(exp_art, assessment.findings)
        specs = _normalize_finding_specs(row.get("expected_findings"))
        cov = finding_area_coverage(specs, assessment.findings)
        acc = finding_status_accuracy(specs, assessment.findings)
        docs = generate_documents(assessment)
        doc_types = [str(x) for x in (row.get("expected_documents") or [])]
        doc_score = document_completeness_score(docs, doc_types)
        st = outcome_label(article_recall=rec, article_precision=prec, finding_coverage=cov)
        if doc_score < 0.6 and st == "pass":
            st = "warn"
        return ScenarioResult(
            id=sid,
            mode="compliance_assessment",
            title=title,
            status=st,
            article_recall=rec,
            article_precision=prec,
            finding_coverage=cov,
            finding_accuracy=acc,
            document_completeness=doc_score,
            expected_articles=exp_art,
            found_article_keys=found_l,
            missing_article_keys=miss_l,
            extra_article_keys=ext_l,
            cost_eur=cost,
            duration_seconds=dur,
        )
    except Exception as exc:  # noqa: BLE001
        return ScenarioResult(
            id=sid,
            mode="compliance_assessment",
            title=title,
            status="error",
            error=str(exc),
            expected_articles=list(row.get("expected_articles") or []),
        )


def _build_report(results: list[ScenarioResult]) -> EvalReport:
    n = len(results)
    if not n:
        return EvalReport(total_scenarios=0, scenarios=[])
    passed = sum(1 for r in results if r.status == "pass")
    warned = sum(1 for r in results if r.status == "warn")
    failed = sum(1 for r in results if r.status == "fail")
    errored = sum(1 for r in results if r.status == "error")
    ok_n = n - errored
    avg_rec = sum(r.article_recall for r in results if r.error is None) / max(1, ok_n)
    avg_prec = sum(r.article_precision for r in results if r.error is None) / max(1, ok_n)
    covs = [r.finding_coverage for r in results if r.finding_coverage is not None]
    avg_cov = sum(covs) / len(covs) if covs else None
    laws = [
        r.law_recall
        for r in results
        if r.law_recall is not None and r.mode == "violation_analysis" and r.error is None
    ]
    avg_law = sum(laws) / len(laws) if laws else None
    total_cost = sum(r.cost_eur for r in results)
    total_dur = sum(r.duration_seconds for r in results)
    v_rows = [r for r in results if r.mode == "violation_analysis" and r.error is None]
    c_rows = [r for r in results if r.mode == "compliance_assessment" and r.error is None]
    v_sum: dict[str, float | int] = {"count": len(v_rows)}
    if v_rows:
        v_sum["avg_article_recall"] = sum(x.article_recall for x in v_rows) / len(v_rows)
        v_sum["avg_article_precision"] = sum(x.article_precision for x in v_rows) / len(v_rows)
    c_sum: dict[str, float | int] = {"count": len(c_rows)}
    if c_rows:
        c_sum["avg_article_recall"] = sum(x.article_recall for x in c_rows) / len(c_rows)
        c_sum["avg_article_precision"] = sum(x.article_precision for x in c_rows) / len(c_rows)
        fc = [x.finding_coverage for x in c_rows if x.finding_coverage is not None]
        c_sum["avg_finding_coverage"] = sum(fc) / len(fc) if fc else 0.0
    return EvalReport(
        total_scenarios=n,
        passed=passed,
        warned=warned,
        failed=failed,
        errored=errored,
        avg_article_recall=avg_rec,
        avg_article_precision=avg_prec,
        avg_finding_coverage=avg_cov,
        avg_law_recall=avg_law,
        total_cost_eur=total_cost,
        total_duration_seconds=total_dur,
        scenarios=sorted(results, key=lambda x: x.id),
        violation_analysis_summary=v_sum,
        compliance_assessment_summary=c_sum,
    )


def _print_summary(report: EvalReport) -> None:
    console.print("[bold]GDPR AI — Evaluation report[/bold]")
    t = Table("Mode", "N", "Avg recall", "Avg precision", "Avg finding cov")
    v = report.violation_analysis_summary or {}
    c = report.compliance_assessment_summary or {}
    t.add_row(
        "violation_analysis",
        str(v.get("count", 0)),
        f"{float(v.get('avg_article_recall', 0)):.3f}" if v.get("count") else "—",
        f"{float(v.get('avg_article_precision', 0)):.3f}" if v.get("count") else "—",
        "—",
    )
    t.add_row(
        "compliance_assessment",
        str(c.get("count", 0)),
        f"{float(c.get('avg_article_recall', 0)):.3f}" if c.get("count") else "—",
        f"{float(c.get('avg_article_precision', 0)):.3f}" if c.get("count") else "—",
        f"{float(c.get('avg_finding_coverage', 0)):.3f}" if c.get("count") else "—",
    )
    t.add_row(
        "TOTAL",
        str(report.total_scenarios),
        f"{report.avg_article_recall:.3f}",
        f"{report.avg_article_precision:.3f}",
        f"{report.avg_finding_coverage or 0:.3f}",
    )
    console.print(t)
    summary = (
        f"Pass {report.passed} | Warn {report.warned} | Fail {report.failed} | "
        f"Error {report.errored} | Cost €{report.total_cost_eur:.2f} | "
        f"Time {report.total_duration_seconds:.1f}s"
    )
    console.print(summary)
    detail = Table("ID", "Mode", "Stat", "Rec", "Prec", "Cov", "€", "s")
    for r in report.scenarios:
        detail.add_row(
            r.id,
            r.mode[:20],
            r.status,
            f"{r.article_recall:.2f}",
            f"{r.article_precision:.2f}",
            f"{(r.finding_coverage or 0):.2f}",
            f"{r.cost_eur:.3f}",
            f"{r.duration_seconds:.1f}",
        )
    console.print(detail)


def _run_replay(replay_path: Path, rows: list[dict[str, Any]]) -> int:
    v_rows = [r for r in rows if r.get("mode") == "violation_analysis"]
    if not replay_path.is_file():
        console.print(f"[red]Replay file not found: {replay_path}[/red]")
        return 2
    data = json.loads(replay_path.read_text(encoding="utf-8"))
    by_id: dict[str, dict[str, Any]] = {str(p["id"]): p for p in data.get("per_scenario", [])}
    results: list[ScenarioResult] = []
    for row in v_rows:
        sid = str(row["id"])
        prev = None
        for cand in legacy_replay_ids(sid):
            if cand in by_id:
                prev = by_id[cand]
                break
        if prev is None:
            console.print(f"[red]Missing replay entry for {sid}[/red]")
            return 2
        act_keys = set(prev.get("actual_keys", []))
        exp = list(row.get("expected_articles") or [])
        acc = list(row.get("acceptable_extras") or [])
        rec, prec, exp_s, act_s, _ = violation_recall_precision_from_act_keys(exp, acc, act_keys)
        missing = exp_s - act_s
        acc_norm = {normalize_article_ref(x) for x in acc}
        extra = sorted(without_recital_keys(act_s - exp_s - acc_norm))
        law_r = law_recall_from_keys(list(row.get("expected_laws") or []), act_keys)
        st = outcome_label(article_recall=rec, article_precision=prec, finding_coverage=None)
        results.append(
            ScenarioResult(
                id=sid,
                mode="violation_analysis",
                title=str(row.get("title", "")),
                status=st,
                article_recall=rec,
                article_precision=prec,
                law_recall=law_r,
                expected_articles=exp,
                found_article_keys=sorted(exp_s - missing),
                missing_article_keys=sorted(missing),
                extra_article_keys=sorted(extra),
                cost_eur=0.0,
                duration_seconds=0.0,
                hallucinations=0,
            )
        )
    report = _build_report(results)
    REPLAY_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPLAY_OUT_PATH.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    _print_summary(report)
    console.print(f"Wrote {REPLAY_OUT_PATH}")
    return 0


def _metric_drop(baseline_val: float, current_val: float) -> float:
    """Regression in percentage points (positive = current worse than baseline)."""
    return (baseline_val - current_val) * 100


def _check_baseline(report: EvalReport) -> int:
    if not BASELINE_PATH.is_file():
        console.print(f"[yellow]No baseline at {BASELINE_PATH}; skip --check-baseline.[/yellow]")
        return 0
    base = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    exit_code = 0
    v_base = base.get("violation_analysis") or {}
    v_cur = report.violation_analysis_summary or {}
    if v_base and v_cur.get("count"):
        for metric, label in (
            ("avg_article_recall", "recall"),
            ("avg_article_precision", "precision"),
        ):
            b_val = float(v_base.get(metric, 0))
            c_val = float(v_cur.get(metric, 0))
            drop = _metric_drop(b_val, c_val)
            if drop > 10:
                console.print(
                    f"[red]Baseline fail: violation_analysis {label} dropped {drop:.1f} pp[/red]"
                )
                exit_code = 1
            elif drop > 5:
                msg = (
                    f"[yellow]Baseline warn: violation_analysis {label} "
                    f"dropped {drop:.1f} pp[/yellow]"
                )
                console.print(msg)
    c_base = base.get("compliance_assessment") or {}
    c_cur = report.compliance_assessment_summary or {}
    if c_base and c_cur.get("count"):
        for metric, label in (
            ("avg_article_recall", "article recall"),
            ("avg_finding_coverage", "finding coverage"),
        ):
            if metric not in c_base:
                continue
            b_val = float(c_base[metric])
            c_val = float(c_cur.get(metric, 0))
            drop = _metric_drop(b_val, c_val)
            if drop > 10:
                console.print(
                    f"[red]Baseline fail: compliance_assessment {label} dropped {drop:.1f} pp[/red]"
                )
                exit_code = 1
            elif drop > 5:
                msg = (
                    f"[yellow]Baseline warn: compliance_assessment {label} "
                    f"dropped {drop:.1f} pp[/yellow]"
                )
                console.print(msg)
    return exit_code


async def _run_live(rows: list[dict[str, Any]]) -> EvalReport:
    kb = load_indexed_article_keys()
    if not kb:
        console.print(
            "[yellow]Warning: empty Chroma index — hallucination gate may be noisy.[/yellow]"
        )
    results: list[ScenarioResult] = []
    for row in rows:
        if row["mode"] == "violation_analysis":
            results.append(await _run_violation_row(row, kb))
        else:
            results.append(await _run_compliance_row(row))
    return _build_report(results)


async def _amain() -> int:
    args = _parse_args()
    rows = load_scenarios(GOLD_PATH)
    ids_list = [s.strip() for s in args.scenarios.split(",") if s.strip()] or None
    rows = filter_scenarios(
        rows,
        mode=args.mode or None,
        ids=ids_list,
        difficulty=args.difficulty or None,
        category=args.category or None,
    )
    if not rows:
        console.print("[red]No scenarios matched filters.[/red]")
        return 2

    if args.dry_run:
        try:
            dry_run_all(rows)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Dry-run failed: {exc}[/red]")
            return 2
        console.print(f"[green]Dry-run OK for {len(rows)} scenario(s).[/green]")
        return 0

    if args.replay is not None:
        return _run_replay(args.replay, rows)

    if not settings.anthropic_api_key:
        console.print("[red]ANTHROPIC_API_KEY missing — cannot run eval.[/red]")
        return 2

    n_v = sum(1 for r in rows if r.get("mode") == "violation_analysis")
    n_c = sum(1 for r in rows if r.get("mode") == "compliance_assessment")
    est_v = estimate_eval_run_cost_eur(n_v, calls_per_scenario=4, tokens_per_call=2000)
    est_c = estimate_eval_run_cost_eur(n_c, calls_per_scenario=5, tokens_per_call=2500)
    est = est_v + est_c
    console.print(
        f"[bold]Rough estimated cost:[/bold] €{est:.2f} "
        f"({n_v} violation + {n_c} compliance scenario(s))."
    )
    if not args.yes:
        console.print("Press Enter to continue, or Ctrl+C to abort.")
        input()

    report = await _run_live(rows)
    _print_summary(report)
    out_path = args.output or DEFAULT_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    console.print(f"Wrote {out_path}")

    if args.check_baseline:
        return _check_baseline(report)

    v = report.violation_analysis_summary or {}
    c = report.compliance_assessment_summary or {}
    if v.get("count") and (
        float(v.get("avg_article_recall", 0)) < 0.7
        or float(v.get("avg_article_precision", 0)) < 0.8
    ):
        console.print("[red]Violation aggregate below typical gate (recall/precision).[/red]")
        return 1
    if c.get("count") and float(c.get("avg_article_recall", 0)) < 0.5:
        console.print("[yellow]Compliance aggregate recall very low.[/yellow]")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
