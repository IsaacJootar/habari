import json

import pytest

from app import llm
from app.models import FactCheckEntry, RetrievalMatch

ENTRY = FactCheckEntry(
    id="test-vaccine-microchip",
    title="No, COVID-19 vaccines do not contain microchips",
    summary="A viral claim that vaccines implant tracking microchips is false.",
    verdict="False",
    source_url="https://example.org/vaccine-microchip",
    topic_tags=["health", "vaccine", "covid"],
    country="Kenya",
    source="Africa Check",
)
MATCHES = [RetrievalMatch(entry=ENTRY, score=90.0)]


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
    monkeypatch.setattr(llm, "_get_client", lambda: fake)
    return fake


def test_no_matches_skips_llm_call_entirely(monkeypatch):
    def _boom():
        raise AssertionError("LLM should never be called when there are no matches")

    monkeypatch.setattr(llm, "_get_client", _boom)
    reply = llm.synthesize_verdict("some claim", [])
    assert reply.verdict == "Unverified"


def test_valid_response_returns_grounded_verdict(monkeypatch):
    content = json.dumps(
        {
            "verdict": "False",
            "explanation": "This is false, vaccines do not contain microchips.",
            "source_url": ENTRY.source_url,
        }
    )
    fake = _patch_client(monkeypatch, content=content)
    reply = llm.synthesize_verdict("vaccines have microchips right?", MATCHES)
    assert reply.verdict == "False"
    assert reply.source_url == ENTRY.source_url
    assert fake.completions.calls == 1


def test_llm_can_override_to_unverified_when_no_real_match(monkeypatch):
    content = json.dumps(
        {
            "verdict": "Unverified",
            "explanation": "None of the candidate articles actually address this claim.",
            "source_url": None,
        }
    )
    _patch_client(monkeypatch, content=content)
    reply = llm.synthesize_verdict("unrelated but tag-matched claim", MATCHES)
    assert reply.verdict == "Unverified"
    assert reply.source_url is None


def test_hallucinated_source_url_falls_back_to_unverified(monkeypatch):
    content = json.dumps(
        {
            "verdict": "False",
            "explanation": "Some explanation.",
            "source_url": "https://not-a-real-retrieved-article.example/",
        }
    )
    _patch_client(monkeypatch, content=content)
    reply = llm.synthesize_verdict("claim", MATCHES)
    assert reply.verdict == "Unverified"


def test_malformed_json_falls_back_to_unverified(monkeypatch):
    _patch_client(monkeypatch, content="not valid json at all")
    reply = llm.synthesize_verdict("claim", MATCHES)
    assert reply.verdict == "Unverified"


def test_unexpected_verdict_value_falls_back_to_unverified(monkeypatch):
    content = json.dumps(
        {"verdict": "Probably True", "explanation": "hedging", "source_url": ENTRY.source_url}
    )
    _patch_client(monkeypatch, content=content)
    reply = llm.synthesize_verdict("claim", MATCHES)
    assert reply.verdict == "Unverified"


def test_api_error_falls_back_to_unverified(monkeypatch):
    _patch_client(monkeypatch, exception=RuntimeError("network exploded"))
    reply = llm.synthesize_verdict("claim", MATCHES)
    assert reply.verdict == "Unverified"
