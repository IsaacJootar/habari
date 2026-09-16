from app.models import unverified_reply


def test_unverified_reply_without_claim_has_no_country_suggestion():
    reply = unverified_reply("en")
    assert "Nation Africa" not in reply.explanation
    assert "Premium Times" not in reply.explanation


def test_unverified_reply_appends_detected_country_outlet():
    reply = unverified_reply("en", "a claim about Tinubu in Lagos, Nigeria")
    assert "Premium Times" in reply.explanation
    assert "premiumtimesng.com" in reply.explanation


def test_unverified_reply_no_suggestion_when_country_undetected():
    reply = unverified_reply("en", "a completely generic claim with no country")
    assert "Premium Times" not in reply.explanation
    assert reply.explanation == unverified_reply("en").explanation


def test_unverified_reply_keeps_correct_language_with_suggestion():
    reply = unverified_reply("sw", "a claim about Ruto in Nairobi, Kenya")
    assert "Nation Africa" in reply.explanation
    assert reply.verdict == "Unverified"
    assert reply.source_url is None
