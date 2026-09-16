import base64
import logging
import os

import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)

TRANSCRIBE_MODEL = "gpt-4o-mini-transcribe"
VISION_MODEL = "gpt-4o-mini"

DOWNLOAD_TIMEOUT_SECONDS = 15.0

_EXTENSION_BY_CONTENT_TYPE = {
    "audio/ogg": "ogg",
    "audio/amr": "amr",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/aac": "aac",
    "audio/wav": "wav",
}

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def download_twilio_media(media_url: str) -> bytes | None:
    """Twilio media URLs require HTTP Basic Auth with the Account
    SID/Auth Token -- fetching them without it returns a 401, not the
    file. Returns None on any failure (never raises) so a media-handling
    problem degrades to "couldn't process this," not a crash.
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not (account_sid and auth_token and media_url):
        logger.error("Missing Twilio credentials or media_url; cannot download media")
        return None
    try:
        response = httpx.get(media_url, auth=(account_sid, auth_token), timeout=DOWNLOAD_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.content
    except Exception:
        logger.exception("Failed to download Twilio media from %s", media_url)
        return None


def transcribe_audio(audio_bytes: bytes, content_type: str) -> str | None:
    """Transcribe a voice note to text via OpenAI's audio transcription
    API. The resulting text is just handed to the same
    detect_language -> retrieve -> synthesize_verdict pipeline as a typed
    message -- transcription only produces the claim text, it never
    itself produces a verdict. Returns None on any failure or empty
    result.
    """
    if not audio_bytes:
        return None
    ext = _EXTENSION_BY_CONTENT_TYPE.get(content_type.split(";")[0].strip(), "ogg")
    try:
        response = _get_client().audio.transcriptions.create(
            model=TRANSCRIBE_MODEL,
            file=(f"voice.{ext}", audio_bytes, content_type),
        )
        text = (getattr(response, "text", None) or "").strip()
        return text or None
    except Exception:
        logger.exception("Audio transcription failed")
        return None


_EXTRACT_CLAIM_SYSTEM_PROMPT = (
    "Extract the exact claim, rumor, or news text visible in this image (e.g. a WhatsApp "
    "screenshot, a flyer, a news graphic, a photo of text). Respond with ONLY the extracted "
    "text, copied as written, nothing else -- no commentary, no description of the image. "
    "If there is no readable claim or meaningful text in the image, respond with exactly: NONE"
)


def extract_claim_from_image(image_bytes: bytes, content_type: str) -> str | None:
    """Ask gpt-4o-mini (multimodal) to read the claim/text visible in an
    image. This step ONLY extracts text -- it never assesses truth. The
    extracted text is handed to the same pipeline as a typed message, so
    the actual verdict is still grounded only in real retrieved/live
    articles, same as always. Returns None if nothing readable was found
    or on any failure.
    """
    if not image_bytes:
        return None
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{content_type};base64,{b64}"
    try:
        response = _get_client().chat.completions.create(
            model=VISION_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": _EXTRACT_CLAIM_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {"url": data_url}}],
                },
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        if not text or text.upper() == "NONE":
            return None
        return text
    except Exception:
        logger.exception("Image claim extraction failed")
        return None
