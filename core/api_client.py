"""HTTP client for communicating with the OpenClaw server."""

from __future__ import annotations
import json
from typing import Iterator
import httpx


class OpenClawClient:
    """Thin client for the OpenClaw server API."""

    def __init__(self, server_url: str, token: str, timeout: float = 60.0):
        self._base = server_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._timeout = timeout

    def health(self) -> dict:
        r = httpx.get(
            f"{self._base}/api/v1/health",
            headers=self._headers,
            timeout=5.0,
        )
        r.raise_for_status()
        return r.json()

    def chat_stream(self, message: str, session_id: str | None = None, client: str = "desktop") -> tuple[list, Iterator[str]]:
        """
        Send a chat message and stream the response.
        Returns (result, delta_iterator) where result is a single-element list.
        After exhausting the iterator, result[0] contains the session_id.
        """
        body = {"message": message, "client": client}
        if session_id:
            body["session_id"] = session_id

        result = [session_id or ""]

        def _stream() -> Iterator[str]:
            with httpx.stream(
                "POST",
                f"{self._base}/api/v1/chat/stream",
                json=body,
                headers=self._headers,
                timeout=self._timeout,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if data["type"] == "delta":
                        yield data["content"]
                    elif data["type"] == "done":
                        result[0] = data.get("session_id", result[0])
                    elif data["type"] == "error":
                        raise RuntimeError(data["message"])

        return result, _stream()

    def get_sessions(self) -> list[dict]:
        r = httpx.get(
            f"{self._base}/api/v1/sessions",
            headers=self._headers,
            timeout=10.0,
        )
        r.raise_for_status()
        return r.json()

    def get_history(self, session_id: str) -> list[dict]:
        r = httpx.get(
            f"{self._base}/api/v1/sessions/{session_id}/history",
            headers=self._headers,
            timeout=10.0,
        )
        r.raise_for_status()
        return r.json()

    def delete_session(self, session_id: str) -> bool:
        r = httpx.delete(
            f"{self._base}/api/v1/sessions/{session_id}",
            headers=self._headers,
            timeout=10.0,
        )
        return r.status_code == 200
