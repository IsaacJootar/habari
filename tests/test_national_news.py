from app.national_news import NATIONAL_OUTLETS, detect_country, suggest_national_outlet


def test_detects_each_sample_country():
    assert detect_country("I heard a rumor about Tinubu in Lagos") == "Nigeria"
    assert detect_country("Something about Ruto in Nairobi") == "Kenya"
    assert detect_country("A claim about Mahama in Accra") == "Ghana"
    assert detect_country("News about Museveni in Kampala") == "Uganda"


def test_no_country_detected_returns_none():
    assert detect_country("a completely generic claim with no country mentioned") is None


def test_suggest_outlet_matches_detected_country():
    result = suggest_national_outlet("something happening in Lagos, Nigeria")
    assert result == NATIONAL_OUTLETS["Nigeria"]


def test_suggest_outlet_none_when_no_country():
    assert suggest_national_outlet("a generic claim") is None
