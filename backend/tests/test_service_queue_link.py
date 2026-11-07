"""The Queue.service_id -> Service foreign key, and upgrading databases created before it existed."""

import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.auth.store import UserStore
from app.queue_store import QueueStore
from app.service_store import SEED_SERVICES, ServiceStore

START = datetime(2026, 11, 5, 9, tzinfo=UTC)
SCHEMA = (Path(__file__).resolve().parent.parent / "app" / "schema.sql").read_text(encoding="utf-8")


@contextmanager
def _connect(path) -> Iterator[sqlite3.Connection]:
    """A committed, closed connection (sqlite3's own context manager commits but never closes)."""
    with closing(sqlite3.connect(path)) as connection, connection:
        yield connection


def _queue_sql(path) -> str:
    with _connect(path) as connection:
        return connection.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'Queue'").fetchone()[0]


# ---------- The foreign key on a current database ----------


def test_queue_must_reference_an_existing_service(queue_store):
    assert "REFERENCES Service(service_id) ON DELETE RESTRICT" in _queue_sql(queue_store.database.path)

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        queue_store.set_status("no-such-service", "open")
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        with queue_store.database.connect() as connection:
            connection.execute("INSERT INTO Queue VALUES (?, 'no-such-service', 'open', ?)",
                               (str(uuid.uuid4()), START.isoformat()))


def test_service_with_a_queue_cannot_be_hard_deleted(queue_store, patient):
    queue_store.join("svc", "Test svc", 10, patient("a"))

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        with queue_store.database.connect() as connection:
            connection.execute("DELETE FROM Service WHERE service_id = 'svc'")
    assert queue_store.waiting_count("svc") == 1


def test_archiving_keeps_queue_history_linked_to_its_service(queue_store, patient):
    user = patient("a")
    queue_store.join("svc", "Test svc", 10, user)

    queue_store.services.archive("svc")
    queue_store.remove_service("svc")

    assert queue_store.services.get("svc") is None
    assert [visit.outcome for visit in queue_store.history.for_user(user)] == ["left"]
    with queue_store.database.connect() as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT status FROM Queue WHERE service_id = 'svc'").fetchone()[0] == "closed"


def test_upgrade_does_nothing_on_a_current_database(queue_store):
    assert queue_store.services.upgrade_queue_table() is False


# ---------- Upgrading a database from before the Service table ----------


def _legacy_database(path: Path) -> None:
    """The A4 schema as it was before services were stored: no Service table and no Queue foreign key."""
    legacy = re.sub(r"CREATE TABLE IF NOT EXISTS Service \(.*?\) STRICT;", "", SCHEMA, flags=re.DOTALL)
    legacy = re.sub(r"CREATE UNIQUE INDEX IF NOT EXISTS Service_active_name[^;]*;", "", legacy)
    legacy = legacy.replace(" REFERENCES Service(service_id) ON DELETE RESTRICT", "")
    assert "Service (" not in legacy and "REFERENCES Service" not in legacy
    with _connect(path) as connection:
        connection.executescript(legacy)


def _add_queue(path: Path, service_id: str, status: str = "open") -> str:
    queue_id = str(uuid.uuid4())
    with _connect(path) as connection:
        connection.execute("INSERT INTO Queue VALUES (?, ?, ?, ?)", (queue_id, service_id, status, START.isoformat()))
    return queue_id


def _add_entry(path: Path, queue_id: str, user_id: str, arrival: int, service_name: str, duration: int) -> None:
    with _connect(path) as connection:
        connection.execute(
            "INSERT INTO QueueEntry (entry_id, queue_id, user_id, arrival, ticket, position, joined_at, status, "
            "priority, finished_at, service_name, duration_minutes) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, 'waiting', 'normal', NULL, ?, ?)",
            (str(uuid.uuid4()), queue_id, user_id, arrival, f"T-{arrival:03d}", START.isoformat(), service_name, duration),
        )


@pytest.fixture
def legacy_path(tmp_path) -> Path:
    path = tmp_path / "legacy.sqlite3"
    _legacy_database(path)
    return path


def test_upgrade_adds_foreign_key_and_keeps_every_row(legacy_path):
    accounts = UserStore(legacy_path)  # opening any store adds the (empty) Service table
    first = accounts.create("first@x.edu", "Queue$mart1", "First").id
    second = accounts.create("second@x.edu", "Queue$mart1", "Second").id
    seeded_queue = _add_queue(legacy_path, "sick-visit")
    custom_queue = _add_queue(legacy_path, "made-in-memory", "closed")
    empty_queue = _add_queue(legacy_path, "never-used")
    _add_entry(legacy_path, seeded_queue, first, 1, "Sick Visit", 12)
    _add_entry(legacy_path, custom_queue, second, 2, "  Old Counseling  ", 25)
    assert "REFERENCES Service" not in _queue_sql(legacy_path)

    store = QueueStore(legacy_path)

    assert "REFERENCES Service(service_id) ON DELETE RESTRICT" in _queue_sql(legacy_path)
    with store.database.connect() as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        queues = {row["service_id"]: (row["queue_id"], row["status"])
                  for row in connection.execute("SELECT * FROM Queue").fetchall()}
        assert connection.execute("SELECT count(*) FROM QueueEntry").fetchone()[0] == 2
        stand_ins = {row["service_id"]: row for row in connection.execute(
            "SELECT * FROM Service WHERE deleted_at IS NOT NULL").fetchall()}
    # Same queues, same IDs and statuses.
    assert queues == {"sick-visit": (seeded_queue, "open"), "made-in-memory": (custom_queue, "closed"),
                      "never-used": (empty_queue, "open")}
    # Seeded services are real and active; queues whose service only lived in memory get archived stand-ins.
    assert [service.id for service in store.services.list()] == [seed[0] for seed in SEED_SERVICES]
    assert set(stand_ins) == {"made-in-memory", "never-used"}
    assert (stand_ins["made-in-memory"]["name"], stand_ins["made-in-memory"]["expected_duration_minutes"]) == (
        "Old Counseling", 25,
    )
    assert (stand_ins["never-used"]["name"], stand_ins["never-used"]["expected_duration_minutes"]) == ("never-used", 10)
    assert store.waiting_count("sick-visit") == 1


def test_upgraded_database_enforces_the_foreign_key_and_upgrades_once(legacy_path):
    store = QueueStore(legacy_path)

    assert store.services.upgrade_queue_table() is False
    assert QueueStore(legacy_path).services.upgrade_queue_table() is False
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        store.set_status("no-such-service", "open")


def test_upgrade_rolls_back_if_foreign_keys_would_break(legacy_path, monkeypatch):
    accounts = UserStore(legacy_path)
    user = accounts.create("first@x.edu", "Queue$mart1", "First").id
    queue_id = _add_queue(legacy_path, "sick-visit")
    _add_entry(legacy_path, queue_id, user, 1, "Sick Visit", 12)
    # Corrupt the legacy data: an entry pointing at a queue that doesn't exist.
    with _connect(legacy_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("UPDATE QueueEntry SET queue_id = ?", (str(uuid.uuid4()),))

    with pytest.raises(sqlite3.IntegrityError, match="Queue upgrade would break foreign keys"):
        ServiceStore(legacy_path).upgrade_queue_table()

    # Nothing changed: the old Queue table is still there with its row.
    assert "REFERENCES Service" not in _queue_sql(legacy_path)
    with _connect(legacy_path) as connection:
        assert connection.execute("SELECT count(*) FROM Queue").fetchone()[0] == 1
