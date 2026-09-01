"""Admin /feeds endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _add_source(client: TestClient, source_id: str = "src-1") -> None:
    client.post(
        "/admin/sources",
        json={
            "id": source_id,
            "name": "S",
            "kind": "rss",
            "url": "https://example.com/feed.xml",
            "enabled": True,
            "config": {},
        },
    )


def _payload(**overrides):
    base = {
        "id": "feed-1",
        "source_id": "src-1",
        "url": "https://example.com/feed.xml",
        "title": "Test Feed",
        "language": "en",
        "category": None,
        "active": True,
    }
    base.update(overrides)
    return base


def test_list_ok_empty(client: TestClient) -> None:
    r = client.get("/admin/feeds")
    assert r.status_code == 200
    assert r.json() == []


def test_create_ok(client: TestClient) -> None:
    _add_source(client)
    r = client.post("/admin/feeds", json=_payload())
    assert r.status_code == 201
    assert r.json()["id"] == "feed-1"


def test_create_validation_error(client: TestClient) -> None:
    _add_source(client)
    r = client.post("/admin/feeds", json=_payload(title=""))
    assert r.status_code == 422


def test_create_fk_error(client: TestClient) -> None:
    # No source added — FK should be rejected.
    r = client.post("/admin/feeds", json=_payload(source_id="does-not-exist"))
    assert r.status_code == 422
    assert "source_id" in r.text


def test_create_duplicate_id_error(client: TestClient) -> None:
    _add_source(client)
    client.post("/admin/feeds", json=_payload())
    r = client.post("/admin/feeds", json=_payload())
    assert r.status_code == 409


def test_get_404(client: TestClient) -> None:
    r = client.get("/admin/feeds/missing")
    assert r.status_code == 404


def test_delete_ok(client: TestClient) -> None:
    _add_source(client)
    client.post("/admin/feeds", json=_payload())
    r = client.delete("/admin/feeds/feed-1")
    assert r.status_code == 204
    assert client.get("/admin/feeds/feed-1").status_code == 404
