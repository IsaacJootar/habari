from fastapi.testclient import TestClient

from app import main
from app.models import WebhookReply

client = TestClient(main.app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_whatsapp_media_with_no_text_returns_voice_note_message(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("synthesize_verdict should not be called for a media-only message")

    monkeypatch.setattr(main, "synthesize_verdict", _boom)
    resp = client.post("/whatsapp", data={"Body": "", "NumMedia": "1"})
    assert resp.status_code == 200
    assert "text/xml" in resp.headers["content-type"] or "application/xml" in resp.headers["content-type"]
    assert "voice note" in resp.text.lower()


def test_whatsapp_empty_message_no_media_returns_english_unverified(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("synthesize_verdict should not be called for an empty message")

    monkeypatch.setattr(main, "synthesize_verdict", _boom)
    resp = client.post("/whatsapp", data={"Body": "   ", "NumMedia": "0"})
    assert resp.status_code == 200
    assert "UNVERIFIED" in resp.text


def test_whatsapp_first_message_from_sender_gets_welcome_text(monkeypatch):
    monkeypatch.setattr(main, "retrieve", lambda claim: [])
    monkeypatch.setattr(main, "live_search", lambda claim: [])
    monkeypatch.setattr(main, "_resolve_and_send", lambda claim, to: None)

    resp = client.post(
        "/whatsapp",
        data={"Body": "some claim", "From": "whatsapp:+254711111111", "NumMedia": "0"},
    )
    assert resp.status_code == 200
    assert "welcome to Habari" in resp.text
    assert "hackathon prototype" in resp.text
    # Welcome text still doubles as the "please wait" ack -- the first
    # message still gets checked, it isn't a wasted turn.
    assert "Checking" in resp.text


def test_whatsapp_second_message_from_same_sender_gets_regular_interim_text(monkeypatch):
    monkeypatch.setattr(main, "retrieve", lambda claim: [])
    monkeypatch.setattr(main, "live_search", lambda claim: [])
    monkeypatch.setattr(main, "_resolve_and_send", lambda claim, to: None)

    sender = "whatsapp:+254722222222"
    first = client.post("/whatsapp", data={"Body": "first claim", "From": sender, "NumMedia": "0"})
    second = client.post("/whatsapp", data={"Body": "second claim", "From": sender, "NumMedia": "0"})

    assert "welcome to Habari" in first.text
    assert "welcome to Habari" not in second.text
    assert "Checking" in second.text


def test_whatsapp_with_text_returns_interim_reply_then_sends_real_verdict(monkeypatch):
    reply = WebhookReply(
        verdict="False",
        explanation="This claim is false according to a real fact-check.",
        source_url="https://example.org/fact-check",
    )
    sent = {}

    def fake_synthesize(claim, matches, live_results, language="en"):
        return reply

    def fake_send(to, body):
        sent["to"] = to
        sent["body"] = body

    monkeypatch.setattr(main, "detect_language", lambda claim: "en")
    monkeypatch.setattr(main, "retrieve", lambda claim: ["fake-match"])
    monkeypatch.setattr(main, "live_search", lambda claim: [])
    monkeypatch.setattr(main, "synthesize_verdict", fake_synthesize)
    monkeypatch.setattr(main, "send_whatsapp_message", fake_send)

    resp = client.post(
        "/whatsapp",
        data={"Body": "coconut oil cures covid, right?", "From": "whatsapp:+254700000000", "NumMedia": "0"},
    )
    assert resp.status_code == 200
    # The immediate TwiML reply is just the interim message, not the verdict --
    # the LLM call happens in the background and is delivered as a follow-up.
    assert "Checking" in resp.text
    assert "FALSE" not in resp.text

    # TestClient runs background tasks before returning, so the follow-up
    # send should already have happened.
    assert sent["to"] == "whatsapp:+254700000000"
    assert "FALSE" in sent["body"]
    assert "https://example.org/fact-check" in sent["body"]


def test_whatsapp_interim_reply_is_language_agnostic_and_instant(monkeypatch):
    # detect_language is itself an LLM call (needed for Hausa/Yoruba/Igbo
    # support) -- it must NOT be called before the interim reply is built,
    # or the "instant" reply isn't instant. Proven here by making
    # detect_language raise if called synchronously on this path; it's
    # only used inside the background task via synthesize_verdict, which
    # is mocked out entirely.
    def _boom_if_called_early(claim):
        raise AssertionError("detect_language must not run before the interim reply is sent")

    monkeypatch.setattr(main, "detect_language", _boom_if_called_early)
    monkeypatch.setattr(main, "retrieve", lambda claim: [])
    monkeypatch.setattr(main, "live_search", lambda claim: [])

    def fake_resolve_and_send(claim, to):
        pass  # detect_language would be called for real here in production

    monkeypatch.setattr(main, "_resolve_and_send", fake_resolve_and_send)

    resp = client.post(
        "/whatsapp",
        data={"Body": "Nimesikia kuwa matokeo ya uchaguzi", "From": "whatsapp:+254700000000", "NumMedia": "0"},
    )
    assert resp.status_code == 200
    # Combined multi-language text -- covers all 5 supported languages at once.
    assert "Checking" in resp.text
    assert "Tunakagua" in resp.text
    assert "Muna duba" in resp.text


def test_whatsapp_background_task_detects_language_and_passes_it_through(monkeypatch):
    captured = {}

    def fake_synthesize(claim, matches, live_results, language="en"):
        captured["language"] = language
        return WebhookReply(verdict="Unverified", explanation="babu bayani", source_url=None)

    monkeypatch.setattr(main, "detect_language", lambda claim: "ha")
    monkeypatch.setattr(main, "retrieve", lambda claim: [])
    monkeypatch.setattr(main, "live_search", lambda claim: [])
    monkeypatch.setattr(main, "synthesize_verdict", fake_synthesize)
    monkeypatch.setattr(main, "send_whatsapp_message", lambda to, body: None)

    resp = client.post(
        "/whatsapp",
        data={
            "Body": "Na ji cewa allurar rigakafi tana da chip a ciki",
            "From": "whatsapp:+2348000000000",
            "NumMedia": "0",
        },
    )
    assert resp.status_code == 200
    # TestClient runs background tasks before returning, so by now
    # detect_language has run (in the background task) and its result
    # reached synthesize_verdict.
    assert captured["language"] == "ha"
