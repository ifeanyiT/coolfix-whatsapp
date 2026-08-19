"""Storage layer — works with SQLite (local) OR Postgres (production).

If DATABASE_URL is set (postgres://...), the app uses Postgres via a psycopg
connection pool. Otherwise it falls back to a local SQLite file. The rest of the
app (repo.py) is written against a small uniform Conn/Cur wrapper so the same
queries run on both. Placeholders use '?'; they're translated to '%s' for Postgres.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import settings
from . import knowledge

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_PG = DATABASE_URL.startswith("postgres")

_pool = None
if IS_PG:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    _dsn = DATABASE_URL
    for a, b in (("postgresql+psycopg://", "postgresql://"), ("postgres://", "postgresql://")):
        if _dsn.startswith(a):
            _dsn = b + _dsn[len(a):]
    _pool = ConnectionPool(_dsn, min_size=1, max_size=5,
                           kwargs={"row_factory": dict_row}, open=False)
    _pool.open()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _q(sql: str) -> str:
    return sql.replace("?", "%s") if IS_PG else sql


class Cur:
    """Uniform cursor: rows behave dict-like on both backends."""
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def lastrowid(self):
        return getattr(self._cur, "lastrowid", None)


class Conn:
    """Uniform connection wrapper over sqlite3 / psycopg."""
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, params=()):
        cur = self.raw.cursor()
        cur.execute(_q(sql), tuple(params))
        return Cur(cur)

    def insert(self, sql, params=()):
        """Run an INSERT and return the new row's id (works on both backends)."""
        if IS_PG:
            cur = self.raw.cursor()
            cur.execute(_q(sql) + " RETURNING id", tuple(params))
            return cur.fetchone()["id"]
        cur = self.raw.execute(sql, tuple(params))
        return cur.lastrowid

    def executescript(self, script):
        if IS_PG:
            cur = self.raw.cursor()
            for stmt in (s.strip() for s in script.split(";")):
                if stmt:
                    cur.execute(stmt)
        else:
            self.raw.executescript(script)


@contextmanager
def connect():
    if IS_PG:
        with _pool.connection() as raw:      # commits on clean exit, rolls back on error
            yield Conn(raw)
    else:
        raw = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA journal_mode=WAL;")
        try:
            yield Conn(raw)
            raw.commit()
        finally:
            raw.close()


# {PK} differs per backend; BIGINT works as a plain integer on both.
_PK = "BIGSERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id {PK}, business_id TEXT NOT NULL,
    name TEXT, email TEXT UNIQUE, role TEXT DEFAULT 'operator', created_at TEXT
);
CREATE TABLE IF NOT EXISTS businesses (
    id TEXT PRIMARY KEY, name TEXT, tagline TEXT, tone TEXT, phone TEXT, email TEXT,
    opening_hours TEXT, service_areas TEXT, booking_rules TEXT, policies TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS services (
    slug TEXT PRIMARY KEY, business_id TEXT NOT NULL,
    name TEXT, description TEXT, price TEXT, keywords TEXT
);
CREATE TABLE IF NOT EXISTS faqs (
    id {PK}, business_id TEXT NOT NULL, question TEXT, answer TEXT, keywords TEXT
);
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id {PK}, business_id TEXT NOT NULL, title TEXT, body TEXT, kind TEXT
);
CREATE TABLE IF NOT EXISTS customers (
    id {PK}, business_id TEXT NOT NULL, wa_number TEXT NOT NULL,
    name TEXT, location TEXT, attributes TEXT, created_at TEXT, updated_at TEXT,
    UNIQUE(business_id, wa_number)
);
CREATE TABLE IF NOT EXISTS conversations (
    id {PK}, business_id TEXT NOT NULL, customer_id BIGINT NOT NULL,
    status TEXT DEFAULT 'active', mode TEXT DEFAULT 'ai', state TEXT, last_intent TEXT,
    created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id {PK}, conversation_id BIGINT NOT NULL, business_id TEXT NOT NULL, customer_id BIGINT,
    direction TEXT, origin TEXT, type TEXT DEFAULT 'text', content TEXT,
    wa_message_id TEXT, status TEXT DEFAULT 'sent', meta TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS leads (
    id {PK}, business_id TEXT NOT NULL, customer_id BIGINT NOT NULL, conversation_id BIGINT,
    service TEXT, status TEXT DEFAULT 'new', location TEXT, preferred_time TEXT, problem TEXT,
    score INTEGER DEFAULT 0, notes TEXT, followed_up_at TEXT, created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS appointments (
    id {PK}, business_id TEXT NOT NULL, customer_id BIGINT NOT NULL, lead_id BIGINT,
    service TEXT, scheduled_for TEXT, slot TEXT, status TEXT DEFAULT 'upcoming',
    notes TEXT, reminded_at TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS ai_interactions (
    id {PK}, conversation_id BIGINT, message_id BIGINT, intent TEXT, confidence REAL,
    requires_human INTEGER, model TEXT, raw TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS human_handoffs (
    id {PK}, conversation_id BIGINT, business_id TEXT, reason TEXT,
    status TEXT DEFAULT 'open', created_at TEXT, resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS automation_executions (
    id {PK}, business_id TEXT, workflow TEXT, status TEXT, detail TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id {PK}, wa_message_id TEXT, direction TEXT, wa_number TEXT, status TEXT,
    payload TEXT, created_at TEXT
);
""".replace("{PK}", _PK)


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
    seed_business()


def seed_business() -> None:
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
