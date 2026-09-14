import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"

# langdetect (55-language classical detector) has no profile at all for
# Hausa, Yoruba, or Igbo, and a fastText lid.176 check on realistic
# (un-toned) Yoruba text still misclassified it -- neither lightweight
# statistical tool reliably covers these. An LLM call is far more accurate
# across all five and, at gpt-4o-mini's price, cheap enough to run on
# every incoming message.
SUPPORTED_LANGUAGES = ("en", "sw", "ha", "yo", "ig")

LANGUAGE_NAMES = {
    "en": "English",
    "sw": "Swahili",
    "ha": "Hausa",
    "yo": "Yoruba",
    "ig": "Igbo",
}

_CLASSIFY_SYSTEM_PROMPT = (
    "Identify which language the following WhatsApp message is written in. "
    "Respond with EXACTLY one of these codes and nothing else: en, sw, ha, yo, ig.\n"
    "en = English, sw = Swahili, ha = Hausa, yo = Yoruba, ig = Igbo.\n"
    "If you are not confident, or the message is in none of these languages, respond with en."
)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def detect_language(text: str) -> str:
    """LLM-based language identification across the five languages Habari
    supports. Defaults to English on empty text, an unrecognized response,
    or any API error -- never guesses at a language we can't actually
    reply in.
    """
    if not text or not text.strip():
        return "en"
    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            temperature=0,
            max_tokens=5,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        code = (response.choices[0].message.content or "").strip().lower()
    except Exception:
        logger.exception("Language detection call failed; defaulting to English")
        return "en"
    return code if code in SUPPORTED_LANGUAGES else "en"
