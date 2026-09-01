# News Engine

A modular, self-hosted pipeline that collects gaming news from RSS/Atom feeds, extracts facts, clusters them into stories, translates to Russian, and renders to multiple outputs (card, Telegram, VK, video). Fact-first: the source article and verified facts are the source of truth; content is derived.

## Language

**Source**:
A publisher or feed that provides news items. Has a URL, publisher name, author, language, and feed URL.
_Avoid_: publisher, outlet

**Article**:
A single fetched news item from a Source — the raw extracted title, text, author, date, and metadata.
_Avoid_: post, item

**Fact**:
A single verifiable claim extracted from an Article, tied to a Story. Has a type (e.g. release_date), confidence, entities, and evidence. Facts are the source of truth, not the rendered content.
_Avoid_: claim, statement

**Entity**:
A named thing mentioned in an Article or Fact — a game, company, person, platform. Entities are canonicalized via aliases (e.g. "GTA 6" → "Grand Theft Auto 6").
_Avoid_: name, tag

**Story**:
The central normalized object. A cluster of one or more Articles (from possibly multiple Sources) about the same event, with its Facts, Entities, importance, translation, content, quality, assets, and render. Everything derives from a Story.
_Avoid_: news item, event, cluster

**Cluster**:
A group of Articles determined to describe the same event, merged into one Story. Clustering resolves duplicate and multi-source coverage.
_Avoid_: group, bucket

**Dedup**:
Removal of near-identical Articles before clustering. Distinct from clustering: dedup removes exact/near-exact copies; clustering merges related-but-different coverage.
_Avoid_: deduplication

**Importance**:
A deterministic score (0-100) ranking how newsworthy a Story is, based on source weight, number of independent sources, freshness, and other signals. Not LLM-based in the first version.
_Avoid_: priority, rank

**Translation**:
The conversion of a Story's text to Russian, preserving gaming terminology via the Terminology engine. Uses OPUS-MT + CTranslate2.
_Avoid_: localization

**Terminology**:
A YAML database of gaming terms and their canonical Russian translations (e.g. "shooter" → "шутер"). Applied during and after Translation.
_Avoid_: glossary, dictionary

**Editorial**:
The Russian-language editorial pass that makes translated text read naturally — fixing word order, removing filler phrases, applying humanizer/ru-text principles.
_Avoid_: copyediting, proofreading

**Quality**:
A deterministic Russian text quality score (0-100) with explainable metrics (sentence length, repetition, burden). Low scores trigger repair.
_Avoid_: score, grade

**Content**:
The derived, formatted output blocks for a Story — headline, deck, body, telegram, vk, card. Content is derived from the Story, never the source of truth.
_Avoid_: copy, post

**Asset**:
A collected media item for a Story — an image or video, deduplicated and scored for quality and relevance.
_Avoid_: media, image

**Render**:
A produced output artifact from a Story — a Card PNG, Telegram post, VK carousel, or video. Renders are derived from Content and Assets.
_Avoid_: output, artifact

## Relationships

- A **Source** provides many **Articles**
- An **Article** belongs to exactly one **Source**
- A **Cluster** groups one or more **Articles** into one **Story**
- A **Story** contains many **Facts** and **Entities**
- A **Fact** belongs to exactly one **Story** and references a **Source**
- A **Story** has one **Translation**, one **Editorial** pass, and one **Quality** score
- A **Story** produces one **Content** object
- A **Story** collects many **Assets**
- A **Story** produces many **Renders** (card, telegram, vk, video)

## Example dialogue

> **Dev:** "When we cluster two Articles about the same game into a Story, do we keep both Facts?"
> **Domain expert:** "Yes — each Fact keeps its own Source and evidence. The Story aggregates them, but the Facts remain the source of truth."
> **Dev:** "So Content is just a formatted view of the Story's Facts?"
> **Domain expert:** "Exactly. Content is derived. If a Fact changes, we re-render Content — we never edit Content directly."

## Flagged ambiguities

- "news item" / "event" / "cluster" were all used to mean **Story** — resolved: **Story** is the canonical term for the central object; **Cluster** is the grouping operation that produces it.
- "claim" and "statement" were used for **Fact** — resolved: **Fact** is a verified claim with confidence and evidence.
- "output" was used for both **Content** and **Render** — resolved: **Content** is the derived text blocks; **Render** is the produced artifact (PNG/post/carousel/video).
