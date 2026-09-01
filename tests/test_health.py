"""Health‑check endpoint tests."""

from __future__ import annotations


def test_health_returns_ok(client) -> None:
    """GET /health should return 200 with a JSON body ``{"status": "ok"}``."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
