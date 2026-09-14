from app import whatsapp


class _FakeMessages:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)


class _FakeClient:
    def __init__(self, account_sid, auth_token):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.messages = _FakeMessages()


def test_sends_via_twilio_client_with_correct_args(monkeypatch):
    fake_client = _FakeClient("ACxxx", "token")
    monkeypatch.setattr(whatsapp, "Client", lambda sid, token: fake_client)
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACxxx")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    whatsapp.send_whatsapp_message(to="whatsapp:+254700000000", body="hello")

    assert len(fake_client.messages.calls) == 1
    call = fake_client.messages.calls[0]
    assert call["to"] == "whatsapp:+254700000000"
    assert call["from_"] == "whatsapp:+14155238886"
    assert call["body"] == "hello"


def test_missing_credentials_does_not_raise(monkeypatch):
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)

    # Should log and return quietly, not raise.
    whatsapp.send_whatsapp_message(to="whatsapp:+254700000000", body="hello")


def test_client_exception_is_swallowed(monkeypatch):
    def _boom(sid, token):
        raise RuntimeError("network exploded")

    monkeypatch.setattr(whatsapp, "Client", _boom)
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACxxx")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    # Should not raise -- a failed follow-up send shouldn't crash the app.
    whatsapp.send_whatsapp_message(to="whatsapp:+254700000000", body="hello")
