import json

import pytest

from app import llm
from app.live_search import LiveSearchResult
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

LIVE_RESULT = LiveSearchResult(
    source="Dubawa",
    title="Kindergarten pupils will not learn Chinese, Ghana curriculum claim is false",
    content="The Education Minister clarified that Chinese is optional from Primary 4, not kindergarten.",
    url="https://dubawa.org/some-live-article",
)


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


def test_no_matches_and_no_live_results_skips_llm_call(monkeypatch):
    def _boom():
        raise AssertionError("LLM should never be called with no matches and no live results")

    monkeypatch.setattr(llm, "_get_client", _boom)
    reply = llm.synthesize_verdict("some claim", [], [])
    assert reply.verdict == "Unverified"


def test_live_results_alone_still_calls_the_llm_and_can_ground(monkeypatch):
    content = json.dumps(
        {
            "verdict": "False",
            "explanation": "Kindergarten pupils will not learn Chinese under the new curriculum.",
            "source_url": LIVE_RESULT.url,
        }
    )
    fake = _patch_client(monkeypatch, content=content)
    reply = llm.synthesize_verdict("kindergarten chinese curriculum claim", [], [LIVE_RESULT])
    assert reply.verdict == "False"
    assert reply.source_url == LIVE_RESULT.url
    assert fake.completions.calls == 1


def test_hallucinated_live_result_url_falls_back_to_unverified(monkeypatch):
    content = json.dumps(
        {
            "verdict": "False",
            "explanation": "Some explanation.",
            "source_url": "https://not-one-of-the-live-results.example/",
        }
    )
    _patch_client(monkeypatch, content=content)
    reply = llm.synthesize_verdict("claim", [], [LIVE_RESULT])
    assert reply.verdict == "Unverified"


def test_combined_matches_and_live_results_both_offered_to_llm(monkeypatch):
    captured = {}

    class _CapturingCompletions:
        def create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return _FakeResponse(json.dumps({"verdict": "Unverified", "explanation": "n/a", "source_url": None}))

    class _CapturingClient:
        def __init__(self):
            self.chat = _FakeChat(_CapturingCompletions())

    monkeypatch.setattr(llm, "_get_client", lambda: _CapturingClient())
    llm.synthesize_verdict("claim", MATCHES, [LIVE_RESULT])
    user_message = captured["messages"][1]["content"]
    assert ENTRY.source_url in user_message
    assert LIVE_RESULT.url in user_message
    assert "Published verdict" in user_message  # static match
    assert "verdict not given" in user_message  # live result


def test_curated_verdict_carries_published_date_from_entry_not_model(monkeypatch):
    dated = ENTRY.model_copy(update={"published_date": "2021-03-17"})
    content = json.dumps(
        {
            "verdict": "False",
            "explanation": "This is false.",
            "source_url": dated.source_url,
            "published_date": "1999-01-01",  # a model-supplied date must be ignored
        }
    )
    _patch_client(monkeypatch, content=content)
    reply = llm.synthesize_verdict("claim", [RetrievalMatch(entry=dated, score=90.0)])
    assert reply.published_date == "2021-03-17"


def test_live_verdict_carries_published_date_from_result(monkeypatch):
    live = LIVE_RESULT.model_copy(update={"published_date": "2026-08-07"})
    content = json.dumps({"verdict": "False", "explanation": "False.", "source_url": live.url})
    _patch_client(monkeypatch, content=content)
    reply = llm.synthesize_verdict("claim", [], [live])
    assert reply.published_date == "2026-08-07"


def test_undated_source_gives_no_published_date(monkeypatch):
    content = json.dumps({"verdict": "False", "explanation": "False.", "source_url": ENTRY.source_url})
    _patch_client(monkeypatch, content=content)
    reply = llm.synthesize_verdict("claim", MATCHES)
    assert reply.published_date is None
