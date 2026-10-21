from datetime import UTC, datetime, timedelta

import pytest

from app.history_store import HistoryStore
from app.queue_store import NotQueuedError, QueueStore


def login(client, email="student@university.edu"):
    response = client.post("/api/auth/login", json={"email": email, "password": "Queue$mart1"})
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_history_records_completion_and_actual_elapsed_wait_once():
    store = QueueStore()
    start = datetime(2026, 10, 21, 9, tzinfo=UTC)
    entry = store.join("svc", "Clinic visit", 20, "patient", "p@x.edu", start)
    assert store.history.for_user("patient") == []
    store.serve_next("svc", start + timedelta(minutes=7, seconds=30))
    visits = store.history.for_user("patient")
    assert len(visits) == 1
    assert visits[0].id == entry.id and visits[0].outcome == "served"
    assert visits[0].waited_minutes == 7
    assert visits[0].finished_at == start + timedelta(minutes=7, seconds=30)
    assert store.serve_next("svc") is None
    assert store.history.for_user("patient") == visits


def test_left_history_survives_rejoin_and_is_ordered_by_completion():
    store = QueueStore()
    start = datetime(2026, 10, 21, 9, tzinfo=UTC)
    first = store.join("one", "First service", 10, "patient", "p@x.edu", start)
    store.leave("patient", start + timedelta(minutes=2))
    with pytest.raises(NotQueuedError):
        store.leave("patient")
    second = store.join("two", "Second service", 5, "patient", "p@x.edu", start + timedelta(minutes=3))
    store.serve_next("two", start + timedelta(minutes=4))
    visits = store.history.for_user("patient")
    assert [visit.id for visit in visits] == [second.id, first.id]
    assert [visit.outcome for visit in visits] == ["served", "left"]
    assert store.history.for_user("other") == []


def test_service_deletion_records_every_waiting_patient():
    store = QueueStore()
    for name in ("a", "b", "c"):
        store.join("deleted", "Deleted clinic service", 10, name, f"{name}@x.edu")
    store.remove_service("deleted")
    store.remove_service("deleted")
    for name in ("a", "b", "c"):
        visits = store.history.for_user(name)
        assert len(visits) == 1
        assert visits[0].outcome == "left"
        assert visits[0].service_name == "Deleted clinic service"
    store.reset()
    assert store.history.for_user("a") == []


def test_history_store_deduplicates_and_clamps_negative_elapsed_time():
    store = HistoryStore()
    now = datetime(2026, 10, 21, tzinfo=UTC)
    fields = dict(entry_id="entry", user_id="patient", ticket="S-1", service_id="svc",
                  service_name="Clinic", joined_at=now, finished_at=now - timedelta(seconds=1))
    first = store.record(**fields, outcome="left")
    assert first.waited_minutes == 0
    assert store.record(**fields, outcome="served") == first
    assert len(store.for_user("patient")) == 1
    store.reset()
    assert store.for_user("patient") == []


def test_history_api_tracks_visits_without_client_recording_and_survives_new_login(client):
    patient = login(client)
    admin = login(client, "admin@university.edu")
    assert client.get("/api/history", headers=patient).json() == []
    joined = client.post("/api/queues/prescription-refill/join", headers=patient).json()
    assert client.get("/api/history", headers=patient).json() == []
    client.post("/api/queues/prescription-refill/serve-next", headers=admin)
    # This student never polled /queues/me to observe completion.
    served = client.get("/api/history", headers=login(client)).json()
    assert len(served) == 1
    assert served[0]["id"] == joined["id"]
    assert served[0]["outcome"] == "served"
    assert served[0]["serviceName"] == "Prescription Refill"
    assert served[0]["joinedAt"] == joined["joinedAt"]
    assert "finishedAt" in served[0] and "userId" not in served[0] and "email" not in served[0]
    second = client.post("/api/queues/flu-shot/join", headers=patient).json()
    client.delete("/api/queues/me", headers=patient)
    visits = client.get("/api/history", headers=patient).json()
    assert [visit["id"] for visit in visits] == [second["id"], joined["id"]]
    assert [visit["outcome"] for visit in visits] == ["left", "served"]
    assert client.get("/api/history", headers=patient).json() == visits
    assert client.get("/api/history", headers=admin).json() == []


def test_deleted_service_name_stays_in_api_history(client):
    patient = login(client)
    admin = login(client, "admin@university.edu")
    client.post("/api/queues/prescription-refill/join", headers=patient)
    client.delete("/api/services/prescription-refill", headers=admin)
    visit = client.get("/api/history", headers=patient).json()[0]
    assert visit["serviceName"] == "Prescription Refill"
    assert visit["outcome"] == "left"


def test_history_is_isolated_even_when_another_user_id_is_submitted(client):
    patient = login(client)
    client.post("/api/queues/prescription-refill/join", headers=patient)
    client.delete("/api/queues/me", headers=patient)
    other = client.post("/api/auth/register", json={"email": "other@university.edu", "password": "Queue$mart1"}).json()
    other_headers = {"Authorization": f"Bearer {other['token']}"}
    assert client.get("/api/history?userId=student", headers=other_headers).json() == []
    assert len(client.get(f"/api/history?userId={other['user']['id']}", headers=patient).json()) == 1
    assert client.post("/api/history", headers=patient, json={"outcome": "served"}).status_code == 405


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_history_requires_authentication(client, headers):
    assert client.get("/api/history", headers=headers).status_code == 401
