from app import language


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content=None, exception=None):
        self._content = content
        self._exception = exception
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self._exception:
            raise self._exception
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, content=None, exception=None):
        self.completions = _FakeCompletions(content=content, exception=exception)
        self.chat = _FakeChat(self.completions)


def _patch_client(monkeypatch, content=None, exception=None):
    fake = _FakeClient(content=content, exception=exception)
    monkeypatch.setattr(language, "_get_client", lambda: fake)
    return fake


def test_empty_text_defaults_to_english_without_calling_llm(monkeypatch):
    def _boom():
        raise AssertionError("should not call the LLM for empty text")

    monkeypatch.setattr(language, "_get_client", _boom)
    assert language.detect_language("") == "en"
    assert language.detect_language("   ") == "en"


def test_each_supported_language_code_is_passed_through(monkeypatch):
    for code in language.SUPPORTED_LANGUAGES:
        _patch_client(monkeypatch, content=code)
        assert language.detect_language("some message") == code


def test_response_with_extra_whitespace_or_case_is_normalized(monkeypatch):
    _patch_client(monkeypatch, content=" SW \n")
    assert language.detect_language("Nimesikia habari hii") == "sw"


def test_unrecognized_response_falls_back_to_english(monkeypatch):
    _patch_client(monkeypatch, content="fr")
    assert language.detect_language("Bonjour le monde") == "en"


def test_api_error_falls_back_to_english(monkeypatch):
    _patch_client(monkeypatch, exception=RuntimeError("network exploded"))
    assert language.detect_language("some message") == "en"
