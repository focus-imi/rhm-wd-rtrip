#!/usr/bin/env python3
"""Phase 0: map JSON census → canonical id index."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from common import (
    CACHE_MAP,
    DISTRICT_NAMES,
    EXPORT,
    TYPE_NAMES,
    ThrottledFetcher,
    ensure_dirs,
    map_url,
    write_jsonl,
)
from parse import parse_map_result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ensure_dirs()
    fetcher = ThrottledFetcher(delay_s=args.delay)

    all_rows: list[dict] = []
    by_id: dict[int, dict] = {}

    for t in range(1, 7):
        cache = CACHE_MAP / f"type_{t}.json"
        url = map_url(t)
        print(f"map type={t} ({TYPE_NAMES.get(t)}) …", flush=True)
        data = fetcher.get_json(url, cache_path=cache, force=args.force)
        rows = parse_map_result(data, t)
        print(f"  clusters→ids: {len(rows)}", flush=True)
        for row in rows:
            all_rows.append(row)
            mid = row["id"]
            if mid not in by_id:
                by_id[mid] = row
            else:
                # shouldn't happen across types
                print(f"  WARN duplicate id {mid} in types {by_id[mid]['map_type']} and {t}", flush=True)

    ids = sorted(by_id)
    print(f"unique ids: {len(ids)} range {ids[0]}–{ids[-1]}", flush=True)

    # Write outputs
    ids_path = EXPORT / "canonical_ids.csv"
    with ids_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "map_type", "map_type_name", "lat_map", "lng_map", "media_code_map", "title_map"])
        for mid in ids:
            r = by_id[mid]
            w.writerow(
                [
                    mid,
                    r["map_type"],
                    TYPE_NAMES.get(r["map_type"], ""),
                    r.get("lat_map") or "",
                    r.get("lng_map") or "",
                    r.get("media_code_map") or "",
                    r.get("title_map") or "",
                ]
            )

    write_jsonl(EXPORT / "map_index.jsonl", [by_id[i] for i in ids])
    (EXPORT / "canonical_ids.txt").write_text("\n".join(map(str, ids)) + "\n", encoding="utf-8")

    summary = {
        "unique_ids": len(ids),
        "by_type": {TYPE_NAMES[t]: sum(1 for r in by_id.values() if r["map_type"] == t) for t in range(1, 7)},
        "with_coords": sum(1 for r in by_id.values() if r.get("lat_map") and r.get("lng_map")),
        "fetched": fetcher.fetched,
        "cached": fetcher.cached,
    }
    (EXPORT / "phase0_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"wrote {ids_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
