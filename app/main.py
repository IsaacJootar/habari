from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Form, Response
from pydantic import BaseModel

from app.language import detect_language
from app.llm import synthesize_verdict
from app.models import WebhookReply, unverified_reply
from app.retrieval import retrieve
from app.whatsapp import (
    INTERIM_TEXT,
    VOICE_NOTE_UNSUPPORTED_TEXT,
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
    return synthesize_verdict(payload.message, matches, language=language)


def _resolve_and_send(claim: str, to: str, language: str) -> None:
    """Runs after the webhook has already replied with the interim message
    -- does the slow retrieval + LLM work, then delivers the real verdict
    as a separate WhatsApp message via Twilio's REST API."""
    matches = retrieve(claim)
    reply = synthesize_verdict(claim, matches, language=language)
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

    A matched claim needs a retrieval + LLM round trip, which takes a few
    seconds with no other sign of life on WhatsApp meanwhile -- so this
    replies immediately with a short "Checking that for you..." message
    and does the real work in the background, sending the actual verdict
    as a follow-up message once it's ready.

    Language (English/Swahili/Hausa/Yoruba/Igbo) is detected automatically
    per message via the LLM -- see app.language.detect_language.
    """
    claim = Body.strip()

    if not claim:
        has_media = NumMedia.strip() not in ("", "0")
        text = VOICE_NOTE_UNSUPPORTED_TEXT if has_media else render_whatsapp_text(unverified_reply("en"))
        return Response(content=build_twiml(text), media_type="application/xml")

    language = detect_language(claim)
    background_tasks.add_task(_resolve_and_send, claim, From, language)
    interim_text = INTERIM_TEXT.get(language, INTERIM_TEXT["en"])
    return Response(content=build_twiml(interim_text), media_type="application/xml")
