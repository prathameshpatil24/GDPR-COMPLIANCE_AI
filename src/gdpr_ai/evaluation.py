"""Gold-set metrics and knowledge-base article inventory for evaluation runs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import chromadb
import yaml  # type: ignore[import-untyped]

from gdpr_ai.config import settings
from gdpr_ai.llm.client import estimate_cost_eur


def load_gold_scenarios(path: Path) -> list[dict[str, Any]]:
    """Load scenario rows from YAML (``scenarios`` list or legacy root list)."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "scenarios" in raw:
        rows = raw["scenarios"]
    elif isinstance(raw, list):
        rows = raw
    else:
        raise ValueError("Gold file must contain a list or a 'scenarios' key")
    return [r for r in rows if isinstance(r, dict) and r.get("id")]


def filter_unified_scenarios(
    scenarios: list[dict[str, Any]],
    *,
    mode: str | None = None,
    ids: list[str] | None = None,
    difficulty: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Filter unified gold rows by mode, ids, difficulty, or category."""
    out = list(scenarios)
    if mode:
        out = [s for s in out if str(s.get("mode", "")) == mode]
    if ids:
        want = {str(i).strip() for i in ids if str(i).strip()}
        out = [s for s in out if str(s.get("id", "")) in want]
    if difficulty:
        out = [s for s in out if str(s.get("difficulty", "")) == difficulty]
    if category:
        out = [s for s in out if str(s.get("category", "")) == category]
    return out


def normalize_article_ref(label: str) -> str:
    """Map citation strings to a coarse key (article number or section id)."""
    s = (label or "").strip()
    if re.match(r"^\d+/\d{4}$", s):
        return s
    m = re.search(r"art\.?\s*(\d+)", s, flags=re.I)
    if m:
        return m.group(1)
    m2 = re.search(r"§\s*([\d.]+)", s)
    if m2:
        return f"§{m2.group(1)}"
    m3 = re.search(r"recital\s*(\d+)", s, flags=re.I)
    if m3:
        return f"recital:{m3.group(1)}"
    return s.lower()


def expected_article_keys(items: list[str]) -> set[str]:
    """Normalize expected article labels to comparable keys."""
    return {normalize_article_ref(x) for x in items}


def violation_article_keys(violations: list[Any]) -> set[str]:
    """Extract normalized keys from structured violations."""
    out: set[str] = set()
    for v in violations:
        out.add(normalize_article_ref(v.article_reference))
    return out


def load_indexed_article_keys() -> set[str]:
    """Collect normalized reference keys present in the vector index metadata."""
    if not settings.chroma_path.exists():
        return set()
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    try:
        coll = client.get_collection(settings.chroma_collection)
    except Exception:  # noqa: BLE001
        return set()
    n = coll.count()
    if n <= 0:
        return set()
    raw = coll.get(include=["metadatas"], limit=n)
    keys: set[str] = set()
    for meta in raw.get("metadatas") or []:
        if not meta:
            continue
        ref = str(meta.get("article_number", "")).strip()
        if ref:
            keys.add(ref)
            keys.add(ref.lower())
            keys.add(normalize_article_ref(ref))
    return keys


def scenario_metrics(
    expected: list[str],
    violations: list[Any],
    kb_keys: set[str],
) -> dict[str, Any]:
    """Compute precision, recall, F1, and hallucination count for one scenario."""
    exp = expected_article_keys(expected)
    act = violation_article_keys(violations)
    inter = exp & act
    if not exp:
        recall = 1.0
    else:
        recall = len(inter) / len(exp)
    if not act:
        precision = 0.0 if exp else 1.0
    else:
        precision = len(inter) / len(act)
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0
    hallucinations = 0
    for v in violations:
        raw_cite = v.article_reference.strip()
        key = normalize_article_ref(raw_cite)
        if key in exp:
            continue
        if raw_cite in kb_keys or raw_cite.lower() in kb_keys or key in kb_keys:
            continue
        hallucinations += 1
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "hallucinations": hallucinations,
        "expected_keys": sorted(exp),
        "actual_keys": sorted(act),
    }


def estimate_eval_run_cost_eur(
    num_scenarios: int,
    calls_per_scenario: int = 4,
    tokens_per_call: int = 2000,
) -> float:
    """Rough order-of-magnitude cost for a full eval run (reasoning-heavy stages dominate)."""
    total_in = num_scenarios * calls_per_scenario * int(tokens_per_call * 0.55)
    total_out = num_scenarios * calls_per_scenario * int(tokens_per_call * 0.45)
    return estimate_cost_eur(settings.model_reasoning, total_in, total_out)
