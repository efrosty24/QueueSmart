import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from app.service_store import SEED_SERVICES, DuplicateServiceNameError, ServiceStore

START = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_path) -> ServiceStore:
    """An empty service store with its own database (no seeded services)."""
    return ServiceStore(tmp_path / "services.sqlite3")


def _insert(store: ServiceStore, **overrides) -> None:
    values = {
        "service_id": "svc", "name": "Service", "description": "Details.", "expected_duration_minutes": 10,
        "priority": "low", "created_at": START.isoformat(), "updated_at": START.isoformat(), "deleted_at": None,
        **overrides,
    }
    with store.database.connect() as connection:
        connection.execute(
            f"INSERT INTO Service ({', '.join(values)}) VALUES ({', '.join('?' * len(values))})", tuple(values.values()),
        )


# ---------- Persistence ----------


def test_created_service_is_saved_and_survives_a_new_connection(store):
    created = store.create("Counseling", "Talk with a campus counselor.", 30, "medium", now=START)

    reopened = ServiceStore(store.database.path)

    assert reopened.get(created.id) == created
    assert reopened.list() == [created]
    assert created.created_at == created.updated_at == START


def test_list_returns_active_services_oldest_first(store):
    later = store.create("Later", "Second.", 5, "low", now=START + timedelta(minutes=1))
    earlier = store.create("Earlier", "First.", 5, "low", now=START)

    assert [service.id for service in store.list()] == [earlier.id, later.id]


def test_update_changes_details_and_keeps_id_and_created_date(store):
    created = store.create("Counseling", "Talk with a campus counselor.", 30, "medium", now=START)

    updated = store.update(created.id, "Counseling (Walk-in)", "Same-day visits.", 45, "high",
                           now=START + timedelta(hours=1))

    assert updated.id == created.id
    assert (updated.name, updated.description, updated.expected_duration_minutes, updated.priority) == (
        "Counseling (Walk-in)", "Same-day visits.", 45, "high",
    )
    assert updated.created_at == START
    assert updated.updated_at == START + timedelta(hours=1)
    assert ServiceStore(store.database.path).get(created.id) == updated


def test_update_and_archive_return_falsy_for_missing_services(store):
    assert store.update("missing", "Name", "Details.", 5, "low") is None
    assert store.archive("missing") is False
    assert store.get("missing") is None


def test_archive_hides_service_but_keeps_the_row(store):
    created = store.create("Counseling", "Talk with a campus counselor.", 30, "medium")

    assert store.archive(created.id, now=START) is True

    assert store.get(created.id) is None
    assert store.list() == []
    assert store.archive(created.id) is False  # already archived
    assert store.update(created.id, "New", "Details.", 5, "low") is None
    with store.database.connect() as connection:
        row = connection.execute("SELECT deleted_at FROM Service WHERE service_id = ?", (created.id,)).fetchone()
    assert row["deleted_at"] == START.isoformat()


# ---------- Unique names ----------


@pytest.mark.parametrize("duplicate", ["Counseling", "COUNSELING", "counseling"])
def test_active_service_names_are_unique_ignoring_case(store, duplicate):
    store.create("Counseling", "First.", 30, "medium")

    with pytest.raises(DuplicateServiceNameError):
        store.create(duplicate, "Second.", 30, "medium")
    assert len(store.list()) == 1


def test_update_cannot_take_another_services_name(store):
    store.create("Counseling", "First.", 30, "medium")
    other = store.create("Vaccines", "Second.", 10, "low")

    with pytest.raises(DuplicateServiceNameError):
        store.update(other.id, "counseling", "Second.", 10, "low")
    assert store.get(other.id).name == "Vaccines"


def test_archived_service_name_can_be_reused(store):
    first = store.create("Counseling", "First.", 30, "medium")
    store.archive(first.id)

    second = store.create("Counseling", "Second.", 30, "medium")

    assert second.id != first.id
    assert [service.id for service in store.list()] == [second.id]


def test_other_integrity_errors_are_not_reported_as_duplicate_names(store):
    created = store.create("Counseling", "First.", 30, "medium")

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        store.create("Bad", "Details.", 0, "low")
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        store.update(created.id, "Counseling", "First.", 481, "medium")
    assert store.get(created.id).expected_duration_minutes == 30


# ---------- Seeding ----------


def test_seed_adds_demo_services_in_order(store):
    store.seed(START)

    assert [(s.id, s.name, s.expected_duration_minutes, s.priority) for s in store.list()] == [
        (seed[0], seed[1], seed[3], seed[4]) for seed in SEED_SERVICES
    ]


def test_seed_is_repeatable_and_keeps_saved_changes(store):
    store.seed(START)
    store.update("sick-visit", "Sick Visit (Walk-in)", "Edited.", 15, "high")
    store.archive("lab-work")

    store.seed(START + timedelta(days=1))

    assert store.get("sick-visit").name == "Sick Visit (Walk-in)"
    assert store.get("lab-work") is None
    with store.database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM Service").fetchone()[0] == len(SEED_SERVICES)


# ---------- Database-level validation ----------


@pytest.mark.parametrize(("column", "value"), [
    ("service_id", None), ("service_id", ""), ("service_id", "x" * 101),
    ("name", None), ("name", ""), ("name", " padded "), ("name", "x" * 101),
    # STRICT: a BLOB can never be stored as TEXT. (Numbers are converted to text by SQLite,
    # so the API's StrictStr is what rejects a numeric name.)
    ("name", b"bytes"),
    ("description", None), ("description", ""), ("description", " padded "), ("description", "x" * 1001),
    ("expected_duration_minutes", None), ("expected_duration_minutes", 0), ("expected_duration_minutes", 481),
    ("expected_duration_minutes", 1.5), ("expected_duration_minutes", "twelve"),
    ("priority", None), ("priority", "urgent"), ("priority", "HIGH"),
    ("created_at", None), ("created_at", "not a date"),
    ("updated_at", None), ("updated_at", "yesterday"),
    ("deleted_at", "not a date"),
])
def test_service_constraints_are_enforced_by_sqlite(store, column, value):
    with pytest.raises(sqlite3.IntegrityError):
        _insert(store, **{column: value})


def test_service_ids_are_unique(store):
    _insert(store)

    with pytest.raises(sqlite3.IntegrityError, match="Service.service_id"):
        _insert(store, name="Another name")


def test_boundary_values_are_accepted_by_sqlite(store):
    _insert(store, service_id="x" * 100, name="n" * 100, description="d" * 1000, expected_duration_minutes=480)
    _insert(store, service_id="y", name="m", description="d", expected_duration_minutes=1, priority="high")

    assert len(store.list()) == 2


def test_lookups_treat_input_as_data(store):
    store.create("Counseling", "First.", 30, "medium")

    assert store.get("' OR 1=1 --") is None
    assert store.archive("' OR 1=1 --") is False
    assert len(store.list()) == 1
