"""Pydantic models for API request/response."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
import uuid


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


# ── Request models ──

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    client: str = "desktop"


# ── Response models ──

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    model: str = ""


class SessionInfo(BaseModel):
    id: str
    title: str
    client: str
    created_at: str
    updated_at: str
    message_count: int = 0


class MessageInfo(BaseModel):
    id: int
    role: str
    content: str
    model: str
    created_at: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
