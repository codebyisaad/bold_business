"""Database fixtures for the real test database (TEST_DATABASE_URL). Pure tests don't use them.

- The schema is applied once per test session, by the owner role, then recruiters are seeded.
- Each test using `db` starts with an empty candidates table (cleared by the owner, since
  the app role has no DELETE). Recruiters stay seeded.
- Code under test connects as the app role, exactly like the API.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from app.config import settings
from app.db import apply_schema, get_session
from app.main import app
from app.models import Candidate
from app.seed import load_recruiters


@pytest.fixture(scope="session")
def owner_engine():
    apply_schema(settings.test_owner_database_url, reset=True)
    load_recruiters(settings.test_owner_database_url)
    engine = create_engine(settings.test_owner_database_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def app_engine(owner_engine):
    engine = create_engine(settings.test_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db(owner_engine, app_engine):
    """The app-role engine, with the candidates table emptied first."""
    with owner_engine.begin() as conn:
        conn.execute(delete(Candidate))
    return app_engine


@pytest.fixture
def client(db):
    def test_session():
        with Session(db) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
