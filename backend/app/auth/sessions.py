"""Sign-in sessions, kept in memory and valid for 7 days.

The client gets a random token and sends it back as "Authorization: Bearer <token>".
The server only keeps a SHA-256 hash of each token, so tokens can't be lifted
from server memory and replayed.
"""

import hashlib
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

SESSION_LIFETIME = timedelta(days=7)


@dataclass(frozen=True)
class Session:
    user_id: str
    expires_at: datetime


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, user_id: str, now: datetime | None = None) -> tuple[str, Session]:
        """Starts a session and returns (token, session). The token is only shown here."""
        token = secrets.token_urlsafe(32)
        session = Session(user_id=user_id, expires_at=(now or _now()) + SESSION_LIFETIME)
        with self._lock:
            self._sessions[_digest(token)] = session
        return token, session

    def get(self, token: str, now: datetime | None = None) -> Session | None:
        """Returns the live session for a token, dropping it if it has expired."""
        key = _digest(token)
        session = self._sessions.get(key)
        if session and session.expires_at <= (now or _now()):
            self.revoke(token)
            return None
        return session

    def revoke(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(_digest(token), None)

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()


sessions = SessionStore()
