# Habari — Written Summary

**OSF × Andela Hackathon — Stability & Social Cohesion track**

---

## The problem

WhatsApp is where most conversation in Africa actually happens. It's not just a messaging app — for a huge share of the continent, it *is* the primary channel for staying in touch, sharing news, and passing along anything that feels urgent or important. That same quality is exactly what makes it so prone to spreading rumors, unverified claims, and outright fake news: WhatsApp makes sharing effortless. A voice note, a screenshot, a forwarded message — one tap, and it's in a dozen family groups and community chats within minutes. The same ease that makes WhatsApp so useful for real communication is what makes misinformation move through it so fast.

Verified information already exists — credible fact-checking organizations publish real, well-researched fact-checks every week. But they live on websites most people don't know exist, and even when they do, people don't leave a WhatsApp conversation mid-scroll to go verify something on a separate site and then come back. That's not how anyone actually behaves in the moment a suspicious message lands in their chat.

So the gap isn't a shortage of fact-checking — it's that real fact-checking and the moment of doubt happen in two different places. The fix is to bring verification into the same channel the rumor is already moving through, with the same ease of forwarding that spreads misinformation now working in favor of the truth instead. That's the premise behind Habari.

## Who it's for

People in rural or peri-urban African communities who receive a suspicious message on WhatsApp and have no fast way to check it. Secondarily, community leaders and local journalists who want a quick first-pass check before escalating or debunking something publicly.

## How Habari works

A user forwards whatever they received — text, a voice note, or a screenshot — to the Habari number, exactly as they'd forward it to a friend. No app to install, no account to create.

Behind an instant "checking that for you" reply, Habari matches the claim against a curated dataset of real, verified fact-checks, searches select fact-checking sites live for anything more recent, and has an AI read only what was actually found to write a plain-language verdict — **True, False, Misleading, or an honest Unverified.** Every verdict links back to the real source article it came from. Nothing is ever answered from the AI's own general knowledge.

That's the one rule that never bends: Habari is a **router and summarizer on top of real fact-checkers, not a source of its own opinions.**

This matters well beyond any single rumor. Much of what circulates is about public life — election results, outbreak notices supposedly from health ministries, forged government announcements and documents, scams impersonating public and telecom services. Left unchecked, these erode trust in institutions and push people to act on things that aren't true. By putting the real, sourced answer in front of people before they act or share, Habari helps them engage with public services and civic life based on what is actually true.

## How the design addresses the core constraints

- **Trust and verification** — every verdict traces to one real, named source, shown with its publication date so people can judge how current it is; no real match means an honest "Unverified," never a guess.
- **Low bandwidth** — the exchange is plain text over WhatsApp; no heavy media required to use it, even though it can accept one if that's what the user has.
- **Accessibility** — accepts a voice note or a photo of a screenshot, not just typed text, and replies in short, plain language, inside an app people already know.
- **Privacy by design** — Habari itself stores no user profiles and no message history; the only thing it holds is a temporary in-memory flag for the current session, gone on restart.
- **Multilingual access** — detects and replies in the sender's own language (English, Swahili, Hausa, Yoruba, Igbo).
- **Local relevance** — sourced from credible African fact-checking organizations, with country-specific news suggestions when nothing else applies. Sources, articles, and country suggestions are simple data rather than hard-coded logic, so adapting Habari to another country or community means adding entries, not rebuilding it.
- **Clear next steps** — an "Unverified" reply always pairs the honest answer with something concrete to check next, never a dead end.

## Tested end-to-end

Habari works today, live, on a real WhatsApp number — real messages, real voice notes, and real verdicts tracing back to real fact-check articles, verified directly on a phone rather than only in a test suite.

## Limitations

As a hackathon build, a few things are still ahead:

- No always-on hosted deployment yet — it runs from a local server during development/demo.
- Live search covers only some fact-checking sites; others block automated requests and rely on the curated dataset for now.
- Non-English replies haven't had a native-speaker review pass yet.
- Country-specific news suggestions cover a handful of countries, not all.

## Why this is worth developing further

Habari proves the core idea works: real fact-checks can meet people exactly where rumors already spread, in their own language, without asking them to change their behavior at all. From here, the path forward is concrete — a real hosted deployment, live search extended to more fact-checkers, a wider dataset and country list, more languages (French, Portuguese, and Arabic, alongside further African languages), and a native-speaker review pass. None of it changes the core design; it's the same trustworthy, low-bandwidth, privacy-respecting router, just reaching further.
