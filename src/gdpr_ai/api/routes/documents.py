"""Generate and fetch compliance documents."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from gdpr_ai.api.schemas import (
    COMPLIANCE_DOC_TYPES,
    DocumentGenerateRequest,
    DocumentGenerateResponse,
    DocumentGetResponse,
    GeneratedDocument,
)
from gdpr_ai.compliance.generator import generate_documents
from gdpr_ai.compliance.schemas import ComplianceAssessment
from gdpr_ai.logger import get_query

router = APIRouter()

_DOC_INDEX: dict[str, dict[str, Any]] = {}


def reset_document_store_for_tests() -> None:
    """Clear generated document metadata (tests only)."""
    _DOC_INDEX.clear()


@router.post("/documents/generate", response_model=DocumentGenerateResponse)
def generate_documents_route(body: DocumentGenerateRequest) -> DocumentGenerateResponse:
    """Render markdown documents from a stored compliance assessment."""
    rec = get_query(body.analysis_id)
    if not rec or not rec.report_json:
        raise HTTPException(status_code=404, detail="Analysis not found or has no stored result")
    mode = rec.analysis_mode or ""
    if mode != "compliance_assessment":
        raise HTTPException(
            status_code=400,
            detail="Document generation is only available for compliance_assessment runs",
        )
    try:
        assessment = ComplianceAssessment.model_validate(rec.report_json)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400,
            detail=f"Stored result is not a compliance assessment: {exc}",
        ) from exc

    all_docs = generate_documents(assessment)
    wanted = set(body.doc_types) if body.doc_types else set(all_docs.keys())
    unknown = wanted - COMPLIANCE_DOC_TYPES
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid doc_types for compliance: {sorted(unknown)}",
        )
    to_render = wanted & set(all_docs.keys())
    if not to_render:
        raise HTTPException(status_code=400, detail="No documents to render")

    out: list[GeneratedDocument] = []
    ts = datetime.now(tz=UTC).isoformat()
    for key in sorted(to_render):
        doc_id = str(uuid.uuid4())
        content = all_docs[key]
        _DOC_INDEX[doc_id] = {
            "analysis_id": body.analysis_id,
            "doc_type": key,
            "content": content,
            "created_at": ts,
        }
        out.append(GeneratedDocument(document_id=doc_id, doc_type=key, content=content))
    return DocumentGenerateResponse(analysis_id=body.analysis_id, documents=out)


@router.get("/documents/{document_id}", response_model=DocumentGetResponse)
def get_document(document_id: str) -> DocumentGetResponse:
    """Return a previously generated document."""
    meta = _DOC_INDEX.get(document_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentGetResponse(
        document_id=document_id,
        analysis_id=str(meta["analysis_id"]),
        doc_type=str(meta["doc_type"]),
        content=str(meta["content"]),
        format="markdown",
        created_at=meta.get("created_at"),
    )
