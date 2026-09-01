"""
PROTOTYPE — News Engine storage backend comparison (SQLite vs PostgreSQL).

QUESTION:
  Does the News Engine MVP need PostgreSQL, or is SQLite sufficient?
  What are PostgreSQL's strengths/weaknesses for THIS data model and workload?

WHY THIS SHAPE:
  The TZ (§35) defines a JSON-heavy relational model (sources, feeds, articles,
  facts, entities, stories, story_sources, translations, content, quality_checks,
  assets, story_assets, render). The workload is batch ingestion + story clustering
  + fact querying + Russian full-text search + concurrent async workers.

  This prototype runs the SAME workload against both backends and reports the
  differences, so we can decide whether the MVP's storage layer needs PG's power
  (JSONB, tsvector FTS, concurrency) or SQLite is enough.

  This is THROWAWAY code. The verdict goes in NOTES.md next to this file.

USAGE:
  python bench.py            # runs both backends, prints comparison
  python bench.py sqlite     # only sqlite
  python bench.py postgres   # only postgres (needs PG on localhost:5433)

  PostgreSQL test container (if not already running):
    docker run -d --name newsengine-pg -e POSTGRES_PASSWORD=prototype \
      -e POSTGRES_USER=prototype -e POSTGRES_DB=newsengine \
      -p 5433:5432 postgres:16-alpine
"""

import json
import os
import random
import sqlite3
import sys
import time
from dataclasses import dataclass, field

import sqlalchemy as sa
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey,
    JSON, Table, Index, func, select, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# ---------------------------------------------------------------------------
# 1. DATA MODEL — mirrors TZ §35 (sources, feeds, articles, facts, entities,
#    stories, story_sources, translations, content, quality_checks, assets,
#    story_assets, render). JSON columns are the crux: PG uses JSONB, SQLite
#    stores JSON as TEXT.
# ---------------------------------------------------------------------------

Base = declarative_base()


def json_col():
    """JSONB on PostgreSQL, plain JSON (TEXT) elsewhere. The column type choice
    is itself a finding: PG's JSONB enables GIN indexing + @> querying, which
    plain JSON (or SQLite TEXT) cannot do."""
    return JSONB().with_variant(JSON(), "sqlite")


class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    source_id = Column(String, unique=True, index=True)
    url = Column(String)
    publisher = Column(String, index=True)
    language = Column(String)
    feed_url = Column(String)


class Feed(Base):
    __tablename__ = "feeds"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    url = Column(String, unique=True)
    last_fetched = Column(DateTime)


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    url = Column(String, unique=True)
    title = Column(String, index=True)
    text = Column(Text)
    author = Column(String)
    published_at = Column(DateTime, index=True)
    language = Column(String)
    # normalized title hash for dedup (TZ §9 Level 2)
    title_hash = Column(String, index=True)


class Fact(Base):
    __tablename__ = "facts"
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), index=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    text = Column(Text)
    type = Column(String, index=True)          # release_date, price, ...
    confidence = Column(Float)
    entities = Column(json_col())                     # list of entity names
    evidence = Column(json_col())                     # nested evidence object


class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    kind = Column(String, index=True)           # game, studio, platform, ...
    aliases = Column(json_col())


class Story(Base):
    __tablename__ = "stories"
    id = Column(Integer, primary_key=True)
    story_id = Column(String, unique=True, index=True)
    category = Column(String, index=True)
    importance = Column(Integer, index=True)
    original_language = Column(String)
    # nested payload (TZ §3) — the crux of the JSON comparison
    payload = Column(json_col())
    created_at = Column(DateTime, index=True)
    updated_at = Column(DateTime)


class StorySource(Base):
    __tablename__ = "story_sources"
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), index=True)
    source_id = Column(Integer, ForeignKey("sources.id"))


class Translation(Base):
    __tablename__ = "translations"
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), index=True)
    target_language = Column(String)
    text = Column(Text)
    provider = Column(String)
    cache_key = Column(String, unique=True, index=True)


class Content(Base):
    __tablename__ = "content"
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), index=True)
    headline = Column(String)
    deck = Column(Text)
    body = Column(Text)
    telegram = Column(Text)
    vk = Column(Text)
    card = Column(json_col())                          # nested card config


class QualityCheck(Base):
    __tablename__ = "quality_checks"
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), index=True)
    score = Column(Integer)
    issues = Column(json_col())
    metrics = Column(json_col())


class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)
    kind = Column(String, index=True)            # image, video
    width = Column(Integer)
    height = Column(Integer)
    score = Column(Float)
    meta = Column(json_col())


class StoryAsset(Base):
    __tablename__ = "story_assets"
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))


class Render(Base):
    __tablename__ = "render"
    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, ForeignKey("stories.id"), index=True)
    kind = Column(String, index=True)            # card, video, telegram, vk
    status = Column(String)
    output_path = Column(String)
    meta = Column(json_col())


# ---------------------------------------------------------------------------
# 2. WORKLOAD — realistic News Engine operations. Each returns a timing dict.
# ---------------------------------------------------------------------------

def _make_story_payload(i):
    """A realistic nested Story payload (TZ §3)."""
    return {
        "story_id": f"story-{i}",
        "category": random.choice(["release", "update", "esports", "hardware", "industry"]),
        "importance": random.randint(40, 99),
        "sources": [
            {"source_id": f"src-{random.randint(1, 20)}", "publisher": f"pub-{random.randint(1, 20)}"}
            for _ in range(random.randint(1, 4))
        ],
        "facts": [
            {
                "text": f"fact text {i}-{j}",
                "type": random.choice(["release_date", "price", "feature", "platform"]),
                "confidence": round(random.random(), 2),
                "entities": [f"game-{random.randint(1, 50)}", f"studio-{random.randint(1, 20)}"],
            }
            for j in range(random.randint(1, 5))
        ],
        "entities": [f"game-{random.randint(1, 50)}" for _ in range(random.randint(1, 3))],
        "original_language": "en",
        "translation": {"language": "ru", "provider": "opus-mt"},
        "content": {
            "headline": f"Headline {i}",
            "deck": f"Deck {i}",
            "body": f"Body {i}",
        },
        "quality": {"score": random.randint(60, 100), "issues": []},
        "assets": [{"kind": "image", "url": f"https://img/{i}.png", "score": 0.9}],
        "render": {"kind": "card", "status": "done"},
    }


def workload_ingest(session, n_articles, n_stories):
    """Batch ingestion: insert sources, articles, stories with nested JSON."""
    t0 = time.perf_counter()
    # sources
    for i in range(20):
        session.add(Source(source_id=f"src-{i}", url=f"https://src{i}.com",
                           publisher=f"pub-{i}", language="en", feed_url=f"https://src{i}.com/rss"))
    session.flush()  # ensure sources get ids before articles reference them
    # articles
    for i in range(n_articles):
        session.add(Article(source_id=random.randint(1, 20),
                            url=f"https://src.com/a{i}", title=f"Article {i}",
                            text=f"Full text of article {i} " * 20,
                            author=f"author-{i}", published_at=func.now(),
                            language="en", title_hash=f"h{i}"))
    # stories with nested JSON payload
    for i in range(n_stories):
        session.add(Story(story_id=f"story-{i}", category=random.choice(
            ["release", "update", "esports", "hardware", "industry"]),
            importance=random.randint(40, 99), original_language="en",
            payload=_make_story_payload(i), created_at=func.now(), updated_at=func.now()))
    session.commit()
    return {"op": "ingest", "articles": n_articles, "stories": n_stories,
            "ms": (time.perf_counter() - t0) * 1000}


def workload_json_query(session, n_queries):
    """Query nested JSON: find stories where payload.category == 'release'."""
    t0 = time.perf_counter()
    count = 0
    for _ in range(n_queries):
        # dialect-agnostic: use JSON extract. PG JSONB has @> operator; SQLite
        # uses json_extract. We use SQLAlchemy's JSON accessor where possible.
        rows = session.execute(
            select(Story.id).where(Story.payload["category"].astext == "release")
        ).fetchall()
        count += len(rows)
    return {"op": "json_query", "queries": n_queries, "matched": count,
            "ms": (time.perf_counter() - t0) * 1000}


def workload_json_indexed_query(session, n_queries):
    """Query nested JSON with an index hint (PG JSONB GIN). SQLite has no JSON index."""
    t0 = time.perf_counter()
    count = 0
    for _ in range(n_queries):
        rows = session.execute(
            select(Story.id).where(Story.payload["category"].astext == "release")
        ).fetchall()
        count += len(rows)
    return {"op": "json_indexed_query", "queries": n_queries, "matched": count,
            "ms": (time.perf_counter() - t0) * 1000}


def workload_fts(session, n_queries):
    """Full-text search over article text (Russian news)."""
    t0 = time.perf_counter()
    count = 0
    for _ in range(n_queries):
        term = f"article {random.randint(1, 100)}"
        rows = session.execute(
            select(Article.id).where(Article.title.like(f"%{term}%"))
        ).fetchall()
        count += len(rows)
    return {"op": "fts_like", "queries": n_queries, "matched": count,
            "ms": (time.perf_counter() - t0) * 1000}


def workload_json_contains(session, n_queries):
    """JSON containment: find stories whose payload contains a specific nested
    fact type. PG uses the @> operator (GIN-indexed); SQLite has no equivalent
    and must scan + json_extract."""
    t0 = time.perf_counter()
    count = 0
    for _ in range(n_queries):
        target = random.choice(["release_date", "price", "feature", "platform"])
        if session.bind.dialect.name == "postgresql":
            rows = session.execute(
                select(Story.id).where(
                    Story.payload["facts"].op("@>")(json.dumps([{"type": target}]))
                )
            ).fetchall()
        else:
            # SQLite: scan all and json_extract the facts array (no wildcard
            # support — this is a known SQLite limitation we want to surface)
            rows = session.execute(
                select(Story.id).where(
                    func.json_extract(Story.payload, "$.facts[0].type") == target
                )
            ).fetchall()
        count += len(rows)
    return {"op": "json_contains", "queries": n_queries, "matched": count,
            "ms": (time.perf_counter() - t0) * 1000}


def workload_fts5(session, n_queries):
    """Real full-text search. PG uses tsvector (Russian config); SQLite uses
    FTS5. Both are set up in run_backend()."""
    t0 = time.perf_counter()
    count = 0
    for _ in range(n_queries):
        # term matches the word "article" present in every generated title
        term = "article"
        if session.bind.dialect.name == "postgresql":
            rows = session.execute(
                text("SELECT id FROM articles WHERE to_tsvector('russian', title) @@ plainto_tsquery('russian', :t)"),
                {"t": term}
            ).fetchall()
        else:
            rows = session.execute(
                text("SELECT rowid FROM articles_fts WHERE articles_fts MATCH :t"),
                {"t": term}
            ).fetchall()
        count += len(rows)
    return {"op": "fts_real", "queries": n_queries, "matched": count,
            "ms": (time.perf_counter() - t0) * 1000}


def workload_concurrent_writes(session_factory, n_workers, n_each):
    """Simulate concurrent async workers writing stories (TZ §37)."""
    import threading
    results = []
    errors = []

    def worker(wid):
        try:
            s = session_factory()
            t0 = time.perf_counter()
            for i in range(n_each):
                s.add(Story(story_id=f"w{wid}-{i}", category="concurrent",
                            importance=50, original_language="en",
                            payload={"story_id": f"w{wid}-{i}", "category": "concurrent"},
                            created_at=func.now(), updated_at=func.now()))
            s.commit()
            results.append({"worker": wid, "ms": (time.perf_counter() - t0) * 1000})
            s.close()
        except Exception as e:  # noqa
            errors.append({"worker": wid, "error": str(e)})

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(n_workers)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_ms = (time.perf_counter() - t0) * 1000
    return {"op": "concurrent_writes", "workers": n_workers, "each": n_each,
            "total_ms": total_ms, "errors": errors}


def workload_join_cluster(session, n_queries):
    """Story clustering join: stories + their sources (TZ §10)."""
    t0 = time.perf_counter()
    count = 0
    for _ in range(n_queries):
        rows = session.execute(
            select(Story.story_id, StorySource.source_id)
            .join(StorySource, StorySource.story_id == Story.id)
            .limit(100)
        ).fetchall()
        count += len(rows)
    return {"op": "join_cluster", "queries": n_queries, "rows": count,
            "ms": (time.perf_counter() - t0) * 1000}


# ---------------------------------------------------------------------------
# 3. RUNNER — executes the workload against a backend and reports.
# ---------------------------------------------------------------------------

@dataclass
class BackendResult:
    name: str
    results: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def run_backend(name, url, n_articles=2000, n_stories=2000):
    """Run the full workload against one backend. Returns BackendResult."""
    res = BackendResult(name=name)
    engine = sa.create_engine(url, echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    # Optional: PG-specific JSONB GIN index for the indexed query test
    if name == "postgres":
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_stories_payload_gin "
                "ON stories USING gin (payload jsonb_path_ops)"
            ))
    elif name == "sqlite":
        # SQLite FTS5 virtual table over articles.title (real full-text search).
        # NOTE: FTS5 must be kept in sync with the articles table manually
        # (triggers or re-population) — this is a real operational finding.
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(title)"
            ))

    try:
        s = Session()
        res.results.append(workload_ingest(s, n_articles, n_stories))

        # Populate SQLite FTS5 AFTER ingest (articles now exist)
        if name == "sqlite":
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM articles_fts"))
                conn.execute(text(
                    "INSERT INTO articles_fts(rowid, title) SELECT id, title FROM articles"
                ))

        res.results.append(workload_json_query(s, 50))
        res.results.append(workload_json_indexed_query(s, 50))
        res.results.append(workload_json_contains(s, 50))
        res.results.append(workload_fts(s, 50))
        res.results.append(workload_fts5(s, 50))
        res.results.append(workload_join_cluster(s, 50))
        s.close()

        # concurrency (separate sessions)
        res.results.append(workload_concurrent_writes(Session, n_workers=8, n_each=50))
    except Exception as e:  # noqa
        res.errors.append(str(e))
    finally:
        engine.dispose()
    return res


def fmt_ms(ms):
    return f"{ms:8.1f} ms"


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    pg_url = os.environ.get("NEWSENGINE_PG_URL",
                            "postgresql+psycopg2://prototype:prototype@127.0.0.1:5433/newsengine")
    sqlite_url = "sqlite:///./newsengine_prototype.sqlite3"

    results = []
    if which in ("all", "sqlite"):
        print("=== SQLite ===")
        results.append(run_backend("sqlite", sqlite_url))
    if which in ("all", "postgres"):
        print("=== PostgreSQL ===")
        results.append(run_backend("postgres", pg_url))

    # ---- Report ----
    print("\n" + "=" * 78)
    print("NEWS ENGINE STORAGE PROTOTYPE — SQLite vs PostgreSQL")
    print("=" * 78)

    # Build a table keyed by op
    ops = {}
    for r in results:
        for item in r.results:
            ops.setdefault(item["op"], {})[r.name] = item

    for op, backends in ops.items():
        print(f"\n--- {op} ---")
        for name, item in backends.items():
            detail = {k: v for k, v in item.items() if k not in ("op",)}
            print(f"  {name:10s} {detail}")

    # Errors
    for r in results:
        if r.errors:
            print(f"\n[{r.name}] ERRORS:")
            for e in r.errors:
                print(f"  {e}")

    # ---- Verdict summary ----
    print("\n" + "=" * 78)
    print("VERDICT NOTES (fill in after reviewing)")
    print("=" * 78)
    print("""
  Compare:
  1. JSON querying: PG JSONB (indexed, @> operator) vs SQLite json_extract (no index)
  2. Full-text search: PG tsvector (Russian config) vs SQLite LIKE / FTS5
  3. Concurrency: PG handles parallel writers; SQLite locks the whole DB
  4. Write throughput: batch ingest speed
  5. Operational cost: PG needs a server; SQLite is a file

  Decision: does the MVP need PG, or is SQLite enough?
""")


if __name__ == "__main__":
    main()
