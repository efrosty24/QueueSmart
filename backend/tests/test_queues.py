from datetime import UTC, datetime, timedelta

import pytest

from app.queue_store import AlreadyQueuedError, NotQueuedError, QueueStore, queues


def _login(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": "Queue$mart1"})
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _register(client, email):
    response = client.post("/api/auth/register", json={"email": email, "password": "Queue$mart1"})
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture
def admin_headers(client):
    return _login(client, "admin@university.edu")


@pytest.fixture
def patient_headers(client):
    return _login(client, "student@university.edu")


def _emails(client, headers, service_id="prescription-refill"):
    return [entry["email"] for entry in client.get(f"/api/queues/{service_id}", headers=headers).json()]


# --- Store: ordering ---------------------------------------------------------

def test_line_follows_arrival_order():
    store = QueueStore()
    start = datetime(2026, 10, 20, 9, tzinfo=UTC)
    for minute, name in enumerate(["a", "b", "c"]):
        store.join("svc", "Service", 10, name, f"{name}@x.edu", start + timedelta(minutes=minute))

    assert [entry.user_id for entry in store.waiting("svc")] == ["a", "b", "c"]
    assert [entry.position for entry in store.waiting("svc")] == [1, 2, 3]


def test_arrival_counter_breaks_ties_when_join_times_match():
    store = QueueStore()
    same_time = datetime(2026, 10, 20, 9, tzinfo=UTC)
    for name in ["a", "b", "c"]:
        store.join("svc", "Service", 10, name, f"{name}@x.edu", same_time)

    assert [entry.user_id for entry in store.waiting("svc")] == ["a", "b", "c"]


def test_urgent_entries_go_first_then_arrival_order():
    store = QueueStore()
    entries = {name: store.join("svc", "Service", 10, name, f"{name}@x.edu") for name in ["a", "b", "c", "d"]}

    store.set_priority("svc", entries["d"].id, "urgent")
    store.set_priority("svc", entries["c"].id, "urgent")

    # c and d are both urgent, so c (who arrived first) stays ahead of d.
    assert [entry.user_id for entry in store.waiting("svc")] == ["c", "d", "a", "b"]
    store.set_priority("svc", entries["c"].id, "normal")
    assert [entry.user_id for entry in store.waiting("svc")] == ["d", "a", "b", "c"]


def test_serve_next_takes_the_front_and_moves_everyone_up():
    store = QueueStore()
    for name in ["a", "b", "c"]:
        store.join("svc", "Service", 10, name, f"{name}@x.edu")

    served = store.serve_next("svc")

    assert served.user_id == "a" and served.status == "served" and served.position is None
    assert [(entry.user_id, entry.position) for entry in store.waiting("svc")] == [("b", 1), ("c", 2)]


def test_serve_next_on_empty_line_returns_none():
    assert QueueStore().serve_next("svc") is None


def test_queues_are_separate_per_service():
    store = QueueStore()
    store.join("one", "One", 10, "a", "a@x.edu")
    store.join("two", "Two", 10, "b", "b@x.edu")

    store.serve_next("one")

    assert store.waiting_count("one") == 0
    assert store.waiting_count("two") == 1


def test_store_rejects_second_active_entry_and_leaving_twice():
    store = QueueStore()
    store.join("svc", "Service", 10, "a", "a@x.edu")

    with pytest.raises(AlreadyQueuedError):
        store.join("other", "Other", 10, "a", "a@x.edu")
    store.leave("a")
    with pytest.raises(NotQueuedError):
        store.leave("a")


def test_set_priority_rejects_unknown_or_finished_entries():
    store = QueueStore()
    entry = store.join("svc", "Service", 10, "a", "a@x.edu")

    with pytest.raises(KeyError):
        store.set_priority("other", entry.id, "urgent")
    store.serve_next("svc")
    with pytest.raises(KeyError):
        store.set_priority("svc", entry.id, "urgent")


def test_position_changes_are_announced():
    store = QueueStore()
    a, b, c = (store.join("svc", "Service", 10, name, f"{name}@x.edu") for name in ["a", "b", "c"])
    d = store.join("svc", "Service", 10, "d", "d@x.edu")

    store.set_priority("svc", d.id, "urgent")  # d jumps ahead; a, b, c move back
    store.serve_next("svc")                    # d served; a, b, c move up again

    assert [u.kind for u in a.updates] == ["joined", "delayed", "moved"]
    assert a.updates[1].message == "The queue order changed, so you moved back to position 2."
    assert [u.message for u in b.updates][-1] == "You're almost up. Head to the clinic now."
    assert [u.message for u in c.updates][-1] == "You moved up to position 3."
    assert [u.kind for u in d.updates] == ["joined", "moved", "served"]


def test_seeded_demo_patients_wait_in_arrival_order():
    assert [entry.email for entry in queues.waiting("sick-visit")] == [
        "jordan.lee@university.edu", "casey.kim@university.edu", "morgan.diaz@university.edu", "riley.chen@university.edu",
    ]
    assert queues.waiting_count("flu-shot") == 2


# --- API: patients -----------------------------------------------------------

def test_patient_joins_at_the_back_with_a_wait_estimate(client, patient_headers):
    response = client.post("/api/queues/sick-visit/join", headers=patient_headers)

    assert response.status_code == 201
    entry = response.json()
    assert entry["serviceId"] == "sick-visit"
    assert entry["serviceName"] == "Sick Visit"
    assert entry["email"] == "student@university.edu"
    assert entry["status"] == "waiting"
    assert entry["priority"] == "normal"
    assert entry["position"] == 5
    assert entry["peopleAhead"] == 4
    assert entry["estimatedWaitMinutes"] == 48
    assert entry["ticket"].startswith("S-")
    assert entry["updates"][0]["kind"] == "joined"
    assert entry["updates"][0]["message"] == "You joined the Sick Visit queue at position 5."
    assert client.get("/api/queues/me", headers=patient_headers).json() == entry


def test_joining_updates_the_service_count_and_estimate(client, patient_headers):
    client.post("/api/queues/prescription-refill/join", headers=patient_headers)

    service = next(s for s in client.get("/api/services", headers=patient_headers).json() if s["id"] == "prescription-refill")
    assert service["queueLength"] == 1
    assert service["estimatedWaitMinutes"] == 6


def test_my_queue_is_null_before_joining(client, patient_headers):
    response = client.get("/api/queues/me", headers=patient_headers)

    assert response.status_code == 200
    assert response.json() is None


def test_patient_cannot_join_two_queues(client, patient_headers):
    client.post("/api/queues/sick-visit/join", headers=patient_headers)
    response = client.post("/api/queues/flu-shot/join", headers=patient_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "You already have an active queue. Leave it before joining another service."
    assert queues.waiting_count("flu-shot") == 2


def test_cannot_join_a_closed_service(client, patient_headers):
    response = client.post("/api/queues/lab-work/join", headers=patient_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "This clinic queue is closed."
    assert queues.waiting_count("lab-work") == 0


def test_cannot_join_an_unknown_service(client, patient_headers):
    response = client.post("/api/queues/missing/join", headers=patient_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Service not found."


def test_patient_leaves_and_people_behind_move_up(client, admin_headers, patient_headers):
    client.post("/api/queues/prescription-refill/join", headers=patient_headers)
    other = _register(client, "other@university.edu")
    client.post("/api/queues/prescription-refill/join", headers=other)

    response = client.delete("/api/queues/me", headers=patient_headers)

    assert response.status_code == 204
    assert client.get("/api/queues/me", headers=patient_headers).json() is None
    assert _emails(client, admin_headers) == ["other@university.edu"]
    moved = client.get("/api/queues/me", headers=other).json()
    assert moved["position"] == 1
    assert moved["updates"][0]["message"] == "You're next in line."


def test_leaving_without_a_queue_returns_404(client, patient_headers):
    response = client.delete("/api/queues/me", headers=patient_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "You're not waiting in a queue."


def test_patient_can_rejoin_after_leaving_at_the_back(client, admin_headers, patient_headers):
    client.post("/api/queues/flu-shot/join", headers=patient_headers)
    client.delete("/api/queues/me", headers=patient_headers)

    response = client.post("/api/queues/flu-shot/join", headers=patient_headers)

    assert response.status_code == 201
    assert response.json()["position"] == 3


def test_served_entry_stays_visible_until_next_join(client, admin_headers, patient_headers):
    client.post("/api/queues/prescription-refill/join", headers=patient_headers)
    client.post("/api/queues/prescription-refill/serve-next", headers=admin_headers)

    served = client.get("/api/queues/me", headers=patient_headers).json()
    assert served["status"] == "served"
    assert served["position"] is None
    assert served["estimatedWaitMinutes"] == 0
    assert served["updates"][0]["kind"] == "served"
    assert client.delete("/api/queues/me", headers=patient_headers).status_code == 404

    rejoined = client.post("/api/queues/flu-shot/join", headers=patient_headers)
    assert rejoined.status_code == 201
    assert client.get("/api/queues/me", headers=patient_headers).json()["serviceId"] == "flu-shot"


def test_queue_endpoints_require_sign_in(client):
    assert client.get("/api/queues/me").status_code == 401
    assert client.delete("/api/queues/me").status_code == 401
    assert client.post("/api/queues/sick-visit/join").status_code == 401


# --- API: admins -------------------------------------------------------------

def test_admin_views_queue_front_first(client, admin_headers):
    response = client.get("/api/queues/sick-visit", headers=admin_headers)

    assert response.status_code == 200
    line = response.json()
    assert [entry["position"] for entry in line] == [1, 2, 3, 4]
    assert [entry["estimatedWaitMinutes"] for entry in line] == [0, 12, 24, 36]
    assert line[0]["email"] == "jordan.lee@university.edu"


def test_admin_serves_next_in_arrival_order(client, admin_headers, patient_headers):
    client.post("/api/queues/prescription-refill/join", headers=patient_headers)
    other = _register(client, "other@university.edu")
    client.post("/api/queues/prescription-refill/join", headers=other)

    response = client.post("/api/queues/prescription-refill/serve-next", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["served"]["email"] == "student@university.edu"
    assert body["served"]["status"] == "served"
    assert [entry["email"] for entry in body["queue"]] == ["other@university.edu"]
    assert body["queue"][0]["position"] == 1


def test_serve_next_on_empty_queue(client, admin_headers):
    response = client.post("/api/queues/prescription-refill/serve-next", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == {"served": None, "queue": []}


def test_admin_can_still_serve_a_closed_service(client, admin_headers):
    client.patch("/api/services/sick-visit/status", headers=admin_headers, json={"status": "closed"})

    response = client.post("/api/queues/sick-visit/serve-next", headers=admin_headers)

    assert response.json()["served"]["email"] == "jordan.lee@university.edu"


def test_urgent_patient_is_served_before_earlier_arrivals(client, admin_headers, patient_headers):
    joined = client.post("/api/queues/sick-visit/join", headers=patient_headers).json()

    response = client.patch(f"/api/queues/sick-visit/entries/{joined['id']}", headers=admin_headers,
                            json={"priority": "urgent"})

    assert response.status_code == 200
    assert response.json()[0]["email"] == "student@university.edu"
    assert response.json()[0]["priority"] == "urgent"
    me = client.get("/api/queues/me", headers=patient_headers).json()
    assert me["position"] == 1
    assert me["updates"][0]["message"] == "You're next in line."
    served = client.post("/api/queues/sick-visit/serve-next", headers=admin_headers).json()["served"]
    assert served["email"] == "student@university.edu"
    # Everyone else keeps arrival order.
    assert _emails(client, admin_headers, "sick-visit")[0] == "jordan.lee@university.edu"


@pytest.mark.parametrize("body", [{}, {"priority": "high"}, {"priority": 1}, {"priority": "urgent", "position": 1}])
def test_priority_validation(client, admin_headers, body):
    entry_id = queues.waiting("sick-visit")[0].id

    response = client.patch(f"/api/queues/sick-visit/entries/{entry_id}", headers=admin_headers, json=body)

    assert response.status_code == 422
    assert queues.waiting("sick-visit")[0].priority == "normal"


def test_priority_for_unknown_entry_returns_404(client, admin_headers):
    response = client.patch("/api/queues/sick-visit/entries/missing", headers=admin_headers, json={"priority": "urgent"})

    assert response.status_code == 404
    assert response.json()["detail"] == "That patient isn't waiting in this queue."


@pytest.mark.parametrize(("method", "path"), [
    ("GET", "/api/queues/missing"),
    ("POST", "/api/queues/missing/serve-next"),
    ("PATCH", "/api/queues/missing/entries/x"),
])
def test_admin_actions_on_unknown_service_return_404(client, admin_headers, method, path):
    response = client.request(method, path, headers=admin_headers, json={"priority": "urgent"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Service not found."


@pytest.mark.parametrize(("method", "path"), [
    ("GET", "/api/queues/sick-visit"),
    ("POST", "/api/queues/sick-visit/serve-next"),
    ("PATCH", "/api/queues/sick-visit/entries/x"),
])
def test_admin_actions_require_admin_and_leave_queue_unchanged(client, patient_headers, method, path):
    before = [entry.id for entry in queues.waiting("sick-visit")]

    assert client.request(method, path, json={"priority": "urgent"}).status_code == 401
    assert client.request(method, path, headers=patient_headers, json={"priority": "urgent"}).status_code == 403
    assert [entry.id for entry in queues.waiting("sick-visit")] == before


def test_deleting_a_service_removes_its_waiting_patients(client, admin_headers, patient_headers):
    client.post("/api/queues/sick-visit/join", headers=patient_headers)

    client.delete("/api/services/sick-visit", headers=admin_headers)

    assert queues.waiting_count("sick-visit") == 0
    assert client.get("/api/queues/me", headers=patient_headers).json() is None
    assert client.post("/api/queues/flu-shot/join", headers=patient_headers).status_code == 201


def test_served_entry_keeps_its_name_after_service_is_deleted(client, admin_headers, patient_headers):
    client.post("/api/queues/prescription-refill/join", headers=patient_headers)
    client.post("/api/queues/prescription-refill/serve-next", headers=admin_headers)

    client.delete("/api/services/prescription-refill", headers=admin_headers)

    me = client.get("/api/queues/me", headers=patient_headers).json()
    assert me["serviceName"] == "Prescription Refill"
    assert me["expectedDurationMinutes"] == 6
