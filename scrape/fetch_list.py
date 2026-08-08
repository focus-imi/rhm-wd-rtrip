#!/usr/bin/env python3
"""Phase 0b: list pagination cross-check against map census."""

from __future__ import annotations

import argparse
import json
import math
import sys

from common import CACHE_HTML, EXPORT, ThrottledFetcher, ensure_dirs, list_url
from parse import parse_list_ids, parse_list_total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--pages", type=int, default=None, help="Override page count")
    args = ap.parse_args()

    ensure_dirs()
    fetcher = ThrottledFetcher(delay_s=args.delay)

    # Page 1 for total
    html1 = fetcher.get(list_url(1), cache_path=CACHE_HTML / "list" / "page_001.html", force=args.force)
    total = parse_list_total(html1) or 1121
    pages = args.pages or math.ceil(total / 10)
    print(f"list total={total} pages={pages}", flush=True)

    ids: set[int] = set(parse_list_ids(html1))
    for page in range(2, pages + 1):
        cache = CACHE_HTML / "list" / f"page_{page:03d}.html"
        html = fetcher.get(list_url(page), cache_path=cache, force=args.force)
        found = parse_list_ids(html)
        ids.update(found)
        if page % 20 == 0 or page == pages:
            print(f"  page {page}/{pages} unique_so_far={len(ids)}", flush=True)

    map_ids_path = EXPORT / "canonical_ids.txt"
    map_ids = set()
    if map_ids_path.exists():
        map_ids = {int(x) for x in map_ids_path.read_text().split() if x}

    only_list = sorted(ids - map_ids)
    only_map = sorted(map_ids - ids)
    union = sorted(ids | map_ids)

    # Prefer union as canonical if list found extras
    (EXPORT / "list_ids.txt").write_text("\n".join(map(str, sorted(ids))) + "\n", encoding="utf-8")
    (EXPORT / "canonical_ids.txt").write_text("\n".join(map(str, union)) + "\n", encoding="utf-8")

    summary = {
        "list_total_reported": total,
        "list_unique_ids": len(ids),
        "map_unique_ids": len(map_ids),
        "union": len(union),
        "only_list": only_list,
        "only_map": only_map,
        "fetched": fetcher.fetched,
        "cached": fetcher.cached,
    }
    (EXPORT / "phase0_list_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("only_list", "only_map")}, indent=2))
    if only_list:
        print(f"only_list ({len(only_list)}): {only_list[:30]}")
    if only_map:
        print(f"only_map ({len(only_map)}): {only_map[:30]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
