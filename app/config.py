"""Central configuration, loaded from environment / .env file.

Nothing here is hard-coded to a secret. Everything sensitive comes from the
environment so the same code runs in demo mode (no credentials) or live mode.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present (safe no-op if missing).
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # --- AI ---
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "mock").lower()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # --- WhatsApp ---
    WHATSAPP_PROVIDER: str = os.getenv("WHATSAPP_PROVIDER", "mock").lower()
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "").strip()
    META_PHONE_NUMBER_ID: str = os.getenv("META_PHONE_NUMBER_ID", "").strip()
    META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "coolfix-verify-token")
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "").strip()

    # --- Security ---
    DASHBOARD_TOKEN: str = os.getenv("DASHBOARD_TOKEN", "").strip()

    # --- Server ---
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # --- Business / storage ---
    BUSINESS_ID: str = os.getenv("BUSINESS_ID", "coolfix")
    DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "coolfix.db"))

    # Conversation memory window (how many past messages the AI sees).
    HISTORY_WINDOW: int = int(os.getenv("HISTORY_WINDOW", "12"))

    @property
    def ai_is_live(self) -> bool:
        return self.AI_PROVIDER == "openai" and bool(self.OPENAI_API_KEY)

    @property
    def whatsapp_is_live(self) -> bool:
        return self.WHATSAPP_PROVIDER == "meta" and bool(self.META_ACCESS_TOKEN)


settings = Settings()
