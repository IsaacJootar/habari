from twilio.twiml.messaging_response import MessagingResponse

from app.models import WebhookReply

VERDICT_LABELS = {
    "en": {"True": "TRUE", "False": "FALSE", "Misleading": "MISLEADING", "Unverified": "UNVERIFIED"},
    "sw": {"True": "KWELI", "False": "SI KWELI", "Misleading": "YAPOTOSHA", "Unverified": "HAIJATHIBITISHWA"},
}

SOURCE_LABEL = {"en": "Source", "sw": "Chanzo"}

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
