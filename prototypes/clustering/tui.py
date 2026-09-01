"""
PROTOTYPE — throwaway TUI shell over the clustering logic module.
Drives the deterministic dedup+cluster pipeline through the ТЗ §46 test cases.
The logic lives in cluster.py (portable, pure); this shell is throwaway.

Run:  python tui.py
Keys:
  [n] next test case      [p] prev test case
  [r] run pipeline        [d] toggle dedup on/off
  [+]/[-] cluster threshold   [t] toggle time window
  [q] quit
"""

from __future__ import annotations

import os
import sys
import time

from cluster import Article, Weights, run_pipeline

# ---------------------------------------------------------------------------
# ТЗ §46 test cases mapped to clustering inputs.
# Each case: (name, [Article...], expected_cluster_count)
# ---------------------------------------------------------------------------

DAY = 24 * 3600
NOW = 1_700_000_000.0


def art(aid, title, entities=(), keywords=(), t=0.0):
    return Article(id=aid, title=title, entities=list(entities),
                   keywords=list(keywords), published_at=t)


TEST_CASES = [
    # 1. одна новость -> 1 cluster
    ("1. одна новость",
     [art("a1", "Exodus release date announced", ["Exodus"], ["release"], NOW)],
     1),
    # 2. одна новость из 5 источников -> 1 cluster
    ("2. одна новость из 5 источников",
     [art("a1", "Exodus release date announced", ["Exodus"], ["release"], NOW),
      art("a2", "Exodus launches April 7, 2027", ["Exodus"], ["launch"], NOW + 3600),
      art("a3", "Mass Effect-like Exodus gets release date", ["Exodus"], ["release"], NOW + 7200),
      art("a4", "Exodus: release date revealed", ["Exodus"], ["release"], NOW + 10800),
      art("a5", "Exodus coming April 7", ["Exodus"], ["release"], NOW + 14400)],
     1),
    # 3. две разные новости об одной игре -> 2 clusters
    ("3. две разные новости об одной игре",
     [art("a1", "Exodus release date announced", ["Exodus"], ["release"], NOW),
      art("a2", "Exodus gets new gameplay trailer", ["Exodus"], ["trailer"], NOW + 3600)],
     2),
    # 4. одинаковая новость с разными заголовками -> 1 cluster (dedup)
    ("4. одинаковая новость с разными заголовками",
     [art("a1", "Cyberpunk 2077 patch 2.0 released", ["Cyberpunk"], ["patch"], NOW),
      art("a2", "Cyberpunk 2077 patch 2.0 is out now", ["Cyberpunk"], ["patch"], NOW + 600)],
     1),
    # 11. конфликтующие источники -> 2 clusters (different claims)
    ("11. конфликтующие источники",
     [art("a1", "Elden Ring DLC delayed to 2027", ["Elden Ring"], ["delay"], NOW),
      art("a2", "Elden Ring DLC releasing this year", ["Elden Ring"], ["release"], NOW + 3600)],
     2),
    # 12. старое событие (вне time window) -> 2 clusters
    ("12. старое событие (вне окна)",
     [art("a1", "Starfield expansion announced", ["Starfield"], ["expansion"], NOW),
      art("a2", "Starfield expansion announced", ["Starfield"], ["expansion"], NOW - 30 * DAY)],
     2),
    # 13. очень важное событие (много источников, разные формулировки) -> 1 cluster
    ("13. очень важное событие (много источников)",
     [art("a1", "GTA 6 announced for 2027", ["GTA 6"], ["announce"], NOW),
      art("a2", "Rockstar confirms GTA 6 release window", ["GTA 6", "Rockstar"], ["release"], NOW + 1800),
      art("a3", "GTA 6 coming 2027, Rockstar says", ["GTA 6", "Rockstar"], ["release"], NOW + 3600),
      art("a4", "Grand Theft Auto 6 launch date set", ["GTA 6"], ["launch"], NOW + 5400)],
     1),
    # 20. несколько новостей в carousel -> N clusters (distinct events)
    ("20. несколько новостей в carousel",
     [art("a1", "Exodus release date announced", ["Exodus"], ["release"], NOW),
      art("a2", "Cyberpunk 2077 patch 2.0 released", ["Cyberpunk"], ["patch"], NOW + 600),
      art("a3", "Starfield expansion announced", ["Starfield"], ["expansion"], NOW + 1200),
      art("a4", "Elden Ring DLC delayed", ["Elden Ring"], ["delay"], NOW + 1800)],
     4),
]


# ---------------------------------------------------------------------------
# TUI
# ---------------------------------------------------------------------------

BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"


def render_state(case_idx, dedup_on, threshold, window, result):
    name, articles, expected = TEST_CASES[case_idx]
    kept, clusters = result
    lines = []
    lines.append(f"{BOLD}Test case {case_idx+1}/{len(TEST_CASES)}: {name}{RESET}")
    lines.append(f"{DIM}expected clusters: {expected}{RESET}")
    lines.append("")
    lines.append(f"{BOLD}Input articles ({len(articles)}):{RESET}")
    for a in articles:
        lines.append(f"  {DIM}{a.id}{RESET} {a.title}  "
                     f"[{','.join(a.entities)}] t={a.published_at:.0f}")
    lines.append("")
    lines.append(f"{BOLD}After dedup{RESET} ({'ON' if dedup_on else 'OFF'}): "
                 f"{len(articles)} -> {len(kept)} kept")
    lines.append("")
    lines.append(f"{BOLD}Clusters ({len(clusters)}):{RESET}  "
                 f"{DIM}(threshold={threshold:.2f}, window={window/DAY:.0f}d){RESET}")
    for ci, cl in enumerate(clusters):
        lines.append(f"  {BOLD}Cluster {ci+1}{RESET} ({len(cl)} articles):")
        for a in cl:
            lines.append(f"    - {a.id}: {a.title}")
    lines.append("")
    lines.append(f"{DIM}match: {'YES' if len(clusters)==expected else 'NO'} "
                 f"(expected {expected}){RESET}")
    return "\n".join(lines)


def render_help():
    return (f"{BOLD}[n]{RESET} next  {BOLD}[p]{RESET} prev  "
            f"{BOLD}[r]{RESET} run  {BOLD}[d]{RESET} dedup  "
            f"{BOLD}[+]{RESET}/{BOLD}[-]{RESET} threshold  "
            f"{BOLD}[t]{RESET} window  {BOLD}[q]{RESET} quit")


def main():
    case_idx = 0
    dedup_on = True
    threshold = 0.55
    window = 7 * DAY
    weights = Weights()
    result = run_pipeline(TEST_CASES[case_idx][1], cluster_threshold=threshold,
                          time_window=window)

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(render_state(case_idx, dedup_on, threshold, window, result))
        print()
        print(render_help())
        key = input("\n> ").strip().lower()

        if key == "q":
            break
        elif key == "n":
            case_idx = (case_idx + 1) % len(TEST_CASES)
        elif key == "p":
            case_idx = (case_idx - 1) % len(TEST_CASES)
        elif key == "r":
            pass  # re-run below
        elif key == "d":
            dedup_on = not dedup_on
        elif key == "+":
            threshold = min(1.0, threshold + 0.05)
        elif key == "-":
            threshold = max(0.0, threshold - 0.05)
        elif key == "t":
            window = 30 * DAY if window == 7 * DAY else 7 * DAY
        else:
            continue

        articles = TEST_CASES[case_idx][1]
        if dedup_on:
            result = run_pipeline(articles, cluster_threshold=threshold,
                                  time_window=window)
        else:
            from cluster import cluster
            kept = list(articles)
            clusters = cluster(kept, threshold, weights, window)
            result = (kept, clusters)


if __name__ == "__main__":
    main()
