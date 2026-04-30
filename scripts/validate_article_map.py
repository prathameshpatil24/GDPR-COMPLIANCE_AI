"""
Validate ``data/gdpr_article_map.yaml`` covers all 99 GDPR articles.

Run: uv run python scripts/validate_article_map.py
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "data" / "gdpr_article_map.yaml"
FULLTEXT_PATH = ROOT / "data" / "gdpr_articles_fulltext.yaml"

logger = logging.getLogger(__name__)

_TOPIC_HINTS: list[tuple[str, str]] = [
    ("scope", "material_scope"),
    ("definitions", "material_scope"),
    ("territorial", "material_scope"),
    ("principles", "material_scope"),
    ("lawfulness", "legal_basis"),
    ("consent", "consent"),
    ("child", "children"),
    ("special categories", "special_categories"),
    ("criminal", "special_categories"),
    ("processing not requiring identification", "processing_without_identification"),
    ("transparent", "transparency"),
    ("information", "transparency"),
    ("access", "right_to_access"),
    ("rectif", "accuracy"),
    ("erasure", "right_to_erasure"),
    ("right to erasure", "right_to_erasure"),
    ("restriction", "data_subject_rights"),
    ("notification obligation", "data_subject_rights"),
    ("data portability", "data_portability"),
    ("object ", "right_to_object"),
    ("automated", "automated_decisions"),
    ("representative", "representatives"),
    ("processor", "controller_processor"),
    ("records of processing", "records_security"),
    ("security of processing", "security"),
    ("personal data breach", "data_breach"),
    ("impact assessment", "dpia"),
    ("prior consultation", "dpia"),
    ("data protection officer", "dpo"),
    ("codes of conduct", "certification_codes"),
    ("certification", "certification_codes"),
    ("transfers", "international_transfer"),
    ("binding corporate rules", "transfer_tools_detail"),
    ("independence", "supervisory_authority"),
    ("cooperation", "international_cooperation"),
    ("remedies", "remedies_and_liability"),
    ("compensation", "remedies_and_liability"),
    ("infringements", "sanctions"),
    ("obligations of secrecy", "records_security"),
    ("delegated", "institutional_and_final_provisions"),
    ("committee", "institutional_and_final_provisions"),
]


def _primary_num(ref: str) -> str:
    m = re.match(r"^(\d+)", str(ref).strip())
    return m.group(1) if m else ""


def _suggest_topic(title: str) -> str:
    low = title.lower()
    for phrase, topic in _TOPIC_HINTS:
        if phrase in low:
            return topic
    return "material_scope"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    m = yaml.safe_load(MAP_PATH.read_text(encoding="utf-8"))
    topics = m.get("topics") or {}
    covered: set[str] = set()
    topic_by_article: dict[str, list[str]] = defaultdict(list)
    for tkey, spec in topics.items():
        if not isinstance(spec, dict):
            continue
        for ref in spec.get("gdpr_articles", []) or []:
            num = _primary_num(ref)
            if num:
                covered.add(num)
                topic_by_article[num].append(str(tkey))

    expected = {str(i) for i in range(1, 100)}
    missing = sorted(expected - covered, key=int)
    logger.info("Coverage: %s / 99 articles", len(covered))
    if missing:
        logger.warning("Missing primary article numbers: %s", ", ".join(missing))
        ft: dict[str, object] = {}
        if FULLTEXT_PATH.exists():
            raw = yaml.safe_load(FULLTEXT_PATH.read_text(encoding="utf-8"))
            ft = raw.get("articles") if isinstance(raw, dict) else {}
        for num in missing:
            title = ""
            if isinstance(ft, dict):
                entry = ft.get(num)
                if isinstance(entry, dict):
                    title = str(entry.get("title", ""))
        logger.warning(
            "  Article %s — %s | suggest topic: %s",
            num,
            title,
            _suggest_topic(title),
        )
    else:
        logger.info("All articles 1–99 appear in the map.")

    from gdpr_ai.pipeline import _ALLOWED_TOPICS
    from gdpr_ai.retrieval.article_map import resolve_topic_key

    missing_aliases: list[str] = []
    for slug in sorted(_ALLOWED_TOPICS):
        if resolve_topic_key(slug) is None:
            missing_aliases.append(slug)
    if missing_aliases:
        logger.error("Class slugs with no resolved topic: %s", missing_aliases)
        raise SystemExit(1)
    logger.info("All classifier slugs resolve via topic_aliases or topic keys.")


if __name__ == "__main__":
    main()
