import json
import os
import sqlite3
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.queue_store import AlreadyQueuedError, QueueStore

START = datetime(2026, 11, 5, 9, tzinfo=UTC)


def _count(store, table, where="1"):
    with store.database.connect() as connection:
        return connection.execute(f"SELECT count(*) FROM {table} WHERE {where}").fetchone()[0]


def test_queue_and_entries_survive_reopening_database(queue_store, patient):
    queue_store.set_status("svc", "open", START)
    a = queue_store.join("svc", "Service", 10, patient("a"), START)
    b = queue_store.join("svc", "Service", 10, patient("b"), START + timedelta(minutes=1))
    queue_store.set_priority("svc", b.id, "urgent")
    queue_store.serve_next("svc", START + timedelta(minutes=2))

    reopened = QueueStore(queue_store.database.path)

    assert reopened.status("svc") == "open"
    served = reopened.get(b.id)
    assert (served.status, served.position, served.priority) == ("served", None, "urgent")
    assert served.finished_at == START + timedelta(minutes=2)
    assert served.email == "b@x.edu"
    assert [u.kind for u in served.updates] == ["joined", "moved", "served"]
    waiting = reopened.waiting("svc")
    assert [(entry.id, entry.position, entry.joined_at) for entry in waiting] == [(a.id, 1, START)]
    assert [u.kind for u in waiting[0].updates] == ["joined", "delayed", "moved"]
    # Tickets keep counting from the saved arrivals.
    assert reopened.join("svc", "Service", 10, patient("c")).ticket == "S-003"


def test_queue_rows_store_the_required_fields(queue_store, patient):
    queue_store.set_status("svc", "closed", START)
    entry = queue_store.join("svc", "Service", 10, patient("a"), START)
    with queue_store.database.connect() as connection:
        queue = connection.execute("SELECT * FROM Queue WHERE service_id = 'svc'").fetchone()
        row = connection.execute("SELECT * FROM QueueEntry WHERE entry_id = ?", (entry.id,)).fetchone()
    assert uuid.UUID(queue["queue_id"]) and queue["created_at"] == START.isoformat()
    assert row["queue_id"] == queue["queue_id"] and row["user_id"] == patient("a")
    assert (row["position"], row["joined_at"], row["status"]) == (1, START.isoformat(), "waiting")


def test_set_status_keeps_queue_id_and_created_date(queue_store):
    queue_store.set_status("svc", "open", START)
    queue_store.set_status("svc", "closed", START + timedelta(days=1))
    with queue_store.database.connect() as connection:
        rows = connection.execute("SELECT status, created_at FROM Queue").fetchall()
    assert [tuple(row) for row in rows] == [("closed", START.isoformat())]
    assert queue_store.status("missing") == "closed"


def test_seed_creates_demo_queues_once_and_preserves_saved_changes(queue_store):
    queue_store.seed()
    assert [queue_store.status(s) for s in ("sick-visit", "flu-shot", "prescription-refill", "lab-work")] == [
        "open", "open", "open", "closed",
    ]
    assert queue_store.waiting_count("sick-visit") == 4
    queue_store.set_status("lab-work", "open")
    queue_store.serve_next("sick-visit")

    reopened = QueueStore(queue_store.database.path)
    reopened.seed()

    assert reopened.status("lab-work") == "open"
    assert reopened.waiting_count("sick-visit") == 3
    assert _count(reopened, "QueueEntry") == 6
    assert _count(reopened, "UserCredentials", "email LIKE '%.%@university.edu'") == 6


def test_reset_deletes_queues_and_entries_then_seeds(queue_store, patient):
    queue_store.join("svc", "Service", 10, patient("a"))
    queue_store.reset()
    assert queue_store.status("svc") == "closed"
    assert queue_store.current_for(patient("a")) is None
    assert _count(queue_store, "QueueEntry") == 6
    assert _count(queue_store, "Queue") == 4


def test_deleting_an_account_cascades_to_its_entries_and_updates(queue_store, patient):
    entry = queue_store.join("svc", "Service", 10, patient("a"))
    with queue_store.database.connect() as connection:
        connection.execute("DELETE FROM UserCredentials WHERE user_id = ?", (patient("a"),))
    assert queue_store.get(entry.id) is None
    assert _count(queue_store, "QueueEntryUpdate") == 0


def test_deleting_a_queue_cascades_to_its_entries(queue_store, patient):
    queue_store.join("svc", "Service", 10, patient("a"))
    with queue_store.database.connect() as connection:
        connection.execute("DELETE FROM Queue")
    assert _count(queue_store, "QueueEntry") == 0
    assert _count(queue_store, "QueueEntryUpdate") == 0


def test_removed_service_closes_its_queue_but_keeps_entries(queue_store, patient):
    queue_store.set_status("svc", "open")
    entry = queue_store.join("svc", "Service", 10, patient("a"))
    queue_store.remove_service("svc")
    assert queue_store.status("svc") == "closed"
    assert queue_store.get(entry.id).status == "left"


def _insert_entry(connection, queue_id, user_id, overrides=None, **fields):
    values = {
        "entry_id": str(uuid.uuid4()), "queue_id": queue_id, "user_id": user_id, "arrival": 100,
        "ticket": "S-100", "position": 1, "joined_at": START.isoformat(), "status": "waiting",
        "priority": "normal", "finished_at": None, "service_name": "Service", "duration_minutes": 10,
    }
    values.update(overrides or {}, **fields)
    connection.execute(
        f"INSERT INTO QueueEntry ({', '.join(values)}) VALUES ({', '.join('?' * len(values))})",
        tuple(values.values()),
    )


@pytest.mark.parametrize("overrides", [
    {"status": "canceled"}, {"status": "served"}, {"status": "served", "position": None},
    {"position": None}, {"position": 0}, {"finished_at": START.isoformat()},
    {"priority": "high"}, {"arrival": 0}, {"joined_at": None}, {"entry_id": "short"},
    {"duration_minutes": 0}, {"service_name": ""}, {"user_id": "missing-user"}, {"queue_id": "missing-queue"},
    # Wrong data types (STRICT tables), invalid timestamps and length limits.
    {"position": "first"}, {"position": 1.5}, {"arrival": "late"}, {"duration_minutes": "ten"},
    {"ticket": b"S-100"}, {"joined_at": "yesterday"}, {"joined_at": "2026-13-05T09:00:00+00:00"},
    {"ticket": "S"}, {"ticket": "S-" + "1" * 19}, {"service_name": "x" * 101}, {"duration_minutes": 481},
])
def test_entry_constraints_are_enforced_by_sqlite(queue_store, patient, overrides):
    queue_store.set_status("svc", "open")
    user_id = patient("a")
    with queue_store.database.connect() as connection:
        queue_id = connection.execute("SELECT queue_id FROM Queue").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError):
        with queue_store.database.connect() as connection:
            _insert_entry(connection, queue_id, user_id, overrides)
    assert _count(queue_store, "QueueEntry") == 0


def test_valid_finished_entry_is_accepted(queue_store, patient):
    queue_store.set_status("svc", "open")
    with queue_store.database.connect() as connection:
        queue_id = connection.execute("SELECT queue_id FROM Queue").fetchone()[0]
        _insert_entry(connection, queue_id, patient("a"), status="served", position=None,
                      finished_at=START.isoformat())
    assert _count(queue_store, "QueueEntry") == 1


def test_database_allows_one_waiting_entry_per_user_and_unique_arrivals(queue_store, patient):
    entry = queue_store.join("svc", "Service", 10, patient("a"))
    with pytest.raises(sqlite3.IntegrityError, match="QueueEntry.user_id"):
        with queue_store.database.connect() as connection:
            _insert_entry(connection, entry.queue_id, patient("a"))
    with pytest.raises(sqlite3.IntegrityError, match="QueueEntry.arrival"):
        with queue_store.database.connect() as connection:
            _insert_entry(connection, entry.queue_id, patient("b"), arrival=entry.arrival)


@pytest.mark.parametrize(("column", "value"), [
    ("queue_id", "short"), ("service_id", ""), ("service_id", "x" * 101), ("service_id", b"svc"),
    ("status", "paused"), ("created_at", None), ("created_at", "not a date"),
])
def test_queue_constraints_are_enforced_by_sqlite(queue_store, column, value):
    values = {"queue_id": str(uuid.uuid4()), "service_id": "svc", "status": "open", "created_at": START.isoformat()}
    values[column] = value
    with pytest.raises(sqlite3.IntegrityError):
        with queue_store.database.connect() as connection:
            connection.execute("INSERT INTO Queue VALUES (?, ?, ?, ?)", tuple(values.values()))
    queue_store.set_status("svc", "open")
    with pytest.raises(sqlite3.IntegrityError, match="Queue.service_id"):
        with queue_store.database.connect() as connection:
            connection.execute("INSERT INTO Queue VALUES (?, 'svc', 'open', ?)", (str(uuid.uuid4()), START.isoformat()))


def test_concurrent_joins_get_distinct_positions_and_tickets(queue_store, patient):
    users = [patient(name) for name in "abcdefgh"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        entries = list(pool.map(lambda user_id: queue_store.join("svc", "Service", 10, user_id), users))
    assert sorted(entry.position for entry in entries) == list(range(1, 9))
    assert len({entry.ticket for entry in entries}) == 8


def test_concurrent_joins_by_one_user_create_one_entry(queue_store, patient):
    user_id = patient("a")

    def join(_):
        try:
            return queue_store.join("svc", "Service", 10, user_id)
        except AlreadyQueuedError:
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(join, range(4)))
    assert sum(result is not None for result in results) == 1
    assert _count(queue_store, "QueueEntry") == 1


def test_failed_change_rolls_back_and_sends_no_notifications(queue_store, patient):
    with queue_store.database.connect() as connection:
        connection.executescript("""
            CREATE TRIGGER reject_update BEFORE INSERT ON QueueEntryUpdate
            BEGIN SELECT RAISE(ABORT, 'Simulated update failure'); END;
        """)
    with pytest.raises(sqlite3.IntegrityError, match="Simulated update failure"):
        queue_store.join("svc", "Service", 10, patient("a"))
    assert _count(queue_store, "QueueEntry") == 0
    assert queue_store.notifications.for_user(patient("a")) == []


@pytest.mark.parametrize(("column", "value"), [
    ("update_id", 0), ("update_id", "one"), ("kind", "left"), ("message", ""), ("message", "x" * 201),
    ("at", None), ("at", "soon"),
])
def test_update_constraints_are_enforced_by_sqlite(queue_store, patient, column, value):
    entry = queue_store.join("svc", "Service", 10, patient("a"))
    values = {"entry_id": entry.id, "update_id": 2, "kind": "moved", "message": "Moved.", "at": START.isoformat()}
    values[column] = value
    with pytest.raises(sqlite3.IntegrityError):
        with queue_store.database.connect() as connection:
            connection.execute("INSERT INTO QueueEntryUpdate VALUES (?, ?, ?, ?, ?)", tuple(values.values()))
    with pytest.raises(sqlite3.IntegrityError, match="QueueEntryUpdate"):
        with queue_store.database.connect() as connection:
            connection.execute("INSERT INTO QueueEntryUpdate VALUES (?, 1, 'moved', 'Duplicate.', ?)",
                               (entry.id, START.isoformat()))
    assert len(queue_store.get(entry.id).updates) == 1


def test_entry_lookups_bind_parameters(queue_store, patient):
    queue_store.join("svc", "Service", 10, patient("a"))
    assert queue_store.get("' OR 1=1 --") is None
    assert queue_store.current_for("' OR 1=1 --") is None
    assert queue_store.waiting("' OR 1=1 --") == []


def test_queue_and_status_survive_a_new_backend_process(client):
    def login(email):
        token = client.post("/api/auth/login", json={"email": email, "password": "Queue$mart1"}).json()["token"]
        return {"Authorization": f"Bearer {token}"}

    admin, student = login("admin@university.edu"), login("student@university.edu")
    client.patch("/api/services/lab-work/status", headers=admin, json={"status": "open"})
    joined = client.post("/api/queues/flu-shot/join", headers=student).json()
    code = """
import json
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    def login(email):
        token = client.post('/api/auth/login', json={'email': email, 'password': 'Queue$mart1'}).json()['token']
        return {'Authorization': 'Bearer ' + token}
    me = client.get('/api/queues/me', headers=login('student@university.edu')).json()
    services = client.get('/api/services', headers=login('admin@university.edu')).json()
    print(json.dumps({'me': me, 'status': {s['id']: s['status'] for s in services}}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
        env=os.environ.copy(), capture_output=True, text=True, check=True, timeout=30,
    )
    saved = json.loads(result.stdout)
    assert saved["me"] == joined
    assert saved["status"]["lab-work"] == "open"
