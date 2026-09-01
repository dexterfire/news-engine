"""Domain models and protocols for News Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Article:
    id: str
    source_id: str
    title: str
    url: str
    published_at: datetime
    language: str
    text: str | None = None
    author: str | None = None
    entities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    feed_url: str | None = None


@dataclass(frozen=True)
class Fact:
    id: str
    story_id: str
    source_id: str
    text: str
    type: str
    confidence: float
    entities: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Story:
    id: str
    title: str
    summary: str
    category: str
    importance: float
    sources: list[str] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    original_language: str = "en"
    translation: dict[str, Any] = field(default_factory=dict)
    content: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    assets: list[dict[str, Any]] = field(default_factory=list)
    render: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
