"""Heuristic topic tags for chunk metadata (taxonomy from architecture docs)."""

from __future__ import annotations

import re
from functools import lru_cache

# Leaf tags used for metadata overlap with classification output.
DEFAULT_TAGS: tuple[str, ...] = ("gdpr",)


@lru_cache(maxsize=256)
def tags_for_gdpr_article(article_number: str) -> tuple[str, ...]:
    """Return topic tags for a GDPR article number (digits only)."""
    n = int(re.sub(r"\D", "", article_number) or "0")
    tags: set[str] = {"gdpr"}
    if n in {4, 7, 8}:
        tags.update({"legal-basis", "consent", "children"})
    elif n == 5:
        tags.update({"gdpr", "accountability"})
    elif n == 6:
        tags.update({"legal-basis", "consent", "contract", "legitimate-interest"})
    elif n == 7:
        tags.update({"legal-basis", "consent"})
    elif n == 9:
        tags.update({"special-categories"})
    elif n in {13, 14}:
        tags.update({"data-subject-rights", "information"})
    elif n == 15:
        tags.update({"data-subject-rights", "access"})
    elif n == 16:
        tags.update({"data-subject-rights", "rectification"})
    elif n == 17:
        tags.update({"data-subject-rights", "erasure"})
    elif n == 18:
        tags.update({"data-subject-rights", "restriction"})
    elif n == 20:
        tags.update({"data-subject-rights", "portability"})
    elif n == 21:
        tags.update({"data-subject-rights", "object", "direct-marketing"})
    elif n == 22:
        tags.update({"data-subject-rights", "automated-decisions"})
    elif n in {24, 25, 26, 28, 30}:
        tags.update({"controller-processor"})
    elif n == 32:
        tags.update({"security-and-breaches", "security-of-processing"})
    elif n == 33:
        tags.update({"security-and-breaches", "notification-to-dpa"})
    elif n == 34:
        tags.update({"security-and-breaches", "notification-to-subjects"})
    elif n in {35, 36}:
        tags.update({"dpia-and-dpo", "dpia"})
    elif n in {37, 38, 39}:
        tags.update({"dpia-and-dpo", "dpo"})
    elif 44 <= n <= 50:
        tags.update({"transfers"})
    elif n == 88:
        tags.update({"employment"})
    return tuple(sorted(tags))


@lru_cache(maxsize=256)
def tags_for_gdpr_recital(number: int) -> tuple[str, ...]:
    """Topic tags for select recitals that anchor high-value retrieval."""
    tags: set[str] = {"gdpr", "gdpr_recital"}
    if number == 32:
        tags.update({"legal-basis", "consent"})
    elif number == 40:
        tags.update({"legal-basis"})
    elif number in {42, 43}:
        tags.update({"legal-basis", "consent"})
    elif number == 70:
        tags.update({"data-subject-rights", "object", "direct-marketing"})
    return tuple(sorted(tags))


def tags_for_bdsg_section(section_number: str, title: str) -> tuple[str, ...]:
    """Infer tags for BDSG sections (employment focus)."""
    tags: set[str] = {"bdsg", "germany"}
    if "26" in section_number:
        tags.add("employment")
    if "Beschaft" in title or "Beschäft" in title:
        tags.add("employment")
    return tuple(sorted(tags))


def tags_for_ttdsg_section(section_number: str, title: str) -> tuple[str, ...]:
    """Infer tags for TTDSG sections."""
    tags: set[str] = {"ttdsg", "telemedia", "germany"}
    if "25" in section_number or "Cookie" in title or "Speicher" in title:
        tags.add("consent")
    return tuple(sorted(tags))


def tags_for_edpb(title: str) -> tuple[str, ...]:
    """Broad tags for EDPB guidelines."""
    t = title.lower()
    tags: set[str] = {"edpb", "guidance"}
    if "consent" in t:
        tags.update({"legal-basis", "consent"})
    if "breach" in t:
        tags.update({"security-and-breaches", "notification-to-dpa"})
    if "impact" in t or "dpia" in t:
        tags.update({"dpia-and-dpo", "dpia"})
    if "officer" in t or "dpo" in t:
        tags.update({"dpia-and-dpo", "dpo"})
    if "contract" in t or "article 6" in t or "6(1)(b)" in t:
        tags.update({"legal-basis", "contract"})
    return tuple(sorted(tags))
