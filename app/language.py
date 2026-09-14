from langdetect import DetectorFactory, LangDetectException, detect

# Makes detection deterministic (langdetect is otherwise randomized internally).
DetectorFactory.seed = 0

SUPPORTED_LANGUAGES = ("en", "sw")
LANGUAGE_NAMES = {"en": "English", "sw": "Swahili"}


def detect_language(text: str) -> str:
    """Best-effort English vs. Swahili detection for a WhatsApp message.

    The brief only requires supporting these two languages, so anything
    else detected (or anything too short/ambiguous to detect at all)
    defaults to English rather than guessing at a third language we
    can't actually reply in.
    """
    if not text or not text.strip():
        return "en"
    try:
        detected = detect(text)
    except LangDetectException:
        return "en"
    return detected if detected in SUPPORTED_LANGUAGES else "en"
