"""Hybrid retrieval over ChromaDB (dense) plus an optional BM25 sidecar index."""

from __future__ import annotations

import logging
import pickle
from collections.abc import Iterable, Sequence
from pathlib import Path

import chromadb

from gdpr_ai.config import settings
from gdpr_ai.exceptions import KnowledgeBaseError
from gdpr_ai.knowledge.bm25_tokens import bm25_tokenize
from gdpr_ai.knowledge.embeddings import embed_texts
from gdpr_ai.models import ClassifiedTopics, ExtractedEntities, RetrievedChunk

logger = logging.getLogger(__name__)


def _dense_query_text(query: str, topics: ClassifiedTopics) -> str:
    """Augment the user query for dense retrieval when topics imply consent or transparency."""
    tags = {x.strip().lower() for x in (topics.topics or []) if x.strip()}
    segments: list[str] = [query]
    if tags & {"consent", "legal-basis", "direct-marketing", "object"}:
        segments.append(
            "EU GDPR Article 5 principles relating to processing of personal data; "
            "lawful basis for processing (Article 6); conditions for consent (Article 7); "
            "right to object to direct marketing (Article 21)."
        )
    if tags & {"transparency", "information", "data-subject-rights"}:
        segments.append(
            "EU GDPR: transparency and information obligations when obtaining personal data "
            "(Articles 12 and 13)."
        )
    if tags & {"transfers"}:
        segments.append(
            "EU GDPR Chapter V: transfers of personal data to third countries "
            "(Articles 44 general principle; 46 appropriate safeguards "
            "including standard contractual clauses)."
        )
    if tags & {"security-and-breaches", "security-of-processing"}:
        segments.append(
            "EU GDPR Article 32 security of processing and Article 25 "
            "data protection by design and by default."
        )
    return "\n".join(segments) if len(segments) > 1 else query


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _topic_overlap(meta_tags: str, topics: Iterable[str]) -> bool:
    tags = {t.strip() for t in (meta_tags or "").split(",") if t.strip()}
    want = {t.strip() for t in topics if t.strip()}
    return bool(tags & want)


def retrieve(
    query: str,
    topics: ClassifiedTopics,
    entities: ExtractedEntities,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Retrieve top-k chunks using dense search fused with BM25 when available."""
    k = top_k if top_k is not None else settings.top_k
    chroma_dir = settings.chroma_path
    if not chroma_dir.exists():
        raise KnowledgeBaseError(
            "ChromaDB directory not found. Build the knowledge base first "
            "(see README / scripts/chunk_and_embed.py)."
        )

    client = chromadb.PersistentClient(path=str(chroma_dir))
    try:
        coll = client.get_collection(settings.chroma_collection)
    except Exception as exc:  # noqa: BLE001
        raise KnowledgeBaseError(f"Unable to open Chroma collection: {exc}") from exc

    dense_query = _dense_query_text(query, topics)
    q_vec = embed_texts(settings.embedding_model, [dense_query])[0]
    n_probe = max(k * 4, 40)
    raw = coll.query(
        query_embeddings=[q_vec],  # type: ignore[arg-type]
        n_results=min(n_probe, max(1, coll.count())),
        include=["documents", "metadatas", "distances"],
    )
    q_ids = raw["ids"]
    q_docs = raw["documents"]
    q_metas = raw["metadatas"]
    q_dists = raw["distances"]
    assert q_ids is not None, "Chroma query returned no ids"
    assert q_docs is not None, "Chroma query returned no documents"
    assert q_metas is not None, "Chroma query returned no metadatas"
    assert q_dists is not None, "Chroma query returned no distances"
    ids = q_ids[0]
    docs = q_docs[0]
    metas = q_metas[0]
    dists = q_dists[0]

    dense_scores: dict[str, float] = {}
    payload: dict[str, tuple[str, dict[str, str]]] = {}
    for cid, doc, meta, dist in zip(ids, docs, metas, dists, strict=True):
        # Lower distance => closer for L2 space used by Chroma defaults.
        dense_scores[cid] = 1.0 / (1.0 + float(dist))
        # Chroma returns metadata values as strings/numbers; normalize to str.
        meta_str = {str(k): "" if v is None else str(v) for k, v in (meta or {}).items()}
        payload[cid] = (doc or "", meta_str)

    topic_list = topics.topics or ["gdpr"]
    filtered = {
        cid: s
        for cid, s in dense_scores.items()
        if _topic_overlap(payload[cid][1].get("topic_tags", ""), topic_list)
    }
    # When topics match some chunks, demote (not drop) the rest so consent queries
    # do not lose GDPR articles to tangentially similar breach guidance, while
    # still backfilling if the filter set is small.
    if not filtered:
        candidates = dense_scores
    else:
        d = float(settings.topic_demote_factor)
        candidates = {cid: s if cid in filtered else d * s for cid, s in dense_scores.items()}

    bm25_scores: dict[str, float] = {}
    bm25_path: Path = settings.bm25_index_path
    if bm25_path.exists():
        with bm25_path.open("rb") as fh:
            bundle = pickle.load(fh)
        bm25 = bundle["bm25"]
        bm25_ids: list[str] = bundle["chunk_ids"]
        q_tokens = bm25_tokenize(dense_query)
        scores = bm25.get_scores(q_tokens)
        for cid, sc in zip(bm25_ids, scores, strict=True):
            bm25_scores[cid] = float(sc)

    fused: dict[str, float] = {}
    dense_n = _normalize({cid: candidates[cid] for cid in candidates})
    bm25_n = _normalize({cid: bm25_scores[cid] for cid in candidates if cid in bm25_scores})
    for cid in candidates:
        d = dense_n.get(cid, 0.0)
        b = bm25_n.get(cid, 0.0) if bm25_scores else 0.0
        if bm25_scores:
            base = 0.5 * d + 0.5 * b
        else:
            base = d
        meta = payload[cid][1]
        if entities.jurisdiction.lower().startswith("germ") and meta.get("source") in {
            "bdsg",
            "ttdsg",
        }:
            base += 0.1
        art_lbl = meta.get("article_number", "").lower()
        if entities.special_categories_present and (
            "special-categories" in meta.get("topic_tags", "") or art_lbl.startswith("art. 9")
        ):
            base += 0.15
        fused[cid] = base

    ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)
    out: list[RetrievedChunk] = []
    seen_text: set[str] = set()
    for cid, score in ranked:
        text, meta = payload[cid]
        sig = text[:200]
        if sig in seen_text:
            continue
        seen_text.add(sig)
        d_score = dense_scores.get(cid, 0.0)
        b_score = bm25_scores.get(cid, 0.0) if bm25_scores else 0.0
        out.append(
            RetrievedChunk(
                chunk_id=cid,
                text=text,
                metadata=meta,
                similarity_score=float(score),
                dense_score=float(d_score),
                bm25_score=float(b_score),
            )
        )
        if len(out) >= k:
            break
    return out


def retrieve_gdpr_chunks_by_article_numbers(
    article_numbers: Sequence[str],
) -> list[RetrievedChunk]:
    """Fetch GDPR corpus chunks by ``article_number`` metadata (e.g. ``Art. 32``).

    Guarantees primary legal text is present for compliance grounding regardless of
    dense-search ranking.
    """
    labels_ordered: list[str] = []
    for raw in article_numbers:
        s = str(raw).strip()
        if not s.isdigit():
            continue
        lab = f"Art. {s}"
        if lab not in labels_ordered:
            labels_ordered.append(lab)
    if not labels_ordered:
        return []

    chroma_dir = settings.chroma_path
    if not chroma_dir.exists():
        logger.warning("ChromaDB missing; cannot fetch mandatory GDPR article chunks")
        return []

    client = chromadb.PersistentClient(path=str(chroma_dir))
    try:
        coll = client.get_collection(settings.chroma_collection)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Mandatory article fetch: cannot open collection: %s", exc)
        return []

    out: list[RetrievedChunk] = []
    seen_ids: set[str] = set()
    for lab in labels_ordered:
        try:
            got = coll.get(where={"article_number": lab}, include=["documents", "metadatas"])
        except Exception as exc:  # noqa: BLE001
            logger.debug("Mandatory article get failed for %s: %s", lab, exc)
            continue
        ids = got.get("ids") or []
        docs = got.get("documents") or []
        metas = got.get("metadatas") or []
        for cid, doc, meta in zip(ids, docs, metas, strict=False):
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            meta_str = {str(k): "" if v is None else str(v) for k, v in (meta or {}).items()}
            out.append(
                RetrievedChunk(
                    chunk_id=cid,
                    text=doc or "",
                    metadata=meta_str,
                    similarity_score=1.0,
                    dense_score=1.0,
                    bm25_score=0.0,
                )
            )
    return out


def default_v2_collection_names() -> list[str]:
    """Chroma collection names for v2 auxiliary knowledge."""
    return [
        settings.chroma_collection_dpia,
        settings.chroma_collection_ropa,
        settings.chroma_collection_tom,
        settings.chroma_collection_consent,
        settings.chroma_collection_ai_act,
    ]


def retrieve_multi_collection(
    query: str,
    collection_names: Sequence[str] | None = None,
    *,
    top_k_per_collection: int = 8,
    top_k: int = 20,
) -> list[RetrievedChunk]:
    """Dense retrieval across multiple Chroma collections; merge by relevance (no BM25 fusion).

    Each result's metadata includes ``chroma_collection`` with the source collection name.
    """
    if collection_names is not None:
        names = list(collection_names)
    else:
        names = default_v2_collection_names()
    chroma_dir = settings.chroma_path
    if not chroma_dir.exists():
        raise KnowledgeBaseError(
            "ChromaDB directory not found. Build the knowledge base first "
            "(see README / scripts/chunk_and_embed.py)."
        )
    client = chromadb.PersistentClient(path=str(chroma_dir))
    q_vec = embed_texts(settings.embedding_model, [query])[0]

    candidates: list[tuple[float, RetrievedChunk]] = []
    for coll_name in names:
        try:
            coll = client.get_collection(coll_name)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping missing v2 collection %s: %s", coll_name, exc)
            continue
        n_docs = max(1, coll.count())
        n_res = min(top_k_per_collection, n_docs)
        raw = coll.query(
            query_embeddings=[q_vec],  # type: ignore[arg-type]
            n_results=n_res,
            include=["documents", "metadatas", "distances"],
        )
        q_ids = raw["ids"]
        q_docs = raw["documents"]
        q_metas = raw["metadatas"]
        q_dists = raw["distances"]
        assert q_ids is not None, "Chroma query returned no ids"
        assert q_docs is not None, "Chroma query returned no documents"
        assert q_metas is not None, "Chroma query returned no metadatas"
        assert q_dists is not None, "Chroma query returned no distances"
        ids = q_ids[0]
        docs = q_docs[0]
        metas = q_metas[0]
        dists = q_dists[0]
        for cid, doc, meta, dist in zip(ids, docs, metas, dists, strict=True):
            score = 1.0 / (1.0 + float(dist))
            meta_str = {str(k): "" if v is None else str(v) for k, v in (meta or {}).items()}
            meta_str["chroma_collection"] = coll_name
            candidates.append(
                (
                    score,
                    RetrievedChunk(
                        chunk_id=cid,
                        text=doc or "",
                        metadata=meta_str,
                        similarity_score=float(score),
                        dense_score=float(score),
                        bm25_score=0.0,
                    ),
                )
            )

    candidates.sort(key=lambda x: x[0], reverse=True)
    out: list[RetrievedChunk] = []
    seen_text: set[str] = set()
    for _sc, ch in candidates:
        sig = ch.text[:200]
        if sig in seen_text:
            continue
        seen_text.add(sig)
        out.append(ch)
        if len(out) >= top_k:
            break
    return out
