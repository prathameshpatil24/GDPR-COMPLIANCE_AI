#!/usr/bin/env python3
"""Download key EDPB guidelines (PDF), extract text, emit structured JSON."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from _http import DEFAULT_HEADERS
from bs4 import BeautifulSoup
from pypdf import PdfReader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
RAW_EDPB_DIR = ROOT / "data" / "raw" / "edpb"
OUT_JSON = ROOT / "data" / "raw" / "edpb_guidelines.json"

# Curated English document pages (PDF links resolved at runtime).
GUIDELINE_PAGES: list[tuple[str, str, str]] = [
    (
        "05/2020",
        "Guidelines 05/2020 on consent under Regulation 2016/679",
        "https://edpb.europa.eu/our-work-tools/our-documents/guidelines/"
        "guidelines-052020-consent-under-regulation-2016679_en",
    ),
    (
        "22/2019",
        "Guidelines 2/2019 on processing of personal data under Article 6(1)(b) GDPR",
        "https://edpb.europa.eu/our-work-tools/our-documents/guidelines/"
        "guidelines-22019-processing-personal-data-under-article-61b_en",
    ),
    (
        "9/2022",
        "Guidelines 9/2022 on personal data breach notification under the GDPR",
        "https://edpb.europa.eu/our-work-tools/our-documents/guidelines/"
        "guidelines-92022-personal-data-breach-notification-under_en",
    ),
    (
        "DPO",
        "Guidelines on Data Protection Officer (DPOs)",
        "https://edpb.europa.eu/our-work-tools/our-documents/guidelines/data-protection-officer_en",
    ),
    (
        "DPIA",
        "Guidelines on Data Protection Impact Assessment (DPIA)",
        "https://edpb.europa.eu/our-work-tools/our-documents/guidelines/"
        "data-protection-impact-assessments-high-risk-processing_en",
    ),
]


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_main_html_text(page_html: str) -> str:
    """Extract visible text from a Drupal guideline page when no PDF is linked."""
    soup = BeautifulSoup(page_html, "lxml")
    main = soup.select_one("article") or soup.select_one("div#main-content") or soup.body
    if not main:
        return ""
    for tag in main.select("script, style, nav, header, footer"):
        tag.decompose()
    return _norm_ws(main.get_text("\n", strip=True))


def pick_pdf_url(page_html: str, base_url: str) -> str | None:
    """Choose the best English PDF link from a guideline landing page."""
    soup = BeautifulSoup(page_html, "lxml")
    candidates: list[str] = []
    for a in soup.select('a[href*=".pdf"]'):
        href = a.get("href") or ""
        if not href.lower().endswith(".pdf"):
            continue
        full = urljoin(base_url, href)
        candidates.append(full)
    if not candidates:
        return None
    en = [c for c in candidates if "_en.pdf" in c.lower() or c.lower().endswith("_en.pdf")]
    if en:
        return en[0]
    return candidates[0]


def extract_adopted_date(page_html: str) -> str:
    soup = BeautifulSoup(page_html, "lxml")
    for tag in soup.select("time[datetime]"):
        dt = tag.get("datetime")
        if dt:
            return str(dt)[:10]
    text = soup.get_text(" ", strip=True)
    m = re.search(r"\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b", text)
    return m.group(1) if m else ""


def pdf_to_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        parts.append(t)
    return "\n\n".join(parts)


def split_into_sections(full_text: str) -> list[dict[str, str]]:
    """Split guideline text into coarse sections using heading-like lines."""
    lines = [ln.strip() for ln in full_text.splitlines()]
    sections: list[dict[str, str]] = []
    current_heading = "Introduction"
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, current_heading
        body = _norm_ws("\n".join(buf))
        if body:
            sections.append({"heading": current_heading, "text": body})
        buf = []

    heading_re = re.compile(
        r"^(?:\d+(?:\.\d+)*[\.)]|[A-Z][A-Z0-9 \-]{3,80}|Version \d|Executive summary)\s*$"
    )
    for ln in lines:
        if not ln:
            continue
        if len(ln) < 120 and heading_re.match(ln):
            flush()
            current_heading = ln
            continue
        buf.append(ln)
    flush()
    if not sections and full_text.strip():
        return [{"heading": "Full text", "text": _norm_ws(full_text)}]
    return sections


async def process_one(
    client: httpx.AsyncClient, guideline_id: str, title: str, page_url: str
) -> dict[str, Any]:
    pr = await client.get(page_url, headers=DEFAULT_HEADERS, timeout=120.0)
    pr.raise_for_status()
    adopted = extract_adopted_date(pr.text)
    pdf_url = pick_pdf_url(pr.text, page_url)
    text = ""
    stored_pdf: str | None = None
    if pdf_url:
        pdf_resp = await client.get(pdf_url, headers=DEFAULT_HEADERS, timeout=120.0)
        pdf_resp.raise_for_status()
        RAW_EDPB_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", guideline_id) + ".pdf"
        pdf_path = RAW_EDPB_DIR / safe_name
        pdf_path.write_bytes(pdf_resp.content)
        stored_pdf = str(pdf_path.relative_to(ROOT))
        text = pdf_to_text(pdf_resp.content)
    else:
        text = extract_main_html_text(pr.text)
        if len(text) < 200:
            raise RuntimeError(f"No usable PDF or body text for {guideline_id} at {page_url}")
    return {
        "guideline_id": guideline_id,
        "title": title,
        "adopted_date": adopted,
        "source_page_url": page_url,
        "pdf_url": pdf_url or "",
        "local_pdf_path": stored_pdf or "",
        "sections": split_into_sections(text),
    }


async def main() -> None:
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for gid, title, page in GUIDELINE_PAGES:
            logger.info("Fetching %s", gid)
            try:
                rec = await process_one(client, gid, title, page)
            except Exception as exc:
                logger.error("Failed %s: %s", gid, exc)
                continue
            results.append(rec)
            await asyncio.sleep(0.5)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %s guidelines to %s", len(results), OUT_JSON)


if __name__ == "__main__":
    asyncio.run(main())
