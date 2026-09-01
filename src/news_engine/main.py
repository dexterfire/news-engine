"""FastAPI entrypoint: /health + /admin/* routers."""

from __future__ import annotations

from fastapi import FastAPI

from news_engine.api.routers import articles, feeds, sources

app = FastAPI(
    title="News Engine",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Admin CRUD surface (storage layer). Future /stories API lives elsewhere.
app.include_router(sources.router, prefix="/admin")
app.include_router(feeds.router, prefix="/admin")
app.include_router(articles.router, prefix="/admin")
