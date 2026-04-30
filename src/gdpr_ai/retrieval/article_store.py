"""Full-text GDPR article and recital assembly for reasoning context."""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from gdpr_ai.config import settings
from gdpr_ai.paths import resolve_project_path
from gdpr_ai.retrieval.article_map import primary_article_number

logger = logging.getLogger(__name__)

_EURLEX_GDPR_HTML = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679"


def _data_path(path: Path) -> Path:
    return resolve_project_path(path)


@lru_cache(maxsize=4)
def _load_yaml(path_str: str) -> dict[str, Any]:
    p = Path(path_str)
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=2)
def _load_json_articles(path_str: str) -> list[dict[str, Any]]:
    p = Path(path_str)
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def load_article_store() -> dict[str, dict[str, Any]]:
    """Return article number -> {title, full_text, chapter, section}."""
    path = _data_path(settings.gdpr_articles_fulltext_path)
    data = _load_yaml(str(path.resolve()))
    articles_raw = data.get("articles")
    articles = articles_raw if isinstance(articles_raw, dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for k, v in articles.items():
        key = primary_article_number(str(k))
        if isinstance(v, dict):
            out[key] = v
    return out


def load_recital_store() -> dict[str, dict[str, Any]]:
    """Return recital number -> {title, full_text, ...}."""
    path = _data_path(settings.gdpr_recitals_fulltext_path)
    data = _load_yaml(str(path.resolve()))
    rec_raw = data.get("recitals")
    rec = rec_raw if isinstance(rec_raw, dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for k, v in rec.items():
        if isinstance(v, dict):
            out[str(k)] = v
    return out


def _article_from_scrape_json(num: str) -> str | None:
    path = _data_path(settings.gdpr_raw_articles_json_path)
    arts = _load_json_articles(str(path.resolve()))
    for a in arts:
        if str(a.get("article_number", "")).strip() == num:
            return str(a.get("text", "")).strip() or None
    return None


def get_article_text(article_number: str) -> str | None:
    """Return consolidated article body text for GDPR articles."""
    num = primary_article_number(article_number)
    store = load_article_store().get(num)
    if store:
        txt = str(store.get("full_text", "")).strip()
        if txt:
            return txt
    scraped = _article_from_scrape_json(num)
    if scraped:
        return scraped
    return None


def get_article_summary(article_number: str, max_chars: int = 500) -> str:
    """
    Return a truncated version of an article — first ``max_chars`` characters.

    For supplementary deterministic context, keeps excerpts short so they do not
    dominate semantic retrieval chunks.
    """
    full = get_article_text(article_number)
    if full and len(full) > max_chars:
        return full[:max_chars] + "..."
    return full or ""


def assemble_supplementary_summaries(
    articles_ordered: list[str],
    *,
    max_chars_per_article: int = 500,
) -> str:
    """Join per-article title + truncated body for deterministic supplement chunks."""
    parts: list[str] = []
    for raw in articles_ordered:
        num = primary_article_number(raw)
        title = get_article_title(num)
        summary = get_article_summary(num, max_chars=max_chars_per_article)
        if summary:
            parts.append(f"--- Article {num}: {title} ---\n{summary}\n")
    return "\n".join(parts)


def get_article_title(article_number: str) -> str:
    num = primary_article_number(article_number)
    store = load_article_store().get(num)
    if store and store.get("title"):
        return str(store["title"])
    arts = _load_json_articles(str(_data_path(settings.gdpr_raw_articles_json_path).resolve()))
    for a in arts:
        if str(a.get("article_number", "")).strip() == num:
            return str(a.get("title", "")).strip() or f"Article {num}"
    return f"Article {num}"


def get_recital_text(recital_number: str) -> str | None:
    """Return recital text if present in store or scraped recitals JSON."""
    n = str(recital_number).strip()
    store = load_recital_store().get(n)
    if store:
        t = str(store.get("full_text", "")).strip()
        if t:
            return t
    path = _data_path(settings.gdpr_raw_recitals_json_path)
    p = Path(str(path.resolve()))
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, list):
        return None
    for r in raw:
        if str(r.get("number", "")) == n:
            return str(r.get("text", "")).strip() or None
    return None


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def keyword_match_score(text: str, keywords: list[str]) -> int:
    """Count how many keywords appear as substrings in ``text`` (case-insensitive)."""
    if not text or not keywords:
        return 0
    low = text.lower()
    n = 0
    seen_kw: set[str] = set()
    for kw in keywords:
        k = kw.strip().lower()
        if len(k) < 2 or k in seen_kw:
            continue
        seen_kw.add(k)
        if k in low:
            n += 1
    return n


def targeting_keywords(query: str, entity_keyword_parts: list[str] | None = None) -> list[str]:
    """Build deduplicated keywords for paragraph targeting from the query and entity strings."""
    parts: list[str] = list(entity_keyword_parts or [])
    parts.append(query)
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        for token in re.findall(r"[\w-]{3,}", (p or "").lower()):
            if token not in seen:
                seen.add(token)
                out.append(token)
    return out


def _split_gdpr_numbered_segments(full_text: str) -> list[str]:
    """Split article body on whitespace before numbered clauses (``1.``, ``2.``, ...)."""
    t = full_text.strip()
    if not t:
        return []
    pieces = re.split(r"(?<=\S)\s+(?=\d+\.\s)", t)
    return [p.strip() for p in pieces if p.strip()]


def _trim_to_approx_tokens(text: str, max_tokens: int) -> str:
    max_chars = max(1, max_tokens * 4)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n[... truncated ...]\n"


def _targeted_body_for_article(
    article_number: str,
    keywords: list[str],
    *,
    max_tokens_per_article: int,
) -> str | None:
    """Return heading + filtered paragraphs for one article, or ``None`` if no text."""
    num = primary_article_number(article_number)
    title = get_article_title(num)
    body = get_article_text(num)
    if not body:
        return None
    segments = _split_gdpr_numbered_segments(body)
    if not segments:
        segments = [body.strip()]
    kept = [s for s in segments if keyword_match_score(s, keywords) > 0]
    if not kept:
        kept = [segments[0]]
    merged = "\n".join(kept)
    merged = _trim_to_approx_tokens(merged, max_tokens_per_article)
    return f"--- Article {num}: {title} ---\n{merged}\n"


def assemble_targeted_context(
    articles_ordered: list[str],
    query_keywords: list[str],
    *,
    max_tokens_per_article: int = 300,
) -> str:
    """Assemble compact legal context: keyword-scored paragraphs per article, capped length."""
    parts: list[str] = []
    for raw in articles_ordered:
        n = primary_article_number(raw)
        block = _targeted_body_for_article(
            n,
            query_keywords,
            max_tokens_per_article=max_tokens_per_article,
        )
        if block:
            parts.append(block)
    return "\n".join(parts)


def assemble_context(
    articles: set[str],
    *,
    max_tokens: int = 30000,
    priority_order: list[str] | None = None,
) -> str:
    """Build a single block of full article text, optionally honoring priority_order first."""
    ordered: list[str] = []
    if priority_order:
        seen: set[str] = set()
        for a in priority_order:
            n = primary_article_number(a)
            if n not in seen and n in {primary_article_number(x) for x in articles}:
                ordered.append(n)
                seen.add(n)
        for a in sorted({primary_article_number(x) for x in articles}):
            if a not in seen:
                ordered.append(a)
                seen.add(a)
    else:
        ordered = sorted({primary_article_number(x) for x in articles}, key=int)

    parts: list[str] = []
    budget = max_tokens
    for num in ordered:
        title = get_article_title(num)
        body = get_article_text(num)
        if not body:
            logger.debug("No full text for article %s; skipping in assembly", num)
            continue
        block = f"--- Article {num}: {title} ---\n{body.strip()}\n"
        cost = _approx_tokens(block)
        if cost > budget:
            truncated = block[: budget * 4]
            parts.append(truncated + "\n[... truncated ...]\n")
            break
        parts.append(block)
        budget -= cost
    return "\n".join(parts)


def assemble_recitals(recitals: set[str]) -> str:
    """Concatenate recital texts."""
    parts: list[str] = []
    for r in sorted(recitals, key=lambda x: int(re.sub(r"\D", "", x) or 0)):
        txt = get_recital_text(r)
        if txt:
            parts.append(f"--- Recital {r} ---\n{txt.strip()}\n")
    return "\n".join(parts)


def eurlex_source_url() -> str:
    """Canonical EUR-Lex HTML URL for GDPR (CELEX:32016R0679)."""
    return _EURLEX_GDPR_HTML
