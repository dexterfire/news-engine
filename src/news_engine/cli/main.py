"""News Engine CLI entry point."""

import click

from news_engine import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Modular self-hosted gaming news engine."""


@main.command()
def hello() -> None:
    """Placeholder command for T00."""
    click.echo("News Engine CLI ready.")


if __name__ == "__main__":
    main()
