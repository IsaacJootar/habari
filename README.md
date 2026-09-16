# Habari

**Habari** ("news" in Swahili) is a WhatsApp bot that helps people check whether a rumor, claim, screenshot, or voice note they've received is true — by routing it to real fact-checks from trusted African fact-checking organizations, never by guessing.

Built for the OSF × Andela Hackathon (Stability & Social Cohesion track).

## Problem

Verified information already exists from credible fact-checking organizations — Africa Check, PesaCheck (Kenya/Tanzania/Uganda), Dubawa (Nigeria), and a growing roster of others (see [Sources](#sources) below) — but it's scattered across websites people don't know to visit. Misinformation, meanwhile, spreads fastest on WhatsApp, the platform people already use daily, even with limited data or bandwidth.

## How it works

A user forwards a message to the bot on WhatsApp — typed text, a voice note, or a screenshot/image, all handled the same way. Habari replies with:
- A verdict: **True / False / Misleading / Unverified**
- A 2-3 sentence plain-language explanation
- A link to the trusted source article
- If nothing matches: an honest "Unverified" plus what to check next

Habari is a **router and summarizer on top of existing trusted fact-checkers** — it never invents a verdict from general AI knowledge. If nothing real is found — neither in the curated dataset nor via live search — it always says "Unverified" rather than guessing.

### The flow, in plain terms

1. **Someone sends a message on WhatsApp** — a claim, a rumor, a screenshot they retyped — to the Habari number.
2. **Twilio hands it to our server, which replies right away** with "⏳ Checking that for you..." (English only — no AI call gates this step, so it's genuinely instant). The person sees something happen immediately instead of silence.
3. **Then, behind the scenes, in order:**
   - **Figure out the language** — a quick AI call reads the message and decides: English, Swahili, Hausa, Yoruba, or Igbo.
   - **Check our own saved file** — fast keyword search through the curated dataset for an obvious match.
   - **Check the internet, live, right now** — separately, Dubawa's and GhanaFact's own sites get searched directly, at that exact moment, catching anything published since the dataset was last updated (the other three sources block automatic searching, so they're limited to what's in the saved file).
   - **Hand everything to the AI** — whatever got found (saved file, live search, or both) goes to the AI along with the original message, under one strict rule: only repeat what a real article actually says, never invent.
4. **The AI decides:**
   - A real article answers the question → it summarizes that article's actual verdict, in plain language, in the person's own language, with the real link.
   - Nothing found actually answers it → an honest "Unverified," plus — if the claim names Nigeria, Kenya, Ghana, or Uganda — a suggestion to also check that country's national newspaper.
5. **The real answer arrives as a second WhatsApp message**, a few seconds after the first "checking" message, delivered via Twilio's messaging API.

So the person sees two messages: an instant "hold on," then the real, honest answer once it's actually been checked — never a fast but made-up one.

```
User (WhatsApp)
   → Twilio WhatsApp Sandbox (webhook)
   → Backend (FastAPI)
       1. Retrieve — fuzzy-match claim against curated dataset of real
          fact-check articles (data/factchecks.json)
       2. Live search — search Dubawa/GhanaFact's own sites right now,
          for anything published since the dataset was last curated
       3. LLM reads whatever was found (curated + live) and grounds a
          verdict + explanation ONLY in that — never outside knowledge.
          Nothing found or nothing relevant → "Unverified," plus a
          country-specific newspaper suggestion where one can be guessed.
   → Reply sent back on WhatsApp
```

A static file alone can never keep up with rumors happening this week — live search is what covers a claim from days ago that was never manually curated. See `BUILD_PLAN.md` Phase 1 ("Live search + national news suggestions") for why only 2 of the 5 sources can be searched live today, and what a claim not in the static file actually looks like end-to-end.

## Sources

Habari only ever cites real, published fact-checks from credible, verified organizations (ideally [IFCN](https://www.poynter.org/ifcn/) signatories) — it never lets the LLM guess from general knowledge. If a rumor isn't covered by any curated source, the honest answer is "Unverified," not a fabricated verdict.

The roster started with three East/West African fact-checkers and is actively growing — coverage gaps get fixed by adding more verified sources and more articles per source, not by loosening that rule. Currently 64 articles across 5 sources:

- [Dubawa](https://dubawa.org) — Nigeria and West Africa — **searched live**
- [GhanaFact](https://ghanafact.com) — Ghana — **searched live**
- [Africa Check](https://africacheck.org) — Pan-African — curated dataset only (blocks automated requests)
- [PesaCheck](https://pesacheck.org) — Kenya, Tanzania, Uganda — curated dataset only (blocks automated requests)
- [AFP Fact Check](https://factcheck.afp.com) — Pan-African desk — curated dataset only (blocks automated requests)

"Searched live" means every incoming claim is checked against that site's own search, right now, in addition to the curated dataset — not limited to whatever was manually curated ahead of time. The other three sites actively block plain automated requests (confirmed directly, not assumed), so they're covered only by the curated snapshot until a proper search API is added for them.

One candidate source (ZimFact) was investigated and deliberately **not** added — credible on paper, but its site is currently down, so no article could be verified. Excluded rather than cited with a broken link; see `BUILD_PLAN.md` Phase 1 for the full reasoning.

**Also, on an "Unverified" reply**, if the claim mentions Nigeria, Kenya, Ghana, or Uganda, Habari suggests that country's national newspaper as somewhere else to check ([Premium Times](https://www.premiumtimesng.com), [Nation Africa](https://nation.africa), [Daily Graphic](https://www.graphic.com.gh), [Daily Monitor](https://www.monitor.co.ug)). These are general news outlets, not fact-checkers — they never produce a verdict, only a "here's where to look next" suggestion.

## Status

**Phases 1-4 done (including both stretch goals) — live on the WhatsApp Sandbox, stress-tested.** See [BUILD_PLAN.md](BUILD_PLAN.md) for the full phase-by-phase checklist.

- [x] FastAPI project skeleton (`app/main.py`)
- [x] Curated dataset of 64 real fact-check articles across 5 sources (`data/factchecks.json`) — see [Sources](#sources)
- [x] Retrieval function (`app/retrieval.py`) — tag-gated fuzzy match, so a claim only surfaces articles it actually shares a topic with, ranked by how many tags matched (then fuzzy text similarity as a tie-breaker)
- [x] LLM verdict synthesis (`app/llm.py`) — grounded strictly in the retrieved article(s); falls back to "Unverified" on any API error, malformed response, or if the model can't trace its answer back to a given article
- [x] Twilio-shaped `/whatsapp` webhook + TwiML replies (`app/whatsapp.py`) — [connected to the real Sandbox](#connecting-the-real-whatsapp-sandbox) and verified with a live WhatsApp round-trip
- [x] 5-language detection — English, Swahili, Hausa, Yoruba, Igbo (`app/language.py`, LLM-based — see BUILD_PLAN.md for why)
- [x] Instant "⏳ Checking that for you..." reply (English only, by design) while the real verdict is generated in the background and sent as a follow-up message (language detection itself moved to the background too — it's an LLM call and was quietly blocking the "instant" reply until this was caught and fixed)
- [x] Live search (`app/live_search.py`) for Dubawa and GhanaFact, so a claim doesn't need to already be in the curated dataset — verified live against a real story not in the 64-entry file
- [x] National newspaper "check here too" suggestions on Unverified replies (`app/national_news.py`), 4 sample countries
- [x] Onboarding message + POC disclaimer for first-time senders (`app/session.py`, `app/whatsapp.py`)
- [x] Stress-tested against the locked demo scenarios (health rumor, election claim, scam) plus an unverifiable claim and a Swahili variant — found and fixed a real retrieval bug in the process (see BUILD_PLAN.md Phase 4)
- [x] Voice note transcription (`app/media.py`) — a voice note gets transcribed (OpenAI `gpt-4o-mini-transcribe`) and the text runs through the normal pipeline; verified with real synthesized speech, not just mocks
- [x] Image/screenshot claim extraction (`app/media.py`) — the visible claim text gets read out of the image (gpt-4o-mini, multimodal) and runs through the normal pipeline; verified with a real generated test image, not just mocks
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
