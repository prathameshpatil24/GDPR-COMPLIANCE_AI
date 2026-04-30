"""Orchestrate deterministic map, graph expansion, full-text chunks, and semantic fallback."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from gdpr_ai.config import settings
from gdpr_ai.models import ClassifiedTopics, ExtractedEntities, RetrievedChunk
from gdpr_ai.retrieval.article_map import (
    load_article_map,
    primary_article_number,
    resolve_articles,
    resolve_topic_key,
)
from gdpr_ai.retrieval.article_store import (
    assemble_supplementary_summaries,
    eurlex_source_url,
    get_article_text,
    keyword_match_score,
    targeting_keywords,
)
from gdpr_ai.retrieval.cross_ref_graph import expand_articles

logger = logging.getLogger(__name__)


def _article_nums_from_chunks(chunks: list[RetrievedChunk]) -> set[str]:
    """Extract primary numeric article ids referenced in chunk metadata."""
    out: set[str] = set()
    for c in chunks:
        lbl = str(c.metadata.get("article_number", ""))
        m = re.search(r"(\d+)", lbl)
        if m:
            out.add(m.group(1))
        assembled = str(c.metadata.get("assembled_articles", ""))
        for part in re.split(r"[\n,]+", assembled):
            p = part.strip()
            if p.isdigit():
                out.add(p)
    return out


def _dedupe_chunks_by_id(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Preserve order; drop duplicate chunk ids."""
    seen: set[str] = set()
    out: list[RetrievedChunk] = []
    for c in chunks:
        if c.chunk_id in seen:
            continue
        seen.add(c.chunk_id)
        out.append(c)
    return out


def _with_retrieval_source(chunk: RetrievedChunk, source: str) -> RetrievedChunk:
    """Return a copy of chunk with ``retrieval_source`` set (explainability)."""
    meta = dict(chunk.metadata)
    meta["retrieval_source"] = source
    return chunk.model_copy(update={"metadata": meta})


def _rank_novel_in_layer(article_nums: set[str], keywords: list[str]) -> list[str]:
    """Order articles: higher query keyword overlap with full text first, then numeric."""
    nums = {primary_article_number(a) for a in article_nums}
    return sorted(
        nums,
        key=lambda a: (-keyword_match_score(get_article_text(a) or "", keywords), int(a)),
    )


def _pick_supplement_articles(
    *,
    novel_arts: set[str],
    mapped_norm: set[str],
    query_keywords: list[str],
    cap: int,
) -> list[str]:
    """Layer 1 (map) novel articles first, then layer 2 (graph-only), each keyword-ranked."""
    if cap <= 0 or not novel_arts:
        return []
    novel_from_map = novel_arts & mapped_norm
    novel_from_graph = novel_arts - mapped_norm
    ordered: list[str] = []
    for bucket in (
        _rank_novel_in_layer(novel_from_map, query_keywords),
        _rank_novel_in_layer(novel_from_graph, query_keywords),
    ):
        for a in bucket:
            if len(ordered) >= cap:
                return ordered
            ordered.append(a)
    return ordered


def prioritize_novel_articles(
    novel_articles: set[str],
    matched_topics: list[str],
    article_map: dict[str, Any],
    max_articles: int,
    *,
    query_keywords: list[str] | None = None,
) -> list[str]:
    """
    Rank novel articles by how many matched topics reference them.

    An article referenced by multiple matched topics ranks above one referenced by a
    single topic. Tie-break: keyword overlap with full article text, then numeric id.
    """
    if max_articles <= 0 or not novel_articles:
        return []
    nums = sorted({primary_article_number(a) for a in novel_articles}, key=int)
    scores: dict[str, int] = {a: 0 for a in nums}
    for topic in matched_topics:
        spec = article_map.get(topic)
        if not isinstance(spec, dict):
            continue
        topic_articles = {primary_article_number(str(x)) for x in (spec.get("gdpr_articles") or [])}
        for article in nums:
            if article in topic_articles:
                scores[article] += 1
    kws = query_keywords or []
    ranked = sorted(
        nums,
        key=lambda a: (-scores[a], -keyword_match_score(get_article_text(a) or "", kws), int(a)),
    )
    return ranked[:max_articles]


def _matched_topic_keys(topic_slugs: list[str]) -> list[str]:
    """Deduplicated YAML topic keys for classifier topic slugs."""
    seen: set[str] = set()
    out: list[str] = []
    for slug in topic_slugs or []:
        k = resolve_topic_key(slug)
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


@dataclass
class RetrievalResult:
    """Outputs of the v4 retrieval path plus explainability metadata."""

    chunks: list[RetrievedChunk]
    articles_from_map: set[str] = field(default_factory=set)
    articles_from_graph: set[str] = field(default_factory=set)
    articles_from_semantic: set[str] = field(default_factory=set)
    all_articles: set[str] = field(default_factory=set)
    full_text_context: str = ""
    recitals: set[str] = field(default_factory=set)
    retrieval_metadata: dict[str, Any] = field(default_factory=dict)


def _entity_keywords(entities: ExtractedEntities) -> list[str]:
    parts: list[str] = []
    parts.extend(entities.actors)
    parts.extend(entities.data_types)
    parts.extend(entities.processing_activities)
    parts.extend(entities.legal_bases_mentioned)
    if entities.summary:
        parts.append(entities.summary)
    return parts


def _synthetic_chunk(
    *,
    chunk_id: str,
    article_num: str,
    text: str,
    tier: str,
    recital_nums: list[str] | None = None,
) -> RetrievedChunk:
    label = f"Art. {primary_article_number(article_num)}"
    meta: dict[str, str] = {
        "article_number": label,
        "source": "gdpr_fulltext",
        "source_url": eurlex_source_url(),
        "topic_tags": "",
        "retrieval_tier": tier,
        "full_citation": f"{label} GDPR",
    }
    if recital_nums:
        meta["recitals"] = ",".join(recital_nums)
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        metadata=meta,
        similarity_score=1.0,
        dense_score=1.0,
        bm25_score=0.0,
    )


def _fulltext_chunks_for_articles(
    articles: set[str],
    *,
    tier: str,
    block: str,
) -> list[RetrievedChunk]:
    """One synthetic chunk holding the assembled multi-article block."""
    if not block.strip():
        return []
    nums = sorted({primary_article_number(a) for a in articles}, key=int)
    cid = f"fulltext:gdpr:{'-'.join(nums[:12])}" + (":more" if len(nums) > 12 else "")
    joined = "\n".join(nums)
    ch = _synthetic_chunk(
        chunk_id=cid,
        article_num=nums[0] if nums else "0",
        text=block,
        tier=tier,
    )
    ch.metadata["assembled_articles"] = joined[:2000]
    return [ch]


def retrieve_deterministic(
    query: str,
    topics: ClassifiedTopics,
    entities: ExtractedEntities,
    *,
    semantic_retrieve_fn: Callable[..., list[RetrievedChunk]],
    top_k: int | None = None,
    mode: str = "violation",
    use_semantic_fallback: bool = True,
    graph_depth: int | None = None,
    max_context_tokens: int | None = None,
) -> RetrievalResult:
    """Semantic-first retrieval with deterministic supplement for map/graph gaps only.

    Runs hybrid semantic search as the baseline, then adds targeted GDPR full text only for
    articles produced by the article map and cross-reference graph that are **not** already
    represented in semantic chunk metadata—capped and prioritized to limit dilution.
    """
    k = top_k if top_k is not None else settings.top_k
    mode_l = (mode or "violation").lower()
    if mode_l == "compliance":
        depth_eff = (
            settings.deterministic_graph_depth_compliance if graph_depth is None else graph_depth
        )
        max_supplement = settings.deterministic_max_supplement_compliance
    else:
        depth_eff = (
            settings.deterministic_graph_depth_violation if graph_depth is None else graph_depth
        )
        max_supplement = settings.deterministic_max_supplement_violation
    # Legacy hook: deterministic_max_context_tokens no longer applies to merged chunks
    # (supplement uses truncated summaries per article). Kept for API stability.
    _ = (
        settings.deterministic_max_context_tokens
        if max_context_tokens is None
        else max_context_tokens
    )

    kw_entities = _entity_keywords(entities)
    query_keywords = targeting_keywords(query, kw_entities)
    gdpr_map, recitals, _bdsg, _ttdsg = resolve_articles(
        topics.topics or [],
        kw_entities,
        text_blob=query,
    )
    mapped_norm = {primary_article_number(a) for a in gdpr_map}
    expanded = expand_articles(mapped_norm, depth=depth_eff)
    graph_only = expanded - mapped_norm
    all_art = set(mapped_norm) | set(expanded)

    semantic: list[RetrievedChunk] = []
    sem_arts: set[str] = set()
    if use_semantic_fallback:
        semantic = semantic_retrieve_fn(query, topics, entities, top_k=k)
        sem_arts = _article_nums_from_chunks(semantic)

    all_article_union = all_art | sem_arts
    novel_arts = all_art - sem_arts
    if mode_l == "compliance":
        topic_defs = load_article_map().get("topics") or {}
        topic_defs = topic_defs if isinstance(topic_defs, dict) else {}
        keys = _matched_topic_keys(list(topics.topics or []))
        injected_ordered = prioritize_novel_articles(
            novel_arts,
            keys,
            topic_defs,
            max_supplement,
            query_keywords=query_keywords,
        )
    else:
        injected_ordered = _pick_supplement_articles(
            novel_arts=novel_arts,
            mapped_norm=mapped_norm,
            query_keywords=query_keywords,
            cap=max_supplement,
        )
    injected_set = set(injected_ordered)

    logger.info("Semantic search found articles: %s", sorted(sem_arts, key=int))
    logger.info("Deterministic map found articles: %s", sorted(all_art, key=int))
    logger.info("Novel articles (deterministic only): %s", sorted(novel_arts, key=int))
    logger.info(
        "Injecting %s supplementary articles (cap: %s, mode: %s)",
        len(injected_ordered),
        max_supplement,
        mode_l,
    )

    meta: dict[str, Any] = {
        "retrieval_mode": mode_l,
        "mapped_article_count": len(mapped_norm),
        "expanded_article_count": len(all_art),
        "recital_count": len(recitals),
        "novel_article_count": len(novel_arts),
        "supplement_injected_articles": injected_ordered,
        "max_deterministic_supplement_articles": max_supplement,
        "deterministic_graph_depth": depth_eff,
    }

    article_sources: dict[str, list[str]] = {}
    for a in sem_arts:
        article_sources.setdefault(a, []).append("semantic")
    for a in mapped_norm:
        article_sources.setdefault(a, []).append("map")
    for a in graph_only:
        article_sources.setdefault(a, []).append("graph")
    for key, paths in article_sources.items():
        article_sources[key] = sorted(frozenset(paths))
    meta["article_sources"] = article_sources

    supp_chunks: list[RetrievedChunk] = []
    supp_block = ""
    if injected_set:
        supp_block = assemble_supplementary_summaries(injected_ordered)
        raw_supp = _fulltext_chunks_for_articles(
            injected_set,
            tier="deterministic_supplement",
            block=supp_block,
        )
        supp_chunks = [_with_retrieval_source(c, "deterministic_map_graph") for c in raw_supp]

    semantic_tagged = [_with_retrieval_source(c, "semantic") for c in semantic]
    out_chunks = _dedupe_chunks_by_id(semantic_tagged + supp_chunks)

    return RetrievalResult(
        chunks=out_chunks,
        articles_from_map=mapped_norm,
        articles_from_graph=graph_only,
        articles_from_semantic=sem_arts,
        all_articles=all_article_union,
        full_text_context=supp_block,
        recitals=set(recitals),
        retrieval_metadata=meta,
    )
