#!/usr/bin/env python3
"""Compare two unified eval JSON reports (EvalReport shape from tests/run_eval.py)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _scenarios_by_id(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in report.get("scenarios") or []:
        sid = str(row.get("id", ""))
        if sid:
            out[sid] = row
    return out


def _fmt_float(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{float(x):.3f}"


def _delta_str(before: float | None, after: float | None) -> tuple[str, str]:
    """Return (delta string, arrow for direction: higher after = ⬆, lower = ⬇)."""
    if before is None and after is None:
        return "—", "—"
    bb = 0.0 if before is None else float(before)
    aa = 0.0 if after is None else float(after)
    d = aa - bb
    if abs(d) < 1e-9:
        return "0.000", "—"
    sign = "+" if d > 0 else ""
    arrow = "⬆" if d > 0 else "⬇"
    return f"{sign}{d:.3f}", arrow


def _metric_row(
    label: str,
    b_val: float | None,
    a_val: float | None,
) -> tuple[str, str, str, str]:
    """One line: label, before, after, delta+arrow."""
    bs = _fmt_float(b_val) if b_val is not None else "—"
    aa_s = _fmt_float(a_val) if a_val is not None else "—"
    dstr, arr = _delta_str(b_val, a_val)
    arr_out = "—" if arr == "—" and dstr == "—" else arr
    return (label, bs, aa_s, f"{dstr}  {arr_out}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("before", type=Path)
    p.add_argument("after", type=Path)
    args = p.parse_args()

    before = _load(args.before)
    after = _load(args.after)
    sb = _scenarios_by_id(before)
    sa = _scenarios_by_id(after)
    common = sorted(frozenset(sb) & frozenset(sa))
    only_before = sorted(frozenset(sb) - frozenset(sa))
    only_after = sorted(frozenset(sa) - frozenset(sb))

    print("=== GDPR AI Eval Comparison ===\n")
    print("Overall:")
    print(f"{'':22} {'Before':>10} {'After':>10} {'Delta':>12}")

    rows = [
        _metric_row(
            "Article recall",
            before.get("avg_article_recall"),
            after.get("avg_article_recall"),
        ),
        _metric_row(
            "Article precision",
            before.get("avg_article_precision"),
            after.get("avg_article_precision"),
        ),
        _metric_row(
            "Finding coverage",
            before.get("avg_finding_coverage"),
            after.get("avg_finding_coverage"),
        ),
        _metric_row(
            "Cost (€)",
            before.get("total_cost_eur"),
            after.get("total_cost_eur"),
        ),
        _metric_row(
            "Duration (s)",
            before.get("total_duration_seconds"),
            after.get("total_duration_seconds"),
        ),
    ]
    for label, bv, av, dv in rows:
        print(f"{label:22} {bv:>10} {av:>10} {dv:>12}")

    print("\nResults:")
    print(f"  Pass:    {before.get('passed', 0)} → {after.get('passed', 0)}")
    print(f"  Warn:    {before.get('warned', 0)} → {after.get('warned', 0)}")
    print(f"  Fail:    {before.get('failed', 0)} → {after.get('failed', 0)}")
    print(f"  Error:   {before.get('errored', 0)} → {after.get('errored', 0)}")

    print("\nPer-scenario:")
    hdr = (
        f"{'ID':10} {'Status (before→after)':26} "
        f"{'Recall (before→after)':24} {'Precision (before→after)':28} Flags"
    )
    print(hdr)
    print("-" * len(hdr))

    for sid in common:
        rb, ra = sb[sid], sa[sid]
        st_b, st_a = str(rb.get("status", "")), str(ra.get("status", ""))
        status_cell = f"{st_b}→{st_a}"

        err_b = st_b == "error"
        err_a = st_a == "error"
        rec_b = float(rb.get("article_recall", 0.0))
        rec_a = float(ra.get("article_recall", 0.0))
        pr_b = float(rb.get("article_precision", 0.0))
        pr_a = float(ra.get("article_precision", 0.0))

        if err_b and err_a:
            rec_cell = "—"
            pr_cell = "—"
        elif err_b:
            rec_cell = f"—→{_fmt_float(rec_a)}"
            pr_cell = f"—→{_fmt_float(pr_a)}"
        elif err_a:
            rec_cell = f"{_fmt_float(rec_b)}→—"
            pr_cell = f"{_fmt_float(pr_b)}→—"
        else:
            rec_cell = f"{_fmt_float(rec_b)}→{_fmt_float(rec_a)}"
            pr_cell = f"{_fmt_float(pr_b)}→{_fmt_float(pr_a)}"

        flags: list[str] = []
        if st_b != st_a:
            flags.append("status changed")
        if not err_b and not err_a:
            if rec_a + 1e-9 < rec_b:
                flags.append("recall dropped")
            if pr_a + 1e-9 < pr_b:
                flags.append("precision dropped")
        elif err_b and not err_a:
            flags.append("recovered from error")
        elif not err_b and err_a:
            flags.append("new error")

        flag_s = ""
        if flags:
            sym = (
                "⚠"
                if any(
                    f in flags
                    for f in ("recall dropped", "precision dropped", "new error", "status changed")
                )
                else "✓"
            )
            flag_s = f"{sym} {', '.join(flags)}"
        elif not err_b and not err_a:
            flag_s = "✓"

        print(f"{sid:10} {status_cell:26} {rec_cell:24} {pr_cell:28} {flag_s}")

    if only_before:
        print(f"\nOnly in BEFORE ({args.before.name}): {', '.join(only_before)}")
    if only_after:
        print(f"Only in AFTER ({args.after.name}): {', '.join(only_after)}")
    print()


if __name__ == "__main__":
    main()
