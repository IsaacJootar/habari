import logging
import os

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from app.models import WebhookReply

logger = logging.getLogger(__name__)

# Shown immediately (synchronously, in the webhook's own TwiML reply) while
# the real verdict is generated in the background -- retrieval + the LLM
# call take a few seconds, and WhatsApp gives no other sign of life while
# that happens.
INTERIM_TEXT = {
    "en": "⏳ Checking that for you...",
    "sw": "⏳ Tunakagua hilo kwa ajili yako...",
    "ha": "⏳ Muna duba wannan a gare ka...",
    "yo": "⏳ À ń ṣàyẹ̀wò náà fún ọ...",
    "ig": "⏳ Anyị na-elele nke ahụ maka gị...",
}

# POC-quality translations, not reviewed by native speakers yet -- worth a
# proper check before the demo (see BUILD_PLAN.md Phase 4).
VERDICT_LABELS = {
    "en": {"True": "TRUE", "False": "FALSE", "Misleading": "MISLEADING", "Unverified": "UNVERIFIED"},
    "sw": {"True": "KWELI", "False": "SI KWELI", "Misleading": "YAPOTOSHA", "Unverified": "HAIJATHIBITISHWA"},
    "ha": {"True": "GASKIYA", "False": "KARYA", "Misleading": "RUDANI", "Unverified": "BA A TABBATAR BA"},
    "yo": {"True": "ÒÒTÓ", "False": "ÈKE", "Misleading": "ÀṢINA", "Unverified": "A KÒ JẸ́RÌÍ"},
    "ig": {"True": "EZIOKWU", "False": "ỤGHA", "Misleading": "NDỤDA", "Unverified": "AKWADOBEGHỊ"},
}

SOURCE_LABEL = {"en": "Source", "sw": "Chanzo", "ha": "Tushen", "yo": "Orísun", "ig": "Isi iyi"}

# Sent when a message carries audio/media but no text -- voice-note
# transcription (Whisper) is a Phase 4 stretch goal, not wired up yet.
VOICE_NOTE_UNSUPPORTED_TEXT = (
    "*Habari*\n\n"
    "We can't check voice notes yet — please type or paste the claim as text.\n\n"
    "Bado hatuwezi kuangalia ujumbe wa sauti — tafadhali andika au bandika dai kwa maandishi."
)


def render_whatsapp_text(reply: WebhookReply, language: str = "en") -> str:
    labels = VERDICT_LABELS.get(language, VERDICT_LABELS["en"])
    label = labels.get(reply.verdict, reply.verdict)
    lines = [f"*{label}*", "", reply.explanation]
    if reply.source_url:
        source_label = SOURCE_LABEL.get(language, SOURCE_LABEL["en"])
        lines += ["", f"{source_label}: {reply.source_url}"]
    return "\n".join(lines)


def build_twiml(text: str) -> str:
    response = MessagingResponse()
    response.message(text)
    return str(response)


def send_whatsapp_message(to: str, body: str) -> None:
    """Send a follow-up WhatsApp message outside the webhook's own TwiML
    reply, via Twilio's REST API -- used to deliver the real verdict after
    the interim "Checking that for you..." message. `to` is already in
    Twilio's "whatsapp:+<number>" form (that's what the webhook's `From`
    field gives us).
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_WHATSAPP_NUMBER")
    if not (account_sid and auth_token and from_number and to):
        logger.error("Missing Twilio credentials/number/recipient; could not send follow-up message")
        return

    try:
        Client(account_sid, auth_token).messages.create(from_=from_number, to=to, body=body)
    except Exception:
        logger.exception("Failed to send follow-up WhatsApp message via Twilio REST API")
