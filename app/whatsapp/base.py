"""Shared WhatsApp provider types."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OutboundResult:
    wa_message_id: str
    status: str          # queued | sent | delivered | failed
    provider: str
    error: str = ""
