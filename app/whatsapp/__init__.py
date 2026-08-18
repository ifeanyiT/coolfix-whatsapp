"""WhatsApp provider selection."""
from __future__ import annotations

from ..config import settings
from .base import OutboundResult
from .mock import MockWhatsApp

_provider = None


def get_provider():
    global _provider
    if _provider is not None:
        return _provider
    if settings.whatsapp_is_live:
        try:
            from .meta import MetaWhatsApp
            _provider = MetaWhatsApp()
        except Exception:
            _provider = MockWhatsApp()
    else:
        _provider = MockWhatsApp()
    return _provider


__all__ = ["get_provider", "OutboundResult"]
