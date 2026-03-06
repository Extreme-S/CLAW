"""Chat endpoints — sync and streaming."""

import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from server.storage.models import ChatRequest, ChatResponse
from server.api.middleware import verify_token

router = APIRouter(prefix="/chat", dependencies=[Depends(verify_token)])

# Chat engine reference, set by main.py
_engine = None


def set_engine(engine):
    global _engine
    _engine = engine


@router.post("", response_model=ChatResponse)
async def chat_sync(req: ChatRequest):
    """Non-streaming chat: returns full response at once."""
    sid, stream = _engine.chat_stream(req.session_id, req.message, req.client)
    full_text = ""
    for delta in stream:
        full_text += delta
    return ChatResponse(session_id=sid, reply=full_text, model=_engine._ai.model_name)


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """Streaming chat: returns newline-delimited JSON chunks.

    Each line is a JSON object:
      {"type": "delta", "content": "..."}      — text delta
      {"type": "done", "session_id": "..."}    — stream complete
      {"type": "error", "message": "..."}      — on failure
    """
    def generate():
        try:
            sid, stream = _engine.chat_stream(req.session_id, req.message, req.client)
            for delta in stream:
                yield json.dumps({"type": "delta", "content": delta}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done", "session_id": sid}, ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
