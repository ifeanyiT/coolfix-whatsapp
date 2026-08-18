# Connect CoolFix to a real WhatsApp business + n8n Cloud

Your setup: **ngrok tunnel** · **n8n Cloud** · Meta account exists, WhatsApp not yet added.

Topology: **Meta → your app** for live chat, **n8n Cloud** for scheduled follow-ups.

```
Customer ─▶ WhatsApp ─▶ Meta Cloud API ─▶ ngrok ─▶ your app /webhook/whatsapp ─▶ AI + DB + reply
                                                          ▲
                                    n8n Cloud (hourly) ───┘  reminders & lead nudges
```

---

## Step 1 — Run the app locally
```bash
.venv\Scripts\python run.py
```
Leave it running. It's on `http://127.0.0.1:8000`.

## Step 2 — Expose it with ngrok
One-time (needs a free ngrok account → copy your authtoken from dashboard.ngrok.com):
```bash
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```
Then, in a **separate terminal**:
```bash
ngrok http 8000
```
Copy the HTTPS forwarding URL it shows, e.g. `https://a1b2c3d4.ngrok-free.app`.
This is your **public base URL** — call it `<BASE>` below.

> Free ngrok URLs change every restart. Each time it changes you must update the Meta
> webhook (Step 4) and the n8n Config node (Step 7). A paid ngrok domain fixes this.

## Step 3 — Meta: add WhatsApp and get a test number
1. Go to **developers.facebook.com → My Apps → Create App**. Choose **Business**, name it.
2. In the app dashboard, **Add product → WhatsApp → Set up**.
3. Open **WhatsApp → API Setup**. You now have:
   - a **test phone number** (Meta provides it),
   - a **Temporary access token** (valid 24h),
   - a **Phone number ID**,
   - a **WhatsApp Business Account ID**.
   Copy the **token** and **Phone number ID**.
4. On that same page under **"To"**, add **your own WhatsApp number** as a recipient and
   confirm the code Meta sends you. (Test numbers can only message approved recipients.)
5. Get your **App Secret**: **App settings → Basic → App Secret → Show**. Copy it.

## Step 4 — Point Meta's webhook at your app
1. **WhatsApp → Configuration → Webhook → Edit**.
2. **Callback URL:** `<BASE>/webhook/whatsapp`
3. **Verify token:** `coolfix-verify-token`  (this must match `.env` — it's the default)
4. Click **Verify and save**. Meta calls your app; it should succeed immediately.
5. Under **Webhook fields**, click **Manage** and **subscribe to `messages`**.

## Step 5 — Configure the app (.env)
Copy `.env.example` to `.env` and set:
```
WHATSAPP_PROVIDER=meta
META_ACCESS_TOKEN=<paste temporary token>
META_PHONE_NUMBER_ID=<paste phone number ID>
META_VERIFY_TOKEN=coolfix-verify-token
META_APP_SECRET=<paste app secret>

# Protects the dashboard + the n8n follow-up endpoints:
DASHBOARD_TOKEN=<make up a strong secret>

# Optional: turn on the real AI brain (otherwise the built-in engine is used)
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```
Restart the app (`Ctrl+C`, then `python run.py`). Confirm at `<BASE>/api/health` that it
reads `"whatsapp_provider":"meta"`.

> The temporary token expires in 24h. For a permanent one: **Business Settings → Users →
> System users → Add**, generate a token with `whatsapp_business_messaging` +
> `whatsapp_business_management`, set it to never expire, and put it in `META_ACCESS_TOKEN`.

## Step 6 — Test with a real phone
From your WhatsApp, message the Meta **test number**:
> How much is AC servicing?

You should get the AI reply within a second. Then try the booking flow
(`I want to book an AC repair` → `I'm in Lekki` → `tomorrow afternoon`) and watch it appear
live in the dashboard at `<BASE>/dashboard` (log in with your `DASHBOARD_TOKEN` if set —
send it as an `Authorization: Bearer` header; for a browser, easiest is to leave
`DASHBOARD_TOKEN` blank while testing).

## Step 7 — n8n Cloud follow-ups
1. Sign up / log in at **app.n8n.cloud**.
2. **Workflows → Import from File** → choose `n8n/coolfix_followups_workflow.json`.
3. Open the **"Config (edit me)"** node and set:
   - `baseUrl` = `<BASE>` (your ngrok HTTPS URL, no trailing slash)
   - `authToken` = the same `DASHBOARD_TOKEN` you put in `.env` (blank if you didn't set one)
4. Click **Test workflow** to run it once now — it fetches due items and sends any nudges/reminders.
5. **Save** and toggle **Active**. It now runs every hour automatically.

That's the spec's follow-up automation, live: stale un-booked leads get a nudge, upcoming
appointments get a reminder — each sent once (the app makes it idempotent).

---

## Optional — n8n as the inbound front door (topology B)
If you'd rather have n8n receive WhatsApp first and orchestrate the reply, import
`n8n/coolfix_whatsapp_workflow.json` instead, set its `OPENAI_API_KEY` / `APP_BASE_URL`,
copy the workflow's **Production webhook URL**, and use *that* as the Meta Callback URL in
Step 4. Keep either the app OR n8n as the inbound path — not both.

## Troubleshooting
| Symptom | Fix |
|--------|-----|
| Meta "webhook verification failed" | `<BASE>` wrong/old, app not running, or verify token ≠ `coolfix-verify-token`. |
| No reply to WhatsApp | Ensure you subscribed to the **messages** field (Step 4.5) and `.env` has `WHATSAPP_PROVIDER=meta`. Check the app terminal + `<BASE>/docs`. |
| Reply works for you but not others | Non-test recipients need Meta **business verification** (Business Settings → Security Center). Until then only approved test numbers work. |
| ngrok URL stopped working | It changed on restart — update Step 4 URL and the n8n Config node. |
| n8n calls return 401 | `authToken` in the Config node must equal `DASHBOARD_TOKEN`. |
