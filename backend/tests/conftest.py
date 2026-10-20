import os

# Must be set before the app is imported: cheap bcrypt rounds keep tests fast.
os.environ.setdefault("QUEUESMART_BCRYPT_ROUNDS", "4")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
