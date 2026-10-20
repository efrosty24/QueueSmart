from datetime import UTC, datetime, timedelta

from app.auth.sessions import SESSION_LIFETIME, SessionStore, sessions

VALID_PASSWORD = "Queue$mart1"


def sign_in(client, email="student@university.edu"):
    return client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD}).json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- SessionStore ----------


def test_session_lasts_seven_days():
    assert SESSION_LIFETIME == timedelta(days=7)
    start = datetime(2026, 10, 1, tzinfo=UTC)
    store = SessionStore()

    token, session = store.create("user-1", now=start)

    assert session.expires_at == start + timedelta(days=7)
    assert store.get(token, now=start + timedelta(days=6, hours=23)) == session
    assert store.get(token, now=start + timedelta(days=7)) is None


def test_expired_session_is_dropped():
    start = datetime(2026, 10, 1, tzinfo=UTC)
    store = SessionStore()
    token, _ = store.create("user-1", now=start)

    store.get(token, now=start + timedelta(days=8))

    # Gone even when asked about an earlier time.
    assert store.get(token, now=start) is None


def test_tokens_are_unique_and_not_stored_in_plain_text():
    store = SessionStore()
    first, _ = store.create("user-1")
    second, _ = store.create("user-1")

    assert first != second
    assert first not in store._sessions and second not in store._sessions


def test_revoke_ends_a_session():
    store = SessionStore()
    token, _ = store.create("user-1")

    store.revoke(token)

    assert store.get(token) is None


# ---------- API ----------


def test_login_returns_token_that_expires_in_seven_days(client):
    before = datetime.now(UTC)
    body = sign_in(client)
    expires_at = datetime.fromisoformat(body["expires_at"])

    assert body["token"]
    assert before + timedelta(days=7) <= expires_at <= datetime.now(UTC) + timedelta(days=7)


def test_register_signs_the_new_account_in(client):
    body = client.post("/api/auth/register", json={"email": "new@university.edu", "password": VALID_PASSWORD}).json()

    response = client.get("/api/auth/me", headers=auth(body["token"]))

    assert response.status_code == 200
    assert response.json()["email"] == "new@university.edu"


def test_me_returns_user_and_role_from_server(client):
    token = sign_in(client, email="admin@university.edu")["token"]

    response = client.get("/api/auth/me", headers=auth(token))

    assert response.status_code == 200
    assert response.json()["email"] == "admin@university.edu"
    assert response.json()["role"] == "admin"


def test_me_requires_a_token(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_unknown_token(client):
    response = client.get("/api/auth/me", headers=auth("made-up-token"))

    assert response.status_code == 401


def test_me_rejects_expired_session(client):
    user_id = client.get("/api/auth/me", headers=auth(sign_in(client)["token"])).json()["id"]
    token, _ = sessions.create(user_id, now=datetime.now(UTC) - timedelta(days=7, seconds=1))

    response = client.get("/api/auth/me", headers=auth(token))

    assert response.status_code == 401


def test_logout_revokes_the_token(client):
    token = sign_in(client)["token"]

    assert client.post("/api/auth/logout", headers=auth(token)).status_code == 204
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401


def test_logout_requires_a_valid_session(client):
    assert client.post("/api/auth/logout").status_code == 401
    assert client.post("/api/auth/logout", headers=auth("made-up-token")).status_code == 401
