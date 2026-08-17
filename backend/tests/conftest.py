"""
Tests run against SQLite in-process rather than Postgres so `pytest` works
with zero external services. Real deployments always use Postgres (see
docker-compose.yml / DATABASE_URL) -- this override is test-only.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.seed import SEED_PASSWORD, run_seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    Base.metadata.drop_all(bind=engine)
    run_seed()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seed_password():
    return SEED_PASSWORD
