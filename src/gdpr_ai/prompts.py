"""Load versioned prompt templates from the repository `prompts/` directory."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    """Return the text of `prompts/<name>.txt`."""
    path = _PROMPTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **variables: str) -> str:
    """Format a prompt template with ``str.format``-style placeholders."""
    template = load_prompt(name)
    return template.format(**variables)
