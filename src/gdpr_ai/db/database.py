"""Application SQLite connection helpers and startup initialization."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import aiosqlite

from gdpr_ai.db.migrations import apply_migrations

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "00000000-0000-4000-8000-000000000000"
DEFAULT_PROJECT_ID = "00000000-0000-4000-8000-000000000001"

_pool: dict[str, Any] = {}


async def init_app_db(db_path: Path) -> None:
    """Create schema and seed a default user/project for unassigned analyses."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await apply_migrations(conn)
        await conn.execute(
            "INSERT OR IGNORE INTO users (id) VALUES (?)",
            (DEFAULT_USER_ID,),
        )
        await conn.execute(
            """
            INSERT OR IGNORE INTO projects (id, user_id, name, system_description)
            VALUES (?, ?, ?, ?)
            """,
            (
                DEFAULT_PROJECT_ID,
                DEFAULT_USER_ID,
                "Default",
                "Analyses not assigned to a named project.",
            ),
        )
        await conn.commit()
    logger.info("Application database initialised at %s", db_path)


async def close_app_db() -> None:
    """Release pooled connections (reserved for future pooling)."""
    _pool.clear()
