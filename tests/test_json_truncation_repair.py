"""Tests for heuristic JSON repair after truncated LLM output."""

from __future__ import annotations

import pytest

from gdpr_ai.llm.client import (
    extract_json_object_with_repair,
    is_truncated_json_error,
    repair_truncated_json,
)


def test_repair_truncated_json_closes_simple_object() -> None:
    assert repair_truncated_json('{"ok": true') == {"ok": True}


def test_repair_truncated_json_closes_empty_array_value() -> None:
    raw = '{"findings": ['
    assert repair_truncated_json(raw) == {"findings": []}


def test_extract_json_object_with_repair_reports_when_repaired() -> None:
    raw = '{"findings": ['
    data, repaired = extract_json_object_with_repair(raw)
    assert repaired is True
    assert data == {"findings": []}


def test_is_truncated_json_error_detects_slice_message() -> None:
    exc = ValueError("Unclosed JSON object in model output (truncated or invalid)")
    assert is_truncated_json_error(exc) is True


def test_extract_json_object_with_repair_passes_through_valid_json() -> None:
    raw = '{"x": 1}'
    data, repaired = extract_json_object_with_repair(raw)
    assert repaired is False
    assert data == {"x": 1}


def test_repair_returns_none_inside_unterminated_string() -> None:
    raw = '{"summary": "half'
    assert repair_truncated_json(raw) is None


@pytest.mark.parametrize(
    ("broken", "expected"),
    [
        ('{"a": 1', {"a": 1}),
        ('```json\n{"b": 2}\n```', {"b": 2}),
    ],
)
def test_repair_truncated_json_variants(broken: str, expected: dict) -> None:
    assert repair_truncated_json(broken) == expected
