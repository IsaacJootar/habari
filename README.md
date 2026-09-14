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

**Phase 1 (in progress):** FastAPI skeleton with a `/webhook` stub and a fuzzy-match retrieval function over a curated JSON dataset of real fact-check articles.

- [x] FastAPI project skeleton (`app/main.py`)
- [x] Retrieval function (`app/retrieval.py`) — `rapidfuzz` token-set matching, confidence-thresholded so a weak match falls back to "Unverified" instead of guessing
- [ ] Curated dataset of 30-50 real fact-check articles (`data/factchecks.json`) — in progress
- [ ] Phase 2: LLM verdict synthesis (OpenAI)
- [ ] Phase 3: Twilio WhatsApp Sandbox integration + language detection
- [ ] Phase 4: Polish, multilingual pass, voice notes (stretch)
- [ ] Phase 5-6: Deliverables (video, deck, written summary), submission

## Running locally

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env         # fill in OPENAI_API_KEY etc. once Phase 2 lands
uvicorn app.main:app --reload
```

Manual check (Phase 1 — plain JSON in/out, not yet Twilio-shaped):

```bash
curl -X POST http://127.0.0.1:8000/webhook -H "Content-Type: application/json" -d "{\"message\": \"I heard COVID vaccines have a microchip inside them\"}"
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
