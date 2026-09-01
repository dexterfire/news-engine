# Clustering Prototype — Verdict

## Question
Does a deterministic (no-LLM) dedup + story-clustering model (ТЗ §10 Variant D:
title similarity + entity overlap + publication time + keyword overlap) correctly
merge multiple publications about the same event into one Story, and keep
different events separate — across the ТЗ §46 test cases?

## Method
`cluster.py` (pure logic) + `tui.py` (throwaway TUI shell). Deterministic
pipeline: `dedup` (near-exact removal, threshold 0.90) then `cluster`
(Union-Find, threshold 0.55, 7-day window). Weights: title 0.45, entity 0.30,
keyword 0.15, time 0.10. Signals: token-Jaccard title, entity Jaccard, keyword
Jaccard, linear time decay.

## Results (ТЗ §46 cases)
| case | input | kept | clusters | expected | result |
|------|-------|------|----------|----------|--------|
| 1. одна новость | 1 | 1 | 1 | 1 | PASS |
| 2. одна новость из 5 источников | 5 | 5 | 1 | 1 | PASS |
| 3. две разные новости об одной игре | 2 | 2 | 2 | 2 | PASS |
| 4. одинаковая новость с разными заголовками | 2 | 2 | 1 | 1 | PASS |
| 11. конфликтующие источники | 2 | 2 | 1 | 2 | **FAIL** |
| 12. старое событие (вне окна) | 2 | 1 | 1 | 2 | **FAIL** |
| 13. очень важное событие (много источников) | 4 | 4 | 3 | 1 | **FAIL** |
| 20. несколько новостей в carousel | 4 | 4 | 4 | 4 | PASS |

## Findings (bugs in the idea, not the code)

### 1. Entity alias resolution is REQUIRED (case 13)
"GTA 6" and "Grand Theft Auto 6" are the same entity but never match — title
similarity 0.14 (no shared tokens after stopword removal), so the article
doesn't merge. **Gaming news is full of abbreviations** (GTA, DLC, FPS, RPG,
MMO). The deterministic model needs an entity alias table / canonicalization
(GTA 6 → grand theft auto 6) BEFORE similarity. This is a hard requirement, not
a nice-to-have.

### 2. Entity overlap is too heavy a signal — merges conflicting claims (case 11)
"Elden Ring DLC delayed to 2027" vs "Elden Ring DLC releasing this year":
entity=1.00 + time=1.00 pushed pair to 0.59 (> 0.55), merging two CONTRADICTORY
claims into one Story. **Two articles about the same game are not necessarily
the same story.** The model needs either (a) a claim/contradiction signal
(extract the assertion, compare for conflict), or (b) lower entity weight so
title/keyword differences dominate. This is the hardest open problem — ТЗ §5
explicitly wants a `conflict` flag on facts, which the clustering layer must
feed.

### 3. Dedup ignores the time window (case 12)
Two "Starfield expansion announced" articles 30 days apart: dedup (threshold
0.90, no time check) removed one, collapsing two temporally-separated events
into one. **Dedup must respect the same time window as clustering** — a
near-identical title 30 days later is a NEW event (re-announcement), not a
duplicate.

### 4. Threshold sensitivity (case 11 vs 13)
pair=0.59 merged conflicting claims (case 11) while pair=0.40-0.47 failed to
merge same-event articles (case 13). A single global threshold can't satisfy
both. **Suggests per-signal gating** (e.g. require title OR entity above a floor,
then combine) rather than one weighted sum.

## What works
- Simple cases (1, 2, 3, 4, 20) cluster correctly with the weighted sum.
- Union-Find gives transitive clustering (5 sources → 1 story) cleanly.
- Deterministic, no LLM, fast — matches ТЗ §53 MVP constraint.

## Verdict
The deterministic weighted-sum approach is a **good MVP foundation but not
production-ready as-is**. Three concrete gaps must be closed before it can
correctly cluster real gaming news:
1. **Entity alias resolution** (abbreviations → canonical names) — mandatory.
2. **Claim/contradiction handling** so conflicting articles don't merge.
3. **Time-window-aware dedup** (dedup must not collapse re-announcements).

Recommended next step: prototype an **entity alias layer** (gaming term →
canonical) and a **claim-extraction + conflict signal**, then re-run these cases.
The `conflict` flag from ТЗ §5 should feed back into clustering.

## Prototype status
THROWAWAY. `tui.py` is the throwaway shell; `cluster.py` is the portable logic
worth keeping (lift into the real module once the gaps above are addressed).
Delete `tui.py` when done; keep `cluster.py` as the seed of the real
`clustering` module.
