#!/usr/bin/env python3
"""Scrape BDSG sections from gesetze-im-internet.de (German text)."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx
from _http import DEFAULT_HEADERS
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BDSG_BASE = "https://www.gesetze-im-internet.de/bdsg_2018"
ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data" / "raw" / "bdsg_sections.json"


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_section_page(html: str, url: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.select_one("div.jnheader h1")
    if not h1:
        return None
    bez = h1.select_one("span.jnenbez")
    tit = h1.select_one("span.jnentitel")
    section_number = _norm_ws(bez.get_text()) if bez else ""
    title = _norm_ws(tit.get_text()) if tit else ""
    parts: list[str] = []
    for absatz in soup.select("div.jurAbsatz"):
        parts.append(_norm_ws(absatz.get_text(" ", strip=True)))
    text_de = _norm_ws("\n\n".join(p for p in parts if p))
    if not section_number:
        return None
    return {
        "section_number": section_number,
        "title": title,
        "text_de": text_de,
        "text_en": None,
        "source_url": url,
    }


async def discover_pages(client: httpx.AsyncClient) -> list[str]:
    resp = await client.get(f"{BDSG_BASE}/", headers=DEFAULT_HEADERS, timeout=60.0)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    pages: set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if re.fullmatch(r"__\d+\.html", href):
            pages.add(href)
    return sorted(pages, key=lambda h: int(re.search(r"(\d+)", h).group(1)))


async def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sections: list[dict[str, Any]] = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        pages = await discover_pages(client)
        for page in pages:
            url = f"{BDSG_BASE}/{page}"
            r = await client.get(url, headers=DEFAULT_HEADERS, timeout=60.0)
            r.raise_for_status()
            parsed = parse_section_page(r.text, url)
            if parsed:
                sections.append(parsed)
            await asyncio.sleep(0.15)
    OUT_PATH.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %s BDSG sections to %s", len(sections), OUT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
