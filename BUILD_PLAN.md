# Habari — Build Plan & Progress

Living checklist for the hackathon build. Updated as work lands — check items off in place rather than rewriting history. See `CLAUDE.md` for the full brief this plan is derived from.

---

## Phase 1 — Scope, data & backend skeleton ✅ DONE (2026-09-14)

- [x] Lock demo scenarios (health rumor, election/political claim, scam)
- [x] Collect curated dataset of real fact-check articles — `data/factchecks.json` (40 entries: 17 PesaCheck, 13 Africa Check, 10 Dubawa)
- [x] FastAPI project skeleton — `app/main.py`
- [x] `/webhook` route (Phase 1 stub: plain JSON in/out, not yet Twilio-shaped)
- [x] Retrieval function over the dataset — `app/retrieval.py` (tag-gated fuzzy match; a pure fuzzy score alone false-positived on unrelated claims, fixed by requiring a shared topic tag before ranking)
- [x] Tests — `tests/test_retrieval.py` (5 passing)
- [x] README first pass
- [x] Git repo initialized, pushed to `github.com/IsaacJootar/habari`

**Known caveat:** the 13 Africa Check dataset entries were cross-verified via search rather than a direct page fetch (site blocked automated access) — worth a manual spot-check before submission.

## Phase 2 — LLM verdict logic ✅ DONE (2026-09-14)

- [x] `app/llm.py` — OpenAI API wrapper (`gpt-4o-mini`, JSON-mode structured output)
- [x] Prompt template: claim + retrieved article(s) → structured verdict (True/False/Misleading/Unverified), plain-language explanation, source link
- [x] Grounding enforced: LLM only ever sees the retrieved article text, never asked to answer from general knowledge; `source_url` must exactly match one of the given articles or the reply is discarded
- [x] No-match case bypasses the LLM entirely and returns "Unverified" directly; the LLM can *also* independently downgrade to "Unverified" if the retrieved article(s) don't actually address the specific claim (verified live — a vaccine-microchip claim correctly got "Unverified" even with 3 vaccine-tagged candidates retrieved, because none specifically addressed microchips)
- [x] Wire into `/webhook`, replacing the Phase 1 stub response
- [x] `openai` added to `requirements.txt` (pinned to installed `3.13.0`), `OPENAI_API_KEY` wired from `.env` via `python-dotenv`
- [x] Tests (`tests/test_llm.py`, 7 cases, fully mocked) — no-match skip, valid match, LLM self-downgrade to Unverified, hallucinated source_url rejected, malformed JSON, invalid verdict value, API error — all fall back to Unverified
- [x] Live smoke test against the real dataset with a real API key: correct verdict/explanation/source_url on a strong match, correct "Unverified" on a weak match

## Phase 3 — WhatsApp integration

- [ ] Twilio account + WhatsApp Sandbox signup (using free trial credit)
- [ ] Public tunnel (ngrok or similar) for local webhook during dev
- [ ] `/webhook` converted from JSON stub to Twilio's form-encoded request format, replying with TwiML
- [ ] Language detection (English/Swahili) — reply in the language the user wrote in
- [ ] Real end-to-end test: message sent on WhatsApp → bot reply received on WhatsApp

## Phase 4 — Polish & multilingual/UX pass

- [ ] Onboarding message for first-time users
- [ ] Hackathon-POC disclaimer text in replies
- [ ] Voice note transcription via Whisper (stretch goal)
- [ ] Stress-test against the locked demo scenarios (health rumor, election claim, scam)

## Phase 5 — Deliverables: repo, video, deck

- [ ] README finalized (architecture diagram, how to run, limitations, next steps)
- [ ] 2-3 minute demo video of real WhatsApp exchanges
- [ ] Pitch deck

## Phase 6 — Written summary & submit

- [ ] Written summary (problem, users, how it works, how design addresses trust/verification, bandwidth, accessibility, privacy, multilingual access)
- [ ] Final end-to-end test
- [ ] Submit — buffer day before 2026-09-21 deadline, not on the day itself
