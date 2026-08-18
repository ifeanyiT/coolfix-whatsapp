# CoolFix Services — AI WhatsApp Customer-Service & Sales Chatbot

A working prototype of an **AI WhatsApp employee** for a small home-services business
("CoolFix Services" — AC installation/repair/servicing, electrical, generators).

Customers chat over WhatsApp; the AI understands intent, answers from the business's
**real** information (never invents prices/hours/areas), collects details, creates and
qualifies leads, books appointments, and hands off to a human when needed — all visible
in a business dashboard.

It runs **fully offline with no Meta account and no API key** thanks to built-in mock
providers. Add an OpenAI key and/or Meta credentials later with zero code changes.

```
WhatsApp msg → webhook → AI intent → retrieve business info → grounded reply
             → action (collect info / lead / booking / handoff) → store → dashboard
```

---

## Quick start (2 commands)

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

Then open:

| URL | What it is |
|-----|------------|
| http://127.0.0.1:8000 | **WhatsApp simulator** — chat as a customer |
| http://127.0.0.1:8000/dashboard | **Business dashboard** — conversations, leads, appointments, analytics |
| http://127.0.0.1:8000/docs | Auto-generated REST API docs |

> No configuration needed for the demo. It starts in **mock AI + mock WhatsApp** mode.

---

## Try it (demo scenarios)

In the simulator, click a scenario chip or type. Try this booking flow and watch the
right-hand panel + dashboard update live:

1. `I want to book an AC repair`
2. `I'm in Lekki`
3. `tomorrow afternoon`  → **appointment booked**, lead marked *booked*

Other scenarios:

| Scenario | Try typing | What happens |
|----------|-----------|--------------|
| FAQ | `What time do you open?` | Answers from business hours |
| Service enquiry | `My AC is not cooling` | Identifies AC Repair, creates lead |
| Sales lead | `I want to install a new AC` | Sales intent → qualified lead |
| Human handoff | `I want to speak to someone` | Pauses AI, flags for operator |
| Emergency | `My AC is sparking!` | Safety message + immediate handoff |
| Out of area | `I need AC repair` → `I'm in Ibadan` | Detects unserved area, offers options |

In the **dashboard → Conversations**, click a conversation to **pause the AI, reply as a
human operator, resume the AI, close the chat, or change the lead status**.

---

## Going live (optional)

Copy `.env.example` to `.env` and fill in what you have:

**Real OpenAI**
```
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

**Real Meta WhatsApp Cloud API**
```
WHATSAPP_PROVIDER=meta
META_ACCESS_TOKEN=...
META_PHONE_NUMBER_ID=...
META_VERIFY_TOKEN=coolfix-verify-token
META_APP_SECRET=...
```
Point your Meta webhook to `https://<your-host>/webhook/whatsapp` (expose it with a tunnel
like ngrok/Cloudflare Tunnel). The `GET` verifies the token; the `POST` receives messages
and verifies the `X-Hub-Signature-256` signature.

**Protect the dashboard** — set `DASHBOARD_TOKEN=<secret>`; dashboard/admin API calls then
require `Authorization: Bearer <secret>`.

Secrets live only in `.env` (git-ignored) — never hard-coded, never sent to the frontend.

---

## Architecture

```
app/
  config.py          Env-driven settings (mock vs live)
  db.py              SQLite schema + seeding (single-file DB, zero setup)
  knowledge.py       CoolFix business knowledge (source of truth)
  repo.py            All DB reads/writes + dashboard queries
  orchestrator.py    The core pipeline (in-app equivalent of the n8n workflow)
  ai/
    base.py          Intent taxonomy + AIResult type + knowledge rendering
    mock_ai.py       Offline rule-based intent + slot extraction
    openai_ai.py     OpenAI adapter (structured JSON, grounded in knowledge)
  whatsapp/
    base.py          Provider interface
    mock.py          Local simulator provider (tracks message IDs + delivery)
    meta.py          Real Meta Cloud API provider + webhook/signature verification
  main.py            FastAPI app: REST API, webhook, static UI
web/
  simulator.html     WhatsApp-style chat simulator
  dashboard.html     Operator dashboard (conversations, leads, appointments, analytics)
n8n/
  coolfix_whatsapp_workflow.json   Importable n8n workflow mirroring the orchestrator
```

**Design principles**
- The **language model never performs business actions.** It only classifies intent and
  extracts data. All bookings, lead status and handoffs are decided in `orchestrator.py`,
  so the bot never claims something happened that didn't.
- **Grounded answers only** — the AI is given the business knowledge and told not to invent.
- **Swappable providers** — AI and WhatsApp are behind interfaces; mock ↔ real is an env flag.
- **Conversation memory** — a windowed history + per-conversation slot state means a bare
  reply like "Ikoyi" is understood as the answer to "what area are you in?".

---

## Intent taxonomy

`greeting · faq · pricing · service_info · booking · complaint · existing_customer ·
new_lead · recommendation · human_support · emergency · unknown`

The AI returns structured data, e.g.:
```json
{ "intent": "booking", "confidence": 0.92, "requires_human": false, "service": "ac_repair" }
```

## Lead statuses
`new · contacted · qualified · appointment_requested · booked · completed · lost · human_handoff`

---

## n8n workflow

`n8n/coolfix_whatsapp_workflow.json` imports into any n8n instance. It represents the same
pipeline as `orchestrator.py`:

`Webhook → Parse → Retrieve Business Knowledge → AI Intent Detection → Route by Intent →
(emergency / human / booking / info) → Generate Reply, Send & Store → Respond`

Set n8n env vars `OPENAI_API_KEY` and `APP_BASE_URL` (e.g. `http://host.docker.internal:8000`).
The workflow calls this app to generate the grounded reply, send via WhatsApp and persist —
so n8n orchestrates while the app remains the single source of business logic.

---

## REST API (selected)

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/webhook/whatsapp` | Meta webhook (verify + receive) |
| POST | `/api/simulator/message` | Send a message as a customer (demo) |
| GET | `/api/analytics` | Conversation/lead/appointment metrics |
| GET | `/api/conversations` · `/api/conversations/{id}` | List / conversation detail |
| GET | `/api/customers` · `/api/leads` · `/api/appointments` | Dashboard data |
| POST | `/api/conversations/{id}/pause` · `/resume` · `/close` · `/reply` | Operator actions |
| POST | `/api/leads/{id}/status` | Update lead status |
| GET | `/api/business` | Business knowledge |

Full interactive docs at `/docs`.

---

## Notes
- Database is a single file `coolfix.db`, created and seeded on first run. Delete it to reset.
- Built with FastAPI + SQLite (standard library) + vanilla HTML/JS. No build step.
- Tested end-to-end on Python 3.14.
