# Habari

**Habari** ("news" in Swahili) is a WhatsApp bot that helps people check whether a rumor, claim, or screenshot they've received is true — by routing it to real fact-checks from trusted African fact-checking organizations, never by guessing.

Built for the OSF × Andela Hackathon (Stability & Social Cohesion track).

## Problem

Verified information already exists from credible regional fact-checkers — Africa Check, PesaCheck (Kenya/Tanzania/Uganda), Dubawa (Nigeria) — but it's scattered across websites people don't know to visit. Misinformation, meanwhile, spreads fastest on WhatsApp, the platform people already use daily, even with limited data or bandwidth.

## How it works

A user forwards a message to the bot on WhatsApp. Habari replies with:
- A verdict: **True / False / Misleading / Unverified**
- A 2-3 sentence plain-language explanation
- A link to the trusted source article
- If nothing matches: an honest "Unverified" plus what to check next

Habari is a **router and summarizer on top of existing trusted fact-checkers** — it never invents a verdict from general AI knowledge. If no real, confident match is found in the curated dataset, it always says "Unverified" rather than guessing.

```
User (WhatsApp)
   → Twilio WhatsApp Sandbox (webhook)
   → Backend (FastAPI)
       1. Classify incoming message (topic, language) — LLM call
       2. Retrieve — fuzzy-match claim against curated dataset of real
          fact-check articles (Africa Check / PesaCheck / Dubawa)
       3. LLM synthesizes verdict + explanation, grounded ONLY in the
          retrieved article. No confident match → "Unverified."
   → Reply sent back on WhatsApp
```

## Status

**Phases 1-3 done, Phase 4 started early — live on the WhatsApp Sandbox.** See [BUILD_PLAN.md](BUILD_PLAN.md) for the full phase-by-phase checklist.

- [x] FastAPI project skeleton (`app/main.py`)
- [x] Curated dataset of 40 real fact-check articles (`data/factchecks.json`)
- [x] Retrieval function (`app/retrieval.py`) — tag-gated fuzzy match, so a claim only surfaces articles it actually shares a topic with, then ranks by text similarity
- [x] LLM verdict synthesis (`app/llm.py`) — grounded strictly in the retrieved article(s); falls back to "Unverified" on any API error, malformed response, or if the model can't trace its answer back to a given article
- [x] Twilio-shaped `/whatsapp` webhook + TwiML replies (`app/whatsapp.py`) — [connected to the real Sandbox](#connecting-the-real-whatsapp-sandbox) and verified with a live WhatsApp round-trip
- [x] 5-language detection — English, Swahili, Hausa, Yoruba, Igbo (`app/language.py`, LLM-based — see BUILD_PLAN.md for why)
- [x] Instant "⏳ Checking that for you..." reply while the real verdict is generated in the background and sent as a follow-up message
- [ ] Phase 4 (remaining): onboarding message, POC disclaimer, voice note transcription (stretch), image/screenshot claim extraction (stretch) — see BUILD_PLAN.md for the technical plan for both
- [ ] Phase 5-6: Deliverables (video, deck, written summary), submission

## Running locally

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env         # fill in OPENAI_API_KEY and Twilio vars
uvicorn app.main:app --reload
```

Manual check — plain JSON, for quick local testing without Twilio:

```bash
curl -X POST http://127.0.0.1:8000/webhook -H "Content-Type: application/json" -d "{\"message\": \"someone shared an article saying Philippine scientists proved coconut oil cures COVID-19\"}"
```

Manual check — Twilio-shaped (what `/whatsapp` actually receives), TwiML back:

```bash
curl -X POST http://127.0.0.1:8000/whatsapp -d "Body=someone shared an article saying Philippine scientists proved coconut oil cures COVID-19" -d "NumMedia=0"
```

### Connecting the real WhatsApp Sandbox

1. In the [Twilio Console](https://console.twilio.com), copy your **Account SID** and **Auth Token** (shown on the dashboard homepage) into `.env` as `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN`.
2. Under Messaging → Try it out → **WhatsApp Sandbox**, note the sandbox number and join code. From your own WhatsApp, message the sandbox number with the given `join <code>` phrase — this opts your number in for testing.
3. Habari needs to be reachable from the internet for Twilio to call it. Run a tunnel, e.g. [ngrok](https://ngrok.com) (free account required — one-time `ngrok config add-authtoken <token>` after signing up):
   ```bash
   ngrok http 8000
   ```
   Copy the `https://...ngrok-free.app` URL it prints.
4. Back in the Twilio Console's WhatsApp Sandbox settings, set **"When a message comes in"** to `<your ngrok URL>/whatsapp`, method **POST**, and save.
5. With `uvicorn app.main:app --reload` running locally, send a real claim to the sandbox number on WhatsApp (e.g. "I heard coconut oil cures COVID-19") and you should get a real verdict back.

Run tests:

```bash
pytest
```

## Design principles

- **Never hallucinate a verdict.** Only answer True/False/Misleading when a real matching source is found; otherwise "Unverified."
- **Low bandwidth first.** Plain text over WhatsApp, no heavy media required.
- **Multilingual.** English and Swahili at minimum.
- **Privacy by design.** No persistent user profiles; no logging of phone numbers or full message content beyond the active session.
- **Always cite a source.** Every verdict links back to the original fact-check article.
- **Clear next step.** An "Unverified" reply tells the user what to check next.

## Limitations (hackathon POC)

This is an invention-sprint proof of concept, not a production system — see `CLAUDE.md` for the full brief, build plan, and non-negotiable design constraints.
