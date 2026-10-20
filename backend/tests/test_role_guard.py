import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import AdminUser, require_admin
from app.main import app

VALID_PASSWORD = "Queue$mart1"


@pytest.fixture
def guarded_client():
    """The real app plus throwaway admin routes, to exercise the guard both ways it's used."""
    test_app = FastAPI()
    test_app.include_router(app.router)

    @test_app.get("/api/test-admin/param")
    def as_parameter(user: AdminUser) -> dict[str, str]:
        return {"email": user.email}

    router = APIRouter(prefix="/api/test-admin", dependencies=[Depends(require_admin)])

    @router.get("/router")
    def on_router() -> dict[str, bool]:
        return {"ok": True}

    test_app.include_router(router)
    return TestClient(test_app)


def token_for(client, email):
    return client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD}).json()["token"]


@pytest.mark.parametrize("path", ["/api/test-admin/param", "/api/test-admin/router"])
def test_admin_can_use_admin_routes(guarded_client, path):
    token = token_for(guarded_client, "admin@university.edu")

    response = guarded_client.get(path, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/api/test-admin/param", "/api/test-admin/router"])
def test_patient_is_forbidden(guarded_client, path):
    token = token_for(guarded_client, "student@university.edu")

    response = guarded_client.get(path, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Only clinic administrators can do this."


@pytest.mark.parametrize("path", ["/api/test-admin/param", "/api/test-admin/router"])
def test_signed_out_is_unauthorized(guarded_client, path):
    assert guarded_client.get(path).status_code == 401


def test_new_admin_account_gets_access(guarded_client):
    body = guarded_client.post(
        "/api/auth/register", json={"email": "front.desk.admin@university.edu", "password": VALID_PASSWORD}
    ).json()

    response = guarded_client.get("/api/test-admin/param", headers={"Authorization": f"Bearer {body['token']}"})

    assert response.status_code == 200
    assert response.json() == {"email": "front.desk.admin@university.edu"}
