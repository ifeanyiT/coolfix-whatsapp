"""SQLite storage layer.

A single file database (coolfix.db) so the prototype needs zero setup.
We open a short-lived connection per operation (thread-safe with FastAPI's
worker threads) and use WAL mode for concurrent reads.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import settings
from . import knowledge


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,
    name TEXT, email TEXT UNIQUE, role TEXT DEFAULT 'operator',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS businesses (
    id TEXT PRIMARY KEY,
    name TEXT, tagline TEXT, tone TEXT, phone TEXT, email TEXT,
    opening_hours TEXT, service_areas TEXT, booking_rules TEXT, policies TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS services (
    slug TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    name TEXT, description TEXT, price TEXT, keywords TEXT
);

CREATE TABLE IF NOT EXISTS faqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,
    question TEXT, answer TEXT, keywords TEXT
);

CREATE TABLE IF NOT EXISTS knowledge_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,
    title TEXT, body TEXT, kind TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,
    wa_number TEXT NOT NULL,
    name TEXT, location TEXT, attributes TEXT,
    created_at TEXT, updated_at TEXT,
    UNIQUE(business_id, wa_number)
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    status TEXT DEFAULT 'active',      -- active | waiting_human | resolved | unresolved
    mode TEXT DEFAULT 'ai',            -- ai | human (paused)
    state TEXT,                        -- JSON slot-filling state
    last_intent TEXT,
    created_at TEXT, updated_at TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    business_id TEXT NOT NULL,
    customer_id INTEGER,
    direction TEXT,                    -- inbound | outbound
    origin TEXT,                       -- customer | ai | human | system
    type TEXT DEFAULT 'text',
    content TEXT,
    wa_message_id TEXT,
    status TEXT DEFAULT 'sent',        -- queued | sent | delivered | read | failed
    meta TEXT,
    created_at TEXT,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    conversation_id INTEGER,
    service TEXT, status TEXT DEFAULT 'new',   -- new|contacted|qualified|appointment_requested|booked|completed|lost|human_handoff
    location TEXT, preferred_time TEXT, problem TEXT,
    score INTEGER DEFAULT 0, notes TEXT,
    followed_up_at TEXT,
    created_at TEXT, updated_at TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    lead_id INTEGER,
    service TEXT, scheduled_for TEXT, slot TEXT,
    status TEXT DEFAULT 'upcoming',    -- upcoming | completed | cancelled
    notes TEXT, reminded_at TEXT, created_at TEXT
);

CREATE TABLE IF NOT EXISTS ai_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER, message_id INTEGER,
    intent TEXT, confidence REAL, requires_human INTEGER,
    model TEXT, raw TEXT, created_at TEXT
);

CREATE TABLE IF NOT EXISTS human_handoffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER, business_id TEXT,
    reason TEXT, status TEXT DEFAULT 'open',   -- open | resolved
    created_at TEXT, resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS automation_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT, workflow TEXT, status TEXT,
    detail TEXT, created_at TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wa_message_id TEXT, direction TEXT, wa_number TEXT,
    status TEXT, payload TEXT, created_at TEXT
);
"""


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
    seed_business()


def seed_business() -> None:
    """Seed CoolFix business knowledge if not already present."""
    b = knowledge.BUSINESS
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM businesses WHERE id=?", (b["id"],)).fetchone()
        if exists:
            return
        conn.execute(
            """INSERT INTO businesses(id,name,tagline,tone,phone,email,opening_hours,
               service_areas,booking_rules,policies,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (b["id"], b["name"], b["tagline"], b["tone"], b["phone"], b["email"],
             json.dumps(b["opening_hours"]), json.dumps(b["service_areas"]),
             json.dumps(b["booking_rules"]), json.dumps(b["policies"]), now_iso()),
        )
        for s in knowledge.SERVICES:
            conn.execute(
                """INSERT INTO services(slug,business_id,name,description,price,keywords)
                   VALUES(?,?,?,?,?,?)""",
                (s["slug"], b["id"], s["name"], s["description"], s["price"],
                 json.dumps(s["keywords"])),
            )
        for f in knowledge.FAQS:
            conn.execute(
                "INSERT INTO faqs(business_id,question,answer,keywords) VALUES(?,?,?,?)",
                (b["id"], f["question"], f["answer"], json.dumps(f["keywords"])),
            )
        for p in b["policies"]:
            conn.execute(
                "INSERT INTO knowledge_entries(business_id,title,body,kind) VALUES(?,?,?,?)",
                (b["id"], p["title"], p["body"], "policy"),
            )
        conn.execute(
            "INSERT INTO users(business_id,name,email,role,created_at) VALUES(?,?,?,?,?)",
            (b["id"], "CoolFix Operator", "operator@coolfixservices.ng", "operator", now_iso()),
        )
