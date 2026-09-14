from app import retrieval
from app.models import FactCheckEntry

SAMPLE_ENTRIES = [
    FactCheckEntry(
        id="test-vaccine-microchip",
        title="No, COVID-19 vaccines do not contain microchips",
        summary="A viral claim that vaccines implant tracking microchips is false; no such technology exists in any approved vaccine.",
        verdict="False",
        source_url="https://example.org/vaccine-microchip",
        topic_tags=["health", "vaccine", "covid"],
        country="Kenya",
        source="Africa Check",
    ),
    FactCheckEntry(
        id="test-mpesa-scam",
        title="Beware fake M-Pesa 'reverse transaction' scam calls",
        summary="Scammers pose as M-Pesa agents claiming a mistaken transfer to trick victims into sending money back.",
        verdict="True",
        source_url="https://example.org/mpesa-scam",
        topic_tags=["scam", "mobile money", "mpesa"],
        country="Kenya",
        source="PesaCheck",
    ),
]


def test_no_match_returns_empty_list_on_empty_dataset(monkeypatch):
    monkeypatch.setattr(retrieval, "load_dataset", lambda: [])
    assert retrieval.retrieve("any claim at all") == []


def test_empty_claim_returns_no_matches(monkeypatch):
    monkeypatch.setattr(retrieval, "load_dataset", lambda: SAMPLE_ENTRIES)
    assert retrieval.retrieve("   ") == []


def test_unrelated_claim_falls_back_to_unverified(monkeypatch):
    monkeypatch.setattr(retrieval, "load_dataset", lambda: SAMPLE_ENTRIES)
    matches = retrieval.retrieve("what time does the post office close on Saturdays")
    assert matches == []


def test_confident_match_returns_correct_entry(monkeypatch):
    monkeypatch.setattr(retrieval, "load_dataset", lambda: SAMPLE_ENTRIES)
    matches = retrieval.retrieve("I heard COVID vaccines have a microchip inside them to track you")
    assert matches, "expected at least one confident match"
    assert matches[0].entry.id == "test-vaccine-microchip"


def test_matches_are_sorted_best_first(monkeypatch):
    monkeypatch.setattr(retrieval, "load_dataset", lambda: SAMPLE_ENTRIES)
    matches = retrieval.retrieve("m-pesa reverse transaction scam call")
    assert matches
    assert matches[0].entry.id == "test-mpesa-scam"
    scores = [m.score for m in matches]
    assert scores == sorted(scores, reverse=True)
