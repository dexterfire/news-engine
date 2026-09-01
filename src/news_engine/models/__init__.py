"""SQLAlchemy models for News Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from news_engine.db import Base, json_col


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=true(), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(json_col(), server_default="'{}'", nullable=False)

    feeds: Mapped[list[Feed]] = relationship("Feed", back_populates="source", cascade="all, delete-orphan")


class Feed(Base, TimestampMixin):
    __tablename__ = "feeds"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str | None] = mapped_column(String(10))
    category: Mapped[str | None] = mapped_column(String(100))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, server_default=true(), nullable=False)

    source: Mapped[Source] = relationship("Source", back_populates="feeds")
    articles: Mapped[list[Article]] = relationship("Article", back_populates="feed", cascade="all, delete-orphan")


class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    feed_id: Mapped[str] = mapped_column(ForeignKey("feeds.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str | None] = mapped_column(Text)
    entities: Mapped[list[str]] = mapped_column(json_col(), server_default="'[]'", nullable=False)
    keywords: Mapped[list[str]] = mapped_column(json_col(), server_default="'[]'", nullable=False)
    importance: Mapped[float | None] = mapped_column(Float)
    is_processed: Mapped[bool] = mapped_column(Boolean, server_default=false(), nullable=False)

    feed: Mapped[Feed] = relationship("Feed", back_populates="articles")
    facts: Mapped[list[Fact]] = relationship("Fact", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_articles_title_fts", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_source_id", "source_id"),
        UniqueConstraint("url", name="uq_articles_url"),
    )


class Entity(Base, TimestampMixin):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(json_col(), server_default="'[]'", nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", json_col(), server_default="'{}'", nullable=False)

    facts: Mapped[list[Fact]] = relationship("Fact", back_populates="entity")


class Fact(Base, TimestampMixin):
    __tablename__ = "facts"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(json_col(), server_default="'{}'", nullable=False)

    article: Mapped[Article] = relationship("Article", back_populates="facts")
    entity: Mapped[Entity | None] = relationship("Entity", back_populates="facts")

    __table_args__ = (
        Index("ix_facts_article_id", "article_id"),
        Index("ix_facts_entity_id", "entity_id"),
    )


class Story(Base, TimestampMixin):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False)
    entities: Mapped[list[str]] = mapped_column(json_col(), server_default="'[]'", nullable=False)
    original_language: Mapped[str] = mapped_column(String(10), server_default="en", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(json_col(), server_default="'{}'", nullable=False)

    story_sources: Mapped[list[StorySource]] = relationship("StorySource", back_populates="story", cascade="all, delete-orphan")
    translations: Mapped[list[Translation]] = relationship("Translation", back_populates="story", cascade="all, delete-orphan")
    quality_checks: Mapped[list[QualityCheck]] = relationship("QualityCheck", back_populates="story", cascade="all, delete-orphan")
    content: Mapped[list[Content]] = relationship("Content", back_populates="story", cascade="all, delete-orphan")
    assets: Mapped[list[Asset]] = relationship("Asset", back_populates="story", cascade="all, delete-orphan")
    renders: Mapped[list[Render]] = relationship("Render", back_populates="story", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_stories_payload_gin", "payload", postgresql_using="gin", postgresql_ops={"payload": "jsonb_path_ops"}),
        Index("ix_stories_importance", "importance"),
        Index("ix_stories_created_at", "created_at"),
    )


class StorySource(Base, TimestampMixin):
    __tablename__ = "story_sources"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str | None] = mapped_column(String(50))
    weight: Mapped[float] = mapped_column(Float, server_default="1.0", nullable=False)

    story: Mapped[Story] = relationship("Story", back_populates="story_sources")

    __table_args__ = (
        UniqueConstraint("story_id", "article_id", name="uq_story_sources_story_article"),
        Index("ix_story_sources_story_id", "story_id"),
    )


class Translation(Base, TimestampMixin):
    __tablename__ = "translations"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    target_lang: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    terminology: Mapped[dict[str, Any]] = mapped_column(json_col(), server_default="'{}'", nullable=False)
    engine: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[float | None] = mapped_column(Float)

    story: Mapped[Story] = relationship("Story", back_populates="translations")

    __table_args__ = (
        UniqueConstraint("story_id", "target_lang", name="uq_translations_story_lang"),
        Index("ix_translations_story_id", "story_id"),
    )


class Content(Base, TimestampMixin):
    __tablename__ = "content"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    format: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(json_col(), server_default="'{}'", nullable=False)
    locale: Mapped[str | None] = mapped_column(String(10))
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)

    story: Mapped[Story] = relationship("Story", back_populates="content")

    __table_args__ = (
        UniqueConstraint("story_id", "format", "locale", name="uq_content_story_format_locale"),
        Index("ix_content_story_id", "story_id"),
    )


class QualityCheck(Base, TimestampMixin):
    __tablename__ = "quality_checks"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    issues: Mapped[list[str]] = mapped_column(json_col(), server_default="'[]'", nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(json_col(), server_default="'{}'", nullable=False)

    story: Mapped[Story] = relationship("Story", back_populates="quality_checks")

    __table_args__ = (
        Index("ix_quality_checks_story_id", "story_id"),
        Index("ix_quality_checks_status", "status"),
    )


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048))
    mime: Mapped[str | None] = mapped_column(String(100))
    bytes_size: Mapped[int | None] = mapped_column(Integer)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", json_col(), server_default="'{}'", nullable=False)

    story: Mapped[Story] = relationship("Story", back_populates="assets")

    __table_args__ = (
        Index("ix_assets_story_id", "story_id"),
        Index("ix_assets_kind", "kind"),
    )


class Render(Base, TimestampMixin):
    __tablename__ = "renders"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)
    output: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(json_col(), server_default="'{}'", nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)

    story: Mapped[Story] = relationship("Story", back_populates="renders")

    __table_args__ = (
        UniqueConstraint("story_id", "output", name="uq_renders_story_output"),
        Index("ix_renders_story_id", "story_id"),
        Index("ix_renders_output", "output"),
        Index("ix_renders_status", "status"),
    )
