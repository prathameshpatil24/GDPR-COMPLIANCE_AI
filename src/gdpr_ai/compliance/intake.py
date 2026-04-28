"""Parse structured or free-text system descriptions into a ``DataMap``."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from gdpr_ai.compliance.schemas import DataMap
from gdpr_ai.config import settings
from gdpr_ai.llm.client import LLMResult, complete_text, extract_json_object
from gdpr_ai.prompts import render_prompt

logger = logging.getLogger(__name__)


def parse_structured_input(data: dict[str, Any]) -> DataMap:
    """Validate JSON/dict input against the ``DataMap`` schema."""
    try:
        return DataMap.model_validate(data)
    except ValidationError as exc:
        logger.debug("DataMap validation failed: %s", exc)
        raise


async def parse_freetext_input(text: str) -> tuple[DataMap, LLMResult]:
    """Use the reasoning engine to extract a ``DataMap`` from prose."""
    schema_hint = json.dumps(DataMap.model_json_schema(), ensure_ascii=False, indent=2)
    user = render_prompt("intake_extract", schema=schema_hint, input_text=text.strip())
    res = await complete_text(
        model=settings.model_extract_classify,
        system="You output only JSON. Use null for unknown fields; do not invent facts.",
        user=user,
        max_tokens=4096,
        temperature=0.0,
    )
    data = extract_json_object(res.text)
    return DataMap.model_validate(data), res
