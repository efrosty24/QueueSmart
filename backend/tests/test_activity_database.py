"""A4 Part 6: real SQLite persistence, constraints, ownership and atomic queue changes."""

import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.history_store import HistoryStore
from app.notification_store import NotificationStore
from app.queue_store import QueueStore

START = datetime(2026, 11, 6, 9, tzinfo=UTC)


def test_activity_survives_reopening_and_read_status_is_preserved(queue_store, patient):
    user_id = patient("a")
    entry = queue_store.join("svc", "Campus clinic", 10, user_id, START)
    queue_store.serve_next("svc", START + timedelta(minutes=8))
    notification = queue_store.notifications.for_user(user_id)[0]
    queue_store.notifications.mark_read(user_id, notification.id, True)
    expected_notifications = queue_store.notifications.for_user(user_id)
    expected_history = queue_store.history.for_user(user_id)

    for _ in range(2):
        reopened = QueueStore(queue_store.database.path)
        assert reopened.notifications.for_user(user_id) == expected_notifications
        assert reopened.history.for_user(user_id) == expected_history
    assert expected_history[0].id == entry.id
    assert expected_history[0].waited_minutes == 8
    assert expected_notifications[0].read is True
    # Separate store instances also retrieve the same persisted data.
    assert NotificationStore(queue_store.database.path).for_user(user_id) == expected_notifications
    assert HistoryStore(queue_store.database.path).for_user(user_id) == expected_history
    with queue_store.database.connect() as connection:
        row = connection.execute("SELECT * FROM Notification WHERE notification_id = ?", (notification.id,)).fetchone()
        assert row["status"] == "viewed" and row["user_id"] == user_id
    reopened.notifications.mark_read(user_id, notification.id, False)
    assert queue_store.notifications.for_user(user_id)[0].read is False
    reopened.notifications.mark_all_read(user_id)
    assert all(item.read for item in queue_store.notifications.for_user(user_id))


def test_existing_queue_activity_is_backfilled_once(queue_store, patient):
    user_id = patient("a")
    queue_store.join("one", "First clinic", 10, user_id, START)
    queue_store.leave(user_id, START + timedelta(minutes=2))
    queue_store.join("two", "Second clinic", 5, user_id, START + timedelta(minutes=3))
    queue_store.serve_next("two", START + timedelta(minutes=5))
    # Simulate the previous A4 database: queue rows persisted, activity tables empty.
    queue_store.notifications.reset()
    queue_store.history.reset()
    reopened = QueueStore(queue_store.database.path)
    visits = reopened.history.for_user(user_id)
    notifications = reopened.notifications.for_user(user_id)
    assert [visit.outcome for visit in visits] == ["served", "left"]
    assert {item.kind for item in notifications} == {"joined", "almost-ready", "served", "left"}
    reopened.notifications.mark_all_read(user_id)
    again = QueueStore(queue_store.database.path)
    assert again.history.for_user(user_id) == visits
    assert len(again.notifications.for_user(user_id)) == len(notifications)
    assert all(item.read for item in again.notifications.for_user(user_id))


def test_activity_remains_after_service_removal_but_cascades_on_account_deletion(queue_store, patient):
    user_id = patient("a")
    queue_store.join("svc", "Deleted clinic service", 5, user_id)
    queue_store.remove_service("svc")
    saved = QueueStore(queue_store.database.path)
    assert saved.history.for_user(user_id)[0].service_name == "Deleted clinic service"
    assert saved.notifications.for_user(user_id)[0].kind == "left"
    with saved.database.connect() as connection:
        connection.execute("DELETE FROM UserCredentials WHERE user_id = ?", (user_id,))
    assert saved.history.for_user(user_id) == []
    assert saved.notifications.for_user(user_id) == []


def test_activity_cascades_on_physical_queue_deletion(queue_store, patient):
    user_id = patient("a")
    queue_store.join("svc", "Clinic", 5, user_id)
    queue_store.leave(user_id)
    with queue_store.database.connect() as connection:
        connection.execute("DELETE FROM Queue")
    assert queue_store.notifications.for_user(user_id) == []
    assert queue_store.history.for_user(user_id) == []


def test_persisted_activity_is_account_scoped_and_queries_bind_parameters(queue_store, patient):
    a, b = patient("a"), patient("b")
    queue_store.join("svc", "Clinic", 5, a)
    queue_store.leave(a)
    note = queue_store.notifications.for_user(a)[0]
    with pytest.raises(KeyError):
        queue_store.notifications.mark_read(b, note.id, True)
    queue_store.notifications.mark_all_read(b)
    assert not any(item.read for item in queue_store.notifications.for_user(a))
    assert queue_store.notifications.for_user("' OR 1=1 --") == []
    assert queue_store.history.for_user("' OR 1=1 --") == []
    with pytest.raises(KeyError):
        queue_store.notifications.mark_read(a, "' OR 1=1 --", True)


@pytest.mark.parametrize("table,operation", [("Notification", "join"), ("History", "leave"),
                                            ("History", "serve"), ("Notification", "serve")])
def test_failed_activity_write_rolls_back_entire_queue_operation(queue_store, patient, table, operation):
    user_id = patient("a")
    if operation != "join":
        queue_store.join("svc", "Clinic", 5, user_id, START)
    entry_before = queue_store.current_for(user_id)
    notifications_before = queue_store.notifications.for_user(user_id)
    with queue_store.database.connect() as connection:
        connection.execute(f"CREATE TRIGGER reject_activity BEFORE INSERT ON {table} "
                           "BEGIN SELECT RAISE(ABORT, 'Activity write failed'); END")
    with pytest.raises(sqlite3.IntegrityError, match="Activity write failed"):
        if operation == "join":
            queue_store.join("svc", "Clinic", 5, user_id, START)
        elif operation == "leave":
            queue_store.leave(user_id, START + timedelta(minutes=1))
        else:
            queue_store.serve_next("svc", START + timedelta(minutes=1))
    assert queue_store.current_for(user_id) == entry_before
    assert queue_store.history.for_user(user_id) == []
    assert queue_store.notifications.for_user(user_id) == notifications_before


def test_concurrent_process_stores_create_one_history_and_completion_notification(queue_store, patient):
    user_id = patient("a")
    queue_store.join("svc", "Clinic", 5, user_id)
    stores = [QueueStore(queue_store.database.path) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        served = list(pool.map(lambda store: store.serve_next("svc"), stores))
    assert sum(entry is not None for entry in served) == 1
    assert len(queue_store.history.for_user(user_id)) == 1
    assert sum(note.kind == "served" for note in queue_store.notifications.for_user(user_id)) == 1


@pytest.fixture
def activity_entry(queue_store, patient):
    return queue_store.join("svc", "Campus clinic", 10, patient("a"), START)


def notification_values(entry):
    return dict(notification_id=str(uuid4()), user_id=entry.user_id, entry_id=entry.id,
                event_key=str(uuid4()), ticket=entry.ticket, service_id=entry.service_id,
                service_name=entry.service_name, kind="joined", category="status", title="Queue joined",
                message="You joined the clinic queue.", at=START.isoformat(), status="sent")


def history_values(entry):
    return dict(entry_id=entry.id, user_id=entry.user_id, ticket=entry.ticket, service_id=entry.service_id,
                service_name=entry.service_name, joined_at=START.isoformat(),
                finished_at=(START + timedelta(minutes=5)).isoformat(), outcome="served", waited_minutes=5)


def insert(connection, table, values):
    connection.execute(f"INSERT INTO {table} ({', '.join(values)}) VALUES ({', '.join('?' * len(values))})",
                       tuple(values.values()))


@pytest.mark.parametrize("column,value", [
    ("notification_id", None), ("notification_id", "short"), ("user_id", None),
    ("user_id", str(uuid4())), ("entry_id", str(uuid4())),
    ("event_key", None), ("event_key", ""), ("event_key", "x" * 101),
    ("ticket", ""), ("ticket", "x" * 21), ("service_id", ""), ("service_id", "x" * 101),
    ("service_name", "   "), ("service_name", "x" * 101), ("kind", "unknown"),
    ("category", "unknown"), ("kind", "moved"), ("title", ""), ("title", "x" * 101),
    ("message", None), ("message", "   "), ("message", "x" * 401),
    ("at", None), ("at", "tomorrow"), ("at", sqlite3.Binary(b"invalid")),
    ("status", None), ("status", "unread"), ("status", 3),
])
def test_notification_constraints_in_sqlite(queue_store, activity_entry, column, value):
    values = notification_values(activity_entry)
    values[column] = value
    with pytest.raises(sqlite3.IntegrityError):
        with queue_store.database.connect() as connection:
            insert(connection, "Notification", values)


@pytest.mark.parametrize("column,value", [
    ("entry_id", None), ("entry_id", str(uuid4())), ("user_id", None), ("user_id", str(uuid4())),
    ("ticket", ""), ("ticket", "x" * 21), ("service_id", ""), ("service_id", "x" * 101),
    ("service_name", "   "), ("service_name", "x" * 101), ("joined_at", None), ("joined_at", "yesterday"),
    ("finished_at", None), ("finished_at", "later"), ("outcome", None), ("outcome", "waiting"),
    ("waited_minutes", None), ("waited_minutes", -1), ("waited_minutes", 1.5), ("waited_minutes", "five"),
])
def test_history_constraints_in_sqlite(queue_store, activity_entry, column, value):
    values = history_values(activity_entry)
    values[column] = value
    with pytest.raises(sqlite3.IntegrityError):
        with queue_store.database.connect() as connection:
            insert(connection, "History", values)


@pytest.mark.parametrize("table", ["Notification", "History"])
def test_foreign_keys_reject_cross_account_activity(queue_store, patient, activity_entry, table):
    values = notification_values(activity_entry) if table == "Notification" else history_values(activity_entry)
    values["user_id"] = patient("other")
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        with queue_store.database.connect() as connection:
            insert(connection, table, values)


def test_database_boundaries_unique_events_and_one_history_per_entry(queue_store, activity_entry):
    note = notification_values(activity_entry)
    note.update(event_key="e" * 100, ticket="T" * 20, service_id="s" * 100, service_name="S" * 100,
                title="T" * 100, message="M" * 400, status="viewed")
    visit = history_values(activity_entry)
    visit.update(ticket="T" * 20, service_id="s" * 100, service_name="S" * 100, waited_minutes=0)
    with queue_store.database.connect() as connection:
        insert(connection, "Notification", note)
        insert(connection, "History", visit)
    for table, values in (("Notification", {**note, "notification_id": str(uuid4())}), ("History", visit)):
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            with queue_store.database.connect() as connection:
                insert(connection, table, values)


def test_store_deduplication_does_not_allow_another_user_to_claim_an_event(queue_store, patient, activity_entry):
    entry = activity_entry
    note = dict(user_id=entry.user_id, entry_id=entry.id, ticket=entry.ticket,
                service_id=entry.service_id, service_name=entry.service_name,
                kind="joined", message="Joined.", at=START, event_key="update:1")
    # Existing event ID returns the same record; it never clears its viewed state.
    first = queue_store.notifications.add(**note)
    queue_store.notifications.mark_read(entry.user_id, first.id, True)
    assert queue_store.notifications.add(**note).read is True
    with pytest.raises(sqlite3.IntegrityError, match="another account"):
        queue_store.notifications.add(**{**note, "user_id": patient("other")})
    visit = dict(entry_id=entry.id, user_id=entry.user_id, ticket=entry.ticket,
                 service_id=entry.service_id, service_name=entry.service_name,
                 joined_at=START, finished_at=START + timedelta(minutes=1), outcome="served")
    queue_store.history.record(**visit)
    with pytest.raises(sqlite3.IntegrityError, match="another account"):
        queue_store.history.record(**{**visit, "user_id": patient("other")})


def test_activity_survives_new_backend_process_and_updates_are_visible_to_parent(client):
    def login(email):
        result = client.post("/api/auth/login", json={"email": email, "password": "Queue$mart1"}).json()
        return {"Authorization": f"Bearer {result['token']}"}

    student, admin = login("student@university.edu"), login("admin@university.edu")
    client.post("/api/queues/prescription-refill/join", headers=student)
    client.post("/api/queues/prescription-refill/serve-next", headers=admin)
    client.post("/api/queues/flu-shot/join", headers=student)
    client.delete("/api/queues/me", headers=student)
    client.post("/api/notifications/read-all", headers=student)
    expected_history = client.get("/api/history", headers=student).json()
    expected_notifications = client.get("/api/notifications", headers=student).json()
    code = """
import json
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    auth = client.post('/api/auth/login', json={'email': 'student@university.edu', 'password': 'Queue$mart1'}).json()
    headers = {'Authorization': 'Bearer ' + auth['token']}
    history = client.get('/api/history', headers=headers).json()
    notifications = client.get('/api/notifications', headers=headers).json()
    client.patch('/api/notifications/' + notifications[0]['id'] + '/read', headers=headers, json={'read': False})
    print(json.dumps({'history': history, 'notifications': notifications}))
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                            env=os.environ.copy(), capture_output=True, text=True, check=True, timeout=30)
    saved = json.loads(result.stdout)
    assert saved["history"] == expected_history
    assert saved["notifications"] == expected_notifications
    assert client.get("/api/notifications", headers=student).json()[0]["read"] is False
