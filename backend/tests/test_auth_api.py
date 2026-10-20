import pytest

VALID_PASSWORD = "Queue$mart1"


def register(client, email="new.student@university.edu", password=VALID_PASSWORD):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def login(client, email="student@university.edu", password=VALID_PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ---------- Registration ----------


def test_register_creates_patient_account(client):
    response = register(client, email="  New.Student@University.edu ")

    assert response.status_code == 201
    user = response.json()["user"]
    assert user["email"] == "new.student@university.edu"
    assert user["role"] == "patient"
    assert "password" not in user and "password_hash" not in user


def test_register_with_admin_in_name_creates_admin(client):
    response = register(client, email="clinic.admin@university.edu")

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "admin"


def test_register_rejects_duplicate_email(client):
    response = register(client, email="student@university.edu")

    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists."


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("Ab!4567", "Use at least 8 characters."),
        ("queue$mart1", "Include at least one uppercase letter."),
        ("QueueSmart1", "Include at least one special character, like ! or #."),
    ],
)
def test_register_rejects_weak_passwords(client, password, message):
    response = register(client, password=password)

    assert response.status_code == 422
    assert response.json()["errors"] == {"password": message}


def test_register_cannot_set_its_own_role(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "sneaky@university.edu", "password": VALID_PASSWORD, "role": "admin"},
    )

    assert response.status_code == 422
    assert response.json()["errors"] == {"role": "Unknown field."}


# ---------- Field types, required fields, length limits ----------


def test_missing_fields_are_reported(client):
    response = client.post("/api/auth/register", json={})

    assert response.status_code == 422
    assert response.json()["errors"] == {"email": "This field is required.", "password": "This field is required."}


def test_non_string_fields_are_rejected(client):
    response = client.post("/api/auth/login", json={"email": 12345, "password": ["Queue$mart1"]})

    assert response.status_code == 422
    assert response.json()["errors"] == {"email": "Must be text.", "password": "Must be text."}


def test_oversized_fields_are_rejected(client):
    response = client.post("/api/auth/login", json={"email": "a" * 400, "password": "x" * 300})

    assert response.status_code == 422
    assert response.json()["errors"] == {"email": "This value is too long.", "password": "This value is too long."}


def test_body_must_be_a_json_object(client):
    response = client.post("/api/auth/login", json=["not", "an", "object"])

    assert response.status_code == 422
    assert "body" in response.json()["errors"]


def test_invalid_json_is_rejected(client):
    response = client.post("/api/auth/login", content="{not json", headers={"Content-Type": "application/json"})

    assert response.status_code == 422
    assert response.json()["errors"] == {"body": "Request body is not valid JSON."}


# ---------- Login ----------


def test_login_with_seed_student(client):
    response = login(client)

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "patient"


def test_login_with_seed_admin(client):
    response = login(client, email="admin@university.edu")

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"


def test_login_after_register_is_case_insensitive_on_email(client):
    register(client, email="new.student@university.edu")

    response = login(client, email="NEW.STUDENT@university.edu")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "new.student@university.edu"


@pytest.mark.parametrize(
    ("email", "password"),
    [("student@university.edu", "Wrong$Pass1"), ("nobody@university.edu", VALID_PASSWORD)],
)
def test_login_failures_share_one_generic_message(client, email, password):
    response = login(client, email=email, password=password)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


@pytest.mark.parametrize("payload", ["' OR '1'='1", "admin@university.edu'--", "admin@university.edu; DROP TABLE users;"])
def test_login_rejects_sql_injection_in_username(client, payload):
    response = login(client, email=payload)

    assert response.status_code == 422
    assert response.json()["errors"] == {"email": "Enter a valid email address, like name@university.edu."}
