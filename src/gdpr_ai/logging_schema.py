"""SQLite DDL and incremental migrations for the query log table."""

from __future__ import annotations

import sqlite3


def ensure_query_log_schema(conn: sqlite3.Connection) -> None:
    """Create ``query_logs`` if needed and add columns present in older deployments."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS query_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            scenario_text TEXT NOT NULL,
            extracted_entities_json TEXT,
            classified_topics_json TEXT,
            retrieved_chunks_count INTEGER,
            retrieved_articles TEXT,
            report_json TEXT,
            violations_count INTEGER,
            severity TEXT,
            latency_total_ms INTEGER,
            latency_extract_ms INTEGER,
            latency_classify_ms INTEGER,
            latency_retrieve_ms INTEGER,
            latency_reason_ms INTEGER,
            latency_validate_ms INTEGER,
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER,
            estimated_cost_eur REAL,
            model_reasoning TEXT,
            feedback TEXT CHECK (feedback IS NULL OR feedback IN ('up', 'down'))
        )
        """
    )
    cur = conn.execute("PRAGMA table_info(query_logs)")
    have = {row[1] for row in cur.fetchall()}
    if "latency_ms" in have and "latency_total_ms" not in have:
        conn.execute("ALTER TABLE query_logs ADD COLUMN latency_total_ms INTEGER")
        conn.execute(
            "UPDATE query_logs SET latency_total_ms = latency_ms WHERE latency_total_ms IS NULL"
        )
        have.add("latency_total_ms")
    for col, decl in (
        ("extracted_entities_json", "TEXT"),
        ("classified_topics_json", "TEXT"),
        ("retrieved_articles", "TEXT"),
        ("violations_count", "INTEGER"),
        ("severity", "TEXT"),
        ("latency_extract_ms", "INTEGER"),
        ("latency_classify_ms", "INTEGER"),
        ("latency_retrieve_ms", "INTEGER"),
        ("latency_reason_ms", "INTEGER"),
        ("latency_validate_ms", "INTEGER"),
        ("input_tokens", "INTEGER"),
        ("output_tokens", "INTEGER"),
        ("model_reasoning", "TEXT"),
        ("analysis_mode", "TEXT"),
    ):
        if col not in have:
            conn.execute(f"ALTER TABLE query_logs ADD COLUMN {col} {decl}")
            have.add(col)
    if "extracted_entities" in have and "extracted_entities_json" not in have:
        conn.execute("ALTER TABLE query_logs ADD COLUMN extracted_entities_json TEXT")
        conn.execute(
            "UPDATE query_logs SET extracted_entities_json = extracted_entities "
            "WHERE extracted_entities_json IS NULL"
        )
    if "classified_topics" in have and "classified_topics_json" not in have:
        conn.execute("ALTER TABLE query_logs ADD COLUMN classified_topics_json TEXT")
        conn.execute(
            "UPDATE query_logs SET classified_topics_json = classified_topics "
            "WHERE classified_topics_json IS NULL"
        )
    conn.commit()
