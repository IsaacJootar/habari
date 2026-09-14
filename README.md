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

**Phases 1-2 done.** See [BUILD_PLAN.md](BUILD_PLAN.md) for the full phase-by-phase checklist.

- [x] FastAPI project skeleton (`app/main.py`)
- [x] Curated dataset of 40 real fact-check articles (`data/factchecks.json`)
- [x] Retrieval function (`app/retrieval.py`) — tag-gated fuzzy match, so a claim only surfaces articles it actually shares a topic with, then ranks by text similarity
- [x] LLM verdict synthesis (`app/llm.py`) — grounded strictly in the retrieved article(s); falls back to "Unverified" on any API error, malformed response, or if the model can't trace its answer back to a given article
- [ ] Phase 3: Twilio WhatsApp Sandbox integration + language detection
- [ ] Phase 4: Polish, multilingual pass, voice notes (stretch)
- [ ] Phase 5-6: Deliverables (video, deck, written summary), submission

## Running locally

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env         # fill in OPENAI_API_KEY (Twilio vars come in Phase 3)
uvicorn app.main:app --reload
```

Manual check (plain JSON in/out for now — Phase 3 makes this Twilio-shaped):

```bash
curl -X POST http://127.0.0.1:8000/webhook -H "Content-Type: application/json" -d "{\"message\": \"someone shared an article saying Philippine scientists proved coconut oil cures COVID-19\"}"
```

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
