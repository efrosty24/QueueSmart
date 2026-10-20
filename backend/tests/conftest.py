import os

# Must be set before the app is imported: cheap bcrypt rounds keep tests fast.
os.environ.setdefault("QUEUESMART_BCRYPT_ROUNDS", "4")

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


@pytest.fixture(autouse=True)
def fresh_store():
    """Every test starts with demo accounts/services/queues and no sessions."""
    users.reset()
    sessions.reset()
    reset_services()
    queues.reset()
