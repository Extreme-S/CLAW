"""Chat engine — multi-turn conversation with context management."""

from __future__ import annotations
from typing import Iterator

from server.storage.database import Database
from server.core.ai_router import AIRouter

SYSTEM_PROMPT = (
    "你是 CLAW（Cognitive Learning & Automated Wisdom），一个赛博风格的 AI 私人助手。"
    "你性格沉稳、高效、偶尔带点幽默。回答简洁精准。用中文交流。"
)

MAX_CONTEXT_MESSAGES = 20


class ChatEngine:
    def __init__(self, db: Database, ai_router: AIRouter):
        self._db = db
        self._ai = ai_router

    def chat_stream(
        self, session_id: str | None, message: str, client: str = "desktop"
    ) -> tuple[str, Iterator[str]]:
        """
        Process a chat message and return (session_id, delta_iterator).
        The iterator yields text deltas. After exhausting the iterator,
        both user message and full AI reply are persisted.
        """
        sid = self._db.get_or_create_session(session_id, client)

        # Save user message
        self._db.save_message(sid, "user", message)

        # Build context
        context = self._build_context(sid, message)

        # Stream AI response
        def _stream() -> Iterator[str]:
            full_text = ""
            for delta in self._ai.stream(context):
                full_text += delta
                yield delta
            # Persist AI reply
            self._db.save_message(sid, "assistant", full_text, self._ai.model_name)
            # Auto-generate session title from first message
            if not self._get_session_title(sid):
                title = message[:30] + ("..." if len(message) > 30 else "")
                self._db.update_session_title(sid, title)

        return sid, _stream()

    def _build_context(self, session_id: str, current_message: str) -> list[dict]:
        """Assemble: system prompt + recent history (user message already saved)."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Load recent conversation (includes the just-saved user message)
        recent = self._db.get_recent_messages(session_id, MAX_CONTEXT_MESSAGES)
        messages.extend(recent)

        return messages

    def _get_session_title(self, session_id: str) -> str:
        sessions = self._db.list_sessions(limit=100)
        for s in sessions:
            if s["id"] == session_id:
                return s.get("title", "")
        return ""
