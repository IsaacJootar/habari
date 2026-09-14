from dotenv import load_dotenv
from fastapi import FastAPI, Form, Response
from pydantic import BaseModel

from app.language import detect_language
from app.llm import synthesize_verdict
from app.models import WebhookReply, unverified_reply
from app.retrieval import retrieve
from app.whatsapp import VOICE_NOTE_UNSUPPORTED_TEXT, build_twiml, render_whatsapp_text

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


@app.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(default=""),
    NumMedia: str = Form(default="0"),
) -> Response:
    """Twilio's actual WhatsApp Sandbox webhook target: form-encoded
    request in, TwiML (XML) reply out."""
    claim = Body.strip()

    if not claim:
        has_media = NumMedia.strip() not in ("", "0")
        text = VOICE_NOTE_UNSUPPORTED_TEXT if has_media else render_whatsapp_text(unverified_reply("en"))
        return Response(content=build_twiml(text), media_type="application/xml")

    language = detect_language(claim)
    matches = retrieve(claim)
    reply = synthesize_verdict(claim, matches, language=language)
    text = render_whatsapp_text(reply, language)
    return Response(content=build_twiml(text), media_type="application/xml")
