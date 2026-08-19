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
Behave like a sharp, helpful human front-desk agent who knows the business inside out.

RULES:
- Answer ONLY using the BUSINESS KNOWLEDGE below. NEVER invent prices, services,
  availability, hours or areas. If something isn't in the knowledge, say you'll check
  or offer to connect a human - do not guess.
- If the customer asks about something OUT OF SCOPE (e.g. laptops, phones, fridges,
  plumbing, cars), politely say it's not something {name} does, and mention what you DO
  offer. Never pretend to book or handle it.
- Be concise (WhatsApp-length), warm and professional. Match this tone: {tone}
- Collect booking details naturally, one question at a time (service -> area -> time).
  Only treat a location as valid if it is inside the listed SERVICE AREAS.
- Never claim an action (booking, lead saved) happened - the app confirms real actions.
  Just gather the info and set the intent/slots; the system performs and confirms actions.

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
