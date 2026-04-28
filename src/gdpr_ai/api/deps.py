"""FastAPI dependencies."""

from __future__ import annotations

from gdpr_ai.config import settings
from gdpr_ai.db.repository import AppRepository


def get_repository() -> AppRepository:
    """Application SQLite repository (path from settings)."""
    return AppRepository(settings.sqlite_path)
