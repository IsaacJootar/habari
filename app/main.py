from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Form, Response
from pydantic import BaseModel

from app.language import detect_language
from app.live_search import live_search
from app.llm import synthesize_verdict
from app.models import WebhookReply, unverified_reply
from app.retrieval import retrieve
from app.session import is_first_time
from app.whatsapp import (
    INTERIM_TEXT,
    VOICE_NOTE_UNSUPPORTED_TEXT,
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


@app.post("/whatsapp")
async def whatsapp_webhook(
    background_tasks: BackgroundTasks,
    Body: str = Form(default=""),
    From: str = Form(default=""),
    NumMedia: str = Form(default="0"),
) -> Response:
    """Twilio's actual WhatsApp Sandbox webhook target: form-encoded
    request in, TwiML (XML) reply out.

    A matched claim needs language detection + retrieval + live search +
    an LLM round trip, which takes a few seconds with no other sign of
    life on WhatsApp meanwhile -- so this replies immediately (no LLM
    calls on this path at all) with a short "Checking that for you..."
    message and does all of that in the background, sending the actual
    verdict as a follow-up message once it's ready.

    Language (English/Swahili/Hausa/Yoruba/Igbo) is detected automatically
    per message via the LLM -- see app.language.detect_language -- but
    only in the background task, since detection itself is an LLM call
    and would otherwise delay this "instant" reply.
    """
    claim = Body.strip()

    if not claim:
        has_media = NumMedia.strip() not in ("", "0")
        text = VOICE_NOTE_UNSUPPORTED_TEXT if has_media else render_whatsapp_text(unverified_reply("en"))
        return Response(content=build_twiml(text), media_type="application/xml")

    background_tasks.add_task(_resolve_and_send, claim, From)
    ack_text = WELCOME_TEXT if is_first_time(From) else INTERIM_TEXT
    return Response(content=build_twiml(ack_text), media_type="application/xml")
