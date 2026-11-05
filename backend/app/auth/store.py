"""Persistent credentials and one-to-one user profiles in SQLite."""

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ..database import Database, database_path
from .passwords import hash_password
from .roles import Role, role_for_email
from .schemas import ProfileDetails
from .validation import validate_email, validate_new_password


@dataclass(frozen=True)
class User:
    id: str
    email: str
    password_hash: str
    role: Role
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    email: str
    full_name: str
    contact_info: str | None
    preferences: str | None


class EmailTakenError(Exception):
    pass


SEED_PASSWORD = "Queue$mart1"
SEED_EMAILS = ("admin@university.edu", "student@university.edu")
SEED_NAMES = ("Clinic Administrator", "Demo Student")


def _to_user(row: sqlite3.Row | None) -> User | None:
    if row is None:
        return None
    return User(
        id=row["user_id"], email=row["email"], password_hash=row["password_hash"],
        role=Role(row["role"]), created_at=datetime.fromisoformat(row["created_at"]),
    )


_PROFILE_QUERY = """
    SELECT c.user_id, p.email, p.full_name, p.contact_info, p.preferences
    FROM UserProfile AS p JOIN UserCredentials AS c ON c.email = p.email
    WHERE c.user_id = ?
"""


class UserStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.database = Database(path if path is not None else database_path())

    def create(
        self, email: str, password: str, full_name: str,
        contact_info: str | None = None, preferences: str | None = None,
    ) -> User:
        email = validate_email(email)
        validate_new_password(password)
        profile = ProfileDetails(full_name=full_name, contact_info=contact_info, preferences=preferences)
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=hash_password(password),
            role=role_for_email(email),
        )
        try:
            # Both records commit together; a failed profile insert rolls back the account.
            with self.database.connect() as connection:
                connection.execute(
                    "INSERT INTO UserCredentials (user_id, email, password_hash, role, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user.id, user.email, user.password_hash, user.role.value, user.created_at.isoformat()),
                )
                connection.execute(
                    "INSERT INTO UserProfile (email, full_name, contact_info, preferences) VALUES (?, ?, ?, ?)",
                    (user.email, profile.full_name, profile.contact_info or None, profile.preferences or None),
                )
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE":
                raise EmailTakenError(email) from None
            raise
        return user

    def get_by_email(self, email: str) -> User | None:
        with self.database.connect() as connection:
            return _to_user(connection.execute(
                "SELECT * FROM UserCredentials WHERE email = ?", (email.strip().lower(),),
            ).fetchone())

    def get_by_id(self, user_id: str) -> User | None:
        with self.database.connect() as connection:
            return _to_user(connection.execute(
                "SELECT * FROM UserCredentials WHERE user_id = ?", (user_id,),
            ).fetchone())

    def get_profile(self, user_id: str) -> UserProfile | None:
        with self.database.connect() as connection:
            row = connection.execute(_PROFILE_QUERY, (user_id,)).fetchone()
            return UserProfile(**dict(row)) if row else None

    def update_profile(
        self, user_id: str, full_name: str,
        contact_info: str | None = None, preferences: str | None = None,
    ) -> UserProfile | None:
        profile = ProfileDetails(full_name=full_name, contact_info=contact_info, preferences=preferences)
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE UserProfile SET full_name = ?, contact_info = ?, preferences = ? "
                "WHERE email = (SELECT email FROM UserCredentials WHERE user_id = ?)",
                (profile.full_name, profile.contact_info or None, profile.preferences or None, user_id),
            )
            row = connection.execute(_PROFILE_QUERY, (user_id,)).fetchone()
            return UserProfile(**dict(row)) if row else None

    def seed(self) -> None:
        """Insert missing demo accounts without overwriting any saved data."""
        for email, full_name in zip(SEED_EMAILS, SEED_NAMES):
            if self.get_by_email(email) is None:
                try:
                    self.create(email, SEED_PASSWORD, full_name)
                except EmailTakenError:
                    # Another process may have seeded it while this process was starting.
                    pass

    def reset(self) -> None:
        """Test helper: delete accounts (cascading to profiles), then seed demos."""
        with self.database.connect() as connection:
            connection.execute("DELETE FROM UserCredentials")
        self.seed()


users = UserStore()
users.seed()
