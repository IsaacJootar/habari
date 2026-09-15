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

# Minimum length (both words) before a substring match counts -- without
# this, a short common word like "it" matches as a substring of totally
# unrelated tag words ("pol-IT-ics", "cIT-izenship"), which false-gated
# claims into completely wrong articles.
MIN_SUBSTRING_MATCH_LENGTH = 4

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


def _words_match(tag_word: str, claim_word: str) -> bool:
    """A tag word "matches" a claim word if one contains the other (handles
    word-form variants a fixed fuzzy-ratio threshold misses, e.g. "scam" in
    "scammed" -- ratio-based matching alone scored that pair at ~73, below
    the typo-tolerance threshold) or if they're a close fuzzy match (handles
    genuine typos/plurals that aren't simple substrings, e.g. "vaccines" ~
    "vaccine")."""
    if (
        len(tag_word) >= MIN_SUBSTRING_MATCH_LENGTH
        and len(claim_word) >= MIN_SUBSTRING_MATCH_LENGTH
        and (tag_word in claim_word or claim_word in tag_word)
    ):
        return True
    return fuzz.ratio(tag_word, claim_word) >= TAG_WORD_MATCH_THRESHOLD


def _tag_mentioned(tag: str, claim_words: list[str]) -> bool:
    """True if every word of a (possibly multi-word) topic tag is present,
    loosely, among the claim's words — e.g. tag "mobile money" needs both
    "mobile" and "money" to show up (typo/plural-tolerant) in the claim."""
    tag_words = _words(tag)
    if not tag_words:
        return False
    return all(
        any(_words_match(tag_word, claim_word) for claim_word in claim_words) for tag_word in tag_words
    )


def _matching_tag_count(entry: FactCheckEntry, claim_words: list[str]) -> int:
    return sum(1 for tag in entry.topic_tags if _tag_mentioned(tag, claim_words))


def retrieve(claim: str, top_k: int = 5, min_score: float = MIN_CONFIDENT_SCORE) -> list[RetrievalMatch]:
    """Match an incoming claim against the curated fact-check dataset.

    An entry is only considered if the claim mentions at least one of its
    topic tags (the relevance gate). Candidates are then ranked primarily
    by how many tags matched (more topical overlap = more likely the real
    subject of the claim, not just an incidental shared word) and secondly
    by fuzzy text similarity as a tie-breaker -- fuzzy score alone ties
    frequently (e.g. two very different articles that both merely mention
    "Ghana" both scored 85.5), which let list order pick the winner instead
    of actual relevance. Returns the top matches at or above `min_score`,
    best first. An empty result means no article was a confident enough
    match — callers must treat that as "Unverified", never guess.

    top_k=5 (not 1) because a generic claim can legitimately tie among
    several real, similarly-tagged articles (e.g. several distinct "job
    scam in Kenya" write-ups) -- handing the LLM a wider candidate set
    reduces the chance the actually-matching one gets excluded by a tie
    it didn't need to lose.
    """
    entries = load_dataset()
    claim_words = _words(claim)
    if not claim_words or not entries:
        return []

    candidates = [
        (entry, _matching_tag_count(entry, claim_words))
        for entry in entries
    ]
    candidates = [(entry, count) for entry, count in candidates if count > 0]
    if not candidates:
        return []

    scored = [
        RetrievalMatch(entry=entry, score=fuzz.WRatio(claim, _searchable_text(entry)))
        for entry, _count in candidates
    ]
    tag_counts = {id(entry): count for entry, count in candidates}
    scored.sort(key=lambda m: (tag_counts[id(m.entry)], m.score), reverse=True)
    confident = [m for m in scored if m.score >= min_score]
    return confident[:top_k]
