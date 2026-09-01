"""Smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from news_engine.main import app


def test_health_smoke() -> None:
    # Arrange / Act
    with TestClient(app) as c:
        r = c.get("/health")
    # Assert
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
