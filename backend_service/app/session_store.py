"""Simple in-memory session store."""
from __future__ import annotations

from threading import RLock
from typing import Dict, List


class SessionStore:
    """Thread-safe in-memory store for chat histories."""

    def __init__(self) -> None:
        self._sessions: Dict[str, List[dict]] = {}
        self._lock = RLock()

    def create_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.setdefault(session_id, [])

    def append_entry(self, session_id: str, entry: dict) -> None:
        with self._lock:
            history = self._sessions.setdefault(session_id, [])
            history.append(entry)

    def get_history(self, session_id: str) -> List[dict]:
        with self._lock:
            return list(self._sessions.get(session_id, []))


session_store = SessionStore()
