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
from app.auth.store import users  # noqa: E402
from app.main import app  # noqa: E402
from app.queue_store import queues  # noqa: E402
from app.services import reset_services  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


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
