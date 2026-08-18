"""Repository: all database reads and writes live here.

Keeping DB access in one module keeps the orchestrator and API thin and makes
it easy to swap SQLite for Postgres/Supabase later.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from . import db
from .config import settings


# ---------------------------------------------------------------- knowledge
def get_business_knowledge(business_id: str = None) -> dict:
    """Retrieve the full business knowledge bundle the AI is allowed to use."""
    business_id = business_id or settings.BUSINESS_ID
    with db.connect() as conn:
        b = conn.execute("SELECT * FROM businesses WHERE id=?", (business_id,)).fetchone()
        if not b:
            return {}
        services = conn.execute(
            "SELECT * FROM services WHERE business_id=?", (business_id,)
        ).fetchall()
        faqs = conn.execute(
            "SELECT * FROM faqs WHERE business_id=?", (business_id,)
        ).fetchall()
        policies = conn.execute(
            "SELECT * FROM knowledge_entries WHERE business_id=?", (business_id,)
        ).fetchall()

    return {
        "id": b["id"],
        "name": b["name"],
        "tagline": b["tagline"],
        "tone": b["tone"],
        "phone": b["phone"],
        "email": b["email"],
        "opening_hours": json.loads(b["opening_hours"]),
        "service_areas": json.loads(b["service_areas"]),
        "booking_rules": json.loads(b["booking_rules"]),
        "services": [
            {
                "slug": s["slug"], "name": s["name"], "description": s["description"],
                "price": s["price"], "keywords": json.loads(s["keywords"]),
            }
            for s in services
        ],
        "faqs": [
            {"question": f["question"], "answer": f["answer"], "keywords": json.loads(f["keywords"])}
            for f in faqs
        ],
        "policies": [{"title": p["title"], "body": p["body"]} for p in policies],
    }


# ---------------------------------------------------------------- customers
def get_or_create_customer(business_id: str, wa_number: str, name: str = None) -> dict:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE business_id=? AND wa_number=?",
            (business_id, wa_number),
        ).fetchone()
        if row:
            return dict(row)
        conn.execute(
            """INSERT INTO customers(business_id,wa_number,name,attributes,created_at,updated_at)
               VALUES(?,?,?,?,?,?)""",
            (business_id, wa_number, name, json.dumps({}), db.now_iso(), db.now_iso()),
        )
        row = conn.execute(
            "SELECT * FROM customers WHERE business_id=? AND wa_number=?",
            (business_id, wa_number),
        ).fetchone()
        return dict(row)


def get_customer(customer_id: int) -> Optional[dict]:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
        return dict(row) if row else None


def update_customer(customer_id: int, **fields) -> None:
    if not fields:
        return
    attributes = fields.pop("attributes", None)
    sets, vals = [], []
    for k, v in fields.items():
        if v is None:
            continue
        sets.append(f"{k}=?")
        vals.append(v)
    if attributes is not None:
        sets.append("attributes=?")
        vals.append(json.dumps(attributes))
    if not sets:
        return
    sets.append("updated_at=?")
    vals.append(db.now_iso())
    vals.append(customer_id)
    with db.connect() as conn:
        conn.execute(f"UPDATE customers SET {', '.join(sets)} WHERE id=?", vals)


# ------------------------------------------------------------ conversations
def get_active_conversation(business_id: str, customer_id: int) -> dict:
    with db.connect() as conn:
        row = conn.execute(
            """SELECT * FROM conversations
               WHERE business_id=? AND customer_id=? AND status NOT IN ('resolved')
               ORDER BY id DESC LIMIT 1""",
            (business_id, customer_id),
        ).fetchone()
        if row:
            return dict(row)
        conn.execute(
            """INSERT INTO conversations(business_id,customer_id,status,mode,state,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?)""",
            (business_id, customer_id, "active", "ai", json.dumps({}), db.now_iso(), db.now_iso()),
        )
        row = conn.execute(
            "SELECT * FROM conversations WHERE business_id=? AND customer_id=? ORDER BY id DESC LIMIT 1",
            (business_id, customer_id),
        ).fetchone()
        return dict(row)


def get_conversation(conversation_id: int) -> Optional[dict]:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        return dict(row) if row else None


def update_conversation(conversation_id: int, **fields) -> None:
    state = fields.pop("state", None)
    sets, vals = [], []
    for k, v in fields.items():
        sets.append(f"{k}=?")
        vals.append(v)
    if state is not None:
        sets.append("state=?")
        vals.append(json.dumps(state))
    sets.append("updated_at=?")
    vals.append(db.now_iso())
    vals.append(conversation_id)
    with db.connect() as conn:
        conn.execute(f"UPDATE conversations SET {', '.join(sets)} WHERE id=?", vals)


def get_conversation_state(conversation_id: int) -> dict:
    conv = get_conversation(conversation_id)
    if not conv:
        return {}
    try:
        return json.loads(conv["state"] or "{}")
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------- messages
def add_message(conversation_id: int, business_id: str, customer_id: int,
                direction: str, origin: str, content: str,
                wa_message_id: str = None, status: str = "sent",
                mtype: str = "text", meta: dict = None) -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO messages(conversation_id,business_id,customer_id,direction,origin,
               type,content,wa_message_id,status,meta,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (conversation_id, business_id, customer_id, direction, origin, mtype, content,
             wa_message_id, status, json.dumps(meta or {}), db.now_iso()),
        )
        mid = cur.lastrowid
        row = conn.execute("SELECT * FROM messages WHERE id=?", (mid,)).fetchone()
        return dict(row)


def get_history(conversation_id: int, limit: int = None) -> list[dict]:
    limit = limit or settings.HISTORY_WINDOW
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def get_all_messages(conversation_id: int) -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY id ASC", (conversation_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def set_message_status(wa_message_id: str, status: str) -> None:
    with db.connect() as conn:
        conn.execute("UPDATE messages SET status=? WHERE wa_message_id=?", (status, wa_message_id))


def set_message_status_by_id(message_id: int, status: str, wa_message_id: str = None) -> None:
    with db.connect() as conn:
        if wa_message_id:
            conn.execute("UPDATE messages SET status=?, wa_message_id=? WHERE id=?",
                         (status, wa_message_id, message_id))
        else:
            conn.execute("UPDATE messages SET status=? WHERE id=?", (status, message_id))


# ------------------------------------------------------------------- leads
def get_open_lead(customer_id: int) -> Optional[dict]:
    with db.connect() as conn:
        row = conn.execute(
            """SELECT * FROM leads WHERE customer_id=?
               AND status NOT IN ('completed','lost') ORDER BY id DESC LIMIT 1""",
            (customer_id,),
        ).fetchone()
        return dict(row) if row else None


def upsert_lead(business_id: str, customer_id: int, conversation_id: int, **fields) -> dict:
    existing = get_open_lead(customer_id)
    with db.connect() as conn:
        if existing:
            sets, vals = [], []
            for k, v in fields.items():
                if v is None:
                    continue
                sets.append(f"{k}=?")
                vals.append(v)
            if sets:
                sets.append("updated_at=?")
                vals.append(db.now_iso())
                vals.append(existing["id"])
                conn.execute(f"UPDATE leads SET {', '.join(sets)} WHERE id=?", vals)
            row = conn.execute("SELECT * FROM leads WHERE id=?", (existing["id"],)).fetchone()
            return dict(row)
        cols = ["business_id", "customer_id", "conversation_id", "created_at", "updated_at"]
        vals = [business_id, customer_id, conversation_id, db.now_iso(), db.now_iso()]
        for k, v in fields.items():
            cols.append(k)
            vals.append(v)
        placeholders = ",".join("?" * len(vals))
        conn.execute(f"INSERT INTO leads({','.join(cols)}) VALUES({placeholders})", vals)
        row = conn.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row)


def set_lead_status(lead_id: int, status: str) -> None:
    with db.connect() as conn:
        conn.execute("UPDATE leads SET status=?, updated_at=? WHERE id=?",
                     (status, db.now_iso(), lead_id))


def get_lead(lead_id: int) -> Optional[dict]:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        return dict(row) if row else None


def mark_lead_followed(lead_id: int) -> None:
    with db.connect() as conn:
        conn.execute("UPDATE leads SET followed_up_at=? WHERE id=?", (db.now_iso(), lead_id))


# ------------------------------------------------------------ appointments
def create_appointment(business_id: str, customer_id: int, lead_id: int,
                       service: str, scheduled_for: str, slot: str, notes: str = None) -> dict:
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO appointments(business_id,customer_id,lead_id,service,scheduled_for,slot,
               status,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
            (business_id, customer_id, lead_id, service, scheduled_for, slot, "upcoming",
             notes, db.now_iso()),
        )
        row = conn.execute("SELECT * FROM appointments ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row)


def set_appointment_status(appointment_id: int, status: str) -> None:
    with db.connect() as conn:
        conn.execute("UPDATE appointments SET status=? WHERE id=?", (status, appointment_id))


def get_appointment(appointment_id: int) -> Optional[dict]:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
        return dict(row) if row else None


def mark_appointment_reminded(appointment_id: int) -> None:
    with db.connect() as conn:
        conn.execute("UPDATE appointments SET reminded_at=? WHERE id=?",
                     (db.now_iso(), appointment_id))


def get_due_followups(business_id: str, stale_hours: int = 20) -> dict:
    """Items n8n should follow up on: stale un-booked leads + un-reminded appointments."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=stale_hours)).isoformat()
    with db.connect() as conn:
        stale_leads = conn.execute(
            """SELECT l.*, cu.name AS customer_name, cu.wa_number
               FROM leads l JOIN customers cu ON cu.id=l.customer_id
               WHERE l.business_id=? AND l.followed_up_at IS NULL
                 AND l.status IN ('new','contacted','qualified','appointment_requested')
                 AND l.updated_at < ?
               ORDER BY l.updated_at ASC""",
            (business_id, cutoff),
        ).fetchall()
        appts = conn.execute(
            """SELECT a.*, cu.name AS customer_name, cu.wa_number
               FROM appointments a JOIN customers cu ON cu.id=a.customer_id
               WHERE a.business_id=? AND a.status='upcoming' AND a.reminded_at IS NULL
               ORDER BY a.id ASC""",
            (business_id,),
        ).fetchall()
    return {
        "stale_leads": [dict(r) for r in stale_leads],
        "upcoming_appointments": [dict(r) for r in appts],
    }


# --------------------------------------------------------------- handoffs
def create_handoff(conversation_id: int, business_id: str, reason: str) -> dict:
    with db.connect() as conn:
        open_ = conn.execute(
            "SELECT * FROM human_handoffs WHERE conversation_id=? AND status='open'",
            (conversation_id,),
        ).fetchone()
        if open_:
            return dict(open_)
        conn.execute(
            """INSERT INTO human_handoffs(conversation_id,business_id,reason,status,created_at)
               VALUES(?,?,?,?,?)""",
            (conversation_id, business_id, reason, "open", db.now_iso()),
        )
        row = conn.execute("SELECT * FROM human_handoffs ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row)


def resolve_handoffs(conversation_id: int) -> None:
    with db.connect() as conn:
        conn.execute(
            "UPDATE human_handoffs SET status='resolved', resolved_at=? WHERE conversation_id=? AND status='open'",
            (db.now_iso(), conversation_id),
        )


# ---------------------------------------------------------------- logging
def log_ai_interaction(conversation_id: int, message_id: int, intent: str,
                       confidence: float, requires_human: bool, model: str, raw: dict) -> None:
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO ai_interactions(conversation_id,message_id,intent,confidence,
               requires_human,model,raw,created_at) VALUES(?,?,?,?,?,?,?,?)""",
            (conversation_id, message_id, intent, confidence, int(requires_human), model,
             json.dumps(raw), db.now_iso()),
        )


def log_automation(business_id: str, workflow: str, status: str, detail: dict) -> None:
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO automation_executions(business_id,workflow,status,detail,created_at)
               VALUES(?,?,?,?,?)""",
            (business_id, workflow, status, json.dumps(detail), db.now_iso()),
        )


def log_whatsapp(wa_message_id: str, direction: str, wa_number: str, status: str, payload: dict) -> None:
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO whatsapp_messages(wa_message_id,direction,wa_number,status,payload,created_at)
               VALUES(?,?,?,?,?,?)""",
            (wa_message_id, direction, wa_number, status, json.dumps(payload), db.now_iso()),
        )


# -------------------------------------------------------------- dashboard
def dashboard_conversations(business_id: str) -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT c.*, cu.name AS customer_name, cu.wa_number, cu.location,
               (SELECT content FROM messages m WHERE m.conversation_id=c.id ORDER BY m.id DESC LIMIT 1) AS last_message,
               (SELECT created_at FROM messages m WHERE m.conversation_id=c.id ORDER BY m.id DESC LIMIT 1) AS last_at,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) AS message_count
               FROM conversations c JOIN customers cu ON cu.id=c.customer_id
               WHERE c.business_id=? ORDER BY c.updated_at DESC""",
            (business_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def dashboard_customers(business_id: str) -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT cu.*,
               (SELECT status FROM leads l WHERE l.customer_id=cu.id ORDER BY l.id DESC LIMIT 1) AS lead_status,
               (SELECT updated_at FROM conversations c WHERE c.customer_id=cu.id ORDER BY c.id DESC LIMIT 1) AS last_conversation
               FROM customers cu WHERE cu.business_id=? ORDER BY cu.updated_at DESC""",
            (business_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def dashboard_leads(business_id: str) -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT l.*, cu.name AS customer_name, cu.wa_number
               FROM leads l JOIN customers cu ON cu.id=l.customer_id
               WHERE l.business_id=? ORDER BY l.updated_at DESC""",
            (business_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def dashboard_appointments(business_id: str) -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT a.*, cu.name AS customer_name, cu.wa_number
               FROM appointments a JOIN customers cu ON cu.id=a.customer_id
               WHERE a.business_id=? ORDER BY a.id DESC""",
            (business_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def conversation_detail(conversation_id: int) -> Optional[dict]:
    conv = get_conversation(conversation_id)
    if not conv:
        return None
    customer = get_customer(conv["customer_id"])
    messages = get_all_messages(conversation_id)
    lead = get_open_lead(conv["customer_id"])
    with db.connect() as conn:
        appts = conn.execute(
            "SELECT * FROM appointments WHERE customer_id=? ORDER BY id DESC",
            (conv["customer_id"],),
        ).fetchall()
        handoffs = conn.execute(
            "SELECT * FROM human_handoffs WHERE conversation_id=? ORDER BY id DESC",
            (conversation_id,),
        ).fetchall()
    return {
        "conversation": conv,
        "customer": customer,
        "messages": messages,
        "lead": lead,
        "appointments": [dict(a) for a in appts],
        "handoffs": [dict(h) for h in handoffs],
    }


def find_conversation_by_number(business_id: str, wa_number: str) -> Optional[dict]:
    customer = None
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE business_id=? AND wa_number=?",
            (business_id, wa_number),
        ).fetchone()
        customer = dict(row) if row else None
    if not customer:
        return None
    conv = get_active_conversation(business_id, customer["id"])
    return conversation_detail(conv["id"])


def analytics(business_id: str) -> dict:
    with db.connect() as conn:
        def one(q, *p):
            return conn.execute(q, p).fetchone()[0]

        conversations = one("SELECT COUNT(*) FROM conversations WHERE business_id=?", business_id)
        leads = one("SELECT COUNT(*) FROM leads WHERE business_id=?", business_id)
        qualified = one(
            "SELECT COUNT(*) FROM leads WHERE business_id=? AND status IN ('qualified','appointment_requested','booked','completed')",
            business_id)
        booked = one("SELECT COUNT(*) FROM appointments WHERE business_id=?", business_id)
        handoffs = one("SELECT COUNT(*) FROM human_handoffs WHERE business_id=?", business_id)
        waiting = one("SELECT COUNT(*) FROM conversations WHERE business_id=? AND status='waiting_human'", business_id)
        messages = one("SELECT COUNT(*) FROM messages WHERE business_id=?", business_id)
    conversion = round((booked / conversations * 100), 1) if conversations else 0.0
    return {
        "conversations": conversations,
        "messages": messages,
        "leads": leads,
        "qualified_leads": qualified,
        "appointments_booked": booked,
        "human_handoffs": handoffs,
        "waiting_for_human": waiting,
        "conversion_rate": conversion,
    }
