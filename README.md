# News Engine

Modular self-hosted gaming news engine. Collects news from RSS/Atom, extracts facts, clusters into Stories, translates to Russian, and renders to multiple outputs.

## Quick start

```bash
python -m pip install -e .[dev]
cp .env.example .env
docker compose up -d
alembic upgrade head
news-engine --help
```

## License

MIT
