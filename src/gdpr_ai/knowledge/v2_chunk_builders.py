"""Build chunk rows for v2 auxiliary knowledge collections (DPIA, RoPA, TOM, consent, AI Act)."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gdpr_ai.config import settings
from gdpr_ai.knowledge.chunk_split import chunk_text_by_tokens

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class V2ChunkRow:
    """One row destined for a dedicated ChromaDB v2 collection."""

    chunk_id: str
    text: str
    metadata: dict[str, str]


def _tags(*parts: str) -> str:
    return ",".join(p.strip() for p in parts if p.strip())


def chunks_from_section_document(
    data: dict[str, Any],
    *,
    source_label: str,
    default_url: str,
    license_id: str,
    publisher: str,
    topic_tags: str,
) -> list[V2ChunkRow]:
    """Chunk a document shaped like EDPB guidelines: sections with heading + text."""
    rows: list[V2ChunkRow] = []
    doc_id = str(data.get("document_id", source_label))
    page_url = str(data.get("source_url", default_url))
    for sidx, sec in enumerate(data.get("sections", []) or []):
        heading = str(sec.get("heading", ""))
        body = str(sec.get("text", ""))
        pieces = chunk_text_by_tokens(body, settings.embedding_model) if body.strip() else [""]
        for idx, piece in enumerate(pieces):
            cid = str(uuid.uuid4())
            text = f"{heading}\n\n{piece}" if heading and piece.strip() else (heading or piece)
            cite = f"{doc_id} — {heading}" if heading else doc_id
            rows.append(
                V2ChunkRow(
                    chunk_id=cid,
                    text=text.strip() or heading,
                    metadata={
                        "source": source_label,
                        "article_number": doc_id,
                        "chapter": str(data.get("chapter", "")),
                        "chunk_index": f"{sidx}-{idx}",
                        "paragraph": str(sec.get("paragraph", "")),
                        "source_url": page_url,
                        "language": "en",
                        "topic_tags": topic_tags,
                        "full_citation": cite,
                        "license": license_id,
                        "source_publisher": publisher,
                    },
                )
            )
    return rows


def chunks_from_ropa_template(path: Path) -> list[V2ChunkRow]:
    """Turn RoPA template JSON into retrieval chunks (fields + narrative)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: list[V2ChunkRow] = []
    base_url = str(
        raw.get(
            "source_url", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679"
        )
    )
    # Flatten field groups into chunk-friendly text blocks
    for group_name in ("controller_record_fields", "processor_record_fields"):
        fields = raw.get(group_name, []) or []
        if not fields:
            continue
        lines = [f"Article 30 GDPR — {group_name}", ""]
        for f in fields:
            fn = str(f.get("field", ""))
            desc = str(f.get("description", ""))
            ex = str(f.get("example", ""))
            lines.append(f"- **{fn}**: {desc}")
            if ex:
                lines.append(f"  Example: {ex}")
        body = "\n".join(lines)
        cid = str(uuid.uuid4())
        rows.append(
            V2ChunkRow(
                chunk_id=cid,
                text=body,
                metadata={
                    "source": "ropa_template",
                    "article_number": "Art. 30 GDPR",
                    "chapter": group_name,
                    "chunk_index": "0",
                    "paragraph": "0",
                    "source_url": base_url,
                    "language": "en",
                    "topic_tags": _tags("controller-processor", "gdpr", "ropa"),
                    "full_citation": "Art. 30 GDPR — Records of processing activities",
                    "license": "eu-public-domain",
                    "source_publisher": "European Union",
                },
            )
        )
    art30_text = str(raw.get("article_30_excerpt", "")).strip()
    if art30_text:
        for idx, piece in enumerate(chunk_text_by_tokens(art30_text, settings.embedding_model)):
            cid = str(uuid.uuid4())
            rows.append(
                V2ChunkRow(
                    chunk_id=cid,
                    text=f"Article 30 GDPR (excerpt)\n\n{piece}",
                    metadata={
                        "source": "gdpr",
                        "article_number": "Art. 30",
                        "chapter": "Art. 30",
                        "chunk_index": str(idx),
                        "paragraph": "0",
                        "source_url": base_url,
                        "language": "en",
                        "topic_tags": _tags("controller-processor", "gdpr", "ropa"),
                        "full_citation": "Art. 30 GDPR",
                        "license": "eu-public-domain",
                        "source_publisher": "European Union",
                    },
                )
            )
    return rows


def chunks_from_tom_catalog(path: Path) -> list[V2ChunkRow]:
    """One chunk per TOM catalog entry."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: list[V2ChunkRow] = []
    base_url = str(
        raw.get(
            "source_url", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679"
        )
    )
    for entry in raw.get("entries", []) or []:
        cat = str(entry.get("category", "measure"))
        art = str(entry.get("gdpr_article", "Art. 32"))
        desc = str(entry.get("description", ""))
        examples = entry.get("implementation_examples", []) or []
        ex_txt = "\n".join(f"- {e}" for e in examples if str(e).strip())
        text = f"Technical and organisational measure: {cat}\n{desc}\n\nExamples:\n{ex_txt}"
        cid = str(uuid.uuid4())
        rows.append(
            V2ChunkRow(
                chunk_id=cid,
                text=text.strip(),
                metadata={
                    "source": "tom_catalog",
                    "article_number": art,
                    "chapter": cat,
                    "chunk_index": "0",
                    "paragraph": "0",
                    "source_url": base_url,
                    "language": "en",
                    "topic_tags": _tags("security-of-processing", "gdpr", "dpia"),
                    "full_citation": f"{art} GDPR — {cat}",
                    "license": "eu-public-domain",
                    "source_publisher": str(entry.get("publisher", "GDPR AI curated catalog")),
                },
            )
        )
    return rows


def chunks_from_ai_act(path: Path) -> list[V2ChunkRow]:
    """Chunk EU AI Act articles relevant to personal data processing."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: list[V2ChunkRow] = []
    default_url = str(
        raw.get(
            "source_url",
            "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",
        )
    )
    for art in raw.get("articles", []) or []:
        num = str(art.get("article_number", ""))
        title = str(art.get("title", ""))
        body = str(art.get("text", ""))
        pieces = chunk_text_by_tokens(body, settings.embedding_model) if body.strip() else [""]
        for idx, piece in enumerate(pieces):
            cid = str(uuid.uuid4())
            header = f"EU AI Act Article {num} — {title}".strip(" —")
            text = f"{header}\n\n{piece}" if piece.strip() else header
            rows.append(
                V2ChunkRow(
                    chunk_id=cid,
                    text=text,
                    metadata={
                        "source": "ai_act",
                        "article_number": f"AI Act Art. {num}",
                        "chapter": title,
                        "chunk_index": str(idx),
                        "paragraph": num,
                        "source_url": str(art.get("source_url", default_url)),
                        "language": "en",
                        "topic_tags": _tags("automated-decisions", "gdpr", "dpia", "transparency"),
                        "full_citation": f"Regulation (EU) 2024/1689 Article {num}",
                        "license": "eu-public-domain",
                        "source_publisher": "European Union",
                    },
                )
            )
    return rows


def load_v2_rows_from_raw(raw_dir: Path) -> dict[str, list[V2ChunkRow]]:
    """Load all v2 chunk rows from ``data/raw`` JSON files."""
    out: dict[str, list[V2ChunkRow]] = {
        settings.chroma_collection_dpia: [],
        settings.chroma_collection_ropa: [],
        settings.chroma_collection_tom: [],
        settings.chroma_collection_consent: [],
        settings.chroma_collection_ai_act: [],
    }
    dpia = raw_dir / "dpia_guidance.json"
    if dpia.exists():
        data = json.loads(dpia.read_text(encoding="utf-8"))
        out[settings.chroma_collection_dpia] = chunks_from_section_document(
            data,
            source_label="dpia_guidance",
            default_url=str(
                data.get(
                    "source_url",
                    "https://www.edpb.europa.eu/system/files/2021-10/edpb_guidelines_201901_wp248_rev01_en.pdf",
                )
            ),
            license_id="eu-reuse-policy",
            publisher="European Data Protection Board",
            topic_tags=_tags("dpia", "gdpr", "security-of-processing"),
        )
    else:
        logger.warning("Missing %s — skipping DPIA guidance chunks", dpia)

    consent = raw_dir / "consent_guidance.json"
    if consent.exists():
        data = json.loads(consent.read_text(encoding="utf-8"))
        out[settings.chroma_collection_consent] = chunks_from_section_document(
            data,
            source_label="consent_guidance",
            default_url=str(
                data.get(
                    "source_url",
                    "https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/"
                    "guidelines-052020-consent-under-regulation-2016679_en",
                )
            ),
            license_id="eu-reuse-policy",
            publisher="European Data Protection Board",
            topic_tags=_tags("consent", "legal-basis", "legitimate-interest", "gdpr"),
        )
    else:
        logger.warning("Missing %s — skipping consent guidance chunks", consent)

    ropa = raw_dir / "ropa_template.json"
    if ropa.exists():
        out[settings.chroma_collection_ropa] = chunks_from_ropa_template(ropa)
    else:
        logger.warning("Missing %s — skipping RoPA chunks", ropa)

    tom = raw_dir / "tom_catalog.json"
    if tom.exists():
        out[settings.chroma_collection_tom] = chunks_from_tom_catalog(tom)
    else:
        logger.warning("Missing %s — skipping TOM catalog chunks", tom)

    ai_act = raw_dir / "ai_act_articles.json"
    if ai_act.exists():
        out[settings.chroma_collection_ai_act] = chunks_from_ai_act(ai_act)
    else:
        logger.warning("Missing %s — skipping AI Act chunks", ai_act)

    return out
