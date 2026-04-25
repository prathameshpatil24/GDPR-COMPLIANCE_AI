#!/usr/bin/env python3
"""Sanity-check retrieval quality with fixed queries (no LLM)."""
from __future__ import annotations

import logging

from gdpr_ai.models import ClassifiedTopics, ExtractedEntities
from gdpr_ai.retriever import retrieve

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUERIES: list[tuple[str, str, list[str]]] = [
    (
        "consent_violation",
        "A retailer emails marketing offers to customers who only accepted terms of service "
        "but never ticked a marketing consent box.",
        ["consent", "legal-basis", "direct-marketing"],
    ),
    (
        "data_breach_notification",
        "A SaaS company discovers an attacker exported customer data but waits two months "
        "before notifying the supervisory authority.",
        ["notification-to-dpa", "security-of-processing", "security-and-breaches"],
    ),
    (
        "right_to_erasure",
        "A social network refuses a user deletion request and keeps posts for advertising "
        "profiling after the user closes their account.",
        ["erasure", "data-subject-rights", "object"],
    ),
    (
        "cross_border_transfer",
        "A German HR department transfers employee records to a US parent company without "
        "SCCs or adequacy safeguards.",
        ["transfers", "employment", "germany"],
    ),
    (
        "dpo_appointment",
        "A city council processes large-scale sensitive data but has not appointed a DPO "
        "despite mandatory conditions being met.",
        ["dpo", "dpia-and-dpo", "special-categories"],
    ),
]


def main() -> None:
    for qid, text, topics in QUERIES:
        print(f"\n=== Query: {qid} ===\n{text}\n")
        entities = ExtractedEntities(
            summary=text,
            jurisdiction="Germany" if "German" in text or "city council" in text else "EU",
        )
        ct = ClassifiedTopics(topics=topics, rationale="hardcoded smoke test")
        chunks = retrieve(text, ct, entities, top_k=5)
        for i, ch in enumerate(chunks, start=1):
            print(f"{i}. score={ch.similarity_score:.4f} id={ch.chunk_id}")
            print(f"   source={ch.metadata.get('source')} ref={ch.metadata.get('article_number')}")
            print(f"   text={ch.text[:240].replace(chr(10), ' ')}...")
        if not chunks:
            logger.error("No chunks for %s", qid)


if __name__ == "__main__":
    main()
