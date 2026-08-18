"""FastAPI application: REST API + WhatsApp webhook + static demo UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request, Depends
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import repo, db
from .config import settings
from .orchestrator import (
    process_inbound, operator_reply, pause_ai, resume_ai, close_conversation,
    send_lead_followup, send_appointment_reminder,
)
from .ai import get_engine
from .whatsapp import get_provider

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="CoolFix WhatsApp AI Chatbot", version="1.0.0")


@app.on_event("startup")
def _startup():
    db.init_db()


# ------------------------------------------------------------------- auth
def require_auth(authorization: str = Header(default="")):
    """Optional bearer auth for dashboard/admin routes.

    Disabled (open) when DASHBOARD_TOKEN is empty - convenient for local demos.
    """
    if not settings.DASHBOARD_TOKEN:
        return True
    if authorization != f"Bearer {settings.DASHBOARD_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# --------------------------------------------------------------- schemas
class SimMessage(BaseModel):
    text: str
    wa_number: str = "+2348000000001"
    name: str | None = None


class InboundMessage(BaseModel):
    """Payload n8n sends after its WhatsApp Trigger receives a message."""
    wa_number: str
    text: str
    name: str | None = None
    deliver: bool = False   # n8n delivers the reply itself via its WhatsApp node


class ReplyIn(BaseModel):
    text: str


class LeadStatusIn(BaseModel):
    status: str


# ------------------------------------------------------------------ pages
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB_DIR / "simulator.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_page():
    return FileResponse(WEB_DIR / "dashboard.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "business": settings.BUSINESS_ID,
        "ai_provider": "openai" if settings.ai_is_live else "mock",
        "ai_engine": get_engine().model,
        "whatsapp_provider": "meta" if settings.whatsapp_is_live else "mock",
    }


# ------------------------------------------------------- WhatsApp webhook
@app.get("/webhook/whatsapp", include_in_schema=False)
def verify_webhook(request: Request):
    params = request.query_params
    result = get_provider().verify_webhook(
        params.get("hub.mode", ""),
        params.get("hub.verify_token", ""),
        params.get("hub.challenge", ""),
    )
    if result is None:
        raise HTTPException(status_code=403, detail="verification failed")
    return PlainTextResponse(str(result))


@app.post("/webhook/whatsapp")
async def receive_webhook(request: Request,
                          x_hub_signature_256: str = Header(default="")):
    body = await request.body()
    provider = get_provider()
    if not provider.verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="bad signature")
    payload = await request.json()

    results = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {c["wa_id"]: c.get("profile", {}).get("name")
                        for c in value.get("contacts", [])}
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                wa_number = msg["from"]
                text = msg["text"]["body"]
                repo.log_whatsapp(msg.get("id", ""), "inbound", wa_number, "received", msg)
                res = process_inbound(wa_number, text, name=contacts.get(wa_number))
                results.append(res)
            # delivery status callbacks
            for st in value.get("statuses", []):
                repo.set_message_status(st.get("id", ""), st.get("status", ""))
    return {"processed": len(results)}


# ------------------------------------------------------- simulator (demo)
@app.post("/api/simulator/message")
def simulator_message(msg: SimMessage):
    """Entry point for the built-in WhatsApp simulator (no Meta needed)."""
    res = process_inbound(msg.wa_number, msg.text, name=msg.name)
    detail = repo.conversation_detail(res["conversation_id"])
    return {"result": res, "messages": detail["messages"] if detail else [],
            "lead": detail["lead"] if detail else None}


@app.post("/api/inbound")
def api_inbound(msg: InboundMessage, _=Depends(require_auth)):
    """Attach point for n8n (or any orchestrator).

    n8n's WhatsApp Trigger receives a message and POSTs it here; the app
    understands it, updates the dashboard/DB, and returns the reply text for
    n8n's WhatsApp Business Cloud node to send back to the customer.
    """
    res = process_inbound(msg.wa_number, msg.text, name=msg.name, deliver=msg.deliver)
    return {
        "reply": res["reply"],
        "intent": res["intent"],
        "confidence": res["confidence"],
        "requires_human": res["requires_human"],
        "paused": res.get("paused", False),
        "actions": res["actions"],
        "wa_number": msg.wa_number,
    }


@app.get("/api/simulator/conversation")
def simulator_conversation(wa_number: str):
    detail = repo.find_conversation_by_number(settings.BUSINESS_ID, wa_number)
    if not detail:
        return {"messages": [], "lead": None, "conversation": None}
    return detail


@app.post("/api/simulator/reset")
def simulator_reset(wa_number: str, _=Depends(require_auth)):
    """Clear one demo customer's data so a scenario can be re-run cleanly."""
    detail = repo.find_conversation_by_number(settings.BUSINESS_ID, wa_number)
    with db.connect() as conn:
        cust = conn.execute(
            "SELECT id FROM customers WHERE business_id=? AND wa_number=?",
            (settings.BUSINESS_ID, wa_number),
        ).fetchone()
        if cust:
            cid = cust["id"]
            conn.execute("DELETE FROM messages WHERE customer_id=?", (cid,))
            conn.execute("DELETE FROM leads WHERE customer_id=?", (cid,))
            conn.execute("DELETE FROM appointments WHERE customer_id=?", (cid,))
            conn.execute("DELETE FROM conversations WHERE customer_id=?", (cid,))
            conn.execute("DELETE FROM customers WHERE id=?", (cid,))
    return {"reset": True, "wa_number": wa_number}


# ----------------------------------------------------------- dashboard API
@app.get("/api/analytics")
def api_analytics(_=Depends(require_auth)):
    return repo.analytics(settings.BUSINESS_ID)


@app.get("/api/conversations")
def api_conversations(_=Depends(require_auth)):
    return repo.dashboard_conversations(settings.BUSINESS_ID)


@app.get("/api/conversations/{conversation_id}")
def api_conversation(conversation_id: int, _=Depends(require_auth)):
    detail = repo.conversation_detail(conversation_id)
    if not detail:
        raise HTTPException(status_code=404, detail="not found")
    return detail


@app.get("/api/customers")
def api_customers(_=Depends(require_auth)):
    return repo.dashboard_customers(settings.BUSINESS_ID)


@app.get("/api/leads")
def api_leads(_=Depends(require_auth)):
    return repo.dashboard_leads(settings.BUSINESS_ID)


@app.get("/api/appointments")
def api_appointments(_=Depends(require_auth)):
    return repo.dashboard_appointments(settings.BUSINESS_ID)


@app.get("/api/business")
def api_business(_=Depends(require_auth)):
    return repo.get_business_knowledge(settings.BUSINESS_ID)


# ----------------------------------------------------- operator actions
@app.post("/api/conversations/{conversation_id}/reply")
def api_reply(conversation_id: int, body: ReplyIn, _=Depends(require_auth)):
    try:
        return operator_reply(conversation_id, body.text)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/conversations/{conversation_id}/pause")
def api_pause(conversation_id: int, _=Depends(require_auth)):
    pause_ai(conversation_id)
    return {"ok": True, "mode": "human"}


@app.post("/api/conversations/{conversation_id}/resume")
def api_resume(conversation_id: int, _=Depends(require_auth)):
    resume_ai(conversation_id)
    return {"ok": True, "mode": "ai"}


@app.post("/api/conversations/{conversation_id}/close")
def api_close(conversation_id: int, _=Depends(require_auth)):
    close_conversation(conversation_id)
    return {"ok": True, "status": "resolved"}


@app.post("/api/leads/{lead_id}/status")
def api_lead_status(lead_id: int, body: LeadStatusIn, _=Depends(require_auth)):
    repo.set_lead_status(lead_id, body.status)
    return {"ok": True, "lead_id": lead_id, "status": body.status}


# ------------------------------------------------- follow-up automations (n8n)
@app.get("/api/followups")
def api_followups(stale_hours: int = 20, _=Depends(require_auth)):
    """Items n8n should act on: stale un-booked leads + un-reminded appointments."""
    return repo.get_due_followups(settings.BUSINESS_ID, stale_hours=stale_hours)


@app.post("/api/leads/{lead_id}/followup")
def api_lead_followup(lead_id: int, _=Depends(require_auth)):
    try:
        return send_lead_followup(lead_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/appointments/{appointment_id}/remind")
def api_appointment_remind(appointment_id: int, _=Depends(require_auth)):
    try:
        return send_appointment_reminder(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# static assets (css/js) if any
if (WEB_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
