import json
import os
import sqlite3
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.auth.passwords import hash_password
from app.auth.store import EmailTakenError, UserStore
from app.database import database_path


@pytest.fixture
def store(tmp_path):
    return UserStore(tmp_path / "nested" / "accounts.sqlite3")


def test_database_path_can_be_configured_or_defaulted(monkeypatch, tmp_path):
    monkeypatch.setenv("QUEUESMART_DATABASE_PATH", str(tmp_path / "configured.sqlite3"))
    assert database_path() == tmp_path / "configured.sqlite3"
    monkeypatch.delenv("QUEUESMART_DATABASE_PATH")
    assert database_path() == Path(__file__).resolve().parents[1] / "data" / "queuesmart.sqlite3"


def test_credentials_and_profile_survive_reopening_database(store):
    user = store.create("  New@University.edu ", "Queue$mart1", "New Student", "555-0100", "Phone")
    reopened = UserStore(store.database.path)
    assert reopened.get_by_id(user.id) == user
    assert reopened.get_by_email("NEW@university.edu") == user
    profile = reopened.get_profile(user.id)
    assert profile.email == user.email
    assert profile.contact_info == "555-0100"
    assert profile.preferences == "Phone"
    assert user.password_hash not in ("Queue$mart1", "")


def test_login_and_profile_survive_a_new_backend_process(client):
    registered = client.post("/api/auth/register", json={
        "email": "persisted@university.edu", "password": "Queue$mart1", "full_name": "Persisted Student",
    }).json()
    client.put("/api/auth/profile", headers={"Authorization": f"Bearer {registered['token']}"}, json={
        "full_name": "Saved Name", "contact_info": "555-0100", "preferences": "Phone",
    })
    code = """
import json
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    response = client.post('/api/auth/login', json={'email': 'persisted@university.edu', 'password': 'Queue$mart1'})
    assert response.status_code == 200, response.text
    auth = response.json()
    profile = client.get('/api/auth/profile', headers={'Authorization': 'Bearer ' + auth['token']})
    print(json.dumps({'user': auth['user'], 'profile': profile.json()}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
        env=os.environ.copy(), capture_output=True, text=True, check=True, timeout=30,
    )
    saved = json.loads(result.stdout)
    assert saved["user"] == registered["user"]
    assert saved["profile"]["full_name"] == "Saved Name"
    assert saved["profile"]["contact_info"] == "555-0100"
    assert saved["profile"]["preferences"] == "Phone"


def test_seed_preserves_saved_accounts_and_profiles(store):
    store.seed()
    admin = store.get_by_email("admin@university.edu")
    store.update_profile(admin.id, "Saved Administrator", "555-0100", "Phone")
    new = store.create("new@university.edu", "Queue$mart1", "New Student")
    reopened = UserStore(store.database.path)
    reopened.seed()
    assert reopened.get_by_id(admin.id) == admin
    assert reopened.get_profile(admin.id).full_name == "Saved Administrator"
    assert reopened.get_by_id(new.id) == new


def test_concurrent_seed_handles_an_account_created_by_another_process(store, monkeypatch):
    store.seed()
    # Simulate a stale lookup: another process inserted each demo after our SELECT.
    monkeypatch.setattr(store, "get_by_email", lambda email: None)
    store.seed()
    with store.database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM UserCredentials").fetchone()[0] == 2


def test_concurrent_registration_enforces_unique_email(store):
    def create():
        try:
            return store.create("same@university.edu", "Queue$mart1", "Student")
        except EmailTakenError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert sum(result is not None for result in results) == 1
    with store.database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM UserCredentials").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM UserProfile").fetchone()[0] == 1


def test_failed_profile_insert_rolls_back_credentials(store):
    with store.database.connect() as connection:
        connection.executescript("""
            CREATE TRIGGER reject_profile BEFORE INSERT ON UserProfile
            BEGIN SELECT RAISE(ABORT, 'Simulated profile failure'); END;
        """)
    with pytest.raises(sqlite3.IntegrityError, match="Simulated profile failure"):
        store.create("rollback@university.edu", "Queue$mart1", "Student")
    assert store.get_by_email("rollback@university.edu") is None


def test_foreign_key_rejects_orphans_and_delete_cascades(store):
    with pytest.raises(sqlite3.IntegrityError):
        with store.database.connect() as connection:
            connection.execute("INSERT INTO UserProfile (email, full_name) VALUES (?, ?)", ("orphan@uni.edu", "Orphan"))
    user = store.create("linked@university.edu", "Queue$mart1", "Student")
    with store.database.connect() as connection:
        connection.execute("DELETE FROM UserCredentials WHERE user_id = ?", (user.id,))
        assert connection.execute("SELECT count(*) FROM UserProfile").fetchone()[0] == 0
    assert store.get_profile(user.id) is None
    assert store.update_profile(user.id, "Missing") is None


@pytest.mark.parametrize(("column", "value"), [
    ("user_id", "invalid-id"), ("email", ""), ("email", "a" * 255),
    ("email", "UPPER@university.edu"), ("email", " user@university.edu "),
    ("password_hash", "Plaintext!1"), ("role", "superuser"), ("created_at", None),
])
def test_credentials_constraints_are_enforced_by_sqlite(store, column, value):
    values = {"user_id": str(uuid.uuid4()), "email": "valid@university.edu", "password_hash": hash_password("Queue$mart1"),
              "role": "patient", "created_at": "2026-11-05T12:00:00+00:00"}
    values[column] = value
    with pytest.raises(sqlite3.IntegrityError):
        with store.database.connect() as connection:
            connection.execute(
                "INSERT INTO UserCredentials (user_id, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                tuple(values.values()),
            )


@pytest.mark.parametrize(("full_name", "contact_info", "preferences"), [
    (None, None, None), ("", None, None), ("   ", None, None), ("x" * 101, None, None),
    ("Student", "x" * 101, None), ("Student", None, "x" * 1001),
])
def test_profile_constraints_are_enforced_by_sqlite(store, full_name, contact_info, preferences):
    user = store.create("student@uni.edu", "Queue$mart1", "Student")
    with pytest.raises(sqlite3.IntegrityError):
        with store.database.connect() as connection:
            connection.execute(
                "UPDATE UserProfile SET full_name = ?, contact_info = ?, preferences = ? WHERE email = ?",
                (full_name, contact_info, preferences, user.email),
            )
    assert store.get_profile(user.id).full_name == "Student"


def test_database_rejects_duplicate_credentials_and_profiles(store):
    user = store.create("student@uni.edu", "Queue$mart1", "Student")
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed: UserCredentials.email"):
        with store.database.connect() as connection:
            connection.execute(
                "INSERT INTO UserCredentials SELECT ?, email, password_hash, role, created_at FROM UserCredentials",
                (str(uuid.uuid4()),),
            )
    with pytest.raises(sqlite3.IntegrityError):
        with store.database.connect() as connection:
            connection.execute("INSERT INTO UserProfile (email, full_name) VALUES (?, ?)", (user.email, "Duplicate"))


def test_database_lookups_bind_parameters(store):
    user = store.create("student@uni.edu", "Queue$mart1", "Student")
    assert store.get_by_id("' OR 1=1 --") is None
    assert store.get_by_email("' OR 1=1 --") is None
    assert store.get_by_id(user.id) == user


def test_reset_cascades_to_profiles(store):
    user = store.create("temporary@university.edu", "Queue$mart1", "Temporary")
    store.reset()
    assert store.get_by_id(user.id) is None
    assert store.get_profile(user.id) is None
    with store.database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM UserProfile").fetchone()[0] == 2
