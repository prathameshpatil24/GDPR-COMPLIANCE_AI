"""In-memory project resources (replaced by SQLite persistence in a later phase)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from gdpr_ai.api.schemas import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)

router = APIRouter()


@dataclass
class _ProjectRow:
    id: str
    name: str
    system_description: str
    created_at: str
    updated_at: str
    analysis_ids: list[str] = field(default_factory=list)


_STORE: dict[str, _ProjectRow] = {}


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


@router.post("/projects", response_model=ProjectResponse)
def create_project(body: ProjectCreateRequest) -> ProjectResponse:
    """Create a new project."""
    pid = str(uuid.uuid4())
    ts = _now()
    row = _ProjectRow(
        id=pid,
        name=body.name.strip(),
        system_description=body.system_description.strip(),
        created_at=ts,
        updated_at=ts,
    )
    _STORE[pid] = row
    return ProjectResponse(
        id=row.id,
        name=row.name,
        system_description=row.system_description,
        created_at=row.created_at,
        updated_at=row.updated_at,
        analyses=list(row.analysis_ids),
    )


@router.get("/projects", response_model=ProjectListResponse)
def list_projects() -> ProjectListResponse:
    """List all projects."""
    items = sorted(_STORE.values(), key=lambda r: r.created_at, reverse=True)
    return ProjectListResponse(
        projects=[
            ProjectResponse(
                id=r.id,
                name=r.name,
                system_description=r.system_description,
                created_at=r.created_at,
                updated_at=r.updated_at,
                analyses=list(r.analysis_ids),
            )
            for r in items
        ]
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str) -> ProjectResponse:
    """Return one project."""
    row = _STORE.get(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=row.id,
        name=row.name,
        system_description=row.system_description,
        created_at=row.created_at,
        updated_at=row.updated_at,
        analyses=list(row.analysis_ids),
    )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, body: ProjectUpdateRequest) -> ProjectResponse:
    """Update project metadata."""
    row = _STORE.get(project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "name" in data and data["name"] is not None:
        row.name = str(data["name"]).strip()
    if "system_description" in data and data["system_description"] is not None:
        row.system_description = str(data["system_description"]).strip()
    row.updated_at = _now()
    return ProjectResponse(
        id=row.id,
        name=row.name,
        system_description=row.system_description,
        created_at=row.created_at,
        updated_at=row.updated_at,
        analyses=list(row.analysis_ids),
    )


def reset_project_store_for_tests() -> None:
    """Clear in-memory projects (tests only)."""
    _STORE.clear()
