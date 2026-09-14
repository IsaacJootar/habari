from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from app.llm import synthesize_verdict
from app.models import WebhookReply
from app.retrieval import retrieve

load_dotenv()

app = FastAPI(title="Habari")


class IncomingMessage(BaseModel):
    message: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook", response_model=WebhookReply)
def webhook(payload: IncomingMessage) -> WebhookReply:
    """Phase 2 stub: takes a plain-text claim, returns an LLM-synthesized
    verdict grounded in the retrieved article(s).

    Does not yet speak Twilio's webhook format (Phase 3) — it exists so
    retrieval + LLM synthesis can be exercised end-to-end before that
    layer is added.
    """
    matches = retrieve(payload.message)
    return synthesize_verdict(payload.message, matches)
