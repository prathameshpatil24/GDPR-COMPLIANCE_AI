"""Scoring helpers for unified violation + compliance gold evaluation."""

from __future__ import annotations

import re
from typing import Any

from gdpr_ai.compliance.schemas import ComplianceStatus, Finding
from gdpr_ai.evaluation import normalize_article_ref

_STATUS_ORDER: dict[str, int] = {
    ComplianceStatus.COMPLIANT.value: 0,
    ComplianceStatus.INSUFFICIENT_INFO.value: 1,
    ComplianceStatus.AT_RISK.value: 2,
    ComplianceStatus.NON_COMPLIANT.value: 3,
}


def status_rank(status: str) -> int:
    """Monotonic rank: higher means more severe / less compliant."""
    return _STATUS_ORDER.get(status, 1)


def _is_recital_key(key: str) -> bool:
    """True when normalized citation is a recital (precision excludes these)."""
    return str(key).strip().lower().startswith("recital:")


def without_recital_keys(keys: set[str]) -> set[str]:
    """Drop recitals so precision reflects substantive GDPR/article citations only."""
    return {k for k in keys if not _is_recital_key(k)}


def outcome_label(
    *,
    article_recall: float,
    article_precision: float,
    finding_coverage: float | None,
) -> str:
    """pass / warn / fail from aggregate thresholds."""
    cov = finding_coverage if finding_coverage is not None else article_recall
    if article_recall >= 0.8 and (article_precision >= 0.8 or cov >= 0.8):
        return "pass"
    if article_recall >= 0.6 or cov >= 0.6:
        return "warn"
    return "fail"


def law_keys_from_violations(violations: list[Any]) -> set[str]:
    """Normalized keys that look like national-law citations (e.g. BDSG/TTDSG sections)."""
    keys: set[str] = set()
    for v in violations:
        raw = str(getattr(v, "article_reference", "") or "").strip()
        if "§" in raw or "BDSG" in raw.upper() or "TTDSG" in raw.upper():
            keys.add(normalize_article_ref(raw))
            keys.add(raw.lower())
    return keys


def law_recall_from_keys(expected_laws: list[str], act_keys: set[str]) -> float:
    """Law recall when actual citations are already normalized keys (replay)."""
    if not expected_laws:
        return 1.0
    exp = {normalize_article_ref(x) for x in expected_laws if x}
    act = {normalize_article_ref(k) for k in act_keys}
    if not exp:
        return 1.0
    return len(exp & act) / len(exp)


def law_recall_score(expected_laws: list[str], violations: list[Any]) -> float:
    """Recall for expected_laws against violation citations."""
    if not expected_laws:
        return 1.0
    act = law_keys_from_violations(violations)
    for v in violations:
        act.add(normalize_article_ref(str(getattr(v, "article_reference", "") or "")))
    return law_recall_from_keys(expected_laws, act)


def article_sets_violation(
    expected: list[str],
    acceptable: list[str],
    violations: list[Any],
) -> tuple[set[str], set[str], set[str], set[str]]:
    """Expected keys, actual keys, missing, extra (extras exclude acceptable)."""

    def key_set(items: list[str]) -> set[str]:
        return {normalize_article_ref(x) for x in items if x}

    exp = key_set(expected)
    acc = key_set(acceptable)
    act: set[str] = set()
    for v in violations:
        act.add(normalize_article_ref(v.article_reference))
    missing = exp - act
    extra = without_recital_keys(act - exp - acc)
    return exp, act, missing, extra


def violation_recall_precision_from_act_keys(
    expected: list[str],
    acceptable: list[str],
    act_keys: set[str],
) -> tuple[float, float, set[str], set[str], set[str]]:
    """Recall/precision when actual output is a set of normalized citation keys."""
    exp = {normalize_article_ref(x) for x in expected if x}
    acc = {normalize_article_ref(x) for x in acceptable if x}
    act_n = {normalize_article_ref(k) for k in act_keys}
    correct = act_n & exp
    unexpected = act_n - exp - acc
    recall = 1.0 if not exp else len(correct) / len(exp)
    unexpected_noprec = without_recital_keys(unexpected)
    denom = len(correct) + len(unexpected_noprec)
    precision = 1.0 if denom == 0 else len(correct) / denom
    missing = exp - act_n
    extra = unexpected
    return recall, precision, exp, act_n, missing | extra


def article_recall_precision_violation(
    expected: list[str],
    acceptable: list[str],
    violations: list[Any],
) -> tuple[float, float]:
    """Recall and precision for article keys (acceptable extras are not FP)."""
    exp, act, _, _ = article_sets_violation(expected, acceptable, violations)
    acc = {normalize_article_ref(x) for x in acceptable if x}
    correct = act & exp
    unexpected = act - exp - acc
    recall = 1.0 if not exp else len(correct) / len(exp)
    unexpected_noprec = without_recital_keys(unexpected)
    denom = len(correct) + len(unexpected_noprec)
    precision = 1.0 if denom == 0 else len(correct) / denom
    return recall, precision


def violation_hallucination_count(
    expected: list[str],
    acceptable: list[str],
    violations: list[Any],
    kb_keys: set[str],
) -> int:
    """Count citations that are neither expected nor acceptable nor indexed."""
    exp = {normalize_article_ref(x) for x in expected if x}
    acc = {normalize_article_ref(x) for x in acceptable if x}
    hallu = 0
    for v in violations:
        raw = str(getattr(v, "article_reference", "") or "").strip()
        key = normalize_article_ref(raw)
        if key in exp or key in acc:
            continue
        if raw in kb_keys or raw.lower() in kb_keys or key in kb_keys:
            continue
        hallu += 1
    return hallu


def compliance_article_metrics(
    expected_articles: list[str],
    findings: list[Finding],
) -> tuple[float, float, list[str], list[str], list[str]]:
    """Recall/precision vs findings' relevant_articles; lists are sorted keys."""
    exp = {normalize_article_ref(x) for x in expected_articles if x}
    act: set[str] = set()
    for f in findings:
        for a in f.relevant_articles:
            act.add(normalize_article_ref(a))
    correct = exp & act
    recall = 1.0 if not exp else len(correct) / len(exp)
    act_for_precision = without_recital_keys(act)
    correct_prec = exp & act_for_precision
    precision = 1.0 if not act_for_precision else len(correct_prec) / len(act_for_precision)
    missing_l = sorted(exp - act)
    extra_l = sorted(without_recital_keys(act - exp))
    found_l = sorted(act & exp)
    return recall, precision, found_l, missing_l, extra_l


_FINDING_AREA_NEEDLE_ALIASES: dict[str, tuple[str, ...]] = {
    "consent": (
        "consent",
        "lawful basis",
        "lawfulness",
        "conditions for consent",
        "article 7",
        "marketing",
        "newsletter",
        "subscribe",
    ),
    "processor": (
        "processor",
        "subprocessor",
        "vendor",
        "mailchimp",
        "dpa",
        "data processing agreement",
        "article 28",
        "art. 28",
    ),
    "transparency": (
        "transparency",
        "privacy notice",
        "privacy policy",
        "information obligation",
        "information to data subjects",
        "article 13",
        "articles 13",
        "articles 12",
    ),
}


def _finding_matches_expected_area(f: Finding, area_needle: str) -> bool:
    """Match gold ``area`` labels to finding text using literals and common synonyms."""
    needle = area_needle.strip().lower()
    if not needle:
        return False
    hay = f"{f.area} {f.description or ''}".lower()
    tokens = _FINDING_AREA_NEEDLE_ALIASES.get(needle, (needle,))
    if any(tok in hay for tok in tokens):
        return True
    return needle in hay or hay in needle


def finding_area_coverage(
    expected_specs: list[dict[str, Any]],
    findings: list[Finding],
) -> float:
    """Fraction of expected areas matched against findings (area + description)."""
    if not expected_specs:
        return 1.0
    hits = 0
    for spec in expected_specs:
        area_needle = str(spec.get("area", "")).lower()
        if not area_needle:
            continue
        if any(_finding_matches_expected_area(f, area_needle) for f in findings):
            hits += 1
    return hits / len(expected_specs)


def finding_status_accuracy(
    expected_specs: list[dict[str, Any]],
    findings: list[Finding],
) -> float:
    """Fraction of expected specs where a matching finding meets min_status rank."""
    if not expected_specs:
        return 1.0
    ok = 0
    for spec in expected_specs:
        area_needle = str(spec.get("area", "")).lower()
        min_s = str(spec.get("min_status", "at_risk"))
        need = status_rank(min_s)
        matched = [f for f in findings if _finding_matches_expected_area(f, area_needle)]
        if not matched:
            continue
        best = max(matched, key=lambda f: status_rank(f.status.value))
        if status_rank(best.status.value) >= need:
            ok += 1
    return ok / len(expected_specs)


_DOC_MARKERS: dict[str, list[str]] = {
    "dpia": ["Data Protection Impact Assessment", "Description of Processing"],
    "ropa": ["Records of Processing", "Processing Activities"],
    "checklist": ["Compliance Checklist"],
    "consent_flow": ["Consent Flow"],
    "retention_policy": ["Retention Policy", "Retention Schedule"],
}


def document_completeness_score(
    documents: dict[str, str],
    expected_types: list[str],
) -> float:
    """Fraction of expected doc types whose rendered markdown contains required markers."""
    if not expected_types:
        return 1.0
    ok = 0
    for dt in expected_types:
        content = documents.get(dt, "")
        markers = _DOC_MARKERS.get(dt, [])
        if markers and all(m in content for m in markers):
            ok += 1
        elif not markers and content.strip():
            ok += 1
        elif not markers:
            ok += 0
    return ok / len(expected_types)


def legacy_replay_ids(sid: str) -> list[str]:
    """IDs that may appear in older replay JSON files."""
    out = [sid]
    if sid.startswith("SC-V-"):
        out.append("SC-" + sid[5:])
    elif re.match(r"^SC-\d{3}$", sid):
        out.append(f"SC-V-{sid[3:]}")
    return out
