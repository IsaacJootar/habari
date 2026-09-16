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


def test_short_common_word_does_not_false_substring_match():
    # A real bug: claim word "it" is a literal substring of "politics" and
    # "citizenship" ("pol-IT-ics", "cIT-izenship") -- without a minimum
    # length guard, an unrelated article tagged "politics" would gate in
    # for any claim that merely contains the word "it".
    assert retrieval._words_match("politics", "it") is False
    assert retrieval._words_match("citizenship", "it") is False
    assert retrieval._words_match("constitution", "it") is False


def test_meaningful_word_variant_still_matches_via_substring():
    # The fix that catches word-form variants (a fuzzy-ratio-only check
    # missed "scam" vs "scammed", scoring ~73, below the typo threshold)
    # must still work for real 4+-letter roots.
    assert retrieval._words_match("scam", "scammed") is True
    assert retrieval._words_match("vaccine", "vaccines") is True


def test_ranking_prefers_more_matching_tags_over_a_fuzzy_score_tie(monkeypatch):
    # Reproduces a real false-positive found when the dataset grew: two
    # articles that only share one generic tag ("ghana") can tie exactly
    # on fuzzy score, letting an unrelated article win purely on list
    # order. The correct, more topically specific article (2 matching
    # tags: "ghana" and "curriculum") must be ranked first.
    entries = [
        FactCheckEntry(
            id="test-wrong-topic-one-tag",
            title="Unrelated claim that happens to mention Ghana",
            summary="A completely different story that only shares the word Ghana with the claim below.",
            verdict="False",
            source_url="https://example.org/wrong",
            topic_tags=["general", "scam", "election", "ghana", "phishing"],
            country="Ghana",
            source="Dubawa",
        ),
        FactCheckEntry(
            id="test-right-topic-two-tags",
            title="False! Kindergarten pupils will not learn Chinese under Ghana's new curriculum",
            summary="The claim that kindergarten pupils will learn Chinese under Ghana's new basic school curriculum is false.",
            verdict="False",
            source_url="https://example.org/right",
            topic_tags=["education", "ghana", "curriculum"],
            country="Ghana",
            source="GhanaFact",
        ),
    ]
    monkeypatch.setattr(retrieval, "load_dataset", lambda: entries)
    matches = retrieval.retrieve("is it true kindergarten pupils will learn chinese in the new Ghana curriculum")
    assert matches
    assert matches[0].entry.id == "test-right-topic-two-tags"


def test_distinctive_brand_name_in_title_triggers_gate_even_without_a_tag_match(monkeypatch):
    # Found via stress-testing: a real claim naming the specific brand
    # involved ("Safaricom") didn't match the real curated article about
    # it, because "Safaricom" wasn't one of the article's generic
    # category tags (scam, mpesa, investment-fraud, deepfake, kenya) and
    # nothing else in the claim matched those tags either. Distinctive
    # title words now act as an additional gate signal alongside tags.
    entry = FactCheckEntry(
        id="test-safaricom-trading-scam",
        title="HOAX: This site running a trading platform supposedly from Safaricom is a scam",
        summary="Scammers set up a fake trading platform impersonating Safaricom to defraud victims.",
        verdict="False",
        source_url="https://example.org/safaricom-scam",
        topic_tags=["scam", "mpesa", "investment-fraud", "deepfake", "kenya"],
        country="Kenya",
        source="PesaCheck",
    )
    monkeypatch.setattr(retrieval, "load_dataset", lambda: [entry])
    matches = retrieval.retrieve("I got a message saying I won a Safaricom trading promotion")
    assert matches
    assert matches[0].entry.id == "test-safaricom-trading-scam"
