"""The core orchestration pipeline (the in-app equivalent of the n8n workflow).

    inbound message
      -> identify customer
      -> get/create conversation + load memory
      -> retrieve business knowledge
      -> AI intent detection + slot extraction
      -> execute action (collect info / lead / booking / handoff)
      -> compose grounded response
      -> send via WhatsApp provider
      -> store everything + log automation

All business-critical actions (bookings, lead status, handoff) are decided HERE,
not by the language model, so the bot never claims an action that didn't happen.
"""
from __future__ import annotations

from . import repo
from .ai import get_engine
from .ai.base import HANDOFF_INTENTS
from .whatsapp import get_provider
from .config import settings

# Slots required before we can book.
REQUIRED_FOR_BOOKING = ["service", "location", "preferred_time"]
LOW_CONFIDENCE = 0.45


def process_inbound(wa_number: str, text: str, name: str = None,
                    business_id: str = None, deliver: bool = True) -> dict:
    """Process one inbound message end-to-end.

    deliver=True  -> the app sends the reply via its own WhatsApp provider
                     (used by the built-in simulator / direct Meta webhook).
    deliver=False -> the app only computes + stores the reply and returns it,
                     letting an external orchestrator (n8n) do the actual send.
    """
    business_id = business_id or settings.BUSINESS_ID
    repo.log_automation(business_id, "whatsapp_inbound", "started",
                        {"wa_number": wa_number, "text": text})

    kb = repo.get_business_knowledge(business_id)
    customer = repo.get_or_create_customer(business_id, wa_number, name)
    conv = repo.get_active_conversation(business_id, customer["id"])

    # 1) store the inbound customer message
    inbound = repo.add_message(conv["id"], business_id, customer["id"],
                               direction="inbound", origin="customer", content=text)

    # 2) If a human has taken over (AI paused), stay silent - just record it.
    if conv["mode"] == "human":
        repo.log_automation(business_id, "whatsapp_inbound", "paused_human",
                            {"conversation_id": conv["id"]})
        return {
            "conversation_id": conv["id"], "customer_id": customer["id"],
            "paused": True, "reply": None, "intent": "human_support",
            "actions": ["ai_paused"], "message_id": inbound["id"],
        }

    # 3) retrieve memory + run the AI (fall back to the mock engine if the LLM errors)
    history = repo.get_history(conv["id"])
    state = _load_state(conv)
    try:
        ai = get_engine().analyze(kb, history, state, text)
    except Exception as e:  # noqa: BLE001 - never let an LLM hiccup break a live chat
        from .ai.mock_ai import MockAI
        repo.log_automation(business_id, "ai_error", "fallback_to_mock", {"error": str(e)[:300]})
        ai = MockAI().analyze(kb, history, state, text)

    # 4) merge extracted info into memory + customer record
    actions: list[str] = []
    _merge_slots(customer, state, ai)

    # 5) decide + execute the action
    requires_human = ai.requires_human or ai.intent in HANDOFF_INTENTS
    if not requires_human and ai.confidence < LOW_CONFIDENCE:
        state["misunderstand_count"] = state.get("misunderstand_count", 0) + 1
        if state["misunderstand_count"] >= 2:
            requires_human = True
    else:
        state["misunderstand_count"] = 0

    if requires_human:
        reply = _handle_handoff(kb, business_id, conv, customer, ai, actions)
    elif ai.intent in ("booking", "new_lead", "recommendation", "service_info") \
            or state.get("awaiting") in REQUIRED_FOR_BOOKING + ["name"]:
        reply = _handle_booking(kb, business_id, conv, customer, state, ai, actions)
    else:
        reply = _handle_informational(kb, conv, ai, actions)

    # 6) persist conversation memory
    repo.update_conversation(conv["id"], state=state, last_intent=ai.intent)

    # 7) store outbound + (optionally) send through WhatsApp
    outbound = repo.add_message(conv["id"], business_id, customer["id"],
                                direction="outbound", origin="ai", content=reply)
    if deliver:
        result = get_provider().send_text(wa_number, reply)
        repo.set_message_status_by_id(outbound["id"], result.status, result.wa_message_id)
        delivery_status, wa_id = result.status, result.wa_message_id
    else:
        # External orchestrator (n8n) will deliver; just mark it generated.
        repo.set_message_status_by_id(outbound["id"], "generated")
        delivery_status, wa_id = "generated", None

    # 8) logging
    repo.log_ai_interaction(conv["id"], inbound["id"], ai.intent, ai.confidence,
                            requires_human, ai.model, ai.raw)
    repo.log_automation(business_id, "whatsapp_inbound", "completed",
                        {"conversation_id": conv["id"], "intent": ai.intent, "actions": actions})

    return {
        "conversation_id": conv["id"], "customer_id": customer["id"],
        "reply": reply, "intent": ai.intent, "confidence": ai.confidence,
        "requires_human": requires_human, "service": ai.service,
        "actions": actions, "message_id": outbound["id"], "model": ai.model,
        "wa_message_id": wa_id, "delivery": delivery_status,
    }


# ----------------------------------------------------------------- handlers
def _handle_handoff(kb, business_id, conv, customer, ai, actions) -> str:
    repo.create_handoff(conv["id"], business_id, reason=ai.intent)
    repo.update_conversation(conv["id"], status="waiting_human", mode="human")
    lead = repo.get_open_lead(customer["id"])
    if lead:
        repo.set_lead_status(lead["id"], "human_handoff")
    actions.append("human_handoff")
    repo.log_automation(business_id, "human_handoff", "created",
                        {"conversation_id": conv["id"], "reason": ai.intent})

    if ai.intent == "emergency":
        return (f"⚠️ That sounds urgent. For safety, switch off at the mains now. "
                f"I'm alerting our team - please call us immediately on {kb['phone']}. "
                f"A human agent will take over this chat right away.")
    if ai.intent == "complaint":
        return ("I'm really sorry about this. I've flagged your message to a human "
                "colleague who will take over and help you directly. Please hold on a moment.")
    return ("Sure - I'm connecting you to a member of our team now. "
            "They'll continue this conversation with you shortly. 👋")


def _handle_booking(kb, business_id, conv, customer, state, ai, actions) -> str:
    # Create/advance a lead as soon as there's buying intent.
    lead = repo.get_open_lead(customer["id"])
    service_slug = state.get("service")
    service = _service(kb, service_slug) if service_slug else None

    if not lead:
        lead = repo.upsert_lead(business_id, customer["id"], conv["id"],
                                service=service_slug, status="new",
                                location=state.get("location"),
                                preferred_time=state.get("preferred_time"),
                                problem=state.get("problem"))
        actions.append("lead_created")
    else:
        repo.upsert_lead(business_id, customer["id"], conv["id"],
                         service=service_slug or lead["service"],
                         location=state.get("location") or lead["location"],
                         preferred_time=state.get("preferred_time") or lead["preferred_time"],
                         problem=state.get("problem") or lead["problem"])

    # Ask for the next missing slot, in order.
    if not service_slug:
        state["awaiting"] = "service"
        names = " / ".join(s["name"].split(" (")[0].replace("Air-Conditioner ", "AC ")
                           for s in kb["services"])
        return f"Happy to arrange that. Which service do you need?\n({names})"

    # We have a service. Confirm we understood it (service_info style) if that's all.
    if state.get("location") and state.get("in_area") is False:
        state["awaiting"] = "location"
        areas = ", ".join(kb["service_areas"][:8])
        actions.append("outside_service_area")
        return (f"Sorry, I'm not sure we cover {state.get('location')} yet. "
                f"We currently serve: {areas}. Which of these are you closest to? "
                f"Otherwise I can connect you to our team.")

    if not state.get("location"):
        state["awaiting"] = "location"
        repo.set_lead_status(lead["id"], "contacted")
        return (f"Got it - {service['name']}. What area are you located in? "
                f"(We cover {', '.join(kb['service_areas'][:6])} and more.)")

    # Location is known and in-area -> qualified.
    repo.upsert_lead(business_id, customer["id"], conv["id"], status="qualified",
                     service=service_slug, location=state.get("location"))
    if "lead_qualified" not in actions:
        actions.append("lead_qualified")

    if not state.get("preferred_time"):
        state["awaiting"] = "preferred_time"
        repo.set_lead_status(lead["id"], "appointment_requested")
        slots = ", ".join(kb["booking_rules"]["slots"])
        return (f"Great, we cover {state.get('location')} 👍 When would suit you? "
                f"You can say e.g. 'tomorrow afternoon'. Slots: {slots}.")

    # We have everything -> book it.
    return _book(kb, business_id, conv, customer, state, lead, actions)


def _book(kb, business_id, conv, customer, state, lead, actions) -> str:
    service = _service(kb, state["service"])
    scheduled_for = state.get("preferred_time", "the requested time").strip().capitalize()
    slot = state.get("slot") or ""
    appt = repo.create_appointment(
        business_id, customer["id"], lead["id"], service["slug"],
        scheduled_for=scheduled_for, slot=slot,
        notes=f"Location: {state.get('location')}. Problem: {state.get('problem') or 'n/a'}",
    )
    repo.set_lead_status(lead["id"], "booked")
    state["awaiting"] = None
    state["booked_appointment_id"] = appt["id"]
    actions.append("appointment_booked")
    repo.update_conversation(conv["id"], status="active")
    repo.log_automation(business_id, "appointment_booking", "created",
                        {"appointment_id": appt["id"], "service": service["slug"]})

    who = state.get("name") or customer.get("name") or "there"
    return (f"✅ Booked, {who}! Here's your appointment:\n"
            f"• Service: {service['name']}\n"
            f"• Area: {state.get('location')}\n"
            f"• When: {scheduled_for}{(' - ' + slot) if slot else ''}\n"
            f"• Callout/diagnosis: as per our pricing ({service['price']})\n\n"
            f"We'll send a reminder before the visit. Anything else I can help with?")


def _handle_informational(kb, conv, ai, actions) -> str:
    actions.append("info_provided")
    if ai.intent == "faq":
        answer = _faq_answer(kb, conv, ai)
        if answer:
            return answer
    if ai.reply:
        return ai.reply
    if ai.intent == "pricing":
        menu = "\n".join(f"• {s['name']}: {s['price']}" for s in kb["services"])
        return f"Here's our pricing:\n{menu}\n\nWhich service are you interested in?"
    if ai.intent == "greeting":
        return (f"Hi! Welcome to {kb['name']} 👋 We handle AC installation, repair and "
                f"servicing, electrical work and generators. How can I help today?")
    # unknown
    return ("I want to make sure I help correctly - could you tell me a bit more? "
            "For example the service you need (AC repair, servicing, installation, "
            "electrical or generator), or say 'talk to someone' for a human.")


# ------------------------------------------------------------------ helpers
def _faq_answer(kb, conv, ai):
    # Use the last customer message to pick the best FAQ by keyword overlap.
    history = repo.get_history(conv["id"], limit=2)
    text = ""
    for m in reversed(history):
        if m["origin"] == "customer":
            text = m["content"].lower()
            break
    best, score = None, 0
    for f in kb["faqs"]:
        s = sum(1 for kw in f["keywords"] if kw in text)
        if s > score:
            best, score = f, s
    if best and score > 0:
        return best["answer"]
    # hours / area quick answers
    if any(w in text for w in ["open", "hour", "time", "close"]):
        hrs = kb["opening_hours"]
        return (f"We're open Mon-Fri {hrs['Monday']}, Sat {hrs['Saturday']}. "
                f"Sunday: {hrs['Sunday']}.")
    if any(w in text for w in ["area", "cover", "where", "location"]):
        return "We cover " + ", ".join(kb["service_areas"]) + ". Which area are you in?"
    return None


def _merge_slots(customer, state, ai):
    ex = ai.extracted or {}
    if ai.service and not state.get("service"):
        state["service"] = ai.service
    for key in ("service", "location", "in_area", "preferred_time", "slot", "problem", "name"):
        if key in ex and ex[key] not in (None, ""):
            state[key] = ex[key]
    # persist useful fields onto the customer record
    updates = {}
    if state.get("name") and not customer.get("name"):
        updates["name"] = state["name"]
    if state.get("location"):
        updates["location"] = state["location"]
    if updates:
        repo.update_customer(customer["id"], **updates)
        customer.update(updates)


def _load_state(conv) -> dict:
    import json
    try:
        return json.loads(conv.get("state") or "{}")
    except json.JSONDecodeError:
        return {}


def _service(kb, slug):
    return next((s for s in kb["services"] if s["slug"] == slug), None)


# =========================================================================
# Operator (human) actions - used by the dashboard conversation view.
# =========================================================================
def operator_reply(conversation_id: int, text: str) -> dict:
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise ValueError("conversation not found")
    customer = repo.get_customer(conv["customer_id"])
    msg = repo.add_message(conversation_id, conv["business_id"], conv["customer_id"],
                           direction="outbound", origin="human", content=text)
    result = get_provider().send_text(customer["wa_number"], text)
    repo.set_message_status_by_id(msg["id"], result.status, result.wa_message_id)
    # Sending as a human implies takeover.
    repo.update_conversation(conversation_id, mode="human")
    repo.log_automation(conv["business_id"], "operator_reply", "sent",
                        {"conversation_id": conversation_id})
    return {"message_id": msg["id"], "delivery": result.status}


def pause_ai(conversation_id: int) -> None:
    repo.update_conversation(conversation_id, mode="human", status="waiting_human")


def resume_ai(conversation_id: int) -> None:
    repo.resolve_handoffs(conversation_id)
    repo.update_conversation(conversation_id, mode="ai", status="active")


def close_conversation(conversation_id: int) -> None:
    repo.resolve_handoffs(conversation_id)
    repo.update_conversation(conversation_id, mode="ai", status="resolved")


# =========================================================================
# Follow-up automations - driven by n8n on a schedule (spec section 16).
# =========================================================================
def _service_name(kb, slug):
    s = _service(kb, slug)
    return s["name"] if s else "your service"


def _send_outbound(business_id, customer, text) -> dict:
    """Send a proactive message to a customer and store it on their conversation."""
    conv = repo.get_active_conversation(business_id, customer["id"])
    msg = repo.add_message(conv["id"], business_id, customer["id"],
                           direction="outbound", origin="system", content=text)
    result = get_provider().send_text(customer["wa_number"], text)
    repo.set_message_status_by_id(msg["id"], result.status, result.wa_message_id)
    return {"message_id": msg["id"], "delivery": result.status, "conversation_id": conv["id"]}


def send_lead_followup(lead_id: int) -> dict:
    lead = repo.get_lead(lead_id)
    if not lead:
        raise ValueError("lead not found")
    kb = repo.get_business_knowledge(lead["business_id"])
    customer = repo.get_customer(lead["customer_id"])
    who = customer.get("name") or "there"
    service = _service_name(kb, lead["service"])
    text = (f"Hi {who}, it's {kb['name']} 👋 You were asking about {service} but we didn't "
            f"finish arranging it. Would you like me to book a visit? Just reply with your "
            f"area and a preferred time and I'll sort it out.")
    out = _send_outbound(lead["business_id"], customer, text)
    repo.mark_lead_followed(lead_id)
    repo.log_automation(lead["business_id"], "lead_followup", "sent",
                        {"lead_id": lead_id, **out})
    return {"lead_id": lead_id, **out}


def send_appointment_reminder(appointment_id: int) -> dict:
    appt = repo.get_appointment(appointment_id)
    if not appt:
        raise ValueError("appointment not found")
    kb = repo.get_business_knowledge(appt["business_id"])
    customer = repo.get_customer(appt["customer_id"])
    who = customer.get("name") or "there"
    service = _service_name(kb, appt["service"])
    when = appt["scheduled_for"] + (f" ({appt['slot']})" if appt.get("slot") else "")
    text = (f"Reminder from {kb['name']}: {who}, your {service} appointment is scheduled for "
            f"{when}. Reply RESCHEDULE to change the time or CANCEL to cancel. See you soon!")
    out = _send_outbound(appt["business_id"], customer, text)
    repo.mark_appointment_reminded(appointment_id)
    repo.log_automation(appt["business_id"], "appointment_reminder", "sent",
                        {"appointment_id": appointment_id, **out})
    return {"appointment_id": appointment_id, **out}
