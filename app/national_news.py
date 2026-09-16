import re

# Not fact-check sources -- general national news outlets. Never used to
# produce a verdict, only offered as a "here's where to look next" suggestion
# when nothing could be verified, since that's more locally useful than only
# pointing at africacheck.org/pesacheck.org/dubawa.org generically. 4 sample
# countries, matching the dataset's existing country coverage.
NATIONAL_OUTLETS = {
    "Nigeria": ("Premium Times", "https://www.premiumtimesng.com"),
    "Kenya": ("Nation Africa", "https://nation.africa"),
    "Ghana": ("Daily Graphic", "https://www.graphic.com.gh"),
    "Uganda": ("Daily Monitor", "https://www.monitor.co.ug"),
}

_COUNTRY_KEYWORDS = {
    "Nigeria": {"nigeria", "nigerian", "naija", "lagos", "abuja", "tinubu", "buhari"},
    "Kenya": {"kenya", "kenyan", "nairobi", "ruto", "mombasa", "kenyatta"},
    "Ghana": {"ghana", "ghanaian", "accra", "mahama", "kumasi", "akufoaddo"},
    "Uganda": {"uganda", "ugandan", "kampala", "museveni"},
}

_WORD_RE = re.compile(r"[a-z0-9']+")


def detect_country(claim: str) -> str | None:
    """Cheap keyword-based guess at which of the 4 sample countries a claim
    is about -- good enough for a "check here too" suggestion, not a
    verdict source, so occasional misses are low-stakes."""
    words = set(_WORD_RE.findall(claim.lower()))
    for country, keywords in _COUNTRY_KEYWORDS.items():
        if words & keywords:
            return country
    return None


def suggest_national_outlet(claim: str) -> tuple[str, str] | None:
    """Returns (outlet_name, url) for the detected country, or None."""
    country = detect_country(claim)
    if country is None:
        return None
    return NATIONAL_OUTLETS.get(country)
