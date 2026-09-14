from typing import Literal

from pydantic import BaseModel

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


class RetrievalMatch(BaseModel):
    entry: FactCheckEntry
    score: float


class WebhookReply(BaseModel):
    verdict: Verdict
    explanation: str
    source_url: str | None = None


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


def unverified_reply(language: str = "en") -> WebhookReply:
    return _UNVERIFIED_BY_LANGUAGE.get(language, UNVERIFIED_REPLY_EN)
