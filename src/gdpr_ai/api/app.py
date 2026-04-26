"""FastAPI application factory and ASGI entrypoint."""
from __future__ import annotations

from fastapi import FastAPI

from gdpr_ai.api.routes import analyze, documents, projects

app = FastAPI(
    title="GDPR AI",
    description="GDPR compliance analysis and assessment tool",
    version="2.0.0",
)

app.include_router(analyze.router, prefix="/api/v1", tags=["analysis"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "version": "2.0.0"}
