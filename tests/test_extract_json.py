"""Tests for model JSON extraction helpers."""

from __future__ import annotations

from gdpr_ai.llm.client import extract_json_object


def test_extract_json_strips_json_fence() -> None:
    raw = '```json\n{"ok": true, "n": 2}\n```'
    assert extract_json_object(raw) == {"ok": True, "n": 2}


def test_extract_json_balanced_with_suffix() -> None:
    raw = 'Here: {"a": {"b": 1}} trailing junk'
    assert extract_json_object(raw) == {"a": {"b": 1}}


def test_extract_json_respects_braces_inside_strings() -> None:
    raw = r'{"desc": "use } carefully", "k": 1}'
    assert extract_json_object(raw)["k"] == 1
    assert "}" in extract_json_object(raw)["desc"]
