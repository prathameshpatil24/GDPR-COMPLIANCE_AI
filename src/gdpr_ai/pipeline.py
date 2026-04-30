"""End-to-end GDPR analysis pipeline (extract → classify → retrieve → reason → validate)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from gdpr_ai.config import settings
from gdpr_ai.exceptions import ExtractionFailed, HallucinationDetected, ReasoningFailed
from gdpr_ai.llm.client import (
    LLMResult,
    complete_text,
    extract_json_object_with_repair,
    is_truncated_json_error,
)
from gdpr_ai.logger import log_query
from gdpr_ai.models import AnalysisReport, ClassifiedTopics, ExtractedEntities, RetrievedChunk
from gdpr_ai.prompts import load_prompt, render_prompt
from gdpr_ai.reasoning.verifier import merge_missing_numeric_articles, verify_completeness
from gdpr_ai.retriever import retrieve, retrieve_gdpr_chunks_by_article_numbers

logger = logging.getLogger(__name__)


def _retrieved_articles_summary(chunks: list[RetrievedChunk]) -> str:
    """Comma-separated unique citation labels from chunk metadata (for logs)."""
    refs = sorted(
        {
            str(c.metadata.get("article_number", "")).strip()
            for c in chunks
            if c.metadata.get("article_number")
        }
    )
    return ",".join(refs)


_ALLOWED_TOPICS = {
    "legal-basis",
    "consent",
    "contract",
    "legitimate-interest",
    "special-categories",
    "data-subject-rights",
    "information",
    "transparency",
    "access",
    "rectification",
    "erasure",
    "restriction",
    "portability",
    "object",
    "automated-decisions",
    "controller-processor",
    "security-of-processing",
    "security-and-breaches",
    "notification-to-dpa",
    "notification-to-subjects",
    "dpia",
    "dpo",
    "transfers",
    "employment",
    "children",
    "direct-marketing",
    "telemedia",
    "gdpr",
    "germany",
}


async def _call_stage_json(
    *,
    model: str,
    system_header: str,
    user: str,
    max_tokens: int,
    retries: int = 3,
) -> tuple[dict[str, Any], LLMResult]:
    last_err: Exception | None = None
    current_cap = max_tokens
    for attempt in range(retries + 1):
        try:
            res = await complete_text(
                model=model,
                system=system_header,
                user=user,
                max_tokens=current_cap,
            )
            data, _ = extract_json_object_with_repair(res.text)
            return data, res
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("Stage parse failed (attempt %s): %s", attempt + 1, exc)
            if attempt < retries and is_truncated_json_error(exc):
                current_cap = min(current_cap + 4096, 32768)
            await asyncio.sleep(0.4 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def _grounding_check(report: AnalysisReport, chunks: list[RetrievedChunk]) -> None:
    """Ensure citations map to retrieved evidence."""
    id_set = {c.chunk_id for c in chunks}
    urls = {c.metadata.get("source_url", "") for c in chunks}
    for v in report.violations:
        if v.supporting_chunk_ids and not set(v.supporting_chunk_ids).issubset(id_set):
            raise HallucinationDetected("Violation references unknown chunk ids")
        if not v.source_url or v.source_url not in urls:
            raise HallucinationDetected("Violation references unknown or empty source_url")


async def extract_entities(scenario: str) -> tuple[ExtractedEntities, LLMResult]:
    """Run the extraction prompt."""
    system = "You output only JSON."
    user = render_prompt("extract", scenario=scenario)
    data, res = await _call_stage_json(
        model=settings.model_extract_classify,
        system_header=system,
        user=user,
        max_tokens=1024,
    )
    try:
        entities = ExtractedEntities.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        raise ExtractionFailed(str(exc)) from exc
    return entities, res


async def classify_topics(
    scenario: str, entities: ExtractedEntities
) -> tuple[ClassifiedTopics, LLMResult]:
    """Run topic classification."""
    system = "You output only JSON."
    user = render_prompt(
        "classify",
        scenario=scenario,
        entities_json=json.dumps(entities.model_dump(), ensure_ascii=False),
    )
    data, res = await _call_stage_json(
        model=settings.model_extract_classify,
        system_header=system,
        user=user,
        max_tokens=512,
    )
    topics = [t for t in data.get("topics", []) if t in _ALLOWED_TOPICS]
    if not topics:
        topics = ["gdpr"]
    ct = ClassifiedTopics(topics=topics[:4], rationale=str(data.get("rationale", "")))
    return ct, res


def _dedupe_chunks_by_id(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Preserve order; drop duplicate chunk ids."""
    seen: set[str] = set()
    out: list[RetrievedChunk] = []
    for c in chunks:
        if c.chunk_id in seen:
            continue
        seen.add(c.chunk_id)
        out.append(c)
    return out


def _articles_from_chunks(chunks: list[RetrievedChunk]) -> list[str]:
    """Collect unique numeric article ids referenced in chunk metadata."""
    found: list[str] = []
    seen: set[str] = set()
    import re

    for c in chunks:
        lbl = str(c.metadata.get("article_number", ""))
        for m in re.finditer(r"(\d+)", lbl):
            d = m.group(1)
            if d not in seen:
                seen.add(d)
                found.append(d)
        assembled = str(c.metadata.get("assembled_articles", ""))
        for part in assembled.split(","):
            part = part.strip()
            if part.isdigit() and part not in seen:
                seen.add(part)
                found.append(part)
    return found


def _serialize_chunk_for_prompt(c: RetrievedChunk) -> dict[str, Any]:
    """JSON-serialize one chunk for reasoning / validation prompts."""
    return {
        "chunk_id": c.chunk_id,
        "text": c.text,
        "metadata": c.metadata,
        "scores": {
            "fused": c.similarity_score,
            "dense": c.dense_score,
            "bm25": c.bm25_score,
        },
    }


def _chunks_for_prompt(chunks: list[RetrievedChunk]) -> str:
    """Build retrieved-context JSON with primary (semantic) vs supplementary sections."""
    primary: list[RetrievedChunk] = []
    supplementary: list[RetrievedChunk] = []
    for c in chunks:
        if c.metadata.get("retrieval_source") == "deterministic_map_graph":
            supplementary.append(c)
        else:
            primary.append(c)
    primary_payload = json.dumps(
        [_serialize_chunk_for_prompt(c) for c in primary],
        ensure_ascii=False,
    )
    supplementary_payload = json.dumps(
        [_serialize_chunk_for_prompt(c) for c in supplementary],
        ensure_ascii=False,
    )
    n = len(primary)
    return (
        f"[Primary evidence from semantic search — {n} relevant excerpts]\n\n"
        f"{primary_payload}\n\n"
        "[Additional regulatory context — for reference only, do not cite unless "
        "directly relevant to the specific query]\n\n"
        f"{supplementary_payload}"
    )


async def reason_report(
    scenario: str,
    entities: ExtractedEntities,
    topics: ClassifiedTopics,
    chunks: list[RetrievedChunk],
) -> tuple[AnalysisReport, LLMResult]:
    """Run the legal reasoning prompt."""
    system = "You output only JSON."
    addon = load_prompt("reason_confidence_addon")
    user = render_prompt(
        "reason",
        scenario=scenario,
        entities_json=json.dumps(entities.model_dump(), ensure_ascii=False),
        topics_json=json.dumps(topics.model_dump(), ensure_ascii=False),
        chunks_json=_chunks_for_prompt(chunks),
    )
    user = f"{user}\n\n{addon}"
    data, res = await _call_stage_json(
        model=settings.model_reasoning,
        system_header=system,
        user=user,
        max_tokens=settings.max_tokens,
    )
    data["extracted_entities"] = entities.model_dump()
    data["classified_topics"] = topics.model_dump()
    try:
        report = AnalysisReport.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        raise ReasoningFailed(str(exc)) from exc
    return report, res


async def validate_report_llm(
    draft: AnalysisReport,
    entities: ExtractedEntities,
    topics: ClassifiedTopics,
    chunks: list[RetrievedChunk],
) -> tuple[AnalysisReport, LLMResult]:
    """Run the hallucination / grounding validator prompt."""
    system = "You output only JSON."
    user = render_prompt(
        "validate",
        draft_json=json.dumps(draft.model_dump(), ensure_ascii=False),
        chunks_json=_chunks_for_prompt(chunks),
        entities_json=json.dumps(entities.model_dump(), ensure_ascii=False),
        topics_json=json.dumps(topics.model_dump(), ensure_ascii=False),
    )
    data, res = await _call_stage_json(
        model=settings.model_reasoning,
        system_header=system,
        user=user,
        max_tokens=settings.max_tokens_validate,
        retries=4,
    )
    report = AnalysisReport.model_validate(data)
    return report, res


async def run_pipeline_logged(scenario_text: str) -> tuple[AnalysisReport, str]:
    """Execute all stages with retries and logging; returns the query log id."""
    t_run = time.perf_counter()
    query_id = str(uuid.uuid4())
    total_in = total_out = 0
    total_cost = 0.0
    lat_extract = lat_classify = lat_retrieve = lat_reason = lat_validate = 0

    t0 = time.perf_counter()
    entities, er = await extract_entities(scenario_text)
    lat_extract = int((time.perf_counter() - t0) * 1000)
    total_in += er.input_tokens
    total_out += er.output_tokens
    total_cost += er.cost_eur

    t0 = time.perf_counter()
    topics, cr = await classify_topics(scenario_text, entities)
    lat_classify = int((time.perf_counter() - t0) * 1000)
    total_in += cr.input_tokens
    total_out += cr.output_tokens
    total_cost += cr.cost_eur

    t0 = time.perf_counter()
    chunks = retrieve(
        scenario_text,
        topics,
        entities,
        top_k=settings.top_k,
        mode="violation",
    )
    lat_retrieve = int((time.perf_counter() - t0) * 1000)

    async def _reason_validate_once() -> tuple[AnalysisReport, int, int]:
        """Reason, optional verify + supplementary reason, then validate."""
        nonlocal total_in, total_out, total_cost, chunks
        working = list(chunks)
        lat_r = 0
        tr = time.perf_counter()
        draft, rr = await reason_report(scenario_text, entities, topics, working)
        lat_r += int((time.perf_counter() - tr) * 1000)
        total_in += rr.input_tokens
        total_out += rr.output_tokens
        total_cost += rr.cost_eur

        if settings.verification_enabled:
            try:
                ver, ver_res = await verify_completeness(
                    original_query=scenario_text,
                    analysis_json=json.dumps(draft.model_dump(), ensure_ascii=False),
                    articles_used=_articles_from_chunks(working),
                    mode="violation",
                )
                total_in += ver_res.input_tokens
                total_out += ver_res.output_tokens
                total_cost += ver_res.cost_eur
                if settings.supplementary_reasoning_enabled:
                    extra_nums = merge_missing_numeric_articles(ver)
                    if ver.needs_supplementary_pass and extra_nums:
                        extra = retrieve_gdpr_chunks_by_article_numbers(extra_nums)
                        working = _dedupe_chunks_by_id(working + extra)
                        chunks = working
                        tr = time.perf_counter()
                        draft, rr = await reason_report(scenario_text, entities, topics, working)
                        lat_r += int((time.perf_counter() - tr) * 1000)
                        total_in += rr.input_tokens
                        total_out += rr.output_tokens
                        total_cost += rr.cost_eur
            except Exception as exc:  # noqa: BLE001
                logger.warning("Verification skipped: %s", exc)

        tv = time.perf_counter()
        validated, vr = await validate_report_llm(draft, entities, topics, working)
        lat_v = int((time.perf_counter() - tv) * 1000)
        total_in += vr.input_tokens
        total_out += vr.output_tokens
        total_cost += vr.cost_eur
        return validated, lat_r, lat_v

    last_exc: Exception | None = None
    report: AnalysisReport | None = None
    for attempt in range(2):
        try:
            validated, lat_reason, lat_validate = await _reason_validate_once()
            _grounding_check(validated, chunks)
            report = validated
            break
        except HallucinationDetected as exc:
            last_exc = exc
            logger.warning("Grounding failure (attempt %s): %s", attempt + 1, exc)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Reason/validate failure (attempt %s): %s", attempt + 1, exc)
    if report is None:
        raise ReasoningFailed(f"Unable to produce a grounded report: {last_exc}")

    latency_total = int((time.perf_counter() - t_run) * 1000)
    log_query(
        scenario_text=scenario_text,
        extracted_entities=entities.model_dump(),
        classified_topics=topics.model_dump(),
        retrieved_chunks_count=len(chunks),
        retrieved_articles=_retrieved_articles_summary(chunks),
        report_json=report.model_dump(),
        violations_count=len(report.violations),
        severity=report.severity_level,
        latency_total_ms=latency_total,
        latency_extract_ms=lat_extract,
        latency_classify_ms=lat_classify,
        latency_retrieve_ms=lat_retrieve,
        latency_reason_ms=lat_reason,
        latency_validate_ms=lat_validate,
        input_tokens=total_in,
        output_tokens=total_out,
        total_tokens=total_in + total_out,
        estimated_cost_eur=total_cost,
        model_reasoning=settings.model_reasoning,
        query_id=query_id,
        analysis_mode="violation_analysis",
    )
    return report, query_id


async def run_pipeline(scenario_text: str) -> AnalysisReport:
    """Execute all stages with retries and logging."""
    report, _ = await run_pipeline_logged(scenario_text)
    return report
