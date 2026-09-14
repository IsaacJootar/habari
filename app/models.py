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
