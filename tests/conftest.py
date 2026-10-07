"""
tests/conftest.py - Shared pytest fixtures for the test suite.

Key design decisions:
  - Uses a StaticPool-backed in-memory SQLite database so that *all*
    connections (TestClient requests, background tasks, fixture assertions)
    share the exact same in-memory database. Without StaticPool each
    connection to sqlite:///:memory: gets an isolated, empty database.
  - Overrides the FastAPI 'get_db' dependency AND patches
    'app.services.SessionLocal' so that background tasks spawned by
    BackgroundTasks also use the test database.
  - Each test gets a fresh schema via create_all / drop_all in the 'db'
    fixture, ensuring full isolation between tests.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import create_app

# ---------------------------------------------------------------------------
# Shared in-memory engine — StaticPool keeps a single connection alive for
# the duration of the test so all sessions see the same data.
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # critical: ensures one shared in-memory DB
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """
    Provide a fresh, isolated database session for each test.

    Creates all tables before the test and drops them afterwards.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Provide a TestClient with:
      1. 'get_db' dependency overridden to use the test database session.
      2. 'app.services.SessionLocal' patched so BackgroundTasks (process_job)
         also open sessions against the same in-memory test database.

    This ensures all layers — HTTP route, background task, and fixture
    assertion — see the exact same data.
    """
    app = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass  # lifecycle managed by the 'db' fixture

    app.dependency_overrides[get_db] = override_get_db

    # Patch the SessionLocal used inside process_job so background tasks
    # write to the same in-memory database instead of the production SQLite file.
    with patch("app.services.SessionLocal", TestingSessionLocal):
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# Shared test data helpers
# ---------------------------------------------------------------------------

VALID_JOB_PAYLOAD = {
    "event_name": "TechConf 2024",
    "issuer_name": "Aereo Academy",
    "issue_date": "2024-11-15",
    "recipients": [
        {
            "recipient_name": "Alice Johnson",
            "recipient_email": "alice@example.com",
            "course_name": "Advanced Python Programming",
        },
        {
            "recipient_name": "Bob Smith",
            "recipient_email": "bob@example.com",
            "course_name": "Cloud Architecture",
        },
    ],
}


def make_recipient(
    name: str = "Test User",
    email: str = "test@example.com",
    course: str = "Test Course",
) -> dict:
    """Helper to build a single recipient dict."""
    return {
        "recipient_name": name,
        "recipient_email": email,
        "course_name": course,
    }


def make_job_payload(recipients: list[dict] | None = None, **overrides) -> dict:
    """
    Helper to build a complete job payload, optionally overriding fields
    or providing a custom recipient list.

    Note: pass recipients=[] to explicitly send an empty list (which should
    fail validation). Pass recipients=None (default) to get a single
    default recipient.
    """
    payload = {
        "event_name": "Test Event",
        "issuer_name": "Test Org",
        "issue_date": "2024-06-01",
        "recipients": [make_recipient()] if recipients is None else recipients,
    }
    payload.update(overrides)
    return payload
