import pytest

from app.auth.store import users


def sign_in(client, email="student@university.edu"):
    response = client.post("/api/auth/login", json={"email": email, "password": "Queue$mart1"})
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_registration_creates_linked_profile_with_optional_details(client):
    response = client.post("/api/auth/register", json={
        "email": "  NEW@university.edu ", "password": "Queue$mart1", "full_name": "  New Student  ",
        "contact_info": "  +1 555 0100  ", "preferences": "  Contact me by phone.  ",
    })
    assert response.status_code == 201
    body = response.json()
    saved = client.get("/api/auth/profile", headers={"Authorization": f"Bearer {body['token']}"})

    assert saved.status_code == 200
    assert saved.json() == {
        "user_id": body["user"]["id"], "email": "new@university.edu", "full_name": "New Student",
        "contact_info": "+1 555 0100", "preferences": "Contact me by phone.",
    }


def test_optional_profile_fields_default_to_null(client):
    profile = client.get("/api/auth/profile", headers=sign_in(client)).json()
    assert profile["full_name"] == "Demo Student"
    assert profile["contact_info"] is None
    assert profile["preferences"] is None
    assert "password" not in profile and "password_hash" not in profile


@pytest.mark.parametrize("email", ["student@university.edu", "admin@university.edu"])
def test_profile_update_is_retrievable_across_sessions(client, email):
    values = {"full_name": "  Updated Name  ", "contact_info": "555-0100", "preferences": "Phone calls"}
    response = client.put("/api/auth/profile", headers=sign_in(client, email), json=values)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"

    saved = client.get("/api/auth/profile", headers=sign_in(client, email))
    assert saved.json() == response.json()
    assert saved.json()["email"] == email


@pytest.mark.parametrize("value", [None, "", "   "])
def test_optional_fields_can_be_cleared(client, value):
    headers = sign_in(client)
    client.put("/api/auth/profile", headers=headers, json={
        "full_name": "Student", "contact_info": "555-0100", "preferences": "Phone calls",
    })
    response = client.put("/api/auth/profile", headers=headers, json={
        "full_name": "Student", "contact_info": value, "preferences": value,
    })
    assert response.status_code == 200
    assert response.json()["contact_info"] is None
    assert response.json()["preferences"] is None


def test_profile_update_cannot_change_another_account(client):
    student = sign_in(client)
    admin = sign_in(client, "admin@university.edu")
    before = client.get("/api/auth/profile", headers=admin).json()
    client.put("/api/auth/profile", headers=student, json={"full_name": "Updated Student"})
    assert client.get("/api/auth/profile", headers=admin).json() == before


@pytest.mark.parametrize("field", ["user_id", "email", "role", "password_hash"])
def test_profile_cannot_override_identity_or_credentials(client, field):
    headers = sign_in(client)
    before = client.get("/api/auth/profile", headers=headers).json()
    response = client.put("/api/auth/profile", headers=headers, json={"full_name": "Changed", field: "forged"})
    assert response.status_code == 422
    assert response.json()["errors"][field] == "Unknown field."
    assert client.get("/api/auth/profile", headers=headers).json() == before


@pytest.mark.parametrize("path", ["/api/auth/profile", "/api/auth/register"])
@pytest.mark.parametrize(("field", "value"), [
    ("full_name", ""), ("full_name", " \t\n "), ("full_name", None), ("full_name", 123),
    ("full_name", "x" * 101), ("contact_info", "x" * 101), ("contact_info", 123),
    ("preferences", "x" * 1001), ("preferences", ["text"]),
])
def test_profile_validation_rejects_bad_values_without_changes(client, path, field, value):
    headers = sign_in(client)
    before = client.get("/api/auth/profile", headers=headers).json()
    body = {"full_name": "Student", field: value}
    if path.endswith("register"):
        body.update(email="invalid.profile@university.edu", password="Queue$mart1")
        response = client.post(path, json=body)
        assert users.get_by_email(body["email"]) is None
    else:
        response = client.put(path, headers=headers, json=body)
    assert response.status_code == 422
    assert field in response.json()["errors"]
    assert client.get("/api/auth/profile", headers=headers).json() == before


def test_profile_accepts_length_boundaries_and_literal_sql_text(client):
    headers = sign_in(client)
    name = "Robert'); DROP TABLE UserCredentials; --"
    values = {"full_name": name.ljust(100, "!"), "contact_info": "c" * 100, "preferences": "p" * 1000}
    response = client.put("/api/auth/profile", headers=headers, json=values)
    assert response.status_code == 200
    assert all(response.json()[key] == value for key, value in values.items())
    assert client.get("/api/auth/me", headers=headers).status_code == 200


@pytest.mark.parametrize("method", ["get", "put"])
@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_profile_requires_authentication(client, method, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    kwargs = {"json": {"full_name": "Student"}} if method == "put" else {}
    assert getattr(client, method)("/api/auth/profile", headers=headers, **kwargs).status_code == 401


@pytest.mark.parametrize("method", ["get", "put"])
def test_missing_profile_returns_404(client, method):
    headers = sign_in(client)
    with users.database.connect() as connection:
        connection.execute("DELETE FROM UserProfile WHERE email = ?", ("student@university.edu",))
    kwargs = {"json": {"full_name": "Student"}} if method == "put" else {}
    assert getattr(client, method)("/api/auth/profile", headers=headers, **kwargs).status_code == 404


def test_duplicate_registration_does_not_overwrite_profile(client):
    headers = sign_in(client)
    before = client.get("/api/auth/profile", headers=headers).json()
    response = client.post("/api/auth/register", json={
        "email": "STUDENT@UNIVERSITY.EDU", "password": "Different!1", "full_name": "Replacement",
    })
    assert response.status_code == 409
    assert client.get("/api/auth/profile", headers=headers).json() == before
    assert sign_in(client)


@pytest.mark.parametrize("path", ["/api/auth/register", "/api/auth/profile"])
def test_full_name_is_required(client, path):
    headers = sign_in(client)
    if path.endswith("register"):
        response = client.post(path, json={"email": "new@university.edu", "password": "Queue$mart1"})
    else:
        response = client.put(path, headers=headers, json={})
    assert response.status_code == 422
    assert response.json()["errors"]["full_name"] == "This field is required."
