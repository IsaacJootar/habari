import logging
import os

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from app.models import WebhookReply

logger = logging.getLogger(__name__)

# Shown immediately (synchronously, in the webhook's own TwiML reply) while
# the real verdict is generated in the background -- retrieval + live
# search + the LLM call take a few seconds, and WhatsApp gives no other
# sign of life while that happens. This used to be picked per-language,
# but detect_language() is itself an LLM call (needed for 5-language
# support, since only English/Swahili can be auto-detected without one) --
# measured directly at 1.4-7s with real variance, which defeated the whole
# point of an "instant" interim reply. English only (an earlier version
# stacked all 5 languages together, which read as cluttered -- user
# feedback after a live test) -- the ⏳ plus a short universal wait is
# enough; the real answer that follows is fully localized.
INTERIM_TEXT = "⏳ Checking that for you..."

# Sent instead of INTERIM_TEXT for a sender's very first message (see
# app/session.py) -- doubles as the "please wait" ack so a first-time
# sender's message still gets checked immediately, not wasted on a
# welcome-only turn. English only, per the copy the user picked; the POC
# disclaimer is folded in here (shown once, not on every reply, to avoid
# being repetitive on a low-bandwidth channel) rather than added
# separately to every reply.
WELCOME_TEXT = (
    "👋 Hey, welcome to Habari! Send me a rumor, claim, or news you've seen "
    "and I'll check it against real fact-checkers before you believe or share it.\n\n"
    "🧪 This is a hackathon prototype, not a production service — always "
    "double-check anything important.\n\n" + INTERIM_TEXT
)

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

# Sent when a message carries media Habari doesn't handle at all (video,
# documents, stickers, etc.) -- audio and images ARE supported (see
# app/media.py), this is only for everything else.
UNSUPPORTED_MEDIA_TEXT = (
    "*Habari*\n\n"
    "We can check text, voice notes, or images — please send your claim as one of those.\n\n"
    "Tunaweza kuangalia maandishi, ujumbe wa sauti, au picha — tafadhali tuma dai lako kwa njia mojawapo."
)

# Sent (from the background task) when a voice note was downloaded but
# couldn't be transcribed, or transcription came back empty.
AUDIO_UNREADABLE_TEXT = (
    "*Habari*\n\n"
    "Sorry, we couldn't understand that voice note — please try again or type your claim instead.\n\n"
    "Samahani, hatukuelewa ujumbe huo wa sauti — jaribu tena au andika dai lako."
)

# Sent (from the background task) when an image was downloaded but no
# readable claim/text could be found in it.
IMAGE_UNREADABLE_TEXT = (
    "*Habari*\n\n"
    "Sorry, we couldn't find any readable claim in that image — please try again or type your claim instead.\n\n"
    "Samahani, hatukupata dai lolote linalosomeka kwenye picha hiyo — jaribu tena au andika dai lako."
)

# Sent (from the background task) when the media file itself couldn't be
# downloaded from Twilio at all (network error, expired URL, etc.).
MEDIA_DOWNLOAD_FAILED_TEXT = (
    "*Habari*\n\n"
    "Sorry, we couldn't download that file — please try sending it again.\n\n"
    "Samahani, hatukuweza kupakua faili hiyo — tafadhali jaribu tena."
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
