# Miniflux as a separate Docker service for collection

We run Miniflux as a separate Docker service (own database, REST API, webhook) for the RSS/Atom ingestion layer, rather than embedding a feedparser library in-process. This follows the ТЗ §6 recommendation and keeps the collector decoupled from the pipeline — Miniflux owns feed polling and storage, and the News Engine pulls from its API. The trade-off is an extra service to run, but it buys a battle-tested collector with webhook support and avoids re-implementing feed parsing (ТЗ §50: don't write our own RSS parser).
