"""
PROTOTYPE — throwaway logic module for dedup + story clustering.
Question: does a deterministic (no-LLM) model correctly merge multiple
publications about the same event into one Story, and keep different events
separate, across the ТЗ §46 test cases?

This module is PURE (no I/O, no terminal). It is the part worth keeping —
the TUI shell (tui.py) is throwaway. Approach follows ТЗ §10 Variant D:
title similarity + entity overlap + publication time + keyword overlap.

Signals (each returns 0..1):
  title_similarity  — token Jaccard on normalized titles
  entity_overlap    — Jaccard on entity sets
  keyword_overlap   — Jaccard on keyword sets
  time_proximity    — 1 if within window, decays to 0 outside

pair_similarity combines them with configurable weights.
dedup removes near-exact duplicates. cluster groups by Union-Find.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Normalization / tokenization (pure)
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "with",
    "at", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "its", "it", "this", "that", "has", "have", "had", "new", "gets",
    "announced", "launches", "launch", "release", "released", "date",
}


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    t = title.lower()
    t = t.translate(str.maketrans("", "", string.punctuation))
    t = re.sub(r"\s+", " ", t).strip()
    return t


def tokenize(text: str) -> set:
    """Token set, stopwords removed."""
    norm = normalize_title(text)
    return {w for w in norm.split() if w and w not in _STOPWORDS}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


# ---------------------------------------------------------------------------
# Similarity signals (pure, each 0..1)
# ---------------------------------------------------------------------------


def title_similarity(title_a: str, title_b: str) -> float:
    """Token Jaccard on normalized titles."""
    return _jaccard(tokenize(title_a), tokenize(title_b))


def entity_overlap(entities_a: Sequence[str], entities_b: Sequence[str]) -> float:
    """Jaccard on entity sets (e.g. game names, publishers)."""
    return _jaccard(set(entities_a), set(entities_b))


def keyword_overlap(keywords_a: Sequence[str], keywords_b: Sequence[str]) -> float:
    """Jaccard on keyword sets."""
    return _jaccard(set(keywords_a), set(keywords_b))


def time_proximity(time_a: float, time_b: float, window: float) -> float:
    """1.0 if within window (seconds), linear decay to 0 at 2*window."""
    diff = abs(time_a - time_b)
    if diff <= window:
        return 1.0
    if diff >= 2 * window:
        return 0.0
    return 1.0 - (diff - window) / window


# ---------------------------------------------------------------------------
# Article + weighted combination
# ---------------------------------------------------------------------------


@dataclass
class Article:
    id: str
    title: str
    entities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    published_at: float = 0.0  # epoch seconds


@dataclass
class Weights:
    title: float = 0.45
    entity: float = 0.30
    keyword: float = 0.15
    time: float = 0.10


def pair_similarity(a: Article, b: Article, weights: Weights, time_window: float) -> float:
    """Weighted combination of the four signals -> 0..1."""
    return (
        weights.title * title_similarity(a.title, b.title)
        + weights.entity * entity_overlap(a.entities, b.entities)
        + weights.keyword * keyword_overlap(a.keywords, b.keywords)
        + weights.time * time_proximity(a.published_at, b.published_at, time_window)
    )


# ---------------------------------------------------------------------------
# Dedup + clustering (pure)
# ---------------------------------------------------------------------------


def dedup(
    articles: Sequence[Article],
    threshold: float,
    weights: Weights,
    time_window: float,
) -> List[Article]:
    """Remove near-exact duplicates (same event, near-identical title).
    Keeps the first occurrence of each duplicate group."""
    kept: List[Article] = []
    for art in articles:
        is_dup = any(
            pair_similarity(art, k, weights, time_window) >= threshold
            for k in kept
        )
        if not is_dup:
            kept.append(art)
    return kept


def cluster(
    articles: Sequence[Article],
    threshold: float,
    weights: Weights,
    time_window: float,
) -> List[List[Article]]:
    """Union-Find clustering: merge any pair above threshold (transitively)."""
    n = len(articles)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for i in range(n):
        for j in range(i + 1, n):
            if pair_similarity(articles[i], articles[j], weights, time_window) >= threshold:
                union(i, j)

    groups: Dict[int, List[Article]] = {}
    for i, art in enumerate(articles):
        groups.setdefault(find(i), []).append(art)
    return list(groups.values())


def run_pipeline(
    articles: Sequence[Article],
    dedup_threshold: float = 0.90,
    cluster_threshold: float = 0.55,
    weights: Optional[Weights] = None,
    time_window: float = 7 * 24 * 3600,  # 7 days
) -> Tuple[List[Article], List[List[Article]]]:
    """Full deterministic pipeline: dedup then cluster. Returns (kept, clusters)."""
    w = weights or Weights()
    kept = dedup(articles, dedup_threshold, w, time_window)
    clusters = cluster(kept, cluster_threshold, w, time_window)
    return kept, clusters
