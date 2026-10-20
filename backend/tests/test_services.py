import pytest

from app.services import services


VALID_SERVICE = {
    "name": "Counseling",
    "description": "Talk with a campus counselor.",
    "expectedDurationMinutes": 30,
    "priority": "medium",
}


@pytest.fixture
def admin_headers(client):
    response = client.post("/api/auth/login", json={"email": "admin@university.edu", "password": "Queue$mart1"})
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture
def patient_headers(client):
    response = client.post("/api/auth/login", json={"email": "student@university.edu", "password": "Queue$mart1"})
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_patient_can_list_seed_services(client, patient_headers):
    response = client.get("/api/services", headers=patient_headers)

    assert response.status_code == 200
    assert len(response.json()) == 4
    service = response.json()[0]
    assert service["id"] == "sick-visit"
    assert service["expectedDurationMinutes"] == 12
    assert service["priority"] == "high"
    assert {item["id"]: item["estimatedWaitMinutes"] for item in response.json()} == {
        "sick-visit": 48, "flu-shot": 10, "prescription-refill": 0, "lab-work": 0,
    }


def test_admin_can_create_service_visible_to_patient(client, admin_headers, patient_headers):
    response = client.post("/api/services", headers=admin_headers, json={
        **VALID_SERVICE, "name": "  Counseling  ", "description": "  Talk with a campus counselor.  ",
    })

    assert response.status_code == 201
    created = response.json()
    assert created == {**VALID_SERVICE, "id": created["id"], "status": "closed", "queueLength": 0, "estimatedWaitMinutes": 0}
    assert created in client.get("/api/services", headers=patient_headers).json()


def test_update_changes_details_and_preserves_id_status_and_count(client, admin_headers):
    original = client.get("/api/services", headers=admin_headers).json()[0]
    response = client.put(f"/api/services/{original['id']}", headers=admin_headers, json=VALID_SERVICE)

    assert response.status_code == 200
    updated = response.json()
    assert updated == {
        **VALID_SERVICE, "id": original["id"], "status": "open", "queueLength": original["queueLength"],
        "estimatedWaitMinutes": 120,
    }
    assert updated in client.get("/api/services", headers=admin_headers).json()


def test_estimate_uses_current_queue_count(client, patient_headers):
    services["sick-visit"].queue_length = 1

    response = client.get("/api/services", headers=patient_headers)

    assert response.status_code == 200
    assert response.json()[0]["estimatedWaitMinutes"] == 12


@pytest.mark.parametrize("queue_status", ["closed", "open"])
def test_admin_can_change_availability(client, admin_headers, queue_status):
    response = client.patch("/api/services/sick-visit/status", headers=admin_headers, json={"status": queue_status})

    assert response.status_code == 200
    assert response.json()["status"] == queue_status
    assert response.json()["estimatedWaitMinutes"] == 48
    assert client.get("/api/services", headers=admin_headers).json()[0]["status"] == queue_status


def test_admin_can_delete_service(client, admin_headers):
    response = client.delete("/api/services/sick-visit", headers=admin_headers)

    assert response.status_code == 204
    assert response.content == b""
    assert "sick-visit" not in [service["id"] for service in client.get("/api/services", headers=admin_headers).json()]


@pytest.mark.parametrize(("method", "path", "body"), [
    ("POST", "/api/services", VALID_SERVICE),
    ("PUT", "/api/services/sick-visit", VALID_SERVICE),
    ("PATCH", "/api/services/sick-visit/status", {"status": "closed"}),
    ("DELETE", "/api/services/sick-visit", None),
])
def test_mutations_require_admin_and_leave_data_unchanged(client, patient_headers, method, path, body):
    before = client.get("/api/services", headers=patient_headers).json()

    assert client.request(method, path, json=body).status_code == 401
    assert client.request(method, path, headers=patient_headers, json=body).status_code == 403
    assert client.get("/api/services", headers=patient_headers).json() == before


def test_listing_requires_sign_in(client):
    assert client.get("/api/services").status_code == 401


@pytest.mark.parametrize(("method", "path", "body"), [
    ("PUT", "/api/services/missing", VALID_SERVICE),
    ("PATCH", "/api/services/missing/status", {"status": "open"}),
    ("DELETE", "/api/services/missing", None),
])
def test_unknown_service_returns_404(client, admin_headers, method, path, body):
    response = client.request(method, path, headers=admin_headers, json=body)

    assert response.status_code == 404
    assert response.json()["detail"] == "Service not found."


@pytest.mark.parametrize("method,path", [("POST", "/api/services"), ("PUT", "/api/services/sick-visit")])
@pytest.mark.parametrize("field", list(VALID_SERVICE))
def test_all_fields_are_required(client, admin_headers, method, path, field):
    body = {key: value for key, value in VALID_SERVICE.items() if key != field}
    response = client.request(method, path, headers=admin_headers, json=body)

    assert response.status_code == 422
    assert response.json()["errors"] == {field: "This field is required."}


@pytest.mark.parametrize(("field", "value"), [
    ("name", ""), ("name", "   "), ("name", "x" * 101), ("name", 123), ("name", None),
    ("description", ""), ("description", " \n "), ("description", "x" * 1001),
    ("description", ["text"]), ("description", None),
    ("expectedDurationMinutes", 0), ("expectedDurationMinutes", -1), ("expectedDurationMinutes", 481),
    ("expectedDurationMinutes", 1.5), ("expectedDurationMinutes", "30"),
    ("expectedDurationMinutes", True), ("expectedDurationMinutes", None),
    ("priority", "urgent"), ("priority", "HIGH"), ("priority", 1), ("priority", None),
    ("id", "client-chosen-id"), ("status", "open"), ("queueLength", 100), ("estimatedWaitMinutes", 999),
])
@pytest.mark.parametrize("method,path", [("POST", "/api/services"), ("PUT", "/api/services/sick-visit")])
def test_invalid_fields_are_rejected_without_changing_records(client, admin_headers, field, value, method, path):
    before = client.get("/api/services", headers=admin_headers).json()
    response = client.request(method, path, headers=admin_headers, json={**VALID_SERVICE, field: value})

    assert response.status_code == 422
    assert field in response.json()["errors"]
    assert client.get("/api/services", headers=admin_headers).json() == before


@pytest.mark.parametrize("duration", [1, 480])
@pytest.mark.parametrize("priority", ["low", "medium", "high"])
def test_valid_boundaries_and_priorities(client, admin_headers, duration, priority):
    response = client.post("/api/services", headers=admin_headers, json={
        "name": "n" * 100, "description": "d" * 1000, "expectedDurationMinutes": duration, "priority": priority,
    })

    assert response.status_code == 201
    assert response.json()["expectedDurationMinutes"] == duration
    assert response.json()["priority"] == priority


@pytest.mark.parametrize("body", [{}, {"status": "paused"}, {"status": 1}, {"status": "open", "name": "Other"}])
def test_status_validation(client, admin_headers, body):
    response = client.patch("/api/services/sick-visit/status", headers=admin_headers, json=body)

    assert response.status_code == 422
    assert client.get("/api/services", headers=admin_headers).json()[0]["status"] == "open"
