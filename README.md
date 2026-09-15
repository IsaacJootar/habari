# Habari

**Habari** ("news" in Swahili) is a WhatsApp bot that helps people check whether a rumor, claim, or screenshot they've received is true — by routing it to real fact-checks from trusted African fact-checking organizations, never by guessing.

Built for the OSF × Andela Hackathon (Stability & Social Cohesion track).

## Problem

Verified information already exists from credible fact-checking organizations — Africa Check, PesaCheck (Kenya/Tanzania/Uganda), Dubawa (Nigeria), and a growing roster of others (see [Sources](#sources) below) — but it's scattered across websites people don't know to visit. Misinformation, meanwhile, spreads fastest on WhatsApp, the platform people already use daily, even with limited data or bandwidth.

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
          fact-check articles from verified fact-checking organizations
       3. LLM synthesizes verdict + explanation, grounded ONLY in the
          retrieved article. No confident match → "Unverified."
   → Reply sent back on WhatsApp
```

## Sources

Habari only ever cites real, published fact-checks from credible, verified organizations (ideally [IFCN](https://www.poynter.org/ifcn/) signatories) — it never lets the LLM guess from general knowledge. If a rumor isn't covered by any curated source, the honest answer is "Unverified," not a fabricated verdict.

The roster started with three East/West African fact-checkers and is actively growing — coverage gaps get fixed by adding more verified sources and more articles per source, not by loosening that rule. Currently 64 articles across 5 sources:

- [Africa Check](https://africacheck.org) — Pan-African
- [PesaCheck](https://pesacheck.org) — Kenya, Tanzania, Uganda
- [Dubawa](https://dubawa.org) — Nigeria and West Africa
- [GhanaFact](https://ghanafact.com) — Ghana
- [AFP Fact Check](https://factcheck.afp.com) — Pan-African desk

One candidate source (ZimFact) was investigated and deliberately **not** added — credible on paper, but its site is currently down, so no article could be verified. Excluded rather than cited with a broken link; see `BUILD_PLAN.md` Phase 1 for the full reasoning.

## Status

**Phases 1-3 done, Phase 4 started early — live on the WhatsApp Sandbox.** See [BUILD_PLAN.md](BUILD_PLAN.md) for the full phase-by-phase checklist.

- [x] FastAPI project skeleton (`app/main.py`)
- [x] Curated dataset of 64 real fact-check articles across 5 sources (`data/factchecks.json`) — see [Sources](#sources)
- [x] Retrieval function (`app/retrieval.py`) — tag-gated fuzzy match, so a claim only surfaces articles it actually shares a topic with, ranked by how many tags matched (then fuzzy text similarity as a tie-breaker)
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
2. Under Messaging → Try it out → **WhatsApp Sandbox**, note the sandbox number and join code (currently `+1 415 523 8886` / `join stage-begun`, but these can change if the sandbox is reset — check the Twilio Console for the current ones). Join it either way:
   - **Scan the QR code** below with your phone — opens WhatsApp with the join message pre-filled, just tap send.
     <br>![WhatsApp Sandbox join QR code](docs/whatsapp-sandbox-qr.png)
   - **Or message it manually:** from your own WhatsApp, send `join stage-begun` to `+1 415 523 8886`.
   Both do exactly the same thing — the QR code just encodes the same `join` message as a scannable link.
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
