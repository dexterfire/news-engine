"""Pydantic schemas for admin CRUD (Source, Feed, Article)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class _ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Source ---------------------------------------------------------------------


class SourceCreate(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    kind: str = Field(min_length=1, max_length=50)
    url: str = Field(min_length=1, max_length=1024)
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class SourceRead(_ApiModel):
    id: str
    name: str
    kind: str
    url: str
    enabled: bool
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# Feed -----------------------------------------------------------------------


class FeedCreate(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    source_id: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=512)
    language: str | None = Field(default=None, max_length=10)
    category: str | None = Field(default=None, max_length=100)
    active: bool = True


class FeedRead(_ApiModel):
    id: str
    source_id: str
    url: str
    title: str
    language: str | None
    category: str | None
    last_checked_at: datetime | None
    active: bool
    created_at: datetime
    updated_at: datetime


# Article --------------------------------------------------------------------


class ArticleCreate(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    feed_id: str = Field(min_length=1, max_length=255)
    source_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1, max_length=2048)
    published_at: datetime
    language: str = Field(min_length=1, max_length=10)
    author: str | None = Field(default=None, max_length=255)
    text: str | None = None
    entities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    importance: float | None = None


class ArticleRead(_ApiModel):
    id: str
    feed_id: str
    source_id: str
    title: str
    url: str
    published_at: datetime
    fetched_at: datetime
    language: str
    author: str | None
    text: str | None
    entities: list[str]
    keywords: list[str]
    importance: float | None
    is_processed: bool
    created_at: datetime
    updated_at: datetime


# Re-export HttpUrl for type-hint convenience.
__all__ = ["HttpUrl", "SourceCreate", "SourceRead", "FeedCreate", "FeedRead", "ArticleCreate", "ArticleRead"]
