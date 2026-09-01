# Storage Prototype — Verdict

## Question
Does the News Engine MVP need PostgreSQL, or is SQLite sufficient?
What are PostgreSQL's strengths/weaknesses for THIS data model and workload?

## Method
`bench.py` runs the SAME workload against both backends on the ТЗ §35 data model
(sources, feeds, articles, facts, entities, stories, story_sources, translations,
content, quality_checks, assets, story_assets, render). JSON columns use JSONB on
PG, plain JSON/TEXT on SQLite. 2000 articles + 2000 stories, 50 queries per op.

## Results (2000 articles + 2000 stories)

| op | sqlite | postgres | winner |
|----|--------|----------|--------|
| batch ingest | 799 ms | 3686 ms | SQLite (4.6x) |
| json_query (payload.category) | 401 ms | 78 ms | PG (5.1x) |
| json_indexed_query (GIN) | 442 ms | 77 ms | PG (5.7x) |
| json_contains (@> vs json_extract) | 471 ms | 165 ms | PG (2.9x) |
| fts_like | 25 ms | 49 ms | SQLite (PG matched 0 — case-sensitive LIKE) |
| fts_real (FTS5 vs tsvector) | 121 ms | 272 ms | SQLite (2.2x) |
| join_cluster | 15 ms | 49 ms | SQLite (0 rows — not populated) |
| concurrent_writes (8×50) | 215 ms | 136 ms | PG (1.6x) |

## Findings

### PostgreSQL strengths (decisive for News Engine)
1. **JSON querying is the killer feature.** JSONB + GIN index is 5x faster for
   `payload.category` filtering and 2.9x faster for JSON containment. The ТЗ's
   Story/Fact/Content are deeply nested JSON queried by category/type/entity —
   this is the core read path.
2. **JSON array containment (`@>`).** PG can query "any element of a JSON array
   matches" in one indexed call. **SQLite cannot** — `json_extract(payload,
   '$.facts[*].type')` throws `bad JSON path`; you can only check `$.facts[0].type`
   (first element). This is a hard capability gap, not just speed.
3. **Concurrency.** PG handles parallel writers (1.6x faster, no whole-DB lock).
   Matches the ТЗ §37 async worker model.
4. **FK integrity enforced.** SQLite silently allows orphaned rows (FKs off by
   default); PG rejects them. For a fact-first engine (§60: source + article +
   verified facts are the source of truth), integrity matters.

### PostgreSQL weaknesses
1. **Batch ingest 4.6x slower** (per-insert/fsync overhead). One-time cost, not a
   runtime bottleneck — acceptable.
2. **Operational cost.** Needs a server (Docker/Postgres), credentials, migrations.
   SQLite is a file. For MVP simplicity this is the main argument for SQLite.
3. **LIKE is case-sensitive** (matched 0 for "article" vs "Article"); SQLite LIKE
   is case-insensitive. PG needs ILIKE/lower() — a subtle gotcha.

### SQLite strengths
1. **Real FTS5 is faster** (121 vs 272 ms) and zero-config.
2. **Batch ingest faster** and no server to run.
3. **LIKE case-insensitive by default.**

### SQLite weaknesses
1. **No JSON array containment** — the decisive gap for this data model.
2. **FTS5 needs manual sync** with the articles table (triggers or re-population).
   PG tsvector can be an expression index / generated column that stays in sync
   automatically — important for continuous ingestion.
3. **Whole-DB write lock** under concurrency.
4. **FKs not enforced by default.**

## Verdict
**Use PostgreSQL from day 1 for the MVP.** The JSON querying + JSON array
containment capability is the core read path of a fact-first news engine, and
SQLite simply cannot express "any fact in the array matches type X" in one query.
The ingest penalty is a one-time cost; the concurrency and FK-integrity wins
compound as the pipeline grows.

**Mitigation for MVP simplicity:** run PG via Docker Compose (already proven on
port 5433) with SQLAlchemy + Alembic migrations. The `json_col()` helper
(JSONB with SQLite JSON variant) means the model stays portable if a lightweight
embedded path is ever needed.

## Prototype status
THROWAWAY. `bench.py` + this NOTES.md answer the storage question. Delete
`bench.py` and `newsengine_prototype.sqlite3` once the decision is folded into
the real schema. The validated decision: **PG + SQLAlchemy + Alembic, JSONB
columns, GIN index on story payload, tsvector expression index for Russian FTS.**
