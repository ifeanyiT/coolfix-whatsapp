"""Mock WhatsApp provider.

Simulates the Meta Cloud API locally: it assigns a message id, marks the
message delivered, and logs it to the whatsapp_messages table so the whole
flow (including delivery tracking) can be demonstrated without a Meta account.
"""
from __future__ import annotations

import uuid

from .. import repo
from .base import OutboundResult


class MockWhatsApp:
    provider = "mock"

    def send_text(self, to: str, text: str) -> OutboundResult:
        wa_id = f"wamid.mock.{uuid.uuid4().hex[:16]}"
        repo.log_whatsapp(wa_id, "outbound", to, "delivered",
                          {"to": to, "type": "text", "text": {"body": text}})
        return OutboundResult(wa_message_id=wa_id, status="delivered", provider=self.provider)

    def verify_webhook(self, mode: str, token: str, challenge: str):
        # The mock accepts any verification so local testing never blocks.
        return challenge

    def verify_signature(self, body: bytes, signature: str) -> bool:
        return True
