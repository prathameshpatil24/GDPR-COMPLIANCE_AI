"""
Smoke-test the completeness verifier (Layer 4) with full and gap analyses.

Requires ``ANTHROPIC_API_KEY`` and ``VERIFICATION_ENABLED=true`` for a live call.

Run: uv run python scripts/test_verification.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

from gdpr_ai.config import settings
from gdpr_ai.reasoning.verifier import verify_completeness

logger = logging.getLogger(__name__)

_COMPLETE = """
{
  "scenario": "Marketing emails without consent",
  "violations": [
    {
      "article": "6(1)(a)",
      "summary": "No valid consent for direct marketing.",
      "assessment": "Controller did not demonstrate consent under Article 6 and 7."
    },
    {
      "article": "7",
      "summary": "Conditions for consent not met.",
      "assessment": "No clear opt-in or withdrawal mechanism described."
    },
    {
      "article": "21(2)",
      "summary": "Direct marketing objection not respected.",
      "assessment": "Marketing continued despite objection rules under 21(3)."
    }
  ],
  "security": "TLS and access controls assumed adequate; breach not alleged.",
  "dpia": "Likely not required for routine email marketing at described scale."
}
"""

_INCOMPLETE = """
{
  "scenario": "Marketing emails without consent",
  "violations": [
    {
      "article": "6(1)(a)",
      "summary": "No valid consent for direct marketing.",
      "assessment": "Brief note only."
    }
  ]
}
"""


async def _run() -> None:
    if not settings.verification_enabled:
        logger.warning("VERIFICATION_ENABLED is false; set to true to run the verifier.")
        raise SystemExit(0)
    if not settings.anthropic_api_key and not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("No ANTHROPIC_API_KEY; skipping live verification.")
        raise SystemExit(0)

    query = "Company sends promotional emails to customers without prior consent."
    articles_used = ["6", "7", "21"]

    v_ok, _res_ok = await verify_completeness(
        original_query=query,
        analysis_json=_COMPLETE,
        articles_used=articles_used,
        mode="violation_analysis",
    )
    logger.info(
        "Complete analysis — score %.3f supplementary=%s missing=%s",
        v_ok.completeness_score,
        v_ok.needs_supplementary_pass,
        v_ok.missing_articles,
    )

    v_bad, _res_bad = await verify_completeness(
        original_query=query,
        analysis_json=_INCOMPLETE,
        articles_used=["6"],
        mode="violation_analysis",
    )
    logger.info(
        "Incomplete analysis — score %.3f supplementary=%s missing=%s",
        v_bad.completeness_score,
        v_bad.needs_supplementary_pass,
        v_bad.missing_articles,
    )
    logger.info(
        "Checklist (truncated): %s",
        json.dumps([c.model_dump() for c in v_bad.checklist[:5]]),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(_run())


if __name__ == "__main__":
    main()
