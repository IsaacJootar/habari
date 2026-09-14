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


def test_whatsapp_with_text_renders_grounded_twiml(monkeypatch):
    reply = WebhookReply(
        verdict="False",
        explanation="This claim is false according to a real fact-check.",
        source_url="https://example.org/fact-check",
    )
    captured = {}

    def fake_synthesize(claim, matches, language="en"):
        captured["claim"] = claim
        captured["language"] = language
        return reply

    monkeypatch.setattr(main, "retrieve", lambda claim: ["fake-match"])
    monkeypatch.setattr(main, "synthesize_verdict", fake_synthesize)

    resp = client.post("/whatsapp", data={"Body": "coconut oil cures covid, right?", "NumMedia": "0"})
    assert resp.status_code == 200
    assert "FALSE" in resp.text
    assert "This claim is false according to a real fact-check." in resp.text
    assert "https://example.org/fact-check" in resp.text
    assert captured["language"] == "en"


def test_whatsapp_swahili_text_is_detected_and_passed_through(monkeypatch):
    captured = {}

    def fake_synthesize(claim, matches, language="en"):
        captured["language"] = language
        return WebhookReply(verdict="Unverified", explanation="hakuna taarifa", source_url=None)

    monkeypatch.setattr(main, "retrieve", lambda claim: [])
    monkeypatch.setattr(main, "synthesize_verdict", fake_synthesize)

    resp = client.post(
        "/whatsapp",
        data={"Body": "Nimesikia kuwa matokeo ya uchaguzi yamegushwa kumpendelea rais", "NumMedia": "0"},
    )
    assert resp.status_code == 200
    assert captured["language"] == "sw"
