"""CLI: init-db, add-source, list-feeds."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from news_engine.api.deps import SessionLocal
from news_engine.models import Feed, Source


@click.group()
def cli() -> None:
    """News Engine operator CLI."""


@cli.command("init-db")
def init_db() -> None:
    """Apply Alembic migrations to the current DATABASE_URL."""
    project_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        click.echo(result.stdout, err=False)
        click.echo(result.stderr, err=True)
        raise SystemExit(result.returncode)
    click.echo("Database schema is up to date.")


@cli.command("add-source")
@click.argument("source_id")
@click.argument("name")
@click.argument("kind")
@click.argument("url")
def add_source(source_id: str, name: str, kind: str, url: str) -> None:
    """Create a Source row."""
    with SessionLocal() as session:
        if session.get(Source, source_id) is not None:
            raise click.ClickException(f"Source '{source_id}' already exists")
        session.add(Source(id=source_id, name=name, kind=kind, url=url))
        session.commit()
    click.echo(f"Source '{source_id}' added.")


@cli.command("list-feeds")
@click.option("--source-id", default=None, help="Filter by source_id.")
def list_feeds(source_id: str | None) -> None:
    """List feeds, ordered by id."""
    with SessionLocal() as session:
        q = session.query(Feed).order_by(Feed.id)
        if source_id is not None:
            q = q.filter(Feed.source_id == source_id)
        feeds = list(q.all())
    if not feeds:
        click.echo("(no feeds)")
        return
    for f in feeds:
        click.echo(f"{f.id}\t{f.source_id}\t{f.title}\t{f.url}")


if __name__ == "__main__":
    cli()
