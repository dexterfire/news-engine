"""Admin CRUD: /admin/articles."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from news_engine.api.deps import get_session
from news_engine.api.schemas import ArticleCreate, ArticleRead
from news_engine.models import Article, Feed, Source

router = APIRouter(prefix="/articles", tags=["admin:articles"])


@router.get("", response_model=list[ArticleRead])
def list_articles(session: Session = Depends(get_session)) -> list[Article]:
    return list(session.query(Article).order_by(Article.published_at.desc()).all())


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(article_id: str, session: Session = Depends(get_session)) -> Article:
    obj = session.get(Article, article_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found")
    return obj


@router.post("", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
def create_article(payload: ArticleCreate, session: Session = Depends(get_session)) -> Article:
    if session.get(Feed, payload.feed_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown feed_id")
    if session.get(Source, payload.source_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown source_id")
    obj = Article(**payload.model_dump())
    session.add(obj)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Article already exists")
    session.refresh(obj)
    return obj


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: str, session: Session = Depends(get_session)) -> None:
    obj = session.get(Article, article_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found")
    session.delete(obj)
    session.commit()
