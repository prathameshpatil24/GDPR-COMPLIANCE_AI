#!/usr/bin/env python3
"""Chunk raw JSON sources, embed with bge-m3, persist to ChromaDB + BM25 sidecar."""
from __future__ import annotations

import json
import logging
import pickle
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from rank_bm25 import BM25Okapi

from gdpr_ai.config import settings
from gdpr_ai.knowledge.bm25_tokens import bm25_tokenize
from gdpr_ai.knowledge.chunk_split import chunk_text_by_tokens
from gdpr_ai.knowledge.embeddings import embed_texts
from gdpr_ai.knowledge.gdpr_text import citation_title, text_pieces_for_gdpr_article
from gdpr_ai.knowledge.topics import (
    tags_for_bdsg_section,
    tags_for_edpb,
    tags_for_gdpr_article,
    tags_for_gdpr_recital,
    tags_for_ttdsg_section,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


@dataclass(slots=True)
class ChunkRow:
    chunk_id: str
    text: str
    metadata: dict[str, str]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_json(path: Path) -> Any:
    if not path.exists():
        logger.warning("Missing %s — skipping", path)
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def gdpr_chunks(data: list[dict[str, Any]]) -> list[ChunkRow]:
    rows: list[ChunkRow] = []
    default_url = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679"
    for art in data:
        num = str(art["article_number"])
        tags = tags_for_gdpr_article(num)
        full = f"Art. {num} GDPR — {citation_title(num, str(art.get('title', '')))}"
        page_url = str(art.get("source_url", default_url))
        publisher = str(art.get("source_publisher", "European Union"))
        license_id = str(art.get("license", "eu-public-domain"))
        pieces = text_pieces_for_gdpr_article(art, settings.embedding_model)
        for idx, (para_lbl, txt) in enumerate(pieces):
            cid = str(uuid.uuid4())
            rows.append(
                ChunkRow(
                    chunk_id=cid,
                    text=txt,
                    metadata={
                        "source": "gdpr",
                        "article_number": f"Art. {num}",
                        "chapter": str(art.get("chapter", "")),
                        "chunk_index": str(idx),
                        "paragraph": str(para_lbl),
                        "source_url": page_url,
                        "language": "en",
                        "topic_tags": ",".join(tags),
                        "full_citation": full,
                        "license": license_id,
                        "source_publisher": publisher,
                    },
                )
            )
    return rows


def gdpr_recital_chunks(data: list[dict[str, Any]]) -> list[ChunkRow]:
    rows: list[ChunkRow] = []
    default_url = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679"
    for r in data:
        num = str(r["number"])
        try:
            n_int = int(num)
        except ValueError:
            n_int = 0
        tags = tags_for_gdpr_recital(n_int)
        title = f"Recital {num} GDPR"
        body = str(r.get("text", ""))
        txt = f"{title}\n\n{body}" if body.strip() else title
        page_url = str(r.get("source_url", default_url))
        publisher = str(r.get("source_publisher", "European Union"))
        license_id = str(r.get("license", "eu-public-domain"))
        cid = str(uuid.uuid4())
        rows.append(
            ChunkRow(
                chunk_id=cid,
                text=txt,
                metadata={
                    "source": "gdpr_recital",
                    "article_number": f"Recital {num}",
                    "chapter": "Recitals",
                    "chunk_index": "0",
                    "paragraph": "0",
                    "source_url": page_url,
                    "language": "en",
                    "topic_tags": ",".join(tags),
                    "full_citation": title,
                    "license": license_id,
                    "source_publisher": publisher,
                },
            )
        )
    return rows


def german_law_chunks(rows_in: list[dict[str, Any]], source: str) -> list[ChunkRow]:
    out: list[ChunkRow] = []
    for sec in rows_in:
        text = sec.get("text_en") or ""
        if not text.strip():
            logger.warning("Skipping %s %s without English text", source, sec.get("section_number"))
            continue
        title = sec.get("title", "")
        section_number = sec.get("section_number", "")
        url = sec.get("source_url", "")
        if source == "bdsg":
            tags = tags_for_bdsg_section(section_number, title)
            cite = f"{section_number} BDSG — {title}"
        else:
            tags = tags_for_ttdsg_section(section_number, title)
            cite = f"{section_number} TTDSG — {title}"
        pieces = chunk_text_by_tokens(text, settings.embedding_model)
        for idx, txt in enumerate(pieces):
            cid = str(uuid.uuid4())
            out.append(
                ChunkRow(
                    chunk_id=cid,
                    text=txt,
                    metadata={
                        "source": source,
                        "article_number": section_number,
                        "chapter": "",
                        "chunk_index": str(idx),
                        "source_url": url,
                        "language": "en",
                        "topic_tags": ",".join(tags),
                        "full_citation": cite,
                        "license": "german-public-law",
                        "source_publisher": "gesetze-im-internet.de",
                    },
                )
            )
    return out


def edpb_chunks(data: list[dict[str, Any]]) -> list[ChunkRow]:
    out: list[ChunkRow] = []
    for g in data:
        gid = str(g.get("guideline_id", ""))
        title = str(g.get("title", ""))
        page_url = str(g.get("source_page_url", ""))
        pdf_url = str(g.get("pdf_url", ""))
        tags = tags_for_edpb(title)
        adopted = str(g.get("adopted_date", ""))
        for sidx, sec in enumerate(g.get("sections", []) or []):
            heading = str(sec.get("heading", ""))
            body = str(sec.get("text", ""))
            pieces = chunk_text_by_tokens(body, settings.embedding_model)
            for idx, txt in enumerate(pieces):
                cid = str(uuid.uuid4())
                cite = f"EDPB Guideline {gid} — {heading}"
                out.append(
                    ChunkRow(
                        chunk_id=cid,
                        text=f"{heading}\n\n{txt}" if heading else txt,
                        metadata={
                            "source": "edpb",
                            "article_number": gid,
                            "chapter": adopted,
                            "chunk_index": f"{sidx}-{idx}",
                            "source_url": pdf_url or page_url,
                            "language": "en",
                            "topic_tags": ",".join(tags),
                            "full_citation": cite,
                            "license": "eu-reuse-policy",
                            "source_publisher": "European Data Protection Board",
                        },
                    )
                )
    return out


def main() -> None:
    all_rows: list[ChunkRow] = []
    if (articles := load_json(RAW / "gdpr_articles.json")) is not None:
        all_rows.extend(gdpr_chunks(articles))
    if (recitals := load_json(RAW / "gdpr_recitals.json")) is not None:
        all_rows.extend(gdpr_recital_chunks(recitals))
    if (bdsg := load_json(RAW / "bdsg_sections.json")) is not None:
        all_rows.extend(german_law_chunks(bdsg, "bdsg"))
    if (ttdsg := load_json(RAW / "ttdsg_sections.json")) is not None:
        all_rows.extend(german_law_chunks(ttdsg, "ttdsg"))
    if (edpb := load_json(RAW / "edpb_guidelines.json")) is not None:
        all_rows.extend(edpb_chunks(edpb))

    if not all_rows:
        raise SystemExit("No chunks built — run scrapers first.")

    processed = settings.processed_dir
    processed.mkdir(parents=True, exist_ok=True)
    jsonl_path = processed / "chunks.jsonl"
    _write_jsonl(
        jsonl_path,
        [{"chunk_id": r.chunk_id, "text": r.text, "metadata": r.metadata} for r in all_rows],
    )

    texts = [r.text for r in all_rows]
    logger.info("Embedding %s chunks", len(texts))
    embeddings = embed_texts(settings.embedding_model, texts, batch_size=8)

    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    coll_name = settings.chroma_collection
    try:
        client.delete_collection(coll_name)
    except Exception:  # noqa: BLE001
        pass
    coll = client.create_collection(name=coll_name, metadata={"hnsw:space": "cosine"})
    coll.add(
        ids=[r.chunk_id for r in all_rows],
        documents=texts,
        embeddings=embeddings,
        metadatas=[r.metadata for r in all_rows],
    )

    tokenized = [bm25_tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized)
    settings.bm25_index_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.bm25_index_path.open("wb") as fh:
        pickle.dump({"bm25": bm25, "chunk_ids": [r.chunk_id for r in all_rows]}, fh)

    sizes = [len(t.split()) for t in texts]
    logger.info("Done. chunks=%s avg_words=%.1f", len(texts), sum(sizes) / max(1, len(sizes)))
    logger.info("Chroma path: %s", settings.chroma_path)
    logger.info("BM25 path: %s", settings.bm25_index_path)


if __name__ == "__main__":
    main()
