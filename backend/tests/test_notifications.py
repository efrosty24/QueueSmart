from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.queue_store import AlreadyQueuedError, QueueStore, queues


def login(client, email="student@university.edu"):
    response = client.post("/api/auth/login", json={"email": email, "password": "Queue$mart1"})
    return {"Authorization": f"Bearer {response.json()['token']}"}


def register(client, email):
    response = client.post("/api/auth/register", json={"email": email, "password": "Queue$mart1"})
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_join_triggers_notification_and_close_alert_for_short_queue():
    store = QueueStore()
    entry = store.join("svc", "Clinic service", 10, "student", "student@x.edu")
    items = store.notifications.for_user("student")
    assert [item.kind for item in items] == ["almost-ready", "joined"]
    assert items[1].entry_id == entry.id
    assert items[1].ticket == entry.ticket
    assert "Clinic service" in items[1].message
    assert not any(item.read for item in items)
    assert store.notifications.for_user("someone-else") == []


def test_close_notification_when_serve_or_leave_moves_patient_to_position_two():
    store = QueueStore()
    for name in ("a", "b", "c", "d"):
        store.join("svc", "Clinic", 10, name, f"{name}@x.edu")
    assert [item.kind for item in store.notifications.for_user("c")] == ["joined"]
    store.serve_next("svc")
    assert store.notifications.for_user("c")[0].kind == "almost-ready"
    store.leave("b")
    assert store.notifications.for_user("d")[0].kind == "almost-ready"
    # Serving the next person doesn't repeat the position-2 alert at position 1.
    store.serve_next("svc")
    assert sum(item.kind == "almost-ready" for item in store.notifications.for_user("d")) == 1


def test_priority_jump_to_front_triggers_close_alert_without_repeated_reads():
    store = QueueStore()
    for name in ("a", "b", "c"):
        entry = store.join("svc", "Clinic", 10, name, f"{name}@x.edu")
    store.set_priority("svc", entry.id, "urgent")
    assert store.notifications.for_user("c")[0].kind == "almost-ready"
    before = store.notifications.for_user("c")
    store.set_priority("svc", entry.id, "urgent")
    assert store.notifications.for_user("c") == before
    with pytest.raises(AlreadyQueuedError):
        store.join("other", "Other", 5, "c", "c@x.edu")
    assert store.notifications.for_user("c") == before


def test_notifications_remain_after_leaving_and_joining_again(client):
    headers = login(client)
    assert client.get("/api/notifications", headers=headers).json() == []
    first = client.post("/api/queues/prescription-refill/join", headers=headers).json()
    client.delete("/api/queues/me", headers=headers)
    client.post("/api/queues/flu-shot/join", headers=headers)
    items = client.get("/api/notifications", headers=headers).json()
    first_items = [item for item in items if item["entryId"] == first["id"]]
    assert {item["kind"] for item in first_items} == {"joined", "almost-ready", "left"}
    assert "userId" not in first_items[0]
    assert client.get("/api/notifications", headers=headers).json() == items


def test_serve_triggers_notification_for_patient_without_browser_polling(client):
    patient = login(client)
    admin = login(client, "admin@university.edu")
    client.post("/api/queues/prescription-refill/join", headers=patient)
    client.post("/api/queues/prescription-refill/serve-next", headers=admin)
    items = client.get("/api/notifications", headers=patient).json()
    assert items[0]["kind"] == "served"
    assert items[0]["category"] == "status"
    assert items[0]["serviceName"] == "Prescription Refill"


def test_notification_read_state_persists_between_sessions_and_is_user_scoped(client):
    headers = login(client)
    other = register(client, "other@university.edu")
    client.post("/api/queues/prescription-refill/join", headers=headers)
    notification_id = client.get("/api/notifications", headers=headers).json()[0]["id"]
    path = f"/api/notifications/{notification_id}/read"
    assert client.get("/api/notifications", headers=other).json() == []
    assert client.patch(path, headers=other, json={"read": True}).status_code == 404
    assert client.patch(path, headers=headers, json={"read": True}).json()["read"] is True
    assert client.get("/api/notifications", headers=login(client)).json()[0]["read"] is True
    assert client.patch(path, headers=headers, json={"read": False}).json()["read"] is False
    assert client.post("/api/notifications/read-all", headers=other).status_code == 204
    assert client.get("/api/notifications", headers=headers).json()[0]["read"] is False
    assert client.post("/api/notifications/read-all", headers=headers).status_code == 204
    assert all(item["read"] for item in client.get("/api/notifications", headers=headers).json())
    assert client.post("/api/notifications/read-all", headers=headers).status_code == 204


@pytest.mark.parametrize("body", [{}, {"read": "true"}, {"read": 1}, {"read": None},
                                   {"read": []}, {"read": True, "userId": "other"}])
def test_read_validation_rejects_invalid_input_without_changes(client, body):
    headers = login(client)
    client.post("/api/queues/prescription-refill/join", headers=headers)
    before = client.get("/api/notifications", headers=headers).json()
    response = client.patch(f"/api/notifications/{before[0]['id']}/read", headers=headers, json=body)
    assert response.status_code == 422
    assert "errors" in response.json()
    assert client.get("/api/notifications", headers=headers).json() == before


@pytest.mark.parametrize("notification_id", ["bad-id", "x" * 500, "123"])
def test_notification_id_format_and_length(client, notification_id):
    response = client.patch(f"/api/notifications/{notification_id}/read", headers=login(client), json={"read": True})
    assert response.status_code == 422


def test_valid_unknown_notification_is_not_found(client):
    response = client.patch(f"/api/notifications/{uuid4()}/read", headers=login(client), json={"read": True})
    assert response.status_code == 404


@pytest.mark.parametrize("method,path,body", [
    ("get", "/api/notifications", None),
    ("post", "/api/notifications/read-all", None),
    ("patch", f"/api/notifications/{uuid4()}/read", {"read": True}),
])
def test_notification_routes_require_authentication(client, method, path, body):
    kwargs = {"json": body} if body is not None else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401
    assert getattr(client, method)(path, headers={"Authorization": "Bearer invalid"}, **kwargs).status_code == 401


def test_reset_removes_notifications_and_read_state():
    queues.join("svc", "Clinic", 10, "student", "student@x.edu", datetime(2026, 10, 21, tzinfo=UTC))
    queues.reset()
    assert queues.notifications.for_user("student") == []
