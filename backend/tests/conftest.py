import os
from pathlib import Path
from tempfile import TemporaryDirectory

# Must be set before the app is imported: cheap bcrypt rounds keep tests fast.
os.environ.setdefault("QUEUESMART_BCRYPT_ROUNDS", "4")
# Never create or reset the developer's database while importing/running tests.
_database_directory = TemporaryDirectory(prefix="queuesmart-tests-")
os.environ["QUEUESMART_DATABASE_PATH"] = str(Path(_database_directory.name) / "test.sqlite3")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.auth.sessions import sessions  # noqa: E402
from app.auth.store import UserStore, users  # noqa: E402
from app.main import app  # noqa: E402
from app.queue_store import QueueStore, queues  # noqa: E402
from app.services import reset_services  # noqa: E402


# Service IDs the queue_store fixture creates, so queues can reference them (Queue -> Service key).
TEST_SERVICE_IDS = ("svc", "one", "two", "other")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def queue_store(tmp_path) -> QueueStore:
    """A queue store with its own database: no seeded queues or patients, only the test
    services that queues must reference (svc, one, two, other)."""
    store = QueueStore(tmp_path / "queues.sqlite3")
    for service_id in TEST_SERVICE_IDS:
        store.services.create(f"Test {service_id}", "Test service.", 10, "medium", service_id=service_id)
    return store


@pytest.fixture
def patient(queue_store):
    """patient("a") creates (once) an account a@x.edu in queue_store's database and returns its user ID."""
    accounts = UserStore(queue_store.database.path)
    ids: dict[str, str] = {}

    def make(name: str) -> str:
        if name not in ids:
            ids[name] = accounts.create(f"{name}@x.edu", "Queue$mart1", name).id
        return ids[name]

    return make


@pytest.fixture(scope="session", autouse=True)
def isolated_database():
    yield
    _database_directory.cleanup()


@pytest.fixture(autouse=True)
def fresh_store():
    """Every test starts with demo accounts/services/queues and no sessions."""
    users.reset()
    sessions.reset()
    reset_services()
    queues.reset()
