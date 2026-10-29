"""
Test setup: a fresh SQLite database per test session (PostgreSQL's JSONB is
mapped to SQLite JSON), the keyword placeholder model, and helpers.
Run from api/:   python -m pytest -q
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_db = Path(tempfile.mkdtemp()) / "test.db"
os.environ.update(
    DATABASE_URL=f"sqlite:///{_db}",
    JWT_SECRET="test-secret-not-for-production-0123456789abcdef",
    USE_FAKE_MODEL="True",
    FRONTEND_ORIGINS="http://localhost:5173,https://sentio.example.app",
)

from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")
def _jsonb_on_sqlite(type_, compiler, **kw):
    return "JSON"


from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_limits():
    """Each test starts with empty rate-limit counters."""
    from app import ratelimit
    for lim in (ratelimit.login_failures, ratelimit.register_limit, ratelimit.analyze_limit, ratelimit.feedback_limit):
        lim.clear()
    yield


_counter = iter(range(10_000))


@pytest.fixture
def user(client):
    """Register a brand-new user and return (username, password, auth headers)."""
    name = f"user{next(_counter)}"
    pw = "correct-horse-1"
    assert client.post("/v1/auth/register", json={"username": name, "password": pw}).status_code == 201
    tok = client.post("/v1/auth/login", json={"username": name, "password": pw}).json()["access_token"]
    return name, pw, {"Authorization": f"Bearer {tok}"}
