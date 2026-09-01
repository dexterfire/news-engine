"""Admin /sources endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _payload(**overrides):
    base = {
        "id": "src-1",
        "name": "Test Source",
        "kind": "rss",
        "url": "https://example.com/feed.xml",
        "enabled": True,
        "config": {},
    }
    base.update(overrides)
    return base


# Arrange / Act / Assert for each case.


def test_list_ok_empty(client: TestClient) -> None:
    # Act
    r = client.get("/admin/sources")
    # Assert
    assert r.status_code == 200
    assert r.json() == []


def test_create_ok(client: TestClient) -> None:
    # Act
    r = client.post("/admin/sources", json=_payload())
    # Assert
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == "src-1"
    assert body["enabled"] is True


def test_create_validation_error(client: TestClient) -> None:
    # Act — empty id
    r = client.post("/admin/sources", json=_payload(id=""))
    # Assert
    assert r.status_code == 422


def test_create_duplicate_id_error(client: TestClient) -> None:
    # Arrange
    client.post("/admin/sources", json=_payload())
    # Act
    r = client.post("/admin/sources", json=_payload())
    # Assert
    assert r.status_code == 409


def test_get_404(client: TestClient) -> None:
    r = client.get("/admin/sources/missing")
    assert r.status_code == 404


def test_delete_ok(client: TestClient) -> None:
    client.post("/admin/sources", json=_payload())
    r = client.delete("/admin/sources/src-1")
    assert r.status_code == 204
    assert client.get("/admin/sources/src-1").status_code == 404
