import pytest

from app.auth.passwords import verify_password
from app.auth.roles import Role
from app.auth.store import SEED_EMAILS, SEED_PASSWORD, EmailTakenError, UserStore


@pytest.fixture
def store() -> UserStore:
    store = UserStore()
    store.reset()
    return store


def test_reset_adds_demo_accounts_with_roles(store):
    admin = store.get_by_email("admin@university.edu")
    student = store.get_by_email("student@university.edu")

    assert admin.role is Role.ADMIN
    assert student.role is Role.PATIENT
    assert all(verify_password(SEED_PASSWORD, store.get_by_email(email).password_hash) for email in SEED_EMAILS)


def test_create_stores_hash_not_password(store):
    user = store.create("new.student@university.edu", "Queue$mart1")

    assert user.password_hash != "Queue$mart1"
    assert store.get_by_email("new.student@university.edu") == user
    assert store.get_by_id(user.id) == user


def test_create_rejects_duplicate_email(store):
    with pytest.raises(EmailTakenError):
        store.create("student@university.edu", "Queue$mart1")


def test_lookups_return_none_when_missing(store):
    assert store.get_by_email("nobody@university.edu") is None
    assert store.get_by_id("missing-id") is None


def test_reset_removes_created_accounts(store):
    store.create("temp@university.edu", "Queue$mart1")
    store.reset()

    assert store.get_by_email("temp@university.edu") is None
