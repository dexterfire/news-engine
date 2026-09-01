"""Admin CRUD: /admin/feeds."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from news_engine.api.deps import get_session
from news_engine.api.schemas import FeedCreate, FeedRead
from news_engine.models import Feed, Source

router = APIRouter(prefix="/feeds", tags=["admin:feeds"])


@router.get("", response_model=list[FeedRead])
def list_feeds(session: Session = Depends(get_session)) -> list[Feed]:
    return list(session.query(Feed).order_by(Feed.id).all())


@router.get("/{feed_id}", response_model=FeedRead)
def get_feed(feed_id: str, session: Session = Depends(get_session)) -> Feed:
    obj = session.get(Feed, feed_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Feed not found")
    return obj


@router.post("", response_model=FeedRead, status_code=status.HTTP_201_CREATED)
def create_feed(payload: FeedCreate, session: Session = Depends(get_session)) -> Feed:
    if session.get(Source, payload.source_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown source_id")
    obj = Feed(**payload.model_dump())
    session.add(obj)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Feed already exists")
    session.refresh(obj)
    return obj


@router.delete("/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feed(feed_id: str, session: Session = Depends(get_session)) -> None:
    obj = session.get(Feed, feed_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Feed not found")
    session.delete(obj)
    session.commit()
