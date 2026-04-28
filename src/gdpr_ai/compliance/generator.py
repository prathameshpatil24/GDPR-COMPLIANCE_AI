"""Render compliance documents from a ComplianceAssessment using Jinja2 templates."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from gdpr_ai.compliance.schemas import (
    ComplianceAssessment,
    ComplianceStatus,
    DataCategory,
    DataMap,
    Finding,
    ProcessingPurpose,
    Sensitivity,
    StorageInfo,
)

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

_DOC_FILENAMES: dict[str, str] = {
    "dpia": "dpia.md.j2",
    "ropa": "ropa.md.j2",
    "checklist": "checklist.md.j2",
    "consent_flow": "consent_flow.md.j2",
    "retention_policy": "retention_policy.md.j2",
}


def _category_by_name(data_map: DataMap) -> dict[str, DataCategory]:
    return {c.name: c for c in data_map.data_categories}


def _findings_by_area(findings: list[Finding], needle: str) -> list[Finding]:
    n = needle.lower().strip()
    return [f for f in findings if n in f.area.lower()]


def _high_risk_findings(findings: list[Finding]) -> list[Finding]:
    return [
        f
        for f in findings
        if f.status in (ComplianceStatus.NON_COMPLIANT, ComplianceStatus.AT_RISK)
    ]


def _findings_with_remediation(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if (f.remediation or "").strip()]


def _get_subjects_for_purpose(data_map: DataMap, purpose: ProcessingPurpose) -> list[str]:
    by_name = _category_by_name(data_map)
    subjects: set[str] = set()
    for cat_name in purpose.data_categories:
        cat = by_name.get(cat_name)
        if cat:
            subjects.update(cat.subjects)
    return sorted(subjects)


def _get_recipients_for_purpose(data_map: DataMap, purpose: ProcessingPurpose) -> list[str]:
    """Destinations from data flows for this purpose's categories plus named third parties."""
    recipients: set[str] = set()
    cats = set(purpose.data_categories)
    for flow in data_map.data_flows:
        if cats.intersection(flow.data_categories):
            recipients.add(flow.destination)
    for tp in data_map.third_parties:
        recipients.add(tp.name)
    return sorted(recipients)


def _get_transfers_for_purpose(data_map: DataMap, purpose: ProcessingPurpose) -> str:
    cats = set(purpose.data_categories)
    parts: list[str] = []
    for flow in data_map.data_flows:
        if not flow.crosses_border:
            continue
        if cats.intersection(flow.data_categories):
            dest = flow.destination_country or "unspecified third country"
            parts.append(f"{flow.destination} ({dest})")
    return "; ".join(parts) if parts else ""


def _get_retention_for_purpose(data_map: DataMap, purpose: ProcessingPurpose) -> str:
    """Best-effort retention hint from storage rows (no direct purpose link in schema)."""
    periods = [s.retention_period for s in data_map.storage if s.retention_period]
    if periods:
        return "; ".join(periods)
    return ""


def _get_storage_for_category(data_map: DataMap, cat: DataCategory) -> list[StorageInfo]:
    if not data_map.storage:
        return []
    return list(data_map.storage)


def _get_purpose_for_category(data_map: DataMap, cat: DataCategory) -> str:
    names = [p.purpose for p in data_map.processing_purposes if cat.name in p.data_categories]
    return "; ".join(names) if names else ""


def _purpose_involves_special_category(data_map: DataMap, purpose: ProcessingPurpose) -> bool:
    by_name = _category_by_name(data_map)
    for cn in purpose.data_categories:
        c = by_name.get(cn)
        if c and c.sensitivity in (Sensitivity.SPECIAL_CATEGORY, Sensitivity.CRIMINAL):
            return True
    return False


def _purposes_special_category(data_map: DataMap) -> list[ProcessingPurpose]:
    return [
        p for p in data_map.processing_purposes if _purpose_involves_special_category(data_map, p)
    ]


def _purposes_needing_consent(data_map: DataMap) -> list[ProcessingPurpose]:
    out: list[ProcessingPurpose] = []
    special = {p.purpose for p in _purposes_special_category(data_map)}
    for p in data_map.processing_purposes:
        basis = (p.legal_basis_claimed or "").lower()
        if "consent" in basis:
            out.append(p)
            continue
        if p.purpose in special:
            continue
        if not p.legal_basis_claimed and any(
            k in p.purpose.lower()
            for k in ("market", "newsletter", "email", "profil", "track", "cookie")
        ):
            out.append(p)
    return out


def _purposes_legitimate_interest(data_map: DataMap) -> list[ProcessingPurpose]:
    out: list[ProcessingPurpose] = []
    for p in data_map.processing_purposes:
        basis = (p.legal_basis_claimed or "").lower()
        if "legitimate" in basis and p not in _purposes_needing_consent(data_map):
            out.append(p)
    return out


def _get_consent_reason(assessment: ComplianceAssessment, purpose: ProcessingPurpose) -> str:
    for f in assessment.findings:
        if "consent" in f.area.lower() and purpose.purpose.lower() in f.description.lower():
            return f.description
    cats = ", ".join(purpose.data_categories)
    return (
        f"Purpose {purpose.purpose!r} uses categories [{cats}]. "
        "Confirm whether consent (Articles 6(1)(a) and 7 GDPR) is appropriate and documented."
    )


def _build_template_context(
    assessment: ComplianceAssessment,
    generated_date: str,
) -> dict[str, Any]:
    data_map = assessment.data_map
    findings = assessment.findings

    def findings_by_area(needle: str) -> list[Finding]:
        return _findings_by_area(findings, needle)

    return {
        "assessment": assessment,
        "data_map": data_map,
        "generated_date": generated_date,
        "findings_by_area": findings_by_area,
        "high_risk_findings": _high_risk_findings(findings),
        "findings_with_remediation": _findings_with_remediation(findings),
        "get_subjects_for_purpose": lambda p: _get_subjects_for_purpose(data_map, p),
        "get_recipients_for_purpose": lambda p: _get_recipients_for_purpose(data_map, p),
        "get_transfers_for_purpose": lambda p: _get_transfers_for_purpose(data_map, p),
        "get_retention_for_purpose": lambda p: _get_retention_for_purpose(data_map, p),
        "get_storage_for_category": lambda c: _get_storage_for_category(data_map, c),
        "get_purpose_for_category": lambda c: _get_purpose_for_category(data_map, c),
        "purposes_needing_consent": _purposes_needing_consent(data_map),
        "purposes_legitimate_interest": _purposes_legitimate_interest(data_map),
        "purposes_special_category": _purposes_special_category(data_map),
        "get_consent_reason": lambda p: _get_consent_reason(assessment, p),
    }


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def generate_documents(
    assessment: ComplianceAssessment,
    *,
    generated_date: str | None = None,
) -> dict[str, str]:
    """Render all compliance markdown documents for ``assessment``.

    Returns a mapping of logical document keys to markdown content.
    """
    day = generated_date or date.today().isoformat()
    ctx = _build_template_context(assessment, day)
    env = _jinja_env()
    out: dict[str, str] = {}
    for key, filename in _DOC_FILENAMES.items():
        template = env.get_template(filename)
        out[key] = template.render(**ctx)
        logger.debug("Rendered compliance document %s", key)
    return out


def save_documents(documents: dict[str, str], output_dir: Path) -> list[Path]:
    """Write document markdown files under ``output_dir``; returns written paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for key, content in documents.items():
        if key not in _DOC_FILENAMES:
            logger.warning("Skipping unknown document key %s", key)
            continue
        path = output_dir / f"{key}.md"
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
