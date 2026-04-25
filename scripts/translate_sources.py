#!/usr/bin/env python3
"""Translate German BDSG/TTDSG sections to English using Claude Haiku."""
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from pathlib import Path

from anthropic import AsyncAnthropic

from gdpr_ai.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
BDSG_PATH = ROOT / "data" / "raw" / "bdsg_sections.json"
TTDSG_PATH = ROOT / "data" / "raw" / "ttdsg_sections.json"

BATCH_SIZE = 6
# One API call per batch: cap at 10 calls/minute for steady throughput.
RATE_LIMIT_SEC = 6.0
# Long TTDSG sections can exceed output limits if batched; allow larger completion budget.
_MAX_TOKENS = 8192
_MAX_BATCH_RETRIES = 2


def _parse_translations_json(raw: str, expected_n: int) -> list[str]:
    """Extract {\"translations\": [...]} from model output (handles markdown fences)."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I).strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise json.JSONDecodeError("No JSON object found", raw, 0)
    payload = json.loads(text[start : end + 1])
    translations = payload.get("translations")
    if not isinstance(translations, list):
        raise ValueError("Missing or invalid 'translations' array")
    if len(translations) != expected_n:
        raise ValueError(
            f"Translation count mismatch: got {len(translations)}, need {expected_n}"
        )
    return [str(t).strip() for t in translations]


async def translate_batch(client: AsyncAnthropic, model: str, sections: list[dict]) -> list[str]:
    """Translate a batch of German sections; returns English paragraphs in order."""
    numbered = "\n\n".join(
        f"[[ITEM_{i+1}]]\n{s['section_number']} {s['title']}\n{s['text_de']}"
        for i, s in enumerate(sections)
    )
    base_prompt = (
        "You are a legal translator specialising in German data protection law. "
        "Translate each German block into English. Preserve legal terminology and numbering.\n\n"
        "Output ONLY a single JSON object, no markdown fences, no commentary: "
        '{"translations": ["<English for ITEM_1>", "<English for ITEM_2>", ...]}\n'
        "One string per [[ITEM_n]] block, same order.\n\n"
    )
    last_raw = ""
    for attempt in range(_MAX_BATCH_RETRIES + 1):
        extra = ""
        if attempt > 0:
            extra = (
                f"\n\nYour previous reply was invalid or truncated. Retry. "
                f"Exactly {len(sections)} strings in 'translations'. Raw reply began with: "
                f"{last_raw[:200]!r}\n\n"
            )
        resp = await client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            temperature=0.0,
            messages=[{"role": "user", "content": base_prompt + extra + numbered}],
        )
        last_raw = ""
        for block in resp.content:
            if block.type == "text":
                last_raw += block.text
        try:
            return _parse_translations_json(last_raw, len(sections))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Batch parse failed attempt %s/%s: %s", attempt + 1, _MAX_BATCH_RETRIES + 1, exc)
            if attempt < _MAX_BATCH_RETRIES:
                await asyncio.sleep(0.8 * (attempt + 1))
    logger.error("Model output (truncated): %s", last_raw[:2000])
    raise ValueError("Could not parse translations after retries; see logs above")


async def translate_batch_splitting(
    client: AsyncAnthropic, model: str, sections: list[dict]
) -> list[str]:
    """Translate sections; split batch on parse errors (long TTDSG text often truncates JSON)."""
    if not sections:
        return []
    if len(sections) == 1:
        return await translate_batch(client, model, sections)
    try:
        return await translate_batch(client, model, sections)
    except ValueError as exc:
        logger.warning("Splitting batch of %s after: %s", len(sections), exc)
        mid = max(1, len(sections) // 2)
        left = await translate_batch_splitting(client, model, sections[:mid])
        right = await translate_batch_splitting(client, model, sections[mid:])
        return left + right


async def translate_file(path: Path) -> None:
    if not path.exists():
        logger.warning("Skip missing file: %s", path)
        return
    raw = json.loads(path.read_text(encoding="utf-8"))
    to_translate = [s for s in raw if not s.get("text_en")]
    if not to_translate:
        logger.info("Nothing to translate in %s", path.name)
        return
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for translation")
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    model = settings.model_translation
    label = "BDSG" if "bdsg" in path.name.lower() else "TTDSG"
    total = len(to_translate)
    done = 0
    for i in range(0, len(to_translate), BATCH_SIZE):
        batch = to_translate[i : i + BATCH_SIZE]
        batch_label = ", ".join(str(s.get("section_number", "?")) for s in batch)
        logger.info(
            "Translating %s batch (%s/%s sections): %s",
            path.name,
            done + len(batch),
            total,
            batch_label,
        )
        translations = await translate_batch_splitting(client, model, batch)
        for sec, en in zip(batch, translations, strict=True):
            sec["text_en"] = en.strip()
            done += 1
            sn = sec.get("section_number", "?")
            print(f"Translated {sn} {label} ({done}/{total})")
        await asyncio.sleep(RATE_LIMIT_SEC)
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Updated %s", path)


def spot_check(path: Path, n: int = 5) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    sample = random.sample(data, min(n, len(data)))
    print(f"\n=== Spot check: {path.name} ({len(sample)} sections) ===")
    for row in sample:
        print("\n--- German ---\n")
        print((row.get("text_de") or "")[:1200])
        print("\n--- English ---\n")
        print((row.get("text_en") or "")[:1200])


async def main() -> None:
    random.seed(42)
    await translate_file(BDSG_PATH)
    await translate_file(TTDSG_PATH)
    if BDSG_PATH.exists():
        spot_check(BDSG_PATH)
    if TTDSG_PATH.exists():
        spot_check(TTDSG_PATH)


if __name__ == "__main__":
    asyncio.run(main())
