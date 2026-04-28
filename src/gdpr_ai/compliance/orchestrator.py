"""End-to-end compliance assessment: intake → map → assess → log."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from gdpr_ai.compliance.assessor import assess_compliance
from gdpr_ai.compliance.intake import parse_freetext_input, parse_structured_input
from gdpr_ai.compliance.mapper import map_articles
from gdpr_ai.compliance.schemas import ComplianceAssessment, ComplianceStatus
from gdpr_ai.config import settings
from gdpr_ai.logger import log_query
from gdpr_ai.models import RetrievedChunk

logger = logging.getLogger(__name__)


def _chunks_summary(chunks: list[RetrievedChunk]) -> str:
    labels: set[str] = set()
    for c in chunks:
        m = c.metadata
        if m.get("article_number"):
            labels.add(str(m["article_number"]))
    return ",".join(sorted(labels))[:4000]


async def run_compliance_assessment_logged(
    input_data: dict[str, Any] | str,
) -> tuple[ComplianceAssessment, str]:
    """Run v2 compliance pipeline and log the result; returns the query log id."""
    t_run = time.perf_counter()
    query_id = str(uuid.uuid4())
    total_in = total_out = 0
    total_cost = 0.0

    t0 = time.perf_counter()
    if isinstance(input_data, str):
        data_map, ir = await parse_freetext_input(input_data)
        total_in += ir.input_tokens
        total_out += ir.output_tokens
        total_cost += ir.cost_eur
        lat_intake = int((time.perf_counter() - t0) * 1000)
        scenario_text = input_data.strip()[:8000]
    else:
        data_map = parse_structured_input(input_data)
        lat_intake = int((time.perf_counter() - t0) * 1000)
        scenario_text = data_map.system_description[:8000]

    t0 = time.perf_counter()
    article_map = map_articles(data_map)
    lat_map = int((time.perf_counter() - t0) * 1000)

    flat = []
    seen: set[str] = set()
    for lst in article_map.values():
        for c in lst:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                flat.append(c)

    t0 = time.perf_counter()
    assessment, ar = await assess_compliance(data_map, article_map)
    lat_assess = int((time.perf_counter() - t0) * 1000)
    total_in += ar.input_tokens
    total_out += ar.output_tokens
    total_cost += ar.cost_eur

    latency_total = int((time.perf_counter() - t_run) * 1000)
    flagged = (
        ComplianceStatus.NON_COMPLIANT,
        ComplianceStatus.AT_RISK,
        ComplianceStatus.INSUFFICIENT_INFO,
    )
    bad = sum(1 for f in assessment.findings if f.status in flagged)
    sev = assessment.overall_risk_level.lower()
    if sev not in {"low", "medium", "high", "critical"}:
        sev = "unknown"

    log_query(
        scenario_text=scenario_text,
        extracted_entities=None,
        classified_topics=None,
        retrieved_chunks_count=len(flat),
        retrieved_articles=_chunks_summary(flat),
        report_json=assessment.model_dump(),
        violations_count=bad,
        severity=sev,
        latency_total_ms=latency_total,
        latency_extract_ms=lat_intake,
        latency_classify_ms=0,
        latency_retrieve_ms=lat_map,
        latency_reason_ms=lat_assess,
        latency_validate_ms=0,
        input_tokens=total_in,
        output_tokens=total_out,
        total_tokens=total_in + total_out,
        estimated_cost_eur=total_cost,
        model_reasoning=settings.model_reasoning,
        feedback=None,
        query_id=query_id,
        analysis_mode="compliance_assessment",
    )
    return assessment, query_id


async def run_compliance_assessment(input_data: dict[str, Any] | str) -> ComplianceAssessment:
    """Run v2 compliance pipeline and log the result."""
    assessment, _ = await run_compliance_assessment_logged(input_data)
    return assessment
