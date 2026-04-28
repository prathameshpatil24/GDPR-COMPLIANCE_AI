"""Tests for application SQLite repository."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from gdpr_ai.db.database import DEFAULT_PROJECT_ID, init_app_db
from gdpr_ai.db.repository import AppRepository


@pytest.fixture
def repo(tmp_path: Path) -> AppRepository:
    db = tmp_path / "r.sqlite"
    asyncio.run(init_app_db(db))
    return AppRepository(db)


@pytest.mark.asyncio
async def test_init_db_creates_default_project(repo: AppRepository) -> None:
    row = await repo.get_project(DEFAULT_PROJECT_ID)
    assert row is not None
    assert row.name == "Default"


@pytest.mark.asyncio
async def test_project_crud(repo: AppRepository) -> None:
    await repo.ensure_user("u1")
    p = await repo.create_project(
        user_id="u1",
        name="Alpha",
        system_description="Processes PII",
    )
    got = await repo.get_project(p.id)
    assert got is not None
    assert got.name == "Alpha"
    listed = await repo.list_projects()
    assert any(x.id == p.id for x in listed)
    upd = await repo.update_project(p.id, name="Beta")
    assert upd is not None
    assert upd.name == "Beta"


@pytest.mark.asyncio
async def test_analysis_and_documents(repo: AppRepository) -> None:
    await repo.create_analysis(
        analysis_id="a1",
        project_id=DEFAULT_PROJECT_ID,
        mode="compliance_assessment",
        input_text="hello",
        result={"ok": True},
        llm_cost_usd=0.01,
        duration_seconds=1.5,
    )
    row = await repo.get_analysis("a1")
    assert row is not None
    assert json.loads(row.result_json) == {"ok": True}
    by_proj = await repo.list_analyses_for_project(DEFAULT_PROJECT_ID)
    assert any(x.id == "a1" for x in by_proj)

    await repo.create_document(
        document_id="d1",
        analysis_id="a1",
        doc_type="checklist",
        content="# Hi",
    )
    doc = await repo.get_document("d1")
    assert doc is not None
    assert doc.content == "# Hi"
    docs = await repo.list_documents_for_analysis("a1")
    assert len(docs) == 1
