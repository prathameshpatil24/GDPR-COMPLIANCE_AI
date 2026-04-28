"""FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from gdpr_ai.api.routes import analyze, documents, projects
from gdpr_ai.config import settings
from gdpr_ai.db.database import close_app_db, init_app_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open resources on startup."""
    await init_app_db(settings.sqlite_path)
    yield
    await close_app_db()


app = FastAPI(
    title="GDPR AI",
    description="GDPR compliance analysis and assessment tool",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(analyze.router, prefix="/api/v1", tags=["analysis"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "version": "2.0.0"}
