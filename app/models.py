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


UNVERIFIED_REPLY = WebhookReply(
    verdict="Unverified",
    explanation=(
        "We couldn't find a matching fact-check for this yet. "
        "Don't share it further until a trusted source confirms it — "
        "try checking africacheck.org, pesacheck.org, or dubawa.org directly."
    ),
    source_url=None,
)
