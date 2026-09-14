from app.language import detect_language


def test_empty_text_defaults_to_english():
    assert detect_language("") == "en"
    assert detect_language("   ") == "en"


def test_english_claim_detected_as_english():
    assert detect_language("I heard the election results were rigged in favor of the president") == "en"


def test_swahili_claim_detected_as_swahili():
    assert detect_language("Nimesikia kuwa matokeo ya uchaguzi yamegushwa kumpendelea rais") == "sw"


def test_unsupported_language_falls_back_to_english():
    # French -- not one of the two supported languages, should not be
    # passed through as-is.
    assert detect_language("J'ai entendu dire que les résultats des élections ont été truqués") == "en"
