"""Async Anthropic client with retries, token accounting, and EUR cost estimates."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from anthropic import APIStatusError, AsyncAnthropic, RateLimitError
from anthropic.types import TextBlock

from gdpr_ai.config import settings
from gdpr_ai.exceptions import ConfigurationError, LLMError

logger = logging.getLogger(__name__)

# Approximate retail EUR per 1M tokens (order-of-magnitude for budgeting).
_RATES_EUR_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (0.90, 4.50),
    "claude-sonnet-4-6": (2.80, 14.00),
}


@dataclass(slots=True)
class LLMResult:
    """Structured LLM response with usage metadata."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_eur: float


def _estimate_cost_eur(model: str, input_tokens: int, output_tokens: int) -> float:
    inp_rate, out_rate = _RATES_EUR_PER_MTOK.get(model, (2.0, 10.0))
    return (input_tokens * inp_rate + output_tokens * out_rate) / 1_000_000


def estimate_cost_eur(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate EUR cost from token usage (same rates as live API calls)."""
    return _estimate_cost_eur(model, input_tokens, output_tokens)


def _strip_markdown_json_fence(raw: str) -> str:
    """Remove optional ``` / ```json wrappers so brace scanning sees real JSON."""
    text = raw.strip()
    fence = re.search(r"^```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text


def _slice_balanced_json_object(s: str) -> str:
    """Return the substring of the first top-level `{...}` object (strings-aware)."""
    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model output")
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    raise ValueError("Unclosed JSON object in model output (truncated or invalid)")


def extract_json_object(raw: str) -> dict[str, Any]:
    """Parse the first JSON object from a model response."""
    cleaned = _strip_markdown_json_fence(raw)
    payload = _slice_balanced_json_object(cleaned)
    return json.loads(payload)


def is_truncated_json_error(exc: BaseException) -> bool:
    """Return True when failure is likely due to cut-off model output."""
    if isinstance(exc, json.JSONDecodeError):
        msg = str(exc).lower()
        if "unterminated" in msg:
            return True
        if "expecting" in msg and any(x in msg for x in ("delimiter", "value", "property name")):
            return True
    msg = str(exc).lower()
    return "unclosed" in msg or "truncated" in msg


def repair_truncated_json(raw: str) -> dict[str, Any] | None:
    """Attempt to close a truncated top-level JSON object (strings-aware, best-effort)."""
    cleaned = _strip_markdown_json_fence(raw)
    start = cleaned.find("{")
    if start == -1:
        return None
    s = cleaned[start:]
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in s:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            stack.append("{")
        elif ch == "[":
            stack.append("[")
        elif ch == "}":
            if not stack or stack[-1] != "{":
                return None
            stack.pop()
        elif ch == "]":
            if not stack or stack[-1] != "[":
                return None
            stack.pop()
    if in_string:
        return None
    if not stack:
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return None
    suffix_chars: list[str] = []
    while stack:
        op = stack.pop()
        suffix_chars.append("}" if op == "{" else "]")
    candidate = s + "".join(suffix_chars)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def extract_json_object_with_repair(raw: str) -> tuple[dict[str, Any], bool]:
    """Parse JSON like :func:`extract_json_object`, then try structural repair if needed."""
    try:
        return extract_json_object(raw), False
    except (json.JSONDecodeError, ValueError) as exc:
        fixed = repair_truncated_json(raw)
        if fixed is not None:
            logger.warning("Heuristic JSON truncation repair succeeded (%s)", exc)
            return fixed, True
        raise


async def complete_text(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float = 0.0,
    max_retries: int = 3,
) -> LLMResult:
    """Call Claude with exponential backoff on transient failures."""
    if not settings.anthropic_api_key:
        raise ConfigurationError("ANTHROPIC_API_KEY is not set")
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    attempt = 0
    delay = 1.0
    last_exc: Exception | None = None
    while attempt < max_retries:
        attempt += 1
        t0 = time.perf_counter()
        try:
            msg = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            text = "".join(b.text for b in msg.content if isinstance(b, TextBlock))
            usage = msg.usage
            in_tok = int(getattr(usage, "input_tokens", 0) or 0)
            out_tok = int(getattr(usage, "output_tokens", 0) or 0)
            cost = _estimate_cost_eur(model, in_tok, out_tok)
            return LLMResult(
                text=text,
                model=model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                latency_ms=latency_ms,
                cost_eur=cost,
            )
        except (RateLimitError, APIStatusError, TimeoutError) as exc:
            last_exc = exc
            code = getattr(exc, "status_code", None)
            if isinstance(exc, APIStatusError) and code in {400, 401, 403}:
                raise LLMError(str(exc)) from exc
            logger.warning("LLM attempt %s failed: %s", attempt, exc)
            await asyncio.sleep(delay)
            delay *= 2
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("LLM attempt %s failed: %s", attempt, exc)
            await asyncio.sleep(delay)
            delay *= 2
    raise LLMError(f"LLM failed after {max_retries} attempts: {last_exc}")
