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
    """Render the business knowledge as text for an LLM system prompt (the RAG context)."""
    L = [
        f"BUSINESS: {kb['name']} - {kb['tagline']}",
        f"PHONE/WHATSAPP: {kb['phone']} | EMAIL: {kb['email']}",
        f"ADDRESS: {kb.get('address','')}",
        f"TONE: {kb['tone']}",
        "",
        "OPENING HOURS:",
    ]
    for day, hrs in kb["opening_hours"].items():
        L.append(f"  {day}: {hrs}")
    L += ["", "SERVICE AREAS (only these): " + ", ".join(kb["service_areas"]), ""]

    L.append("SERVICES (answer only about these):")
    for s in kb["services"]:
        L.append(f"- {s['name']} (slug: {s['slug']})")
        L.append(f"    What: {s.get('description', s.get('short',''))}")
        L.append(f"    Price: {s['price']}")
        if s.get("duration"):
            L.append(f"    Duration: {s['duration']}")
        if s.get("includes"):
            L.append(f"    Includes: {', '.join(s['includes'])}")
        for prob, cause in (s.get("common_problems") or {}).items():
            L.append(f"    Problem '{prob}': {cause}")
        if s.get("notes"):
            L.append(f"    Notes: {s['notes']}")
    L.append("")

    br = kb["booking_rules"]
    L.append("BOOKING RULES:")
    L.append(f"  Slots: {', '.join(br['slots'])}")
    for k in ("same_day", "sunday", "reschedule"):
        if br.get(k):
            L.append(f"  {br[k]}")
    L.append("")

    pay = kb.get("payment", {})
    if pay:
        L.append("PAYMENT: " + ", ".join(pay.get("methods", [])) + f". {pay.get('when','')} {pay.get('deposit','')}")
    L.append("")

    L.append("POLICIES:")
    for p in kb["policies"]:
        L.append(f"  - {p['title']}: {p['body']}")
    L.append("")

    L.append("FAQs:")
    for f in kb["faqs"]:
        L.append(f"  Q: {f['question']}\n    A: {f['answer']}")

    oos = kb.get("out_of_scope")
    if oos:
        L += ["", "OUT OF SCOPE (do NOT offer or pretend to do these): " + ", ".join(oos["examples"]),
              "  " + oos["note"]]
    return "\n".join(L)
