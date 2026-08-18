"""OpenAI engine.

Same interface as MockAI. It asks the model to return STRUCTURED JSON
(intent + slots + reply), grounded strictly in the business knowledge.
If anything goes wrong it raises, and the caller falls back to the mock engine.
"""
from __future__ import annotations

import json

import httpx

from ..config import settings
from .base import AIResult, INTENTS, render_knowledge

SYSTEM_TEMPLATE = """You are the WhatsApp assistant for {name}, a home-services business.
You answer ONLY using the business information below. NEVER invent prices, services,
availability, opening hours or service areas. If information is missing, say you need to
check or offer to connect a human. Be concise, warm and professional. Match this tone: {tone}

=== BUSINESS KNOWLEDGE ===
{knowledge}
=== END KNOWLEDGE ===

You must reply with a single JSON object (no markdown) using this schema:
{{
  "intent": one of {intents},
  "confidence": number 0-1,
  "requires_human": boolean,   // true for complaints, emergencies, or explicit human requests
  "service": service slug or null,  // one of the slugs in SERVICES
  "extracted": {{                 // include only fields present in THIS message or clearly implied
     "name": string,
     "location": string,
     "in_area": boolean,          // true only if location is within the listed service areas
     "preferred_time": string,
     "problem": string
  }},
  "reply": string   // your natural-language reply to the customer
}}

Context you should use:
- Currently known about this customer/booking: {state}
- The assistant last asked the customer for: {awaiting}
  (so a short bare answer like "Ikoyi" or "tomorrow afternoon" answers THAT question).
"""


class OpenAIEngine:
    def __init__(self):
        self.model = settings.OPENAI_MODEL
        self.api_key = settings.OPENAI_API_KEY
        self.url = "https://api.openai.com/v1/chat/completions"

    def analyze(self, kb: dict, history: list[dict], state: dict, message: str) -> AIResult:
        system = SYSTEM_TEMPLATE.format(
            name=kb["name"], tone=kb["tone"], knowledge=render_knowledge(kb),
            intents=INTENTS, state=json.dumps(state), awaiting=state.get("awaiting") or "nothing",
        )
        messages = [{"role": "system", "content": system}]
        for h in history[-settings.HISTORY_WINDOW:]:
            role = "assistant" if h["origin"] in ("ai", "human") else "user"
            messages.append({"role": role, "content": h["content"]})
        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=30) as client:
            resp = client.post(self.url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        extracted = parsed.get("extracted") or {}
        # strip empty strings
        extracted = {k: v for k, v in extracted.items() if v not in (None, "", [])}
        return AIResult(
            intent=parsed.get("intent", "unknown"),
            confidence=float(parsed.get("confidence", 0.5)),
            requires_human=bool(parsed.get("requires_human", False)),
            service=parsed.get("service"),
            extracted=extracted,
            reply=parsed.get("reply", ""),
            model=self.model,
            raw=parsed,
        )
