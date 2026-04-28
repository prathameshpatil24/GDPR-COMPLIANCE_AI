"""DDL for the application SQLite database."""

from __future__ import annotations

import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    system_description TEXT NOT NULL,
    data_map_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    mode TEXT NOT NULL CHECK(mode IN ('violation_analysis', 'compliance_assessment')),
    input_text TEXT,
    result_json TEXT NOT NULL,
    llm_cost_usd REAL,
    duration_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analyses(id),
    doc_type TEXT NOT NULL CHECK(doc_type IN (
        'dpia', 'ropa', 'checklist', 'consent_flow', 'retention_policy', 'violation_report'
    )),
    content TEXT NOT NULL,
    format TEXT NOT NULL DEFAULT 'markdown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def apply_migrations(conn: aiosqlite.Connection) -> None:
    """Create tables if they do not exist."""
    await conn.executescript(SCHEMA_SQL)
