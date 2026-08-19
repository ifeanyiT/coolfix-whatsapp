"""Rule-based mock AI engine.

No network, no API key. It does keyword intent detection and slot extraction
so the whole chatbot workflow can be demonstrated offline. It implements the
same interface as the OpenAI engine, so switching is a one-line env change.
"""
from __future__ import annotations

import re

from .base import AIResult

EMERGENCY_WORDS = ["spark", "sparks", "burning", "smoke", "smell of burn", "shock", "shocked",
                   "fire", "electrocut", "explos"]
HUMAN_WORDS = ["speak to someone", "speak with someone", "talk to someone", "human", "agent",
               "representative", "real person", "call me", "customer service", "speak to a person",
               "speak to somebody", "talk to a person"]
COMPLAINT_WORDS = ["terrible", "rubbish", "disappointed", "angry", "refund", "complain", "complaint",
                   "unhappy", "worst", "useless", "scam", "poor service", "bad service", "annoyed"]
BOOKING_WORDS = ["book", "booking", "appointment", "schedule", "come tomorrow", "come today",
                 "send someone", "can someone come", "come over", "visit", "come and", "reserve",
                 "when can you come", "arrange"]
PRICING_WORDS = ["how much", "price", "cost", "charge", "rate", "fee", "quote", "quotation", "pricing"]
GREETING_WORDS = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "hallo"]

TIME_WORDS = ["today", "tomorrow", "morning", "afternoon", "evening", "tonight", "asap", "now",
              "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
              "next week", "weekend"]


class MockAI:
    model = "mock-rules"

    def analyze(self, kb: dict, history: list[dict], state: dict, message: str) -> AIResult:
        text = message.lower().strip()
        awaiting = state.get("awaiting")
        extracted = {}

        # Politely decline things the business doesn't do (unless mid-booking).
        oos = self._out_of_scope(kb, text) if awaiting not in ("service", "location", "preferred_time") else None
        if oos:
            names = "air-conditioning, electrical work and generators"
            reply = (f"Sorry, we don't handle {oos} - {kb['name']} only does {names}. "
                     f"Can I help you with any of those?")
            return AIResult(intent="unknown", confidence=0.9, requires_human=False,
                            service=None, extracted={}, reply=reply, model=self.model,
                            raw={"engine": "mock", "out_of_scope": oos})

        service_slug = self._match_service(kb, text)
        location, in_area = self._match_location(kb, message, awaiting)
        preferred_time, slot = self._match_time(text, awaiting)
        name = self._match_name(message, awaiting)

        if service_slug:
            extracted["service"] = service_slug
        if location:
            extracted["location"] = location
            extracted["in_area"] = in_area
        if preferred_time:
            extracted["preferred_time"] = preferred_time
            if slot:
                extracted["slot"] = slot
        if name:
            extracted["name"] = name

        # ---- intent detection (priority order) ----
        faq_hit = self._faq_hit(kb, text)
        intent, confidence, requires_human = self._detect_intent(
            text, awaiting, service_slug, preferred_time, state, faq_hit
        )

        reply = self._informational_reply(kb, intent, service_slug, location, in_area)

        return AIResult(
            intent=intent, confidence=confidence, requires_human=requires_human,
            service=service_slug, extracted=extracted, reply=reply, model=self.model,
            raw={"engine": "mock", "awaiting": awaiting},
        )

    # ---------------------------------------------------------------- intent
    def _detect_intent(self, text, awaiting, service_slug, preferred_time, state, faq_hit):
        if self._any(text, EMERGENCY_WORDS):
            return "emergency", 0.97, True
        if self._any(text, HUMAN_WORDS):
            return "human_support", 0.96, True
        if self._any(text, COMPLAINT_WORDS):
            return "complaint", 0.9, True
        asks_hours = self._any(text, ["open", "hour", "close", "closing", "what time", "when do you"])
        # Mid-booking: keep treating short replies as booking answers.
        if awaiting in ("service", "location", "preferred_time", "name"):
            return "booking", 0.9, False
        # Explicit booking request wins.
        if self._any(text, BOOKING_WORDS):
            return "booking", 0.92, False
        # A matched FAQ (our knowledge bank) answers the question directly.
        if faq_hit:
            return "faq", 0.88, False
        # A bare time only means booking if we're already in a service context.
        if preferred_time and not asks_hours and state.get("service"):
            return "booking", 0.88, False
        if self._any(text, PRICING_WORDS):
            return "pricing", 0.9, False
        if service_slug:
            return "service_info", 0.85, False
        if self._any(text, GREETING_WORDS) and len(text.split()) <= 4:
            return "greeting", 0.8, False
        return "unknown", 0.35, False

    # ------------------------------------------------------------- reply text
    def _informational_reply(self, kb, intent, service_slug, location, in_area):
        if intent == "greeting":
            names = ", ".join(s["name"].split(" (")[0] for s in kb["services"][:3])
            return (f"Hi! Welcome to {kb['name']} 👋 We handle AC installation, repair, "
                    f"servicing, electrical work and generators. How can I help today?")
        if intent == "faq":
            return None  # filled below by _faq answer through orchestrator fallback
        if intent == "pricing":
            if service_slug:
                svc = self._service(kb, service_slug)
                price = svc['price'].rstrip('.')
                return f"{svc['name']}: {price}. Would you like to book it?"
            menu = "\n".join(f"• {s['name']}: {s['price']}" for s in kb["services"])
            return f"Here's our pricing:\n{menu}\n\nWhich one do you need?"
        if intent == "service_info":
            svc = self._service(kb, service_slug)
            if svc:
                return (f"{svc['name']} — {svc['description']} Price: {svc['price']}. "
                        f"Would you like me to book someone for this?")
        return None

    # ------------------------------------------------------------ extractors
    def _out_of_scope(self, kb, text):
        """Return the out-of-scope item if the customer wants us to work on it."""
        oos = kb.get("out_of_scope") or {}
        service_ctx = ["repair", "fix", "service", "servicing", "install", "not working",
                       "broken", "faulty", "won't", "wont", "problem with", "help with", "spoil"]
        has_ctx = any(w in text for w in service_ctx)
        if not has_ctx:
            return None
        for item in oos.get("examples", []):
            if re.search(rf"\b{re.escape(item)}s?\b", text):
                return item
        return None

    def _faq_hit(self, kb, text):
        for f in kb.get("faqs", []):
            if any(kw in text for kw in f["keywords"]):
                return True
        return False

    def _match_service(self, kb, text):
        best = None
        for s in kb["services"]:
            for kw in s["keywords"]:
                if kw in text:
                    return s["slug"]
        return best

    def _match_location(self, kb, message, awaiting):
        areas = kb["service_areas"]
        low = message.lower()
        for area in areas:
            if re.search(rf"\b{re.escape(area.lower())}\b", low):
                canonical = "Victoria Island" if area.lower() in ("vi", "victoria island") else area
                return canonical, True
        # "in Somewhere" / "at Somewhere" pattern -> unknown area
        m = re.search(r"\b(?:in|at|from|around|located in|location is|area is|its|it's)\s+([A-Za-z][A-Za-z\- ]{2,20})",
                      message, re.IGNORECASE)
        if m:
            cand = m.group(1).strip().title()
            return cand, False
        # If we explicitly asked for location, take the whole short message as a place.
        if awaiting == "location":
            cand = message.strip().title()
            if 2 < len(cand) <= 24 and cand.replace(" ", "").isalpha():
                return cand, False
        return None, None

    def _match_time(self, text, awaiting):
        found = [w for w in TIME_WORDS if w in text]
        clock = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s?(am|pm)\b", text)
        phrase_parts = []
        day = next((w for w in ["today", "tomorrow", "monday", "tuesday", "wednesday",
                                 "thursday", "friday", "saturday", "sunday", "weekend"] if w in text), None)
        daypart = next((w for w in ["morning", "afternoon", "evening", "tonight"] if w in text), None)
        if day:
            phrase_parts.append(day)
        if daypart:
            phrase_parts.append(daypart)
        if clock:
            phrase_parts.append(clock.group(0))
        if not phrase_parts and awaiting == "preferred_time" and text:
            phrase_parts.append(text)
        if not phrase_parts and not found:
            return None, None
        preferred = " ".join(phrase_parts) if phrase_parts else " ".join(found)
        slot = None
        if daypart in ("evening", "tonight"):
            slot = "Evening (4pm-6pm)"
        elif daypart == "afternoon":
            slot = "Afternoon (12pm-4pm)"
        elif daypart == "morning":
            slot = "Morning (9am-12pm)"
        return preferred.strip(), slot

    def _match_name(self, message, awaiting):
        # Only trust explicit name phrases - "I'm in Lekki" must NOT become a name.
        stop = set(TIME_WORDS) | {"in", "at", "on", "the", "a", "not", "here", "there",
                                  "looking", "trying", "having", "from", "around", "so",
                                  "just", "really", "very", "okay", "ok", "yes", "no"}
        m = re.search(r"\b(?:my name is|this is|call me|name's|names)\s+([A-Za-z]+)",
                      message, re.IGNORECASE)
        if m:
            cand = m.group(1).strip().title()
            if cand.lower() not in stop and len(cand) > 1:
                return cand
        if awaiting == "name":
            first = message.strip().split()[0].title() if message.strip() else None
            if first and first.isalpha() and len(first) > 1 and first.lower() not in stop:
                return first
        return None

    # -------------------------------------------------------------- helpers
    def _service(self, kb, slug):
        return next((s for s in kb["services"] if s["slug"] == slug), None)

    def _faq_match(self, text):
        # returns index-ish signal; real answer selection happens in orchestrator
        for kw in ["open", "hours", "time", "area", "cover", "warranty", "guarantee", "pay",
                   "payment", "where"]:
            if kw in text:
                return kw
        return None

    @staticmethod
    def _any(text, words):
        return any(w in text for w in words)
