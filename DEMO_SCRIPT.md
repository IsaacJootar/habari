# Demo Video Script

The hackathon brief just asks for "a short demo video" — no fixed length specified. This is the short cut: ~60-75 seconds, 4 shots, only what's needed to prove the core claim. Every message below has already been tested live and produces the result shown — nothing here is scripted fiction.

**Before recording:**
1. Make sure the local server and the ngrok tunnel are both running, and the Sandbox webhook is pointed at the current tunnel URL — check `curl <tunnel-url>/health`.
2. If it's been a while since you joined, confirm your number is still in the Sandbox (rejoin with `join stage-begun` to `+1 415 523 8886` if unsure — that exchange doesn't need to be in the video).
3. Have all 3 messages below ready to paste/send so there's no typing delay on camera.

---

## Short cut (~60-75s)

**1. Cold open (8-10s)**
Say or caption: *"Habari checks a rumor against real fact-checks on WhatsApp — and never invents an answer."*

**2. A real, cited verdict (20-25s)**
Send: `I heard coconut oil cures COVID-19`
Expected: instant "⏳ Checking that for you...", then:
> **FALSE**
> Coconut oil does not cure COVID-19...
> Source: pesacheck.org/...

Caption: *"A real verdict from a real fact-checker, with the source cited."*

**3. The differentiator — live search (20-25s)**
Send: `Is it true Ernest Bai Koroma said SLPP will win the 2028 election?`
Expected: FALSE, grounded in a real Dubawa article.

Caption: *"This claim was never in our dataset — Habari found it by searching live, right now."*

**4. Close (10s)**
Send: `I heard the moon turned green last night`
Expected: **UNVERIFIED** — no forced match.

Caption: *"And when nothing real matches, it says so. Habari — real fact-checks, no guessing."*

---

## Extended cut (~2.5 min), if you want more depth

Same 4 shots above, plus these inserted between steps 2 and 3:

**Multilingual (15-20s)**
Send: `Nimesikia mafuta ya nazi yanaponya covid-19`
Expected: same FALSE verdict, in Swahili, same real source.
Caption: *"Answered in the user's own language — Swahili, Hausa, Yoruba, and Igbo are all supported."*

**Voice note (20-25s)**
Record and send a voice note saying: *"I heard coconut oil cures COVID-19, is that true?"* (same claim as step 2, different format).
Expected: transcribed automatically, same correct verdict and source.
Caption: *"Voice notes are transcribed automatically, then checked the same way."*

**Screenshot/image (15-20s)**
Send a photo of a claim (a screenshotted headline, or a photo of printed/handwritten text).
Expected: the claim text is extracted and checked the same way.
Caption: *"Screenshots work too — the format most misinformation actually arrives in."*

---

## Notes

- The short cut alone already proves the three things that matter most: a real cited source (not the AI's opinion), live coverage beyond the curated dataset, and an honest refusal to guess. Everything in the extended cut is reinforcement, not new proof.
- If recording the extended cut, steps reusing the coconut oil claim (typed vs. voice) are deliberate — it shows the voice pipeline converges on the identical, already-verified answer.
- Keep the phone's notification banner / lock screen out of frame if it shows anything unrelated.
