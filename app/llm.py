import json
import logging

from openai import OpenAI

from app.language import LANGUAGE_NAMES
from app.models import RetrievalMatch, WebhookReply, unverified_reply

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are Habari, a WhatsApp fact-checking assistant for African audiences.

You will be given a user's claim and one or more candidate fact-check articles that a \
retrieval system found. Your ONLY job is to decide which article, if any, actually \
addresses the user's specific claim, and phrase that article's already-published \
verdict in plain language. You must NEVER use outside knowledge, and you must NEVER \
invent, guess, or infer a verdict that isn't already stated in one of the given articles.

Respond with a single JSON object, no other text, with exactly these fields:
{
  "verdict": one of "True", "False", "Misleading", or "Unverified",
  "explanation": a 2-3 sentence, plain-language explanation a non-expert can understand,
  "source_url": the exact source_url of the article you used, copied character-for-character, or null
}

Rules:
- If one of the candidate articles clearly addresses the same claim the user is asking \
about, use that article's own published verdict (True/False/Misleading) as your verdict. \
Do not change or soften it.
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


def _build_user_prompt(claim: str, matches: list[RetrievalMatch]) -> str:
    articles = []
    for i, match in enumerate(matches, start=1):
        entry = match.entry
        articles.append(
            f"Article {i} (source: {entry.source}, country: {entry.country})\n"
            f"Title: {entry.title}\n"
            f"Published verdict: {entry.verdict}\n"
            f"Summary: {entry.summary}\n"
            f"source_url: {entry.source_url}"
        )
    articles_block = "\n\n".join(articles)
    return (
        f'User\'s claim: "{claim}"\n\n'
        f"Candidate fact-check articles:\n\n{articles_block}\n\n"
        "Respond with the JSON object described in your instructions."
    )


def synthesize_verdict(claim: str, matches: list[RetrievalMatch], language: str = "en") -> WebhookReply:
    """Ask the LLM to pick the best-matching retrieved article (if any) and
    phrase a grounded verdict from it, in the given language ("en"/"sw").

    The model can only choose among the retrieved articles or say none of
    them actually address the claim (Unverified) — it is never asked to
    answer from outside knowledge. Any failure (API error, malformed
    response, a verdict/url that doesn't trace back to a given article)
    falls back to "Unverified" rather than risk showing a wrong or guessed
    verdict.
    """
    if not matches:
        return unverified_reply(language)

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
                {"role": "user", "content": _build_user_prompt(claim, matches)},
            ],
        )
        raw = response.choices[0].message.content or ""
    except Exception:
        logger.exception("LLM call failed; falling back to Unverified")
        return unverified_reply(language)

    return _parse_reply(raw, matches, language)


def _parse_reply(raw: str, matches: list[RetrievalMatch], language: str = "en") -> WebhookReply:
    valid_urls = {match.entry.source_url for match in matches}
    try:
        data = json.loads(raw)
        verdict = data["verdict"]
        explanation = (data.get("explanation") or "").strip()

        if verdict == "Unverified":
            return WebhookReply(
                verdict="Unverified",
                explanation=explanation or unverified_reply(language).explanation,
                source_url=None,
            )

        if verdict not in ("True", "False", "Misleading"):
            raise ValueError(f"unexpected verdict {verdict!r}")

        source_url = data.get("source_url")
        if source_url not in valid_urls:
            # The model must cite one of the articles we actually gave it --
            # anything else means it drifted from grounding, so don't trust it.
            raise ValueError(f"source_url {source_url!r} not among retrieved articles")
        if not explanation:
            raise ValueError("empty explanation")

        return WebhookReply(verdict=verdict, explanation=explanation, source_url=source_url)
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        logger.exception("Could not trust LLM reply, falling back to Unverified. Raw: %s", raw)
        return unverified_reply(language)
