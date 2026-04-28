"""Request and response models for the HTTP API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ALLOWED_DOC_TYPES = frozenset(
    {"dpia", "ropa", "checklist", "consent_flow", "retention_policy", "violation_report"}
)
COMPLIANCE_DOC_TYPES = frozenset(
    {"dpia", "ropa", "checklist", "consent_flow", "retention_policy"},
)


class ViolationAnalyzeRequest(BaseModel):
    """Body for violation (v1) analysis."""

    scenario: str = Field(..., min_length=10, max_length=8000)
    project_id: str | None = Field(
        None,
        description="Project to attach this run to (defaults to the built-in Default project).",
    )


class ComplianceAnalyzeRequest(BaseModel):
    """Body for compliance (v2) analysis: freetext or structured data map."""

    system_description: str | None = Field(None, max_length=32000)
    data_map: dict[str, Any] | None = None
    project_id: str | None = Field(
        None,
        description="Project to attach this run to (defaults to the built-in Default project).",
    )

    @model_validator(mode="after")
    def one_input_shape(self) -> ComplianceAnalyzeRequest:
        has_text = self.system_description is not None and self.system_description.strip() != ""
        has_map = self.data_map is not None
        if has_text == has_map:
            raise ValueError("Provide exactly one of system_description or data_map")
        return self


class AnalysisRunResponse(BaseModel):
    """Returned immediately after an analysis completes."""

    analysis_id: str
    mode: Literal["violation_analysis", "compliance_assessment"]
    result: dict[str, Any]


class AnalysisGetResponse(BaseModel):
    """Stored analysis payload."""

    analysis_id: str
    mode: str | None
    result: dict[str, Any]
    scenario_text: str
    created_at: str | None = None


class DocumentGenerateRequest(BaseModel):
    """Request generated markdown documents for a completed analysis."""

    analysis_id: str
    doc_types: list[str] | None = None

    @model_validator(mode="after")
    def validate_types(self) -> DocumentGenerateRequest:
        if self.doc_types is None:
            return self
        bad = [d for d in self.doc_types if d not in ALLOWED_DOC_TYPES]
        if bad:
            raise ValueError(f"Unknown doc_types: {bad}")
        return self


class GeneratedDocument(BaseModel):
    """One rendered document."""

    document_id: str
    doc_type: str
    content: str
    format: Literal["markdown"] = "markdown"


class DocumentGenerateResponse(BaseModel):
    """All documents produced in one call."""

    analysis_id: str
    documents: list[GeneratedDocument]


class DocumentGetResponse(BaseModel):
    """Fetch one stored document."""

    document_id: str
    analysis_id: str
    doc_type: str
    content: str
    format: str = "markdown"
    created_at: str | None = None


class ProjectCreateRequest(BaseModel):
    """Create a tracked project."""

    name: str = Field(..., min_length=1, max_length=256)
    system_description: str = Field(..., min_length=1, max_length=32000)


class ProjectUpdateRequest(BaseModel):
    """Update project fields."""

    name: str | None = Field(None, min_length=1, max_length=256)
    system_description: str | None = Field(None, min_length=1, max_length=32000)


class ProjectResponse(BaseModel):
    """Project resource."""

    id: str
    name: str
    system_description: str
    created_at: str
    updated_at: str
    analyses: list[str] = Field(default_factory=list)


class ProjectListResponse(BaseModel):
    """List of projects."""

    projects: list[ProjectResponse]


class HealthResponse(BaseModel):
    """Service health."""

    status: str
    version: str
