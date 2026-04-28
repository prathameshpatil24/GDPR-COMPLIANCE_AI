"""Async CRUD for users, projects, analyses, and documents."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite


@dataclass(slots=True)
class ProjectRow:
    """Persisted project."""

    id: str
    user_id: str
    name: str
    system_description: str
    data_map_json: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class AnalysisRow:
    """Persisted analysis run."""

    id: str
    project_id: str
    mode: str
    input_text: str | None
    result_json: str
    llm_cost_usd: float | None
    duration_seconds: float | None
    created_at: str


@dataclass(slots=True)
class DocumentRow:
    """Persisted generated document."""

    id: str
    analysis_id: str
    doc_type: str
    content: str
    format: str
    created_at: str


class AppRepository:
    """All application DB access (one connection per operation)."""

    def __init__(self, db_path: Path) -> None:
        self._path = db_path

    async def _setup(self, conn: aiosqlite.Connection) -> None:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")

    async def ensure_user(self, user_id: str | None = None) -> str:
        """Create a user row if missing; returns the id."""
        uid = user_id or str(uuid.uuid4())
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            await conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
            await conn.commit()
        return uid

    async def create_project(
        self,
        *,
        user_id: str,
        name: str,
        system_description: str,
        data_map_json: str | None = None,
    ) -> ProjectRow:
        """Insert a project and return it."""
        pid = str(uuid.uuid4())
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            await conn.execute(
                """
                INSERT INTO projects (id, user_id, name, system_description, data_map_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (pid, user_id, name, system_description, data_map_json),
            )
            await conn.commit()
        out = await self.get_project(pid)
        assert out is not None
        return out

    async def get_project(self, project_id: str) -> ProjectRow | None:
        """Load one project by id."""
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            cur = await conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = await cur.fetchone()
        return _project_from_row(row) if row else None

    async def list_projects(self) -> list[ProjectRow]:
        """List projects newest first."""
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            cur = await conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
            rows = await cur.fetchall()
        return [_project_from_row(r) for r in rows]

    async def update_project(
        self,
        project_id: str,
        *,
        name: str | None = None,
        system_description: str | None = None,
        data_map_json: str | None = None,
    ) -> ProjectRow | None:
        """Update allowed fields; returns the row or None if missing."""
        existing = await self.get_project(project_id)
        if not existing:
            return None
        new_name = name if name is not None else existing.name
        new_desc = (
            system_description if system_description is not None else existing.system_description
        )
        new_map = data_map_json if data_map_json is not None else existing.data_map_json
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            await conn.execute(
                """
                UPDATE projects
                SET name = ?, system_description = ?, data_map_json = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_name, new_desc, new_map, project_id),
            )
            await conn.commit()
        return await self.get_project(project_id)

    async def create_analysis(
        self,
        *,
        analysis_id: str,
        project_id: str,
        mode: str,
        input_text: str | None,
        result: dict[str, Any],
        llm_cost_usd: float | None,
        duration_seconds: float | None,
    ) -> AnalysisRow:
        """Persist one analysis result; ``analysis_id`` should match the query log id."""
        proj = await self.get_project(project_id)
        if not proj:
            raise ValueError(f"Unknown project_id {project_id!r}")
        blob = json.dumps(result)
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            await conn.execute(
                """
                INSERT INTO analyses (
                    id, project_id, mode, input_text, result_json, llm_cost_usd, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    project_id,
                    mode,
                    input_text,
                    blob,
                    llm_cost_usd,
                    duration_seconds,
                ),
            )
            await conn.commit()
        out = await self.get_analysis(analysis_id)
        assert out is not None
        return out

    async def get_analysis(self, analysis_id: str) -> AnalysisRow | None:
        """Fetch one analysis."""
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            cur = await conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
            row = await cur.fetchone()
        return _analysis_from_row(row) if row else None

    async def list_analyses_for_project(self, project_id: str) -> list[AnalysisRow]:
        """All analyses for a project, newest first."""
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            cur = await conn.execute(
                """
                SELECT * FROM analyses WHERE project_id = ?
                ORDER BY created_at DESC
                """,
                (project_id,),
            )
            rows = await cur.fetchall()
        return [_analysis_from_row(r) for r in rows]

    async def create_document(
        self,
        *,
        document_id: str,
        analysis_id: str,
        doc_type: str,
        content: str,
        format: str = "markdown",
    ) -> DocumentRow:
        """Store generated document text."""
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            await conn.execute(
                """
                INSERT INTO documents (id, analysis_id, doc_type, content, format)
                VALUES (?, ?, ?, ?, ?)
                """,
                (document_id, analysis_id, doc_type, content, format),
            )
            await conn.commit()
        out = await self.get_document(document_id)
        assert out is not None
        return out

    async def get_document(self, document_id: str) -> DocumentRow | None:
        """Fetch one document."""
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            cur = await conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            row = await cur.fetchone()
        return _document_from_row(row) if row else None

    async def list_documents_for_analysis(self, analysis_id: str) -> list[DocumentRow]:
        """Documents linked to an analysis."""
        async with aiosqlite.connect(self._path) as conn:
            await self._setup(conn)
            cur = await conn.execute(
                """
                SELECT * FROM documents WHERE analysis_id = ?
                ORDER BY created_at DESC
                """,
                (analysis_id,),
            )
            rows = await cur.fetchall()
        return [_document_from_row(r) for r in rows]


def _project_from_row(row: aiosqlite.Row) -> ProjectRow:
    return ProjectRow(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        name=str(row["name"]),
        system_description=str(row["system_description"]),
        data_map_json=row["data_map_json"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _analysis_from_row(row: aiosqlite.Row) -> AnalysisRow:
    return AnalysisRow(
        id=str(row["id"]),
        project_id=str(row["project_id"]),
        mode=str(row["mode"]),
        input_text=row["input_text"],
        result_json=str(row["result_json"]),
        llm_cost_usd=float(row["llm_cost_usd"]) if row["llm_cost_usd"] is not None else None,
        duration_seconds=float(row["duration_seconds"])
        if row["duration_seconds"] is not None
        else None,
        created_at=str(row["created_at"]),
    )


def _document_from_row(row: aiosqlite.Row) -> DocumentRow:
    return DocumentRow(
        id=str(row["id"]),
        analysis_id=str(row["analysis_id"]),
        doc_type=str(row["doc_type"]),
        content=str(row["content"]),
        format=str(row["format"]),
        created_at=str(row["created_at"]),
    )


__all__ = ["AnalysisRow", "AppRepository", "DocumentRow", "ProjectRow"]
