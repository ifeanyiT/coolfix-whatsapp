"""Real Meta WhatsApp Cloud API provider.

Only used when WHATSAPP_PROVIDER=meta and META_ACCESS_TOKEN is set. Credentials
come from the environment - never hard-coded. This is ready for real use once
you connect a Meta app; the mock provider covers local demos.
"""
from __future__ import annotations

import hashlib
import hmac

import httpx

from ..config import settings
from .. import repo
from .base import OutboundResult


class MetaWhatsApp:
    provider = "meta"

    def __init__(self):
        self.token = settings.META_ACCESS_TOKEN
        self.phone_id = settings.META_PHONE_NUMBER_ID
        self.base = f"https://graph.facebook.com/v21.0/{self.phone_id}/messages"

    def send_text(self, to: str, text: str) -> OutboundResult:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(self.base, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            wa_id = data.get("messages", [{}])[0].get("id", "")
            repo.log_whatsapp(wa_id, "outbound", to, "sent", payload)
            return OutboundResult(wa_message_id=wa_id, status="sent", provider=self.provider)
        except Exception as e:  # noqa: BLE001
            repo.log_whatsapp("", "outbound", to, "failed", {"error": str(e), "payload": payload})
            return OutboundResult(wa_message_id="", status="failed", provider=self.provider, error=str(e))

    def verify_webhook(self, mode: str, token: str, challenge: str):
        if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
            return challenge
        return None

    def verify_signature(self, body: bytes, signature: str) -> bool:
        if not settings.META_APP_SECRET:
            return True
        if not signature or not signature.startswith("sha256="):
            return False
        expected = hmac.new(settings.META_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature.split("=", 1)[1])
