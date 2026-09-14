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

# Kept for backwards compatibility with existing callers/tests that assume English.
UNVERIFIED_REPLY = UNVERIFIED_REPLY_EN


def unverified_reply(language: str = "en") -> WebhookReply:
    return UNVERIFIED_REPLY_SW if language == "sw" else UNVERIFIED_REPLY_EN
