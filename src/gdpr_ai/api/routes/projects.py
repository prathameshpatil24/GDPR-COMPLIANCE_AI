"""Project resources backed by the application SQLite database."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from gdpr_ai.api.deps import get_repository
from gdpr_ai.api.schemas import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from gdpr_ai.db.database import DEFAULT_USER_ID
from gdpr_ai.db.repository import AppRepository

router = APIRouter()


async def _project_response(repo: AppRepository, project_id: str) -> ProjectResponse | None:
    row = await repo.get_project(project_id)
    if not row:
        return None
    analyses = await repo.list_analyses_for_project(project_id)
    return ProjectResponse(
        id=row.id,
        name=row.name,
        system_description=row.system_description,
        created_at=row.created_at,
        updated_at=row.updated_at,
        analyses=[a.id for a in analyses],
    )


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    body: ProjectCreateRequest,
    repo: AppRepository = Depends(get_repository),
) -> ProjectResponse:
    """Create a new project."""
    await repo.ensure_user(DEFAULT_USER_ID)
    row = await repo.create_project(
        user_id=DEFAULT_USER_ID,
        name=body.name.strip(),
        system_description=body.system_description.strip(),
    )
    out = await _project_response(repo, row.id)
    assert out is not None
    return out


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(repo: AppRepository = Depends(get_repository)) -> ProjectListResponse:
    """List all projects."""
    rows = await repo.list_projects()
    projects: list[ProjectResponse] = []
    for r in rows:
        pr = await _project_response(repo, r.id)
        if pr:
            projects.append(pr)
    return ProjectListResponse(projects=projects)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    repo: AppRepository = Depends(get_repository),
) -> ProjectResponse:
    """Return one project."""
    out = await _project_response(repo, project_id)
    if not out:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    repo: AppRepository = Depends(get_repository),
) -> ProjectResponse:
    """Update project metadata."""
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    name = str(data["name"]).strip() if "name" in data else None
    sdesc = str(data["system_description"]).strip() if "system_description" in data else None
    updated = await repo.update_project(project_id, name=name, system_description=sdesc)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    out = await _project_response(repo, project_id)
    assert out is not None
    return out
