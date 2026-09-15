# Habari — Project Brief for Claude Code

> Claude Code reads this file automatically at the start of every session for context. Work through the "Build Plan" phases one session at a time — don't try to do everything at once.

---

## 1. Event Context

Built for the **OSF × Andela Hackathon** — an invention sprint to help people access civic information they can trust and act on. Submission deadline: **September 21, 2026**.

Track: **Stability & Social Cohesion** (reduces friction from rumor-driven mistrust and misinformation).

Required submission deliverables:
1. A working proof of concept
2. A GitHub repository
3. A short demo video
4. A pitch deck
5. A written summary

Design constraints called out by the hackathon brief that this project must visibly address: **trust and verification, low bandwidth, accessibility, privacy, multilingual access, local relevance, clear next steps for users.**

Note: this is an invention sprint, not a production launch — the POC needs to clearly demonstrate the problem, intended users, how the solution works, and why it's worth developing further. It does not need to be production-hardened.

---

## 2. The Concept

**Habari** ("habari" = "news" in Swahili) is a WhatsApp-based tool. A user forwards a rumor, claim, screenshot text, or voice note they've received, and the bot replies with:

- A verdict: **True / False / Misleading / Unverified**
- A short, plain-language explanation (2–3 sentences)
- A link to the trusted source it used
- If nothing matches: an honest "Unverified — here's what I'd check" instead of a guess

It is explicitly a **router and summarizer on top of existing trusted fact-checkers** (Africa Check, PesaCheck, Dubawa) — not a tool that invents its own verdicts from general AI knowledge. This is the core trust decision behind the whole design and should never be compromised for a "cooler demo."

## 3. Problem Statement

Verified information already exists from credible regional fact-checking organizations (Africa Check, PesaCheck in Kenya/Tanzania/Uganda, Dubawa in Nigeria), but it's scattered across websites people don't know to visit. Rumors and misinformation, meanwhile, spread fastest on WhatsApp — the platform people already use daily, even with low bandwidth and no data plan for browsing full websites.

## 4. Target Users

- People in rural or peri-urban African communities who receive a suspicious message, health rumor, election claim, or scam attempt via WhatsApp and have no fast way to check if it's true.
- Secondary users: community leaders or local journalists who want a quick first-pass check before escalating or debunking something publicly.

## 5. Design Principles (non-negotiable)

- **Never hallucinate a verdict.** Only answer with True/False/Misleading when a real matching source is found. Otherwise return "Unverified."
- **Low bandwidth first.** Text-based replies over WhatsApp, no heavy media required to use it.
- **Multilingual.** Support English and Swahili at minimum; detect the user's language and reply in kind.
- **Privacy by design.** Don't log phone numbers or full message content beyond what's needed for the active session. No persistent user profiles.
- **Always cite a source.** Every verdict includes a link back to the original fact-check article.
- **Clear next step.** If unverified, tell the user what to do next (e.g. "check with [X] or wait for more sources").

## 6. Architecture

```
User (WhatsApp)
   → Twilio WhatsApp Sandbox (webhook)
   → Backend (FastAPI, Python)
       Step 1: Classify incoming message (topic, language, urgency) — LLM call
       Step 2: Retrieval — match claim against curated dataset of real
                fact-check articles (Africa Check / PesaCheck / Dubawa)
       Step 3: LLM synthesizes verdict + explanation, grounded ONLY in
                the retrieved article(s). No match → "Unverified."
   → Reply sent back to user on WhatsApp
```

### Tech stack
- **Backend:** Python, FastAPI
- **Messaging:** Twilio WhatsApp Sandbox (no need for full WhatsApp Business API approval for a POC)
- **LLM:** ChatGPT API (OpenAI) for classification + grounded verdict generation
- **Retrieval:** Start simple — keyword/fuzzy match over a local JSON/CSV dataset of ~30–50 curated articles. Upgrade to embeddings/vector search only if time allows.
- **Voice notes (stretch goal):** Whisper API for transcription before running the same pipeline.
- **Secrets:** `.env` file (e.g. `OPENAI_API_KEY`), excluded via `.gitignore` from the very first commit.

### Data source
Manually curated dataset of real articles from credible, verified fact-checking organizations (ideally IFCN — International Fact-Checking Network — signatories). Started with:
- Africa Check (africacheck.org)
- PesaCheck (pesacheck.org) — East Africa, strong Kenya relevance
- Dubawa (dubawa.org)

**Source roster is expected to grow — this is the answer to "what if a rumor isn't covered by these three," not loosening the grounding rule.** The one invariant that never changes: Habari only ever cites real, published fact-checks from credible organizations, never general AI knowledge. Coverage gaps get fixed by adding more verified sources and more articles per source (see BUILD_PLAN.md for the current roster and what's been added since the initial three), not by letting the LLM guess. See `data/factchecks.json` for the live roster.

Each entry: `{ id, title, summary, verdict, source_url, topic_tags, country, source }`.

## 7. Build Plan (Sept 14 → Sept 21, compressed — Claude Code can move faster than one phase per day)

**Phase 1 — Scope, data & backend skeleton** *(target: Day 1–2)*
Lock 3–4 demo scenarios (a health rumor, an election claim, a scam). Manually collect 30–50 real fact-check articles into a JSON/CSV dataset. Stand up the FastAPI project with a `/webhook` route and the retrieval function that matches an incoming claim against the dataset. Aim to do this in one focused Claude Code session rather than spreading it out.

**Phase 2 — LLM verdict logic** *(target: Day 2–3)*
Prompt that takes the claim + retrieved article(s) and returns a structured verdict (True/False/Misleading/Unverified), plain-language explanation, and source link, using the ChatGPT API. Must default to "Unverified" when no good match is found — test this edge case hard before moving on.

**Phase 3 — WhatsApp integration** *(target: Day 3–4)*
Wire Twilio WhatsApp Sandbox to the webhook. Full round-trip: user sends a message, bot replies with a verdict. Add language detection (English/Swahili).

**Phase 4 — Polish & multilingual/UX pass** *(target: Day 4–5)*
Onboarding message, optional voice note transcription, optional image/screenshot claim extraction, disclaimer that this is a hackathon POC, stress-test against the demo scenarios. See `BUILD_PLAN.md` Phase 4 for the concrete technical plan for both media types.

**Phase 5 — Deliverables: repo, video, deck** *(target: Day 5–6)*
Clean README (problem, architecture diagram, how to run, limitations, next steps). Record a 2–3 minute demo video of real WhatsApp exchanges. Build the pitch deck.

**Phase 6 — Written summary & submit** *(target: Day 6, with Day 7 as buffer)*
Write the final summary covering problem, users, how it works, and how the design addresses trust/verification, low bandwidth, accessibility, privacy, and multilingual access. Final end-to-end test. Submit with a full day of buffer before the deadline — don't plan to finish on Sept 21 itself.

## 8. Working Agreement for Claude Code Sessions

- **Do not add any "Co-Authored-By: Claude" line, Claude attribution, or similar tag to git commits.** Commits should list only the human contributor(s). This applies to every commit for the whole project.
- Work in the phases above. Claude Code can often cover more than one phase per session — let it move at its natural pace rather than artificially spreading work across a full week, but still land and verify one phase before starting the next.
- Always keep API keys and secrets out of committed code.
- Prioritize a working end-to-end path (even a narrow one) over a polished partial feature — the demo needs a real round-trip.
- Write a short test or manual-check step after each phase before moving to the next.
- Update the README incrementally as features land, not all at once at the end.

## 9. Submission Reminders

- Project idea must be original (it is — this brief documents the reasoning). AI tools may assist development but shouldn't have generated the core idea.
- All work must be created for this hackathon and accessible to the judging team (public repo, working demo link/video).
- Deadline: **September 21, 2026**. Don't submit at the last hour — leave buffer for upload or connector issues.
