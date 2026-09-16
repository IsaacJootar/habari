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

### Source expansion (added 2026-09-15)

**Decision:** user raised a real concern — limiting to 3 fact-checkers means a genuine rumor could go unmatched and come back "Unverified" more often than it should. The fix is NOT to let the LLM guess when nothing matches (that would break the core trust design in `CLAUDE.md`) — it's to widen the pool of real, verified sources and deepen the article count. Agreed direction: grow the source roster over time, always vetting each new organization's credibility (ideally IFCN-signatory status) before adding it, never loosen the grounding rule itself.

- [x] **Verified and added GhanaFact and AFP Fact Check.** Dataset grew from 40 to **64 entries** (all 40 originals unchanged): 17 PesaCheck, 15 GhanaFact, 13 Africa Check, 10 Dubawa, 9 AFP Fact Check.
  - **GhanaFact** — confirmed IFCN-verified signatory (Ghana's first full-time fact-checker to sign the Code of Principles, run by FactSpace West Africa). 15 entries, all verified by direct page fetch.
  - **AFP Fact Check** — confirmed IFCN-verified signatory with an active Poynter Code of Principles profile and named Africa-based staff. 9 entries; `factcheck.afp.com` blocks automated fetches (Akamai), so 2 were verified via live wire-service mirrors and 7 via cross-referencing exact document IDs/authors/dates against independent search results — same fallback method used for the original Africa Check entries.
  - **ZimFact — dropped, not used.** Credible on paper (est. 2018, Voluntary Media Council of Zimbabwe), but its site (`zimfact.org`) is currently down (hosting-suspended page on every URL tried) — excluded entirely rather than cited with a broken/unverifiable link. One other candidate article (an AI-generated herbal-cure video claim) was also dropped for lack of a pinned, verifiable URL. This is the right call per the "never fabricate" rule — a source being reputable historically doesn't make it usable if it can't be verified right now.
- [x] **Found and fixed two real retrieval bugs surfaced by the larger, more diverse dataset** (see `app/retrieval.py`, `tests/test_retrieval.py` for the regression tests):
  1. Short common claim words (e.g. "it") were matching as a false substring inside unrelated tag words ("pol-IT-ics", "cIT-izenship") — a Ghana-curriculum claim was gating in and nearly losing to a completely unrelated Ghana-election article. Fixed with a minimum length guard (4 chars) before substring matching applies.
  2. Ranking previously used fuzzy score alone, which ties frequently (many pairs scored an identical 85.5) — ties were being broken by list order, not relevance. Fixed by ranking primarily on *how many* tags matched (more topical overlap wins) and using fuzzy score only as a tie-breaker within that.
  - Also widened `top_k` from 3 to 5 candidates handed to the LLM, since a generic claim can legitimately tie among several real, similarly-tagged articles — a wider pool reduces the chance the actually-correct one gets excluded by a tie it didn't need to lose.
  - Verified live end-to-end after the fix: both previously-broken claims now correctly ground in the right article with the exact right source_url.

### Live search + national news suggestions (added 2026-09-15)

**Decision:** user raised the deeper version of the coverage question — a static 64-article file, however curated, can never keep up with rumors happening this week; real fact-checking means going and checking right now, not just searching a fixed file. Agreed direction: search the fact-checker sites live, at request time, in addition to the static dataset — same grounding rule as always (only repeat what a real article actually says), just applied to freshly-fetched content instead of only pre-curated content. Also added: national newspaper links (not fact-check sources) as a "check here too" suggestion on Unverified replies, for 4 sample countries.

- [x] **Live search for Dubawa and GhanaFact** (`app/live_search.py`). Scope decided with the user after directly testing all 5 sources against a plain server-side request (not assumed): Africa Check, PesaCheck, and AFP Fact Check all block plain automated requests (Cloudflare/Akamai JS challenge) — PesaCheck's block was found only after initially (incorrectly) telling the user it would work, corrected once actually tested. Only Dubawa and GhanaFact's WordPress REST APIs (`/wp-json/wp/v2/posts?search=...`) respond to a plain request; those two stay static-dataset-only for now.
  - Claim text has to be reduced to ~3 keywords before searching — tested directly against Dubawa's live API: a 7-word claim sentence returned 0 results, 4 words returned fewer, 2-3 words reliably found the right article. WordPress's default search behaves like an AND across query words, so it wants a short keyword query, not a sentence — same as typing into a site's search box.
  - Live results have no pre-known verdict (unlike static dataset entries) — the LLM has to read the article's actual content and determine the verdict itself, only when the article clearly and explicitly reaches one; `app/llm.py`'s prompt was extended to handle both kinds of candidate (labeled "Published verdict" for static entries vs. "verdict not given -- read and determine" for live ones) in the same call.
  - Found and fixed a genuine encoding bug on GhanaFact's own server (not ours): some titles contain an unrecoverable invalid byte exactly where an apostrophe belongs (e.g. "Ghana�s new curriculum") — repaired with a safe, well-justified heuristic (replace with a proper apostrophe) rather than showing a broken character.
- [x] **National newspaper "check here too" links** (`app/national_news.py`), 4 sample countries: Nigeria (Premium Times), Kenya (Nation Africa), Ghana (Daily Graphic), Uganda (Daily Monitor). Important distinction kept: these are NOT fact-check sources and never produce a verdict (general newspapers report news, they don't publish verdicts) — they're only offered as a locally-relevant "where to look next" on an honest Unverified reply, same spirit as the existing "check africacheck.org/pesacheck.org/dubawa.org" fallback, just more specific when a country can be guessed from the claim text (cheap keyword match, not ML — low-stakes if it misses since it's a suggestion, not a verdict).
- [x] **Found and fixed a real latency bug while testing this.** `detect_language()` (an LLM call, needed since only English/Swahili can be auto-detected without one) was being awaited *before* sending the "instant" interim reply — measured directly at 1.4-7s with real variance, which defeated the entire point of an instant acknowledgment. Fixed by moving language detection into the background task entirely, alongside retrieval/live search/verdict synthesis; the interim reply is now one combined multi-language message sent with zero LLM calls on that path. Interim reply latency measured directly: ~5-7s before the fix, ~0.4s after.
- [x] Tests: `tests/test_live_search.py`, `tests/test_national_news.py`, `tests/test_models.py`, plus updates to `tests/test_llm.py` and `tests/test_whatsapp.py` for the new signatures (50 total passing).
- [x] **Live end-to-end verification of the actual point of this feature:** confirmed a claim about a real story (Ernest Bai Koroma / SLPP, Sierra Leone) that is genuinely *not* one of the 64 curated entries was found via live search on Dubawa and correctly grounded — right verdict (False), right explanation, right real source_url, something the static-only system could never have answered. Also confirmed the national-outlet suggestion appears correctly on a genuinely unverifiable claim naming Nigeria.
- [x] Reconnected the real WhatsApp Sandbox to this updated code (ngrok tunnel restarted — reused the same URL as before, `https://elvin-fasciculate-wiley.ngrok-free.dev`, Sandbox webhook setting unchanged) and confirmed the live TwiML response reflects the new instant multi-language interim text.

**Known limitation carried forward:** live search covers 2 of 5 sources; Africa Check, PesaCheck, and AFP Fact Check remain static-dataset-only until/unless a proper search API is set up for the sites that block direct automated access.

## Phase 2 — LLM verdict logic ✅ DONE (2026-09-14)

- [x] `app/llm.py` — OpenAI API wrapper (`gpt-4o-mini`, JSON-mode structured output). Chose `gpt-4o-mini` over `gpt-4o`: this is a grounded-summarization task (rephrase an already-published verdict from retrieved text), not one needing frontier reasoning. At $0.15/1M input + $0.60/1M output tokens, each verdict call costs a small fraction of a cent — dev testing plus a live demo stays well inside the $5 OpenAI free-trial credit.
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
- [x] Language detection (English/Swahili at the time) — reply generated in the detected language (LLM writes the explanation in-language; static Unverified/voice-note messages have pre-written copies). Superseded by the LLM-based 5-language detection below.
- [x] Voice-note-without-transcription handled gracefully (bilingual "not supported yet" message) rather than erroring
- [x] Tests: `tests/test_language.py`, `tests/test_whatsapp.py` (21 tests total now passing)
- [x] Live smoke tests (Twilio-shaped form POSTs): English matched claim, Swahili matched claim (correct verdict + Swahili explanation + real source), media-only message, empty message — all correct
- [x] Sandbox activated (accepted WhatsApp/Meta third-party terms, user confirmed), webhook URL saved in Twilio Console → Sandbox settings → "When a message comes in", method POST
- [x] User joined the Sandbox from their own WhatsApp
- [x] Real end-to-end test: message sent on WhatsApp → bot reply received on WhatsApp. Confirmed live: "coconut oil cures COVID-19" → correct FALSE verdict, correct explanation, correct real source_url, delivered back to the user's WhatsApp

## Phase 4 — Polish & multilingual/UX pass (started early, 2026-09-14)

- [x] **Interim "please wait" reply.** Retrieval + the LLM call take a few seconds with no sign of life on WhatsApp otherwise. `/whatsapp` now replies instantly with "⏳ Checking that for you..." (localized), then does the real work in a FastAPI `BackgroundTask` and sends the actual verdict as a follow-up message via Twilio's REST API (`app/whatsapp.py: send_whatsapp_message`, needs `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`/`TWILIO_WHATSAPP_NUMBER` in `.env`, already set). Verified live on the real Sandbox.
- [x] **Expanded from 2 to 5 languages: English, Swahili, Hausa, Yoruba, Igbo** (the three major Nigerian languages, per user request). Investigated two lightweight detectors first — `langdetect` (55 languages, no Hausa/Yoruba/Igbo profiles at all) and fastText's `lid.176` model (~900KB, no Hausa/Igbo labels either, and misclassified realistic un-toned Yoruba text) — neither covers these three reliably. Switched `app/language.py`'s `detect_language()` to an LLM call (gpt-4o-mini, five-way classification, defaults to English on any failure/low confidence) instead, which correctly identified all 5 languages in live testing and produces fluent in-language explanations, including on a real grounded verdict (Hausa "coconut oil cures COVID" claim → correct FALSE + real source, in Hausa). Costs one extra small LLM call per incoming message; accepted given the already-agreed budget approach.
- [ ] Onboarding message for first-time users
- [ ] Hackathon-POC disclaimer text in replies
- [ ] **Voice note transcription (stretch goal).** Currently, any message with media and no text gets a generic "can't check that yet" reply regardless of media type — this is the fix plus the real capability.
  - **Use case:** Voice notes are themselves a common vector for spreading rumors on WhatsApp ("I got a voice note saying..."). Forwarding the original audio to Habari preserves the exact claim instead of the user's own paraphrase introducing errors. Also lower-friction for users less comfortable typing (especially in a local-language script) — directly serves the brief's accessibility/low-literacy target users.
  - **Format:** WhatsApp voice notes arrive via Twilio as `audio/ogg` (Opus codec) at `MediaUrl0`.
  - **Plan:** read `MediaContentType0` from the Twilio webhook payload to detect audio; download the file from `MediaUrl0` (needs an authenticated request — Twilio media URLs require the Account SID/Auth Token, already in `.env`); send the audio to OpenAI's transcription API (Whisper or gpt-4o-mini's audio transcription); run the resulting text through the existing `detect_language` → `retrieve` → `synthesize_verdict` pipeline unchanged, same as a typed message.
- [ ] **Image/screenshot claim extraction (stretch goal, added 2026-09-14).** Not in the original brief's phase scope, added after discussion.
  - **Use case:** A large share of real misinformation spreads *as* an image — a doctored "breaking news" graphic, a screenshot of a fake headline or WhatsApp status, a photo of a flyer or newspaper clipping. People forward the image because that's what they actually received; retyping a long or stylized graphic by hand is friction most people won't bother with. Named directly in the original brief ("a rumor, claim, screenshot text, or voice note") but never scoped into a phase until now.
  - **Format:** WhatsApp images arrive via Twilio typically as `image/jpeg` (sometimes `image/png`) at `MediaUrl0`.
  - **Plan:** same media-type check as voice notes but for `image/*`; download via `MediaUrl0`; send the image directly to gpt-4o-mini (multimodal, no separate OCR library needed) asking it to extract the claim text; run the extracted text through the same existing pipeline. Needs its own accuracy check before relying on it (image → text extraction can misread text same as any OCR-like step).
- [ ] Stress-test against the locked demo scenarios (health rumor, election claim, scam)

**Caveat carried over from Phase 3:** all non-English static/label text (Swahili, and now Hausa/Yoruba/Igbo) is POC-quality, not reviewed by native speakers — worth a check before the real demo/submission.

## Phase 5 — Deliverables: repo, video, deck

- [x] **Judge onboarding: QR code + manual join, both shown.** Generated `docs/whatsapp-sandbox-qr.png` from the verified real join link (`wa.me/14155238886?text=join%20stage-begun` — same number/phrase confirmed live in Phase 3), decoded it back to confirm it's correct before adding to the repo. README's Sandbox section now shows both the QR scan and the manual `join stage-begun` text as a fallback.
- [ ] README finalized (architecture diagram, how to run, limitations, next steps)
- [ ] 2-3 minute demo video of real WhatsApp exchanges
- [ ] Pitch deck
- [ ] **Deployment decision:** current setup only works while the dev machine's local server + ngrok tunnel are running — not viable for judges to try unattended. User has both Namecheap and AWS space available for a real deployment; needs a decision on which to use and the actual deploy work, before or alongside the video/deck.

## Phase 6 — Written summary & submit

- [ ] Written summary (problem, users, how it works, how design addresses trust/verification, bandwidth, accessibility, privacy, multilingual access)
- [ ] Final end-to-end test
- [ ] Submit — buffer day before 2026-09-21 deadline, not on the day itself
