"""In-memory user accounts. There is no database in this assignment, so all
accounts reset when the server restarts. A4 replaces this with persistent storage.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .passwords import hash_password
from .roles import Role, role_for_email


@dataclass(frozen=True)
class User:
    id: str
    email: str
    password_hash: str
    role: Role
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EmailTakenError(Exception):
    pass


# Demo accounts available on every start. Test values only; see backend/README.md.
SEED_PASSWORD = "Queue$mart1"
SEED_EMAILS = ("admin@university.edu", "student@university.edu")


class UserStore:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        # FastAPI runs sync endpoints in a thread pool, so guard writes.
        self._lock = threading.Lock()

    def create(self, email: str, password: str) -> User:
        """Expects an already-validated, normalized email."""
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=hash_password(password),
            role=role_for_email(email),
        )
        with self._lock:
            if email in self._users:
                raise EmailTakenError(email)
            self._users[email] = user
        return user

    def get_by_email(self, email: str) -> User | None:
        return self._users.get(email)

    def get_by_id(self, user_id: str) -> User | None:
        return next((user for user in self._users.values() if user.id == user_id), None)

    def reset(self) -> None:
        """Clears every account and re-adds the demo accounts."""
        with self._lock:
            self._users.clear()
        for email in SEED_EMAILS:
            self.create(email, SEED_PASSWORD)


users = UserStore()
users.reset()
