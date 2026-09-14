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


def test_whatsapp_with_text_returns_interim_reply_then_sends_real_verdict(monkeypatch):
    reply = WebhookReply(
        verdict="False",
        explanation="This claim is false according to a real fact-check.",
        source_url="https://example.org/fact-check",
    )
    sent = {}

    def fake_synthesize(claim, matches, language="en"):
        return reply

    def fake_send(to, body):
        sent["to"] = to
        sent["body"] = body

    monkeypatch.setattr(main, "detect_language", lambda claim: "en")
    monkeypatch.setattr(main, "retrieve", lambda claim: ["fake-match"])
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


def test_whatsapp_swahili_text_gets_swahili_interim_and_language_passed(monkeypatch):
    captured = {}

    def fake_synthesize(claim, matches, language="en"):
        captured["language"] = language
        return WebhookReply(verdict="Unverified", explanation="hakuna taarifa", source_url=None)

    # detect_language is now an LLM call -- mocked here since accuracy is
    # covered separately in tests/test_language.py; this test only checks
    # that main.py wires the detected language through correctly.
    monkeypatch.setattr(main, "detect_language", lambda claim: "sw")
    monkeypatch.setattr(main, "retrieve", lambda claim: [])
    monkeypatch.setattr(main, "synthesize_verdict", fake_synthesize)
    monkeypatch.setattr(main, "send_whatsapp_message", lambda to, body: None)

    resp = client.post(
        "/whatsapp",
        data={
            "Body": "Nimesikia kuwa matokeo ya uchaguzi yamegushwa kumpendelea rais",
            "From": "whatsapp:+254700000000",
            "NumMedia": "0",
        },
    )
    assert resp.status_code == 200
    assert "Tunakagua" in resp.text
    assert captured["language"] == "sw"


def test_whatsapp_hausa_text_gets_hausa_interim_and_language_passed(monkeypatch):
    captured = {}

    def fake_synthesize(claim, matches, language="en"):
        captured["language"] = language
        return WebhookReply(verdict="Unverified", explanation="babu bayani", source_url=None)

    monkeypatch.setattr(main, "detect_language", lambda claim: "ha")
    monkeypatch.setattr(main, "retrieve", lambda claim: [])
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
    assert "Muna duba" in resp.text
    assert captured["language"] == "ha"
