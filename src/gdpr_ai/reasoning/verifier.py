"""Completeness verification pass (v4)."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from gdpr_ai.config import settings
from gdpr_ai.llm.client import (
    LLMResult,
    complete_text,
    extract_json_object_with_repair,
    is_truncated_json_error,
)
from gdpr_ai.prompts import load_prompt

logger = logging.getLogger(__name__)


def _normalize_verification_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Coerce list entries the model sometimes returns as objects into strings."""
    out = dict(data)
    for key in ("critical_gaps", "suggested_additions"):
        raw = out.get(key)
        if not isinstance(raw, list):
            continue
        normalized: list[str] = []
        for x in raw:
            if isinstance(x, str):
                normalized.append(x)
            elif isinstance(x, dict):
                normalized.append(json.dumps(x, ensure_ascii=False))
            else:
                normalized.append(str(x))
        out[key] = normalized
    return out


class ChecklistItem(BaseModel):
    """One checklist row from the verifier model."""

    item: str = ""
    status: str = ""
    detail: str = ""
    missing_articles: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    """Structured output of the completeness reviewer."""

    completeness_score: float = Field(ge=0.0, le=1.0)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    critical_gaps: list[str] = Field(default_factory=list)
    suggested_additions: list[str] = Field(default_factory=list)
    needs_supplementary_pass: bool = False
    missing_articles: list[str] = Field(default_factory=list)


async def verify_completeness(
    *,
    original_query: str,
    analysis_json: str,
    articles_used: list[str],
    mode: str,
) -> tuple[VerificationResult, LLMResult]:
    """Run a structured completeness check using a small reasoning model."""
    template = load_prompt("verify_completeness")
    user = template.format(
        original_query=original_query,
        analysis_json=analysis_json,
        articles_used=", ".join(articles_used) if articles_used else "(none)",
        mode=mode,
    )
    cap = 4096
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            res = await complete_text(
                model=settings.model_extract_classify,
                system="You output only JSON.",
                user=user,
                max_tokens=cap,
                temperature=0.0,
            )
            data, _ = extract_json_object_with_repair(res.text)
            if isinstance(data, dict):
                data = _normalize_verification_payload(data)
            vr = VerificationResult.model_validate(data)
            miss = list(dict.fromkeys(vr.missing_articles))
            for row in vr.checklist:
                if row.status in {"partial", "missing"}:
                    miss.extend(row.missing_articles)
            miss = list(dict.fromkeys(miss))[:32]
            gaps = vr.critical_gaps or []
            vr = vr.model_copy(
                update={
                    "missing_articles": miss,
                    "needs_supplementary_pass": bool(miss or gaps),
                }
            )
            return vr, res
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Verification parse failed (attempt %s): %s", attempt + 1, exc)
            if attempt < 2 and is_truncated_json_error(exc):
                cap += 2048
    raise last_exc  # type: ignore[misc]


def merge_missing_numeric_articles(ver: VerificationResult) -> list[str]:
    """Return article numbers suitable for ``retrieve_gdpr_chunks_by_article_numbers``."""
    import re

    out: list[str] = []
    for m in ver.missing_articles:
        s = str(m).strip()
        digits = re.findall(r"\d+", s)
        for d in digits:
            if d not in out:
                out.append(d)
    return out[:24]
