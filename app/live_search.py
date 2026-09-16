import html
import logging
import re

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# WordPress's default search behaves like an AND across query words --
# tested directly against Dubawa's live API: a 2-word query returned
# results, 3 was still fine, 4 words returned fewer, and the raw claim
# sentence (7+ words) returned zero. So the claim needs reducing to a
# short keyword query first, the way a person would actually type into a
# site's search box, not handed over as a full sentence.
MAX_SEARCH_KEYWORDS = 3

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "did", "do", "does", "for",
    "from", "had", "has", "have", "he", "her", "his", "how", "i", "if", "in", "is", "it", "its",
    "just", "me", "my", "new", "no", "not", "of", "on", "or", "our", "she", "so", "that", "the",
    "their", "them", "there", "these", "they", "this", "to", "was", "we", "were", "what", "when",
    "where", "which", "who", "will", "with", "you", "your",
}
_WORD_RE = re.compile(r"[a-z0-9']+")


def _extract_search_keywords(claim: str, max_keywords: int = MAX_SEARCH_KEYWORDS) -> str:
    """Reduce a claim sentence to a short keyword query. Keeps the
    longest/most distinctive words (short filler words survive the
    stopword filter too, e.g. "who", "did" as topic-bearing in some
    claims -- length is just a cheap proxy for "more likely a proper
    noun or specific term")."""
    words = []
    seen = set()
    for word in _WORD_RE.findall(claim.lower()):
        if word in _STOPWORDS or len(word) <= 2 or word in seen:
            continue
        seen.add(word)
        words.append(word)
    if len(words) > max_keywords:
        words = sorted(words, key=len, reverse=True)[:max_keywords]
    return " ".join(words)

# Only these two of Habari's five sources can be searched live, at request
# time, with a plain server-side HTTP call -- Africa Check, PesaCheck, and
# AFP Fact Check all sit behind bot-blocking (Cloudflare/Akamai) that
# returns a JS challenge page instead of content to any non-browser
# client. Confirmed directly (not assumed) against all three before
# settling on this scope. Those three remain covered only by the curated
# static dataset (see app/retrieval.py) until/unless a proper search API
# is added for them.
LIVE_SEARCH_SOURCES = {
    "Dubawa": "https://dubawa.org/wp-json/wp/v2/posts",
    "GhanaFact": "https://ghanafact.com/wp-json/wp/v2/posts",
}

LIVE_SEARCH_TIMEOUT_SECONDS = 6.0
MAX_RESULTS_PER_SOURCE = 3
_REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HabariBot/1.0)"}

_TAG_RE = re.compile(r"<[^>]+>")


class LiveSearchResult(BaseModel):
    source: str
    title: str
    content: str
    url: str


def _clean_html(raw: str) -> str:
    """Strip HTML tags and unescape entities from a WordPress API field."""
    text = _TAG_RE.sub(" ", raw or "")
    text = html.unescape(text)
    # Observed directly on live GhanaFact responses: some titles contain a
    # genuine U+FFFD (invalid byte on their end, not ours) exactly where an
    # apostrophe belongs, e.g. "Ghana�s new curriculum". The original
    # byte is unrecoverable, but a lost apostrophe is overwhelmingly the
    # likely cause, so repair it rather than show a broken character.
    text = text.replace("�", "'")
    return " ".join(text.split())


def _search_one_source(source_name: str, base_url: str, query: str) -> list[LiveSearchResult]:
    params = {
        "search": query,
        "per_page": MAX_RESULTS_PER_SOURCE,
        "_fields": "title,link,content,excerpt",
    }
    try:
        response = httpx.get(
            base_url, params=params, timeout=LIVE_SEARCH_TIMEOUT_SECONDS, headers=_REQUEST_HEADERS
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        logger.exception("Live search request failed for %s", source_name)
        return []

    results = []
    for item in data:
        title = _clean_html(item.get("title", {}).get("rendered", ""))
        content = _clean_html(item.get("content", {}).get("rendered", "")) or _clean_html(
            item.get("excerpt", {}).get("rendered", "")
        )
        link = item.get("link")
        if title and link and content:
            results.append(LiveSearchResult(source=source_name, title=title, content=content, url=link))
    return results


def live_search(claim: str) -> list[LiveSearchResult]:
    """Search Dubawa's and GhanaFact's own sites live, right now, for
    articles that might address this claim -- this is what covers a claim
    that isn't in the curated static dataset at all (e.g. something
    published last week). Unlike the static dataset, these results don't
    come with a pre-known verdict; the LLM has to actually read the
    content and determine whether/what the article concludes, same as a
    person would. Never raises -- any failure (network, bad response,
    one source down) degrades to returning fewer results, not an error.
    """
    if not claim or not claim.strip():
        return []
    query = _extract_search_keywords(claim)
    if not query:
        return []
    results: list[LiveSearchResult] = []
    for source_name, base_url in LIVE_SEARCH_SOURCES.items():
        results.extend(_search_one_source(source_name, base_url, query))
    return results
