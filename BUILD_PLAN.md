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

## Phase 3 — WhatsApp integration ✅ DONE (2026-09-14)

- [x] Twilio account signup — done by user
- [x] Account SID / Auth Token in `.env` (fetched from console.twilio.com, not shown in chat)
- [x] Public tunnel: ngrok running (already installed + authenticated on this machine), tunnel at `https://elvin-fasciculate-wiley.ngrok-free.dev` → `localhost:8000` (this URL changes if ngrok is restarted — free tier doesn't keep a fixed subdomain)
- [x] New `/whatsapp` route: Twilio's form-encoded request in, TwiML reply out (`app/whatsapp.py`, `app/main.py`) — kept the old JSON `/webhook` around too for quick manual testing
- [x] Language detection (English/Swahili) — `app/language.py` (`langdetect`, deterministic seed); reply is generated in the detected language (LLM writes the explanation in-language; static Unverified/voice-note messages have pre-written EN/SW copies)
- [x] Voice-note-without-transcription handled gracefully (bilingual "not supported yet" message) rather than erroring
- [x] Tests: `tests/test_language.py`, `tests/test_whatsapp.py` (21 tests total now passing)
- [x] Live smoke tests (Twilio-shaped form POSTs): English matched claim, Swahili matched claim (correct verdict + Swahili explanation + real source), media-only message, empty message — all correct
- [x] Sandbox activated (accepted WhatsApp/Meta third-party terms, user confirmed), webhook URL saved in Twilio Console → Sandbox settings → "When a message comes in", method POST
- [x] User joined the Sandbox from their own WhatsApp
- [x] Real end-to-end test: message sent on WhatsApp → bot reply received on WhatsApp. Confirmed live: "coconut oil cures COVID-19" → correct FALSE verdict, correct explanation, correct real source_url, delivered back to the user's WhatsApp

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
