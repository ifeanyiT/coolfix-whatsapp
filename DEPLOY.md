# Put the app online, then attach n8n WhatsApp to it

Goal (your analogy): the app runs live like a website; n8n just **attaches** WhatsApp to it.
Nothing about the app is stopped or rebuilt.

```
Customer ─▶ WhatsApp ─▶ n8n Cloud (WhatsApp Trigger)
                          └─▶ calls your LIVE app /api/inbound  (understands + stores + dashboard)
                          ◀─┘ app returns the reply text
                        n8n (WhatsApp Business Cloud) ─▶ sends reply ─▶ Customer
```

---

## Part 1 — Put the app online (once)

The app currently runs only on your laptop. Deploy it so it has a permanent public URL
(like the furniture site that's already live). We use **Render**.

### 1a. Put the code on GitHub
Render deploys from a Git repo.
```bash
git init
git add .
git commit -m "CoolFix WhatsApp AI chatbot"
```
Create an empty repo on github.com, then:
```bash
git remote add origin https://github.com/<you>/coolfix-whatsapp.git
git branch -M main
git push -u origin main
```

### 1b. Deploy on Render
1. Go to **dashboard.render.com → New → Blueprint**.
2. Connect your GitHub repo. Render reads `render.yaml` and creates the web service.
3. In the service's **Environment**, set the secret values (left blank in the blueprint):
   - `DASHBOARD_TOKEN` = a strong secret you invent (protects the dashboard + `/api/inbound`)
   - `OPENAI_API_KEY` = your key **if** you set `AI_PROVIDER=openai` (optional; mock works without)
   - Meta values only if you also want the app to send directly (not needed for the n8n attach path)
4. Deploy. When it's live you get a URL like `https://coolfix-whatsapp.onrender.com` — call it `<APP>`.
5. Check `<APP>/api/health` and open `<APP>/dashboard` — it's the same app, now on the internet.

> Cost note: `render.yaml` uses the **starter** plan so the app is always-on and your data
> persists (via the 1 GB disk). To try it free first, change `plan: starter` → `plan: free`
> and delete the `disk:` block (data resets on restart, and the app sleeps when idle).

---

## Part 2 — Attach n8n WhatsApp (app keeps running)

1. In **n8n Cloud → Workflows → Import from File**, import `n8n/coolfix_whatsapp_attach.json`.
2. **WhatsApp Trigger** node → create **WhatsApp Trigger** credentials (Meta app ID + app secret +
   a verify token). n8n shows you a **callback URL** — put that URL + verify token into your Meta
   app's WhatsApp webhook config, and subscribe to the **messages** field. (This is where Meta
   sends messages — to n8n, not your laptop, so no ngrok.)
3. **Ask the App** node → set:
   - URL → `<APP>/api/inbound`
   - `Authorization` header → `Bearer <your DASHBOARD_TOKEN>` (or delete the header if you left it blank)
4. **Send WhatsApp Reply** node → create **WhatsApp Business Cloud** credentials (access token +
   business account) and set your **Phone Number ID**.
5. **Save** and **Activate**.

### Test
From your phone, WhatsApp your Meta number: "How much is AC servicing?"
- n8n Trigger fires → calls `<APP>/api/inbound` → app replies → n8n sends it back.
- Open `<APP>/dashboard` — the conversation, customer and any lead/booking are there.

The app never stopped. You attached WhatsApp to it. ✅

---

## Part 3 — Follow-ups (optional, also n8n)
Import `n8n/coolfix_followups_workflow.json`, set its **Config** node (`baseUrl` = `<APP>`,
`authToken` = `DASHBOARD_TOKEN`), Activate. It sends appointment reminders + nudges hourly.

## Notes
- Keep the app's `WHATSAPP_PROVIDER=mock` in this setup — n8n does the sending, so the app
  should not also send (avoids double messages). `/api/inbound` already tells it not to.
- If a human takes over a chat in the dashboard, `/api/inbound` returns an empty reply and the
  workflow's **Reply to send?** step correctly sends nothing.
- Swapping to the real OpenAI brain later = set `AI_PROVIDER=openai` + `OPENAI_API_KEY` in Render. No code change.
