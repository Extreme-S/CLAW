"""SQLite storage for sessions and messages."""

import sqlite3
import os
from datetime import datetime
from typing import Optional

from server.storage.models import new_session_id


class Database:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         TEXT PRIMARY KEY,
                title      TEXT DEFAULT '',
                client     TEXT DEFAULT 'desktop',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                model      TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, created_at);
        """)
        self._conn.commit()

    # ── Sessions ──

    def get_or_create_session(self, session_id: Optional[str], client: str = "desktop") -> str:
        if session_id:
            row = self._conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row:
                return row["id"]
        sid = session_id or new_session_id()
        self._conn.execute(
            "INSERT INTO sessions (id, client) VALUES (?, ?)", (sid, client)
        )
        self._conn.commit()
        return sid

    def list_sessions(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute("""
            SELECT s.*, COUNT(m.id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: str) -> bool:
        self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cur = self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def update_session_title(self, session_id: str, title: str):
        self._conn.execute(
            "UPDATE sessions SET title = ?, updated_at = datetime('now') WHERE id = ?",
            (title, session_id)
        )
        self._conn.commit()

    # ── Messages ──

    def save_message(self, session_id: str, role: str, content: str, model: str = ""):
        self._conn.execute(
            "INSERT INTO messages (session_id, role, content, model) VALUES (?, ?, ?, ?)",
            (session_id, role, content, model)
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?",
            (session_id,)
        )
        self._conn.commit()

    def get_messages(self, session_id: str, limit: int = 100) -> list[dict]:
        rows = self._conn.execute("""
            SELECT id, role, content, model, created_at
            FROM messages WHERE session_id = ?
            ORDER BY created_at ASC
            LIMIT ?
        """, (session_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_recent_messages(self, session_id: str, n: int = 20) -> list[dict]:
        """Get last N messages for context building."""
        rows = self._conn.execute("""
            SELECT role, content FROM (
                SELECT role, content, created_at FROM messages
                WHERE session_id = ? AND role != 'system'
                ORDER BY created_at DESC LIMIT ?
            ) ORDER BY created_at ASC
        """, (session_id, n)).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self._conn.close()
