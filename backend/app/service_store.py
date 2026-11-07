"""Persistent clinic services in SQLite (Assignment 4).

A service's details (name, description, expected duration, priority) live in the
Service table. Its open/closed availability is its Queue row's status (queue_store).
Deleting a service archives it so past queue activity still points at a real row.
"""

import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .database import Database, database_path

Priority = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ServiceRecord:
    id: str
    name: str
    description: str
    expected_duration_minutes: int
    priority: Priority
    created_at: datetime
    updated_at: datetime


class DuplicateServiceNameError(Exception):
    pass


# Demo services added to a new database. IDs are stable so seeded queues and the
# frontend's service icons can refer to them.
SEED_SERVICES: tuple[tuple[str, str, str, int, Priority], ...] = (
    ("sick-visit", "Sick Visit", "Meet with clinic staff about a new health concern.", 12, "high"),
    ("flu-shot", "Flu Shot", "Visit the campus clinic for your seasonal flu vaccination.", 5, "low"),
    ("prescription-refill", "Prescription Refill", "Talk with clinic staff about an existing prescription.", 6, "medium"),
    ("lab-work", "Lab Work", "Sample collection and testing requested by your clinic provider.", 10, "medium"),
)

# Archived stand-in for a queue whose service only existed in memory before A4 (see upgrade).
_LEGACY_DESCRIPTION = "Service saved before services were stored in the database."

_COLUMNS = "service_id, name, description, expected_duration_minutes, priority, created_at, updated_at"


def _record(row: sqlite3.Row) -> ServiceRecord:
    return ServiceRecord(
        id=row["service_id"], name=row["name"], description=row["description"],
        expected_duration_minutes=row["expected_duration_minutes"], priority=row["priority"],
        created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _is_duplicate_name(error: sqlite3.IntegrityError) -> bool:
    return "Service.name" in str(error)


class ServiceStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.database = Database(path if path is not None else database_path())

    def list(self) -> list[ServiceRecord]:
        """Active services, oldest first (seeded services keep their seed order)."""
        with self.database.connect() as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM Service WHERE deleted_at IS NULL ORDER BY created_at, rowid",
            ).fetchall()
        return [_record(row) for row in rows]

    def get(self, service_id: str) -> ServiceRecord | None:
        """An active service, or None if it doesn't exist or was deleted."""
        with self.database.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM Service WHERE service_id = ? AND deleted_at IS NULL", (service_id,),
            ).fetchone()
        return _record(row) if row else None

    def create(self, name: str, description: str, expected_duration_minutes: int, priority: Priority,
               *, service_id: str | None = None, now: datetime | None = None) -> ServiceRecord:
        now = now or datetime.now(UTC)
        service_id = service_id or str(uuid4())
        try:
            with self.database.connect() as connection:
                connection.execute(
                    f"INSERT INTO Service ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (service_id, name, description, expected_duration_minutes, priority, now.isoformat(), now.isoformat()),
                )
        except sqlite3.IntegrityError as error:
            if _is_duplicate_name(error):
                raise DuplicateServiceNameError(name) from None
            raise
        return self.get(service_id)

    def update(self, service_id: str, name: str, description: str, expected_duration_minutes: int,
               priority: Priority, *, now: datetime | None = None) -> ServiceRecord | None:
        """Changes an active service's details. Returns None if there is no such service."""
        now = now or datetime.now(UTC)
        try:
            with self.database.connect() as connection:
                changed = connection.execute(
                    "UPDATE Service SET name = ?, description = ?, expected_duration_minutes = ?, priority = ?, "
                    "updated_at = ? WHERE service_id = ? AND deleted_at IS NULL",
                    (name, description, expected_duration_minutes, priority, now.isoformat(), service_id),
                ).rowcount
        except sqlite3.IntegrityError as error:
            if _is_duplicate_name(error):
                raise DuplicateServiceNameError(name) from None
            raise
        return self.get(service_id) if changed else None

    def archive(self, service_id: str, *, now: datetime | None = None) -> bool:
        """Hides an active service from listings. The row stays for past queue activity."""
        now = now or datetime.now(UTC)
        with self.database.connect() as connection:
            changed = connection.execute(
                "UPDATE Service SET deleted_at = ?, updated_at = ? WHERE service_id = ? AND deleted_at IS NULL",
                (now.isoformat(), now.isoformat(), service_id),
            ).rowcount
        return changed == 1

    def reset(self) -> None:
        """Test helper: deletes every queue (cascading to entries and activity) and service, then seeds."""
        with self.database.connect() as connection:
            connection.execute("DELETE FROM Queue")
            connection.execute("DELETE FROM Service")
        self.seed()

    def upgrade_queue_table(self, now: datetime | None = None) -> bool:
        """Adds the Queue.service_id -> Service foreign key to a database created before the
        Service table existed. Returns True if an upgrade ran. Safe to call on any database.

        SQLite can't add a foreign key to an existing table, so this follows SQLite's
        documented rebuild: create the new table, copy rows, drop the old one, rename.
        Every queue first gets a Service row: seeded services are added, and any other
        queue gets an archived stand-in named from its most recent entry.
        """
        with self.database.connect() as connection:
            table = connection.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'Queue'").fetchone()
        if "REFERENCES Service" in table["sql"]:
            return False

        now = now or datetime.now(UTC)
        self.seed(now)
        with self.database.connect() as connection:
            orphans = connection.execute("""
                SELECT q.service_id,
                       (SELECT e.service_name FROM QueueEntry e WHERE e.queue_id = q.queue_id
                        ORDER BY e.arrival DESC LIMIT 1) AS name,
                       (SELECT e.duration_minutes FROM QueueEntry e WHERE e.queue_id = q.queue_id
                        ORDER BY e.arrival DESC LIMIT 1) AS duration
                FROM Queue q
                WHERE NOT EXISTS (SELECT 1 FROM Service s WHERE s.service_id = q.service_id)
            """).fetchall()
            connection.executemany(
                f"INSERT INTO Service ({_COLUMNS}, deleted_at) VALUES (?, ?, ?, ?, 'medium', ?, ?, ?)",
                [(row["service_id"], " ".join((row["name"] or "").split())[:100].strip() or row["service_id"],
                  _LEGACY_DESCRIPTION, row["duration"] or 10, now.isoformat(), now.isoformat(), now.isoformat())
                 for row in orphans],
            )

        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        create_queue = re.search(r"CREATE TABLE IF NOT EXISTS Queue \(.*?\) STRICT;", schema, re.DOTALL).group(0)
        # Foreign keys must be off while the table is swapped, and that can't change inside a transaction.
        connection = sqlite3.connect(self.database.path, timeout=10, isolation_level=None)
        try:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(create_queue.replace("EXISTS Queue (", "EXISTS Queue_upgrade (", 1))
            connection.execute("INSERT INTO Queue_upgrade SELECT queue_id, service_id, status, created_at FROM Queue")
            connection.execute("DROP TABLE Queue")
            connection.execute("ALTER TABLE Queue_upgrade RENAME TO Queue")
            problems = connection.execute("PRAGMA foreign_key_check").fetchall()
            if problems:
                connection.execute("ROLLBACK")
                raise sqlite3.IntegrityError(f"Queue upgrade would break foreign keys: {problems}")
            connection.execute("COMMIT")
        finally:
            connection.close()
        return True

    def seed(self, now: datetime | None = None) -> None:
        """Adds missing demo services. Saved services (including edited or archived seeds) are never overwritten."""
        now = (now or datetime.now(UTC)).isoformat()
        with self.database.connect() as connection:
            connection.executemany(
                f"INSERT OR IGNORE INTO Service ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(*seed, now, now) for seed in SEED_SERVICES],
            )
