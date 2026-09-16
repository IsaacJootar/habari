from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Form, Response
from pydantic import BaseModel

from app.language import detect_language
from app.live_search import live_search
from app.llm import synthesize_verdict
from app.media import download_twilio_media, extract_claim_from_image, transcribe_audio
from app.models import WebhookReply, unverified_reply
from app.retrieval import retrieve
from app.session import is_first_time
from app.whatsapp import (
    AUDIO_UNREADABLE_TEXT,
    IMAGE_UNREADABLE_TEXT,
    INTERIM_TEXT,
    MEDIA_DOWNLOAD_FAILED_TEXT,
    UNSUPPORTED_MEDIA_TEXT,
    WELCOME_TEXT,
    build_twiml,
    render_whatsapp_text,
    send_whatsapp_message,
)

load_dotenv()

app = FastAPI(title="Habari")


class IncomingMessage(BaseModel):
    message: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook", response_model=WebhookReply)
def webhook(payload: IncomingMessage) -> WebhookReply:
    """Plain-JSON dev/manual-test endpoint (not what Twilio calls -- see
    /whatsapp for that). Kept around because it's convenient for exercising
    retrieval + LLM synthesis without needing a Twilio-shaped request."""
    language = detect_language(payload.message)
    matches = retrieve(payload.message)
    live_results = live_search(payload.message)
    return synthesize_verdict(payload.message, matches, live_results, language=language)


def _resolve_and_send(claim: str, to: str) -> None:
    """Runs after the webhook has already replied with the interim message
    -- does the slow language detection + retrieval + live search + LLM
    work, then delivers the real verdict as a separate WhatsApp message
    via Twilio's REST API. Language detection lives here (not before the
    interim reply) because it's itself an LLM call -- see INTERIM_TEXT's
    comment in app.whatsapp for why."""
    language = detect_language(claim)
    matches = retrieve(claim)
    live_results = live_search(claim)
    reply = synthesize_verdict(claim, matches, live_results, language=language)
    text = render_whatsapp_text(reply, language)
    send_whatsapp_message(to=to, body=text)


def _resolve_media_and_send(media_url: str, content_type: str, to: str, kind: str) -> None:
    """Background counterpart of _resolve_and_send for a voice note or
    image: download the file from Twilio, turn it into claim text (via
    transcription or image text extraction), then run that text through
    the exact same pipeline as a typed message. Only the "get some text
    out of the media" step is new -- verdict grounding is unchanged, and
    just as strict (the transcription/extraction step never itself
    produces a verdict, only claim text)."""
    media_bytes = download_twilio_media(media_url)
    if not media_bytes:
        send_whatsapp_message(to=to, body=MEDIA_DOWNLOAD_FAILED_TEXT)
        return

    if kind == "audio":
        claim = transcribe_audio(media_bytes, content_type)
        failure_text = AUDIO_UNREADABLE_TEXT
    else:
        claim = extract_claim_from_image(media_bytes, content_type)
        failure_text = IMAGE_UNREADABLE_TEXT

    if not claim:
        send_whatsapp_message(to=to, body=failure_text)
        return

    _resolve_and_send(claim, to)


@app.post("/whatsapp")
async def whatsapp_webhook(
    background_tasks: BackgroundTasks,
    Body: str = Form(default=""),
    From: str = Form(default=""),
    NumMedia: str = Form(default="0"),
    MediaContentType0: str = Form(default=""),
    MediaUrl0: str = Form(default=""),
) -> Response:
    """Twilio's actual WhatsApp Sandbox webhook target: form-encoded
    request in, TwiML (XML) reply out.

    A matched claim needs language detection + retrieval + live search +
    an LLM round trip, which takes a few seconds with no other sign of
    life on WhatsApp meanwhile -- so this replies immediately (no LLM
    calls on this path at all) with a short "Checking that for you..."
    message and does all of that in the background, sending the actual
    verdict as a follow-up message once it's ready. A voice note or image
    goes through the same instant-ack-then-background pattern, with an
    extra step first (transcription / image text extraction) to turn it
    into claim text.

    Language (English/Swahili/Hausa/Yoruba/Igbo) is detected automatically
    per message via the LLM -- see app.language.detect_language -- but
    only in the background task, since detection itself is an LLM call
    and would otherwise delay this "instant" reply.
    """
    claim = Body.strip()
    ack_text = WELCOME_TEXT if is_first_time(From) else INTERIM_TEXT

    if not claim:
        has_media = NumMedia.strip() not in ("", "0")
        if not has_media:
            text = render_whatsapp_text(unverified_reply("en"))
            return Response(content=build_twiml(text), media_type="application/xml")

        media_type = MediaContentType0.split(";")[0].strip().lower()
        if media_type.startswith("audio/"):
            background_tasks.add_task(_resolve_media_and_send, MediaUrl0, media_type, From, "audio")
            return Response(content=build_twiml(ack_text), media_type="application/xml")
        if media_type.startswith("image/"):
            background_tasks.add_task(_resolve_media_and_send, MediaUrl0, media_type, From, "image")
            return Response(content=build_twiml(ack_text), media_type="application/xml")

        return Response(content=build_twiml(UNSUPPORTED_MEDIA_TEXT), media_type="application/xml")

    background_tasks.add_task(_resolve_and_send, claim, From)
    return Response(content=build_twiml(ack_text), media_type="application/xml")
