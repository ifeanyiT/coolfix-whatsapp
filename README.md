# CoolFix — AI WhatsApp Customer-Service & Sales Assistant

A production-deployed **AI "WhatsApp employee"** for a real small business
(**CoolFix Services** — a Lagos home-services company: AC install/repair/servicing,
electrical work, generators).

A customer sends a WhatsApp message and, within seconds, the AI understands what they
want, answers from the business's **real** information, captures the lead, books the
appointment (onto Google Calendar), sends reminders, and hands off to a human when
needed — all visible in a business dashboard.

> **Status:** live and deployed — real WhatsApp number, real AI, permanent database.

---

## What it does
- 💬 **Instant replies, 24/7** on WhatsApp (via Meta Cloud API + n8n)
- 🧠 **Agentic AI (OpenAI)** grounded in a business knowledge base (RAG) — real prices,
  hours, services, policies; **never invents** info; politely declines out-of-scope requests
- 🎯 **Lead capture & qualification** — turns chats into customers
- 📅 **Appointment booking** → creates a **Google Calendar** event with a concrete time
- 🔔 **WhatsApp reminders & follow-ups** (hourly, via n8n)
- 🤝 **Human handoff** — complaints, emergencies, or "talk to a person" → operator takes over
- 📊 **Operator dashboard** — conversations, customers, leads, appointments, analytics; reply as a human
- 🗄️ **Permanent Postgres storage** — nothing is ever lost
- 🛟 **Graceful fallback** — if the LLM errors, a built-in rule engine keeps the bot answering

## Architecture
```
Customer ─▶ WhatsApp ─▶ Meta Cloud API ─▶ n8n (WhatsApp Trigger)
                                             │
                                             ▼
                                 FastAPI app  /api/inbound
                                   • OpenAI agentic AI + RAG knowledge base
                                   • leads, bookings, human handoff
                                   ▼
                                 PostgreSQL (permanent)
                                   │
             ┌─────────────────────┼───────────────────────────┐
             ▼                     ▼                           ▼
   n8n → WhatsApp reply   n8n → Google Calendar      n8n → WhatsApp reminders
                          (event on each booking)     (hourly follow-ups/nudges)

   Operator dashboard  ◀── live conversations, take over, leads, analytics
```

## Tech stack
- **Backend:** Python + FastAPI
- **AI:** OpenAI (agentic, grounded in a knowledge base) with a rule-based fallback engine
- **Data:** PostgreSQL (Supabase); SQLite for local dev — one dialect-aware layer
- **Messaging:** Meta WhatsApp Cloud API, orchestrated by n8n
- **Calendar:** Google Calendar (via n8n)
- **Frontend:** vanilla HTML/JS — marketing site, live demo, operator dashboard
- **Hosting:** Docker on Render (auto-deploy from GitHub)

## Project layout
```
app/
  config.py         Env-driven settings
  db.py             Dialect-aware storage (SQLite local / Postgres prod)
  knowledge.py      Business knowledge = source of truth (mirrored in KNOWLEDGE.md)
  repo.py           Data access + dashboard queries
  orchestrator.py   Core pipeline: understand → act → respond → store; booking→calendar webhook
  ai/               mock (fallback) + openai (agentic, grounded) engines
  whatsapp/         mock + Meta Cloud API providers
  main.py           FastAPI app: REST API, webhook, /api/inbound, dashboard
web/
  landing.html      Marketing site + embedded live demo
  dashboard.html    Operator dashboard (token login)
  simulator.html    Raw simulator with AI-internals panel (/demo)
n8n/
  coolfix_whatsapp_attach.json    Inbound: WhatsApp → app → reply
  coolfix_calendar_workflow.json  Booking → Google Calendar event
  coolfix_followups_workflow.json Hourly WhatsApp reminders & nudges
```

## Run locally
```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```
- Marketing site + live demo: http://127.0.0.1:8000
- Dashboard: http://127.0.0.1:8000/dashboard
- API docs: http://127.0.0.1:8000/docs

Runs on SQLite + the built-in AI engine with **zero config**. Set `DATABASE_URL`,
`AI_PROVIDER=openai` + `OPENAI_API_KEY`, and the Meta/n8n vars to go live (see `.env.example`,
`DEPLOY.md`, and `CONNECT.md`).

## Docs in this repo
- **KNOWLEDGE.md** — the business knowledge reference (edit `app/knowledge.py` to change it)
- **DEPLOY.md** — deploy the app + attach n8n WhatsApp + calendar/reminders
- **CONNECT.md** — connect a real Meta WhatsApp number
- **SOCIAL_POSTS.md** — ready-to-post LinkedIn & Facebook announcements
