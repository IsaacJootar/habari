import json
import logging

from openai import OpenAI

from app.language import LANGUAGE_NAMES
from app.live_search import LiveSearchResult
from app.models import RetrievalMatch, WebhookReply, unverified_reply, with_national_suggestion

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are Habari, a WhatsApp fact-checking assistant for African audiences.

You will be given a user's claim and one or more candidate articles found by a retrieval \
system. Your ONLY job is to decide which article, if any, actually addresses the user's \
specific claim, and report what that article says. You must NEVER use outside knowledge, \
and you must NEVER invent, guess, or infer a verdict that isn't actually supported by the \
text of one of the given articles.

Two kinds of candidate articles may appear, marked accordingly:
- Articles with a "Published verdict" field are from a curated dataset of already-verified \
fact-checks -- if one of these addresses the claim, use its stated verdict exactly, don't \
change or soften it.
- Articles marked "(verdict not given -- read the content and determine it yourself)" are \
from a live, just-now web search and have no pre-assigned verdict. For these, read the \
"Content" field and decide the verdict ONLY if that article's own text clearly and \
explicitly reaches a conclusion about this specific claim (e.g. it says something is false, \
confirmed, misleading, a hoax, etc.). If the article doesn't clearly address this specific \
claim or doesn't reach a clear conclusion, do not use it -- treat it as if it weren't there.

Respond with a single JSON object, no other text, with exactly these fields:
{
  "verdict": one of "True", "False", "Misleading", or "Unverified",
  "explanation": a 2-3 sentence, plain-language explanation a non-expert can understand,
  "source_url": the exact source_url (or url) of the article you used, copied character-for-character, or null
}

Rules:
- source_url must be copied EXACTLY from the article you used. Never write a URL that \
wasn't given to you.
- If none of the candidate articles actually address this specific claim (they might just \
share a topic or keyword), respond with verdict "Unverified", source_url null, and an \
explanation that briefly says why and what the user should do next (e.g. check with a \
trusted fact-checker before sharing).
- Keep the explanation short, plain, and non-technical — it will be sent as a WhatsApp message.
- Write the "explanation" field in {language_name}, regardless of what language the \
candidate articles are written in.
"""


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _build_user_prompt(
    claim: str, matches: list[RetrievalMatch], live_results: list[LiveSearchResult]
) -> str:
    articles = []
    i = 0
    for match in matches:
        i += 1
        entry = match.entry
        articles.append(
            f"Article {i} (source: {entry.source}, country: {entry.country})\n"
            f"Title: {entry.title}\n"
            f"Published verdict: {entry.verdict}\n"
            f"Summary: {entry.summary}\n"
            f"source_url: {entry.source_url}"
        )
    for result in live_results:
        i += 1
        articles.append(
            f"Article {i} (source: {result.source}, verdict not given -- read the content and determine it yourself)\n"
            f"Title: {result.title}\n"
            f"Content: {result.content}\n"
            f"source_url: {result.url}"
        )
    articles_block = "\n\n".join(articles)
    return (
        f'User\'s claim: "{claim}"\n\n'
        f"Candidate articles:\n\n{articles_block}\n\n"
        "Respond with the JSON object described in your instructions."
    )


def synthesize_verdict(
    claim: str,
    matches: list[RetrievalMatch],
    live_results: list[LiveSearchResult] | None = None,
    language: str = "en",
) -> WebhookReply:
    """Ask the LLM to pick the best-matching candidate article (if any) and
    phrase a grounded verdict from it, in the given language.

    `matches` come from the curated static dataset (each has an
    already-known verdict); `live_results` come from a live, request-time
    search of the sites that allow it (no pre-known verdict -- the model
    has to read the content itself). The model can only choose among these
    or say none of them actually address the claim (Unverified) — it is
    never asked to answer from outside knowledge. Any failure (API error,
    malformed response, a verdict/url that doesn't trace back to a given
    article) falls back to "Unverified" rather than risk showing a wrong
    or guessed verdict.
    """
    live_results = live_results or []
    if not matches and not live_results:
        return unverified_reply(language, claim)

    language_name = LANGUAGE_NAMES.get(language, "English")
    # .replace, not .format -- the prompt's JSON example has literal braces.
    system_prompt = SYSTEM_PROMPT.replace("{language_name}", language_name)

    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _build_user_prompt(claim, matches, live_results)},
            ],
        )
        raw = response.choices[0].message.content or ""
    except Exception:
        logger.exception("LLM call failed; falling back to Unverified")
        return unverified_reply(language, claim)

    return _parse_reply(raw, matches, live_results, language, claim)


def _parse_reply(
    raw: str,
    matches: list[RetrievalMatch],
    live_results: list[LiveSearchResult],
    language: str = "en",
    claim: str = "",
) -> WebhookReply:
    valid_urls = {match.entry.source_url for match in matches} | {result.url for result in live_results}
    try:
        data = json.loads(raw)
        verdict = data["verdict"]
        explanation = (data.get("explanation") or "").strip()

        if verdict == "Unverified":
            explanation = explanation or unverified_reply(language, claim).explanation
            return WebhookReply(
                verdict="Unverified",
                explanation=with_national_suggestion(explanation, language, claim),
                source_url=None,
            )

        if verdict not in ("True", "False", "Misleading"):
            raise ValueError(f"unexpected verdict {verdict!r}")

        source_url = data.get("source_url")
        if source_url not in valid_urls:
            # The model must cite one of the articles we actually gave it --
            # anything else means it drifted from grounding, so don't trust it.
            raise ValueError(f"source_url {source_url!r} not among candidate articles")
        if not explanation:
            raise ValueError("empty explanation")

        # The date comes from the cited article's own metadata, never from the model.
        published = {match.entry.source_url: match.entry.published_date for match in matches}
        published.update({result.url: result.published_date for result in live_results})
        return WebhookReply(
            verdict=verdict,
            explanation=explanation,
            source_url=source_url,
            published_date=published.get(source_url),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        logger.exception("Could not trust LLM reply, falling back to Unverified. Raw: %s", raw)
        return unverified_reply(language, claim)
