#!/usr/bin/env python3
"""Scrape GDPR articles and recitals into structured JSON.

Primary source: EUR-Lex consolidated HTML. When the site returns an AWS WAF
challenge (common for unattended clients), falls back to gdpr-info.eu per-article
and per-recital pages. Mirror text is unofficial consolidation; metadata records
the page URL and publisher for attribution.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx
from _http import DEFAULT_HEADERS
from bs4 import BeautifulSoup, Tag

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GDPR_URL = (
    "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R0679"
)
MIRROR_ARTICLE_TEMPLATE = "https://gdpr-info.eu/art-{n}-gdpr/"
MIRROR_RECITAL_TEMPLATE = "https://gdpr-info.eu/recitals/no-{n}/"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
ARTICLES_PATH = RAW_DIR / "gdpr_articles.json"
RECITALS_PATH = RAW_DIR / "gdpr_recitals.json"

MIRROR_PUBLISHER = "gdpr-info.eu (unofficial mirror; EU legislative text)"


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_text_from_element(soup_el: Any) -> str:
    """Flatten element text (tables, nested tags) into plain text."""
    return _norm_ws(soup_el.get_text(" ", strip=True))


def _recital_numbers_from_html(html: str) -> list[int]:
    found = {int(x) for x in re.findall(r"rct_(\d+)", html, flags=re.I)}
    return sorted(found)


def parse_gdpr_html(html: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse EUR-Lex GDPR HTML into article and recital records."""
    soup = BeautifulSoup(html, "lxml")
    container = soup.select_one("div.eli-container") or soup

    recitals: list[dict[str, Any]] = []
    articles: list[dict[str, Any]] = []
    current_chapter = "Preamble / General"

    for el in container.descendants:
        if not getattr(el, "name", None):
            continue
        classes = el.get("class") or []
        if el.name == "p" and ("oj-ti-section-1" in classes or "oj-ti-section-2" in classes):
            label = _extract_text_from_element(el)
            if label:
                current_chapter = label
            continue
        if el.name != "div":
            continue
        el_id = el.get("id") or ""
        if el_id.startswith("rct_") and el_id[4:].isdigit():
            num = int(el_id[4:])
            text = _extract_text_from_element(el)
            recitals.append({"number": num, "text": text})
            continue
        if el_id.startswith("art_") and el_id[4:].isdigit():
            art_num = el_id[4:]
            title_el = el.select_one("p.oj-ti-art")
            subtitle_el = el.select_one("p.oj-sti-art")
            if not title_el:
                continue
            title_line = _extract_text_from_element(title_el)
            subtitle = _extract_text_from_element(subtitle_el) if subtitle_el else ""
            title = subtitle or title_line
            body_html = str(el)
            full_text = _extract_text_from_element(el)
            recital_refs = _recital_numbers_from_html(body_html)
            articles.append(
                {
                    "article_number": str(art_num),
                    "title": title,
                    "chapter": current_chapter,
                    "text": full_text,
                    "recitals": recital_refs,
                }
            )

    articles.sort(key=lambda a: int(a["article_number"]))
    recitals.sort(key=lambda r: r["number"])
    return articles, recitals


def _is_waf_or_non_lex_html(html: str) -> bool:
    """Return True when the response is not usable EUR-Lex consolidated HTML."""
    if "AwsWafIntegration" in html:
        return True
    if "div.eli-container" not in html and "id=\"art_1\"" not in html:
        return True
    return False


def _strip_mirror_footer(content: Tag) -> None:
    """Remove 'Suitable Recitals' and trailing navigation from gdpr-info pages."""
    for h2 in content.find_all("h2"):
        if "suitable recitals" in h2.get_text(" ", strip=True).lower():
            for nxt in list(h2.find_all_next()):
                nxt.decompose()
            h2.decompose()
            return


def parse_gdpr_info_article_html(html: str, article_num: int, page_url: str) -> dict[str, Any] | None:
    """Parse a single gdpr-info.eu article page into our article record shape."""
    soup = BeautifulSoup(html, "lxml")
    entry = soup.select_one("div.entry-content")
    if entry is None:
        return None
    _strip_mirror_footer(entry)
    h1 = soup.select_one("h1.entry-title") or soup.select_one("h1")
    raw_title = _extract_text_from_element(h1) if h1 else ""
    m = re.match(r"^Art\.\s*\d+\s*GDPR\s*[–-]?\s*(.+)$", raw_title, flags=re.I)
    title = m.group(1).strip() if m else raw_title
    body = _extract_text_from_element(entry)
    if len(body) < 20:
        return None
    return {
        "article_number": str(article_num),
        "title": title,
        "chapter": "Consolidated GDPR (mirror)",
        "text": body,
        "recitals": [],
        "source_url": page_url,
        "source_publisher": MIRROR_PUBLISHER,
        "license": "eu-public-domain",
    }


def parse_gdpr_info_recital_html(html: str, recital_num: int, page_url: str) -> dict[str, Any] | None:
    """Parse a single gdpr-info.eu recital page."""
    soup = BeautifulSoup(html, "lxml")
    entry = soup.select_one("div.entry-content")
    if entry is None:
        return None
    body = _extract_text_from_element(entry)
    if len(body) < 10:
        return None
    return {
        "number": recital_num,
        "text": body,
        "source_url": page_url,
        "source_publisher": MIRROR_PUBLISHER,
        "license": "eu-public-domain",
    }


async def fetch_html(client: httpx.AsyncClient) -> str:
    resp = await client.get(GDPR_URL, headers=DEFAULT_HEADERS, timeout=120.0)
    resp.raise_for_status()
    return resp.text


async def fetch_mirror_corpus(client: httpx.AsyncClient) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Download articles 1–99 and recitals 1–173 from gdpr-info.eu."""
    articles: list[dict[str, Any]] = []
    recitals: list[dict[str, Any]] = []
    delay_s = 0.12

    for n in range(1, 100):
        url = MIRROR_ARTICLE_TEMPLATE.format(n=n)
        resp = await client.get(url, headers=DEFAULT_HEADERS, timeout=60.0)
        await asyncio.sleep(delay_s)
        if resp.status_code != 200:
            logger.warning("Mirror article %s HTTP %s", n, resp.status_code)
            continue
        parsed = parse_gdpr_info_article_html(resp.text, n, url)
        if parsed:
            articles.append(parsed)
        else:
            logger.warning("Mirror article %s parse failed", n)

    for n in range(1, 174):
        url = MIRROR_RECITAL_TEMPLATE.format(n=n)
        resp = await client.get(url, headers=DEFAULT_HEADERS, timeout=60.0)
        await asyncio.sleep(delay_s)
        if resp.status_code != 200:
            logger.warning("Mirror recital %s HTTP %s", n, resp.status_code)
            continue
        parsed = parse_gdpr_info_recital_html(resp.text, n, url)
        if parsed:
            recitals.append(parsed)
        else:
            logger.warning("Mirror recital %s parse failed", n)

    articles.sort(key=lambda a: int(a["article_number"]))
    recitals.sort(key=lambda r: int(r["number"]))
    return articles, recitals


async def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        html = await fetch_html(client)
        articles, recitals = parse_gdpr_html(html)
        if _is_waf_or_non_lex_html(html) or len(articles) < 10:
            logger.warning(
                "EUR-Lex HTML missing or blocked (WAF). Using gdpr-info.eu mirror (%s articles parsed).",
                len(articles),
            )
            articles, recitals = await fetch_mirror_corpus(client)

    ARTICLES_PATH.write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    RECITALS_PATH.write_text(json.dumps(recitals, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %s articles to %s", len(articles), ARTICLES_PATH)
    logger.info("Wrote %s recitals to %s", len(recitals), RECITALS_PATH)


if __name__ == "__main__":
    asyncio.run(main())
