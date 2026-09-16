from app import media


class _FakeResponse:
    def __init__(self, content=b"filedata", status_code=200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_download_twilio_media_uses_basic_auth(monkeypatch):
    captured = {}

    def fake_get(url, auth=None, timeout=None):
        captured["url"] = url
        captured["auth"] = auth
        return _FakeResponse(content=b"audio-bytes")

    monkeypatch.setattr(media.httpx, "get", fake_get)
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACxxx")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")

    result = media.download_twilio_media("https://api.twilio.com/media/123")
    assert result == b"audio-bytes"
    assert captured["auth"] == ("ACxxx", "token")


def test_download_twilio_media_missing_credentials_returns_none(monkeypatch):
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    assert media.download_twilio_media("https://api.twilio.com/media/123") is None


def test_download_twilio_media_request_failure_returns_none(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("network exploded")

    monkeypatch.setattr(media.httpx, "get", _boom)
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACxxx")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    assert media.download_twilio_media("https://api.twilio.com/media/123") is None


class _FakeTranscriptionResponse:
    def __init__(self, text):
        self.text = text


class _FakeTranscriptions:
    def __init__(self, text=None, exception=None):
        self._text = text
        self._exception = exception

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._exception:
            raise self._exception
        return _FakeTranscriptionResponse(self._text)


class _FakeAudio:
    def __init__(self, transcriptions):
        self.transcriptions = transcriptions


class _FakeAudioClient:
    def __init__(self, text=None, exception=None):
        self.transcriptions = _FakeTranscriptions(text=text, exception=exception)
        self.audio = _FakeAudio(self.transcriptions)


def test_transcribe_audio_returns_stripped_text(monkeypatch):
    fake = _FakeAudioClient(text="  I heard something on the radio  ")
    monkeypatch.setattr(media, "_get_client", lambda: fake)
    result = media.transcribe_audio(b"some audio bytes", "audio/ogg")
    assert result == "I heard something on the radio"


def test_transcribe_audio_empty_result_returns_none(monkeypatch):
    fake = _FakeAudioClient(text="   ")
    monkeypatch.setattr(media, "_get_client", lambda: fake)
    assert media.transcribe_audio(b"some audio bytes", "audio/ogg") is None


def test_transcribe_audio_no_bytes_returns_none(monkeypatch):
    def _boom():
        raise AssertionError("should not call the API with no audio bytes")

    monkeypatch.setattr(media, "_get_client", _boom)
    assert media.transcribe_audio(b"", "audio/ogg") is None


def test_transcribe_audio_api_error_returns_none(monkeypatch):
    fake = _FakeAudioClient(exception=RuntimeError("network exploded"))
    monkeypatch.setattr(media, "_get_client", lambda: fake)
    assert media.transcribe_audio(b"some audio bytes", "audio/ogg") is None


class _FakeChatMessage:
    def __init__(self, content):
        self.content = content


class _FakeChatChoice:
    def __init__(self, content):
        self.message = _FakeChatMessage(content)


class _FakeChatResponse:
    def __init__(self, content):
        self.choices = [_FakeChatChoice(content)]


class _FakeChatCompletions:
    def __init__(self, content=None, exception=None):
        self._content = content
        self._exception = exception

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._exception:
            raise self._exception
        return _FakeChatResponse(self._content)


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeVisionClient:
    def __init__(self, content=None, exception=None):
        self.completions = _FakeChatCompletions(content=content, exception=exception)
        self.chat = _FakeChat(self.completions)


def test_extract_claim_from_image_returns_extracted_text(monkeypatch):
    fake = _FakeVisionClient(content="Government bans all okada riders starting Monday")
    monkeypatch.setattr(media, "_get_client", lambda: fake)
    result = media.extract_claim_from_image(b"some image bytes", "image/jpeg")
    assert result == "Government bans all okada riders starting Monday"


def test_extract_claim_from_image_none_response_returns_none(monkeypatch):
    fake = _FakeVisionClient(content="NONE")
    monkeypatch.setattr(media, "_get_client", lambda: fake)
    assert media.extract_claim_from_image(b"some image bytes", "image/jpeg") is None


def test_extract_claim_from_image_empty_response_returns_none(monkeypatch):
    fake = _FakeVisionClient(content="   ")
    monkeypatch.setattr(media, "_get_client", lambda: fake)
    assert media.extract_claim_from_image(b"some image bytes", "image/jpeg") is None


def test_extract_claim_from_image_no_bytes_returns_none(monkeypatch):
    def _boom():
        raise AssertionError("should not call the API with no image bytes")

    monkeypatch.setattr(media, "_get_client", _boom)
    assert media.extract_claim_from_image(b"", "image/jpeg") is None


def test_extract_claim_from_image_api_error_returns_none(monkeypatch):
    fake = _FakeVisionClient(exception=RuntimeError("network exploded"))
    monkeypatch.setattr(media, "_get_client", lambda: fake)
    assert media.extract_claim_from_image(b"some image bytes", "image/jpeg") is None
