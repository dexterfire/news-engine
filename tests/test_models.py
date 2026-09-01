"""CRUD tests for the Feed model."""

from __future__ import annotations

from sqlalchemy.orm import Session

from news_engine.models import Feed, Source


def _make_source(session: Session, source_id: str = "src1") -> Source:
    source = Source(
        id=source_id,
        name="Test Source",
        kind="rss",
        url="https://example.com",
        enabled=True,
        config={},
    )
    session.add(source)
    session.commit()
    return source


def test_feed_create_read_update_delete(db_session: Session) -> None:
    """A Feed can be created, read, updated, and deleted."""
    _make_source(db_session, "src1")

    feed = Feed(
        id="feed1",
        source_id="src1",
        url="https://example.com/feed",
        title="Initial Title",
        language="en",
        active=True,
    )
    db_session.add(feed)
    db_session.commit()

    fetched = db_session.get(Feed, "feed1")
    assert fetched is not None
    assert fetched.title == "Initial Title"
    assert fetched.language == "en"
    assert fetched.active is True

    fetched.title = "Updated Title"
    db_session.commit()
    assert db_session.get(Feed, "feed1").title == "Updated Title"

    db_session.delete(fetched)
    db_session.commit()
    assert db_session.get(Feed, "feed1") is None


def test_feed_requires_source(db_session: Session) -> None:
    """Inserting a Feed without a matching Source must fail (FK constraint)."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    feed = Feed(
        id="feed_orphan",
        source_id="missing_source",
        url="https://example.com/feed",
        title="Orphan Feed",
        language="en",
    )
    db_session.add(feed)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
