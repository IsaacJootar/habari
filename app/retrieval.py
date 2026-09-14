import json
import re
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz

from app.models import FactCheckEntry, RetrievalMatch

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "factchecks.json"

# Once a claim shares at least one topic tag with an entry, this is the
# minimum ranking score (title+summary vs. claim) needed to trust the match
# enough to hand it to the LLM as grounding. A pure fuzzy score with no
# keyword gate turned out to false-positive badly on longer, unrelated
# claims (a "how do I reverse an M-Pesa transaction" claim matched a
# COVID-cure article at 85+) — so relevance is decided by shared topic
# tags first, and fuzzy score is only used to rank/filter within that
# topically-relevant set.
MIN_CONFIDENT_SCORE = 40.0

# How close a claim word needs to be to a tag word to count as "mentioning"
# that tag (handles simple plurals/typos, e.g. "vaccines" ~ "vaccine").
TAG_WORD_MATCH_THRESHOLD = 85.0

_WORD_RE = re.compile(r"[a-z0-9']+")


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


@lru_cache(maxsize=1)
def load_dataset() -> list[FactCheckEntry]:
    if not DATA_PATH.exists():
        return []
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [FactCheckEntry(**item) for item in raw]


def _searchable_text(entry: FactCheckEntry) -> str:
    return " ".join([entry.title, entry.summary, " ".join(entry.topic_tags)])


def _tag_mentioned(tag: str, claim_words: list[str]) -> bool:
    """True if every word of a (possibly multi-word) topic tag is present,
    loosely, among the claim's words — e.g. tag "mobile money" needs both
    "mobile" and "money" to show up (typo/plural-tolerant) in the claim."""
    tag_words = _words(tag)
    if not tag_words:
        return False
    return all(
        any(fuzz.ratio(tag_word, claim_word) >= TAG_WORD_MATCH_THRESHOLD for claim_word in claim_words)
        for tag_word in tag_words
    )


def retrieve(claim: str, top_k: int = 3, min_score: float = MIN_CONFIDENT_SCORE) -> list[RetrievalMatch]:
    """Match an incoming claim against the curated fact-check dataset.

    An entry is only considered if the claim mentions at least one of its
    topic tags (the relevance gate); matches are then ranked by fuzzy
    text similarity. Returns the top matches at or above `min_score`, best
    first. An empty result means no article was a confident enough match —
    callers must treat that as "Unverified", never guess.
    """
    entries = load_dataset()
    claim_words = _words(claim)
    if not claim_words or not entries:
        return []

    candidates = [entry for entry in entries if any(_tag_mentioned(tag, claim_words) for tag in entry.topic_tags)]
    if not candidates:
        return []

    scored = [
        RetrievalMatch(entry=entry, score=fuzz.WRatio(claim, _searchable_text(entry)))
        for entry in candidates
    ]
    scored.sort(key=lambda m: m.score, reverse=True)
    confident = [m for m in scored if m.score >= min_score]
    return confident[:top_k]
