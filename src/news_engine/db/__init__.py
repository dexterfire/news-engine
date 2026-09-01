"""Database layer: SQLAlchemy engine, session, base, and JSON column helper."""

from __future__ import annotations

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def json_col() -> TypeDecorator:
    """Return a JSON column type that uses JSONB on PostgreSQL and plain JSON elsewhere."""
    return JSONB().with_variant(JSON(), "sqlite")


class Json(TypeDecorator):
    """Portable JSON column: JSONB on Postgres, native JSON on SQLite."""
    impl = JSON
    cache_ok = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())
