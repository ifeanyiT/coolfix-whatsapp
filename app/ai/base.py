"""Shared AI types and prompt/knowledge helpers used by every engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# The configurable intent taxonomy (spec section 6).
INTENTS = [
    "greeting",
    "faq",
    "pricing",
    "service_info",
    "booking",
    "complaint",
    "existing_customer",
    "new_lead",
    "recommendation",
    "human_support",
    "emergency",
    "unknown",
]

# Intents that express buying intent -> should create/advance a lead.
BUYING_INTENTS = {"booking", "new_lead", "recommendation", "service_info"}

# Intents that always require a human.
HANDOFF_INTENTS = {"human_support", "complaint", "emergency"}


@dataclass
class AIResult:
    intent: str = "unknown"
    confidence: float = 0.0
    requires_human: bool = False
    service: Optional[str] = None          # service slug, if identified
    extracted: dict = field(default_factory=dict)  # name, location, preferred_time, problem
    reply: str = ""                        # draft reply (used for informational intents)
    model: str = "mock"
    raw: dict = field(default_factory=dict)


def render_knowledge(kb: dict) -> str:
    """Render the business knowledge as compact text for an LLM system prompt."""
    lines = [
        f"BUSINESS: {kb['name']} - {kb['tagline']}",
        f"PHONE: {kb['phone']} | EMAIL: {kb['email']}",
        f"TONE: {kb['tone']}",
        "",
        "OPENING HOURS:",
    ]
    for day, hrs in kb["opening_hours"].items():
        lines.append(f"  {day}: {hrs}")
    lines.append("")
    lines.append("SERVICE AREAS: " + ", ".join(kb["service_areas"]))
    lines.append("")
    lines.append("SERVICES:")
    for s in kb["services"]:
        lines.append(f"  - {s['name']} ({s['slug']}): {s['description']} | Price: {s['price']}")
    lines.append("")
    lines.append("FAQs:")
    for f in kb["faqs"]:
        lines.append(f"  Q: {f['question']}\n    A: {f['answer']}")
    lines.append("")
    lines.append("POLICIES:")
    for p in kb["policies"]:
        lines.append(f"  - {p['title']}: {p['body']}")
    br = kb["booking_rules"]
    lines.append("")
    lines.append(f"BOOKING SLOTS: {', '.join(br['slots'])}. {br.get('note','')}")
    return "\n".join(lines)
