"""SQLite-backed query logging and lightweight analytics."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gdpr_ai.config import settings
from gdpr_ai.logging_schema import ensure_query_log_schema


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@dataclass(slots=True)
class QueryLogRecord:
    """One persisted query log row."""

    id: str
    timestamp: str
    scenario_text: str
    extracted_entities: dict[str, Any] | None
    classified_topics: dict[str, Any] | None
    retrieved_chunks_count: int
    retrieved_articles: str | None
    report_json: dict[str, Any] | None
    violations_count: int
    severity: str | None
    latency_total_ms: int
    latency_extract_ms: int
    latency_classify_ms: int
    latency_retrieve_ms: int
    latency_reason_ms: int
    latency_validate_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_eur: float
    model_reasoning: str | None
    feedback: str | None
    analysis_mode: str | None


def log_query(
    *,
    scenario_text: str,
    extracted_entities: dict[str, Any] | None,
    classified_topics: dict[str, Any] | None,
    retrieved_chunks_count: int,
    retrieved_articles: str | None,
    report_json: dict[str, Any] | None,
    violations_count: int,
    severity: str | None,
    latency_total_ms: int,
    latency_extract_ms: int,
    latency_classify_ms: int,
    latency_retrieve_ms: int,
    latency_reason_ms: int,
    latency_validate_ms: int,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    estimated_cost_eur: float,
    model_reasoning: str | None,
    feedback: str | None = None,
    query_id: str | None = None,
    analysis_mode: str | None = None,
) -> str:
    """Insert a query log row and return its primary key."""
    qid = query_id or str(uuid.uuid4())
    ts = datetime.now(tz=UTC).isoformat()
    conn = _connect(settings.log_db_path)
    try:
        ensure_query_log_schema(conn)
        conn.execute(
            """
            INSERT INTO query_logs (
                id, timestamp, scenario_text, extracted_entities_json, classified_topics_json,
                retrieved_chunks_count, retrieved_articles, report_json, violations_count, severity,
                latency_total_ms, latency_extract_ms, latency_classify_ms, latency_retrieve_ms,
                latency_reason_ms, latency_validate_ms, input_tokens, output_tokens, total_tokens,
                estimated_cost_eur, model_reasoning, feedback, analysis_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                qid,
                ts,
                scenario_text,
                json.dumps(extracted_entities) if extracted_entities is not None else None,
                json.dumps(classified_topics) if classified_topics is not None else None,
                retrieved_chunks_count,
                retrieved_articles,
                json.dumps(report_json) if report_json is not None else None,
                violations_count,
                severity,
                latency_total_ms,
                latency_extract_ms,
                latency_classify_ms,
                latency_retrieve_ms,
                latency_reason_ms,
                latency_validate_ms,
                input_tokens,
                output_tokens,
                total_tokens,
                estimated_cost_eur,
                model_reasoning,
                feedback,
                analysis_mode,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return qid


def _row_to_record(row: sqlite3.Row) -> QueryLogRecord:
    d = dict(row)

    def loads(raw: object) -> dict[str, Any] | None:
        if raw is None:
            return None
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        return json.loads(str(raw))

    raw_ent = d.get("extracted_entities_json")
    if raw_ent is None:
        raw_ent = d.get("extracted_entities")
    raw_top = d.get("classified_topics_json")
    if raw_top is None:
        raw_top = d.get("classified_topics")
    raw_rep = d.get("report_json")
    lat_total = d.get("latency_total_ms")
    if lat_total is None:
        lat_total = d.get("latency_ms")
    return QueryLogRecord(
        id=str(d["id"]),
        timestamp=str(d.get("timestamp", "")),
        scenario_text=str(d["scenario_text"]),
        extracted_entities=loads(raw_ent) if raw_ent else None,
        classified_topics=loads(raw_top) if raw_top else None,
        retrieved_chunks_count=int(d.get("retrieved_chunks_count") or 0),
        retrieved_articles=d.get("retrieved_articles"),
        report_json=loads(raw_rep) if raw_rep else None,
        violations_count=int(d.get("violations_count") or 0),
        severity=d.get("severity"),
        latency_total_ms=int(lat_total or 0),
        latency_extract_ms=int(d.get("latency_extract_ms") or 0),
        latency_classify_ms=int(d.get("latency_classify_ms") or 0),
        latency_retrieve_ms=int(d.get("latency_retrieve_ms") or 0),
        latency_reason_ms=int(d.get("latency_reason_ms") or 0),
        latency_validate_ms=int(d.get("latency_validate_ms") or 0),
        input_tokens=int(d.get("input_tokens") or 0),
        output_tokens=int(d.get("output_tokens") or 0),
        total_tokens=int(d.get("total_tokens") or 0),
        estimated_cost_eur=float(d.get("estimated_cost_eur") or 0.0),
        model_reasoning=d.get("model_reasoning"),
        feedback=d.get("feedback"),
        analysis_mode=d.get("analysis_mode"),
    )


def get_query(query_id: str) -> QueryLogRecord | None:
    """Return one log row by id, or None if missing."""
    conn = _connect(settings.log_db_path)
    try:
        ensure_query_log_schema(conn)
        cur = conn.execute("SELECT * FROM query_logs WHERE id = ?", (query_id,))
        row = cur.fetchone()
        return _row_to_record(row) if row else None
    finally:
        conn.close()


def list_recent_queries(limit: int = 10) -> list[QueryLogRecord]:
    """Return the most recent queries, newest first."""
    conn = _connect(settings.log_db_path)
    try:
        ensure_query_log_schema(conn)
        cur = conn.execute(
            "SELECT * FROM query_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [_row_to_record(r) for r in cur.fetchall()]
    finally:
        conn.close()


def set_feedback(query_id: str, rating: str) -> bool:
    """Set thumbs up/down feedback. Returns False if id not found."""
    if rating not in {"up", "down"}:
        raise ValueError("rating must be 'up' or 'down'")
    conn = _connect(settings.log_db_path)
    try:
        ensure_query_log_schema(conn)
        cur = conn.execute("UPDATE query_logs SET feedback = ? WHERE id = ?", (rating, query_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_stats() -> dict[str, float]:
    """Aggregate counters and averages for all logged queries."""
    conn = _connect(settings.log_db_path)
    try:
        ensure_query_log_schema(conn)
        total = conn.execute("SELECT COUNT(*) FROM query_logs").fetchone()[0]
        if not total:
            return {
                "total_queries": 0.0,
                "avg_latency_ms": 0.0,
                "avg_cost_eur": 0.0,
                "total_cost_eur": 0.0,
                "total_tokens": 0.0,
                "avg_violations_per_query": 0.0,
            }
        row = conn.execute(
            """
            SELECT AVG(latency_total_ms), AVG(estimated_cost_eur), SUM(estimated_cost_eur),
                   SUM(total_tokens), AVG(COALESCE(violations_count, 0))
            FROM query_logs
            """
        ).fetchone()
        return {
            "total_queries": float(total),
            "avg_latency_ms": float(row[0] or 0.0),
            "avg_cost_eur": float(row[1] or 0.0),
            "total_cost_eur": float(row[2] or 0.0),
            "total_tokens": float(row[3] or 0.0),
            "avg_violations_per_query": float(row[4] or 0.0),
        }
    finally:
        conn.close()
