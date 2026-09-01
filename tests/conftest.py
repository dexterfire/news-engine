"""Test fixtures: isolated SQLite DB, dependency overrides, TestClient."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# Force a temporary SQLite file BEFORE any app import.
_TMP_DB = Path(tempfile.gettempdir()) / "newsengine_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"

from news_engine.api.deps import get_session  # noqa: E402
from news_engine.db import Base  # noqa: E402
from news_engine.main import app  # noqa: E402


@pytest.fixture
def db_engine() -> Generator:
    """Fresh SQLite engine per test, FK enforcement on, schema created."""
    engine = create_engine(
        f"sqlite:///{_TMP_DB}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        # Clean tables for next test.
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    SessionTesting = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    """TestClient with get_session overridden to use the test session."""

    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
