"""AI engine selection.

get_engine() returns the configured engine. If OpenAI is selected but no key
is present, we fall back to the mock engine so the app never crashes.
"""
from __future__ import annotations

from ..config import settings
from .base import AIResult
from .mock_ai import MockAI

_engine = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    if settings.ai_is_live:
        try:
            from .openai_ai import OpenAIEngine
            _engine = OpenAIEngine()
        except Exception:
            _engine = MockAI()
    else:
        _engine = MockAI()
    return _engine


__all__ = ["get_engine", "AIResult"]
