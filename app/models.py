from typing import Literal

from pydantic import BaseModel

from app.national_news import suggest_national_outlet

Verdict = Literal["True", "False", "Misleading", "Unverified"]


class FactCheckEntry(BaseModel):
    id: str
    title: str
    summary: str
    verdict: Literal["True", "False", "Misleading"]
    source_url: str
    topic_tags: list[str]
    country: str
    source: str
    published_date: str | None = None  # YYYY-MM-DD, only where read from the page itself


class RetrievalMatch(BaseModel):
    entry: FactCheckEntry
    score: float


class WebhookReply(BaseModel):
    verdict: Verdict
    explanation: str
    source_url: str | None = None
    published_date: str | None = None


UNVERIFIED_REPLY_EN = WebhookReply(
    verdict="Unverified",
    explanation=(
        "We couldn't find a matching fact-check for this yet. "
        "Don't share it further until a trusted source confirms it — "
        "try checking africacheck.org, pesacheck.org, or dubawa.org directly."
    ),
    source_url=None,
)

# POC-quality Swahili translation, not reviewed by a native speaker yet --
# worth a proper check before the demo (see BUILD_PLAN.md Phase 3).
UNVERIFIED_REPLY_SW = WebhookReply(
    verdict="Unverified",
    explanation=(
        "Hatujapata ukaguzi wa ukweli unaolingana na hili bado. "
        "Usiendelee kusambaza ujumbe huu mpaka chanzo cha kuaminika kikithibitishe — "
        "jaribu kuangalia moja kwa moja africacheck.org, pesacheck.org, au dubawa.org."
    ),
    source_url=None,
)

# POC-quality translations, not reviewed by native speakers yet -- worth a
# proper check before the demo (see BUILD_PLAN.md Phase 4).
UNVERIFIED_REPLY_HA = WebhookReply(
    verdict="Unverified",
    explanation=(
        "Ba mu sami wani bincike da ya dace da wannan ba tukuna. "
        "Kada ka ci gaba da yada wannan sakon har sai wata majiya amintacciya ta tabbatar da shi — "
        "duba africacheck.org, pesacheck.org, ko dubawa.org kai tsaye."
    ),
    source_url=None,
)

UNVERIFIED_REPLY_YO = WebhookReply(
    verdict="Unverified",
    explanation=(
        "A ò rí ìròyìn tí ó bá èyí mu síbẹ̀. "
        "Má ṣe pín ìhìn yìí síwájú sí i kí a tó jẹ́rìí i rẹ̀ láti ọ̀dọ̀ orísun tí a gbẹ́kẹ̀lé — "
        "ṣàyẹ̀wò africacheck.org, pesacheck.org, tàbí dubawa.org tààrà."
    ),
    source_url=None,
)

UNVERIFIED_REPLY_IG = WebhookReply(
    verdict="Unverified",
    explanation=(
        "Anyị achọtabeghị nyocha kwesịrị ekwesị maka nke a. "
        "Ekesala ozi a ọzọ ruo mgbe isi iyi a na-atụkwasị obi kwadoro ya — "
        "lelee africacheck.org, pesacheck.org, ma ọ bụ dubawa.org."
    ),
    source_url=None,
)

# Kept for backwards compatibility with existing callers/tests that assume English.
UNVERIFIED_REPLY = UNVERIFIED_REPLY_EN

_UNVERIFIED_BY_LANGUAGE = {
    "en": UNVERIFIED_REPLY_EN,
    "sw": UNVERIFIED_REPLY_SW,
    "ha": UNVERIFIED_REPLY_HA,
    "yo": UNVERIFIED_REPLY_YO,
    "ig": UNVERIFIED_REPLY_IG,
}

# POC-quality translations, not reviewed by native speakers.
_ALSO_CHECK_PHRASES = {
    "en": "You could also check",
    "sw": "Unaweza pia kuangalia",
    "ha": "Hakanan za ka iya duba",
    "yo": "O tún lè ṣàyẹ̀wò",
    "ig": "Ị nwekwara ike ịlele",
}


def with_national_suggestion(explanation: str, language: str, claim: str) -> str:
    """Appends a "you could also check <national newspaper>" suggestion to
    an Unverified explanation, if the claim text names one of a few sample
    countries. Not a fact-check source (general newspapers report news,
    they don't publish verdicts) -- just a more locally useful "where to
    look next" than only naming the fact-checker sites generically. Used
    on both the static fallback text and the LLM's own Unverified
    explanation, so the suggestion shows up regardless of which one is in
    play.
    """
    suggestion = suggest_national_outlet(claim) if claim else None
    if not suggestion:
        return explanation
    name, url = suggestion
    lead_in = _ALSO_CHECK_PHRASES.get(language, _ALSO_CHECK_PHRASES["en"])
    return f"{explanation} {lead_in} {name}: {url}"


def unverified_reply(language: str = "en", claim: str = "") -> WebhookReply:
    """The honest "we don't have a verified answer" fallback."""
    base = _UNVERIFIED_BY_LANGUAGE.get(language, UNVERIFIED_REPLY_EN)
    explanation = with_national_suggestion(base.explanation, language, claim)
    if explanation == base.explanation:
        return base
    return WebhookReply(verdict="Unverified", explanation=explanation, source_url=None)
