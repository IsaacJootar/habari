from fastapi import FastAPI
from pydantic import BaseModel

from app.retrieval import retrieve

app = FastAPI(title="Habari")


class IncomingMessage(BaseModel):
    message: str


class WebhookReply(BaseModel):
    verdict: str
    explanation: str
    source_url: str | None = None


UNVERIFIED_REPLY = WebhookReply(
    verdict="Unverified",
    explanation=(
        "We couldn't find a matching fact-check for this yet. "
        "Don't share it further until a trusted source confirms it — "
        "try checking africacheck.org, pesacheck.org, or dubawa.org directly."
    ),
    source_url=None,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook", response_model=WebhookReply)
def webhook(payload: IncomingMessage) -> WebhookReply:
    """Phase 1 stub: takes a plain-text claim, returns the retrieval result.

    This does not yet call the LLM (Phase 2) or speak Twilio's webhook
    format (Phase 3) — it exists so the retrieval step can be exercised
    end-to-end before those layers are added.
    """
    matches = retrieve(payload.message)
    if not matches:
        return UNVERIFIED_REPLY

    top = matches[0].entry
    return WebhookReply(
        verdict=top.verdict,
        explanation=top.summary,
        source_url=top.source_url,
    )
