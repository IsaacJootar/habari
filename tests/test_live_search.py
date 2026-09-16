from app import live_search


def test_extract_keywords_drops_stopwords_and_short_words():
    claim = "is it true kindergarten pupils will learn chinese in the new Ghana curriculum"
    keywords = live_search._extract_search_keywords(claim, max_keywords=10)
    words = keywords.split()
    assert "is" not in words
    assert "it" not in words
    assert "the" not in words
    assert "in" not in words
    assert "kindergarten" in words
    assert "chinese" in words
    assert "curriculum" in words


def test_extract_keywords_caps_at_max_keywords():
    claim = "kindergarten pupils learn chinese ghana curriculum education policy announcement today"
    keywords = live_search._extract_search_keywords(claim, max_keywords=3)
    assert len(keywords.split()) == 3


def test_extract_keywords_empty_for_only_stopwords():
    assert live_search._extract_search_keywords("is it the that this") == ""


def test_live_search_returns_empty_for_blank_claim():
    assert live_search.live_search("") == []
    assert live_search.live_search("   ") == []


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_search_one_source_parses_and_cleans_wordpress_response(monkeypatch):
    payload = [
        {
            "title": {"rendered": "False! Some <b>claim</b> is not true"},
            "content": {"rendered": "<p>Full article body with &amp; an entity.</p>"},
            "excerpt": {"rendered": "<p>short excerpt</p>"},
            "link": "https://example.org/article-1",
        }
    ]
    monkeypatch.setattr(live_search.httpx, "get", lambda *a, **k: _FakeResponse(payload))

    results = live_search._search_one_source("TestSource", "https://example.org/wp-json", "claim")
    assert len(results) == 1
    assert results[0].title == "False! Some claim is not true"
    assert results[0].content == "Full article body with & an entity."
    assert results[0].url == "https://example.org/article-1"
    assert results[0].source == "TestSource"


def test_search_one_source_repairs_mojibake_apostrophe(monkeypatch):
    payload = [
        {
            "title": {"rendered": "Ghana�s new curriculum is real"},
            "content": {"rendered": "Some content here."},
            "excerpt": {"rendered": ""},
            "link": "https://example.org/article-2",
        }
    ]
    monkeypatch.setattr(live_search.httpx, "get", lambda *a, **k: _FakeResponse(payload))

    results = live_search._search_one_source("TestSource", "https://example.org/wp-json", "claim")
    assert "�" not in results[0].title
    assert "Ghana" in results[0].title


def test_search_one_source_returns_empty_on_request_failure(monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("network exploded")

    monkeypatch.setattr(live_search.httpx, "get", _boom)
    results = live_search._search_one_source("TestSource", "https://example.org/wp-json", "claim")
    assert results == []


def test_search_one_source_returns_empty_on_http_error(monkeypatch):
    monkeypatch.setattr(
        live_search.httpx, "get", lambda *a, **k: _FakeResponse([], status_code=503)
    )
    results = live_search._search_one_source("TestSource", "https://example.org/wp-json", "claim")
    assert results == []


def test_live_search_queries_all_configured_sources(monkeypatch):
    calls = []

    def fake_search_one(source_name, base_url, query):
        calls.append(source_name)
        return []

    monkeypatch.setattr(live_search, "_search_one_source", fake_search_one)
    live_search.live_search("some claim about something")
    assert set(calls) == set(live_search.LIVE_SEARCH_SOURCES.keys())
