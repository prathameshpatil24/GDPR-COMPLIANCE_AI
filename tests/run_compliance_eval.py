#!/usr/bin/env python3
"""Compliance gold-set evaluation: full assessment + document checks, or --dry-run (schema only)."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from gdpr_ai.compliance.generator import generate_documents
from gdpr_ai.compliance.intake import parse_structured_input
from gdpr_ai.compliance.orchestrator import run_compliance_assessment_logged
from gdpr_ai.compliance.schemas import ComplianceAssessment, Finding
from gdpr_ai.config import settings
from gdpr_ai.evaluation import (
    estimate_eval_run_cost_eur,
    load_gold_scenarios,
    normalize_article_ref,
)
from gdpr_ai.logger import get_query

console = Console()
ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "gold" / "compliance_scenarios.yaml"
OUT_PATH = ROOT / "logs" / "compliance_eval_results.json"
BASELINE_PATH = ROOT / "gold" / "compliance_baseline.json"

# Minimum substrings expected in generated markdown (sanity check, not legal completeness).
_DOC_MARKERS: dict[str, list[str]] = {
    "dpia": ["Data Protection Impact Assessment", "Description of Processing"],
    "ropa": ["Records of Processing", "Processing Activities"],
    "checklist": ["Compliance Checklist"],
    "consent_flow": ["Consent Flow"],
    "retention_policy": ["Retention Policy", "Retention Schedule"],
}


def _article_keys_from_findings(findings: list[Finding]) -> set[str]:
    keys: set[str] = set()
    for f in findings:
        for a in f.relevant_articles:
            raw = (a or "").strip()
            if not raw:
                continue
            keys.add(normalize_article_ref(raw))
            keys.add(raw.lower())
    return keys


def _article_recall_precision(expected: list[str], actual_keys: set[str]) -> dict[str, float]:
    exp = {normalize_article_ref(x) for x in expected if x}
    act = set()
    for k in actual_keys:
        act.add(normalize_article_ref(str(k)))
    inter = exp & act
    recall = 1.0 if not exp else len(inter) / len(exp)
    precision = 1.0 if not act else len(inter) / len(act)
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "expected_n": len(exp),
        "actual_n": len(act),
    }


def _finding_coverage(expected_areas: list[str], findings: list[Finding]) -> dict[str, Any]:
    hits = 0
    detail: list[dict[str, Any]] = []
    for area in expected_areas:
        a = area.lower()
        matched = any(a in f.area.lower() or f.area.lower() in a for f in findings)
        if matched:
            hits += 1
        detail.append({"area": area, "matched": matched})
    denom = len(expected_areas)
    recall = 1.0 if denom == 0 else hits / denom
    return {"recall": recall, "hits": hits, "total": denom, "detail": detail}


def _document_completeness(
    assessment: ComplianceAssessment,
    expected_types: list[str],
) -> dict[str, Any]:
    docs = generate_documents(assessment)
    per: dict[str, Any] = {}
    for dt in expected_types:
        content = docs.get(dt, "")
        markers = _DOC_MARKERS.get(dt, [])
        ok = all(m in content for m in markers) if markers else bool(content.strip())
        per[dt] = {"ok": ok, "markers_checked": markers}
    all_ok = all(v["ok"] for v in per.values()) if per else True
    return {"all_ok": all_ok, "per_type": per}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run compliance gold scenarios.")
    p.add_argument(
        "--scenarios",
        type=str,
        default="",
        help="Comma-separated ids (default: all), e.g. SC-C-001,SC-C-002",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Load YAML and validate structured DataMap skeleton only (no language model).",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive cost confirmation before live runs.",
    )
    p.add_argument(
        "--write-baseline",
        action="store_true",
        help=f"Write aggregate metrics to {BASELINE_PATH} after a successful run.",
    )
    return p.parse_args()


def _filter_rows(rows: list[dict], wanted: set[str]) -> list[dict]:
    if not wanted:
        return rows
    return [r for r in rows if str(r.get("id", "")) in wanted]


def _dry_run_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        sid = str(row["id"])
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
        out.append({"id": sid, "title": row.get("title", ""), "dry_run_ok": True})
    return out


async def _eval_rows(rows: list[dict]) -> list[dict]:
    per: list[dict] = []
    for row in rows:
        sid = str(row["id"])
        text = str(row.get("system_description", "")).strip()
        console.print(f"Evaluating {sid} …")
        assessment, qid = await run_compliance_assessment_logged(text)
        log = get_query(qid)
        cost = float(log.estimated_cost_eur) if log else 0.0
        latency_ms = int(log.latency_total_ms) if log else 0
        keys = _article_keys_from_findings(assessment.findings)
        art = _article_recall_precision(list(row.get("expected_articles", [])), keys)
        cov = _finding_coverage(list(row.get("expected_findings", [])), assessment.findings)
        doc_expect = list(row.get("expected_documents", []))
        doc_m = _document_completeness(assessment, doc_expect)
        per.append(
            {
                "id": sid,
                "title": row.get("title", ""),
                "difficulty": row.get("difficulty", ""),
                "article_metrics": art,
                "finding_coverage": cov,
                "document_completeness": doc_m,
                "cost_eur": cost,
                "latency_ms": latency_ms,
                "findings_count": len(assessment.findings),
            }
        )
    return per


def _aggregate(per: list[dict]) -> dict[str, Any]:
    if not per:
        return {}
    ap = sum(p["article_metrics"]["precision"] for p in per) / len(per)
    ar = sum(p["article_metrics"]["recall"] for p in per) / len(per)
    af1 = sum(p["article_metrics"]["f1"] for p in per) / len(per)
    fc = sum(p["finding_coverage"]["recall"] for p in per) / len(per)
    doc_ok = sum(1 for p in per if p["document_completeness"]["all_ok"]) / len(per)
    cost = sum(p["cost_eur"] for p in per)
    lat = sum(p["latency_ms"] for p in per) / len(per)
    return {
        "mean_article_precision": ap,
        "mean_article_recall": ar,
        "mean_article_f1": af1,
        "mean_finding_coverage_recall": fc,
        "fraction_documents_complete": doc_ok,
        "total_cost_eur": cost,
        "mean_latency_ms": lat,
    }


def _print_table(per: list[dict], agg: dict[str, Any]) -> None:
    table = Table("ID", "Title", "Art R", "Art P", "Areas", "Docs OK", "€", "ms")
    for p in sorted(per, key=lambda x: x["id"]):
        am = p["article_metrics"]
        table.add_row(
            p["id"],
            (p.get("title") or "")[:28],
            f"{am['recall']:.2f}",
            f"{am['precision']:.2f}",
            f"{p['finding_coverage']['recall']:.2f}",
            "Y" if p["document_completeness"]["all_ok"] else "N",
            f"{p['cost_eur']:.3f}",
            str(p["latency_ms"]),
        )
    if agg:
        table.add_row(
            "AGG",
            "",
            f"{agg['mean_article_recall']:.2f}",
            f"{agg['mean_article_precision']:.2f}",
            f"{agg['mean_finding_coverage_recall']:.2f}",
            f"{agg['fraction_documents_complete']:.2f}",
            f"{agg['total_cost_eur']:.3f}",
            f"{agg['mean_latency_ms']:.0f}",
        )
    console.print(table)


async def _amain() -> int:
    args = _parse_args()
    rows = load_gold_scenarios(GOLD_PATH)
    wanted = {s.strip() for s in args.scenarios.split(",") if s.strip()}
    rows = _filter_rows(rows, wanted)
    if not rows:
        console.print("[red]No scenarios matched the filter.[/red]")
        return 2

    if args.dry_run:
        dr = _dry_run_rows(rows)
        run_id = datetime.now(tz=UTC).isoformat()
        payload = {
            "run_id": run_id,
            "mode": "dry_run",
            "scenario_count": len(dr),
            "per_scenario": dr,
            "aggregate": {"dry_run_passed": len(dr)},
        }
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"[green]Dry-run OK for {len(dr)} scenario(s).[/green] Wrote {OUT_PATH}")
        if args.write_baseline:
            baseline_payload = {
                "note": (
                    "Dry-run: gold file and DataMap skeleton only. "
                    "Re-run without --dry-run and use --write-baseline for scored metrics."
                ),
                **payload,
            }
            BASELINE_PATH.write_text(json.dumps(baseline_payload, indent=2), encoding="utf-8")
            console.print(f"Wrote {BASELINE_PATH}")
        return 0

    if not settings.anthropic_api_key:
        console.print("[red]ANTHROPIC_API_KEY missing — cannot run compliance eval.[/red]")
        return 2

    est = estimate_eval_run_cost_eur(len(rows), calls_per_scenario=5, tokens_per_call=2500)
    console.print(
        f"[bold]Rough estimated cost:[/bold] €{est:.2f} for {len(rows)} scenario(s) "
        "(intake + mapping + assessment + document generation per scenario)."
    )
    if not args.yes:
        console.print("Press Enter to continue, or Ctrl+C to abort.")
        input()

    per = await _eval_rows(rows)
    agg = _aggregate(per)
    run_id = datetime.now(tz=UTC).isoformat()
    payload: dict[str, Any] = {
        "run_id": run_id,
        "mode": "live",
        "scenario_count": len(per),
        "aggregate": agg,
        "per_scenario": per,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _print_table(per, agg)
    console.print(f"Wrote {OUT_PATH}")
    if args.write_baseline:
        baseline = {
            "updated_at": run_id,
            "source": "tests/run_compliance_eval.py --write-baseline",
            "aggregate": agg,
            "scenario_count": len(per),
        }
        BASELINE_PATH.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        console.print(f"Wrote {BASELINE_PATH}")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
