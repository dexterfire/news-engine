"""Admin /articles endpoint tests."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient


def _setup(client: TestClient) -> None:
    client.post(
        "/admin/sources",
        json={
            "id": "src-1",
            "name": "S",
            "kind": "rss",
            "url": "https://example.com/feed.xml",
            "enabled": True,
            "config": {},
        },
    )
    client.post(
        "/admin/feeds",
        json={
            "id": "feed-1",
            "source_id": "src-1",
            "url": "https://example.com/feed.xml",
            "title": "F",
            "language": "en",
            "category": None,
            "active": True,
        },
    )


def _payload(**overrides):
    base = {
        "id": "art-1",
        "feed_id": "feed-1",
        "source_id": "src-1",
        "title": "Hello",
        "url": "https://example.com/a/1",
        "published_at": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
        "language": "en",
        "author": None,
        "text": None,
        "entities": [],
        "keywords": [],
    }
    base.update(overrides)
    return base


def test_list_ok_empty(client: TestClient) -> None:
    r = client.get("/admin/articles")
    assert r.status_code == 200
    assert r.json() == []


def test_create_ok(client: TestClient) -> None:
    _setup(client)
    r = client.post("/admin/articles", json=_payload())
    assert r.status_code == 201
    assert r.json()["id"] == "art-1"


def test_create_validation_error(client: TestClient) -> None:
    _setup(client)
    r = client.post("/admin/articles", json=_payload(title=""))
    assert r.status_code == 422


def test_create_fk_error_feed(client: TestClient) -> None:
    _setup(client)
    r = client.post("/admin/articles", json=_payload(feed_id="nope"))
    assert r.status_code == 422
    assert "feed_id" in r.text


def test_create_fk_error_source(client: TestClient) -> None:
    _setup(client)
    r = client.post("/admin/articles", json=_payload(source_id="nope"))
    assert r.status_code == 422
    assert "source_id" in r.text


def test_create_duplicate_id_error(client: TestClient) -> None:
    _setup(client)
    client.post("/admin/articles", json=_payload())
    r = client.post("/admin/articles", json=_payload())
    assert r.status_code == 409


def test_get_404(client: TestClient) -> None:
    r = client.get("/admin/articles/missing")
    assert r.status_code == 404


def test_delete_ok(client: TestClient) -> None:
    _setup(client)
    client.post("/admin/articles", json=_payload())
    r = client.delete("/admin/articles/art-1")
    assert r.status_code == 204
    assert client.get("/admin/articles/art-1").status_code == 404
