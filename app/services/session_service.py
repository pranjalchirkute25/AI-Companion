"""
In-memory session service maintaining capped session history server-side.
Provides reflection state tracking, TTL cleanup, and memory boundary constraints.
"""

import time
import uuid
from typing import Any

from app.config import get_settings


class SessionService:
    """Manages active Socratic thinking sessions with size caps and TTL eviction."""

    def __init__(self, max_history: int = 10, session_ttl_seconds: int = 86400):
        self._sessions: dict[str, dict[str, Any]] = {}
        self._max_history = max_history
        self._session_ttl = session_ttl_seconds

    def create_or_update_session(
        self,
        session_id: str | None,
        intake_data: dict[str, Any],
        initial_analysis: dict[str, Any] | None = None,
    ) -> str:
        """Initializes a new session or updates an existing one with intake data."""
        sid = session_id.strip() if session_id and session_id.strip() else str(uuid.uuid4())

        now = time.time()
        if sid in self._sessions:
            self._sessions[sid]["last_accessed"] = now
            self._sessions[sid]["intake_data"] = intake_data
            if initial_analysis:
                self._sessions[sid]["initial_analysis"] = initial_analysis
        else:
            self._sessions[sid] = {
                "session_id": sid,
                "created_at": now,
                "last_accessed": now,
                "intake_data": intake_data,
                "initial_analysis": initial_analysis,
                "reflection_steps": [],
                "confirmed_assumptions": [],
                "acknowledged_conflicts": [],
                "open_questions": [],
                "user_notes": "",
            }

        self._cleanup_stale_sessions()
        return sid

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieves session data by ID, updating last accessed time."""
        if not session_id or session_id not in self._sessions:
            return None

        session = self._sessions[session_id]
        if time.time() - session["last_accessed"] > self._session_ttl:
            self._sessions.pop(session_id, None)
            return None

        session["last_accessed"] = time.time()
        return session

    def add_reflection_step(
        self,
        session_id: str,
        question: str,
        user_answer: str,
        response_data: dict[str, Any],
    ) -> int:
        """Appends a reflection step to the session history while enforcing size cap."""
        session = self.get_session(session_id)
        if not session:
            # Create stub session if not found
            self.create_or_update_session(
                session_id=session_id,
                intake_data={"decision_description": "", "drawing_factors": ""},
            )
            session = self.get_session(session_id)

        step_record = {
            "step": len(session["reflection_steps"]) + 1,
            "question": question,
            "answer": user_answer,
            "response": response_data,
            "timestamp": time.time(),
        }

        session["reflection_steps"].append(step_record)

        # Enforce server-side history size cap (keep newest entries)
        if len(session["reflection_steps"]) > self._max_history:
            session["reflection_steps"] = session["reflection_steps"][-self._max_history:]

        session["last_accessed"] = time.time()
        return len(session["reflection_steps"])

    def update_reasoning_map_state(
        self,
        session_id: str,
        confirmed_assumptions: list[str],
        acknowledged_conflicts: list[str],
        open_questions: list[str],
        user_notes: str | None = None,
    ) -> None:
        """Updates user's confirmed acknowledgments for Reasoning Map export."""
        session = self.get_session(session_id)
        if not session:
            self.create_or_update_session(
                session_id=session_id,
                intake_data={"decision_description": "", "drawing_factors": ""},
            )
            session = self.get_session(session_id)

        session["confirmed_assumptions"] = confirmed_assumptions
        session["acknowledged_conflicts"] = acknowledged_conflicts
        session["open_questions"] = open_questions
        if user_notes is not None:
            session["user_notes"] = user_notes
        session["last_accessed"] = time.time()

    def _cleanup_stale_sessions(self) -> None:
        """Removes sessions older than TTL."""
        now = time.time()
        stale_keys = [
            sid
            for sid, sdata in self._sessions.items()
            if now - sdata.get("last_accessed", 0) > self._session_ttl
        ]
        for sid in stale_keys:
            self._sessions.pop(sid, None)

    def clear(self) -> None:
        """Clears all sessions (useful for tests)."""
        self._sessions.clear()


_session_instance: SessionService | None = None


def get_session_service() -> SessionService:
    """Singleton getter for SessionService."""
    global _session_instance
    if _session_instance is None:
        settings = get_settings()
        _session_instance = SessionService(
            max_history=settings.MAX_SESSION_HISTORY,
            session_ttl_seconds=settings.SESSION_TTL_SECONDS,
        )
    return _session_instance
