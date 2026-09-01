# News Engine — AGENTS.md

Modular self-hosted gaming news engine. Collects news from RSS/Atom, extracts facts, clusters into Stories, translates to Russian, and renders to multiple outputs (card, Telegram, VK, video). Fact-first: the source article and verified facts are the source of truth; content is derived.

## Domain language

Read `CONTEXT.md` before working. Use its glossary vocabulary (Source, Article, Fact, Entity, Story, Cluster, Dedup, Importance, Translation, Terminology, Editorial, Quality, Content, Asset, Render) and respect the ADRs in `docs/adr/`.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues in `dexterfire/news-engine`, operated via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles mapped to label strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
