"""Admin CRUD: /admin/sources."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from news_engine.api.deps import get_session
from news_engine.api.schemas import SourceCreate, SourceRead
from news_engine.models import Source

router = APIRouter(prefix="/sources", tags=["admin:sources"])


@router.get("", response_model=list[SourceRead])
def list_sources(session: Session = Depends(get_session)) -> list[Source]:
    return list(session.query(Source).order_by(Source.id).all())


@router.get("/{source_id}", response_model=SourceRead)
def get_source(source_id: str, session: Session = Depends(get_session)) -> Source:
    obj = session.get(Source, source_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source not found")
    return obj


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreate, session: Session = Depends(get_session)) -> Source:
    obj = Source(**payload.model_dump())
    session.add(obj)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Source already exists")
    session.refresh(obj)
    return obj


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, session: Session = Depends(get_session)) -> None:
    obj = session.get(Source, source_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source not found")
    session.delete(obj)
    session.commit()
