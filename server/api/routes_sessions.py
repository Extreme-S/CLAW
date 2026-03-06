"""Session management endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from server.storage.models import SessionInfo, MessageInfo
from server.api.middleware import verify_token

router = APIRouter(prefix="/sessions", dependencies=[Depends(verify_token)])

# Database reference, set by main.py
_db = None


def set_db(db):
    global _db
    _db = db


@router.get("", response_model=list[SessionInfo])
async def list_sessions():
    rows = _db.list_sessions()
    return [SessionInfo(**r) for r in rows]


@router.get("/{session_id}/history", response_model=list[MessageInfo])
async def get_history(session_id: str):
    msgs = _db.get_messages(session_id)
    if not msgs:
        raise HTTPException(404, "Session not found or empty")
    return [MessageInfo(**m) for m in msgs]


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    ok = _db.delete_session(session_id)
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"ok": True}
