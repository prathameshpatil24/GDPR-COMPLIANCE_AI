"""Generate and fetch compliance documents."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from gdpr_ai.api.deps import get_repository
from gdpr_ai.api.schemas import (
    COMPLIANCE_DOC_TYPES,
    DocumentGenerateRequest,
    DocumentGenerateResponse,
    DocumentGetResponse,
    GeneratedDocument,
)
from gdpr_ai.compliance.generator import generate_documents
from gdpr_ai.compliance.schemas import ComplianceAssessment
from gdpr_ai.db.repository import AppRepository
from gdpr_ai.logger import get_query

router = APIRouter()


@router.post("/documents/generate", response_model=DocumentGenerateResponse)
async def generate_documents_route(
    body: DocumentGenerateRequest,
    repo: AppRepository = Depends(get_repository),
) -> DocumentGenerateResponse:
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
    for key in sorted(to_render):
        doc_id = str(uuid.uuid4())
        content = all_docs[key]
        await repo.create_document(
            document_id=doc_id,
            analysis_id=body.analysis_id,
            doc_type=key,
            content=content,
            format="markdown",
        )
        out.append(
            GeneratedDocument(
                document_id=doc_id,
                doc_type=key,
                content=content,
            )
        )
    return DocumentGenerateResponse(analysis_id=body.analysis_id, documents=out)


@router.get("/documents/{document_id}", response_model=DocumentGetResponse)
async def get_document(
    document_id: str,
    repo: AppRepository = Depends(get_repository),
) -> DocumentGetResponse:
    """Return a previously generated document."""
    meta = await repo.get_document(document_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentGetResponse(
        document_id=meta.id,
        analysis_id=meta.analysis_id,
        doc_type=meta.doc_type,
        content=meta.content,
        format=meta.format,
        created_at=meta.created_at,
    )
