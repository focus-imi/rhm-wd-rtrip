#!/usr/bin/env python3
"""Phase 2: scrape author pages discovered from monument details."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from common import CACHE_HTML, EXPORT, ThrottledFetcher, append_jsonl, author_url, ensure_dirs, write_jsonl
from parse import parse_author


def load_ids(path: Path) -> list[int]:
    return [int(x) for x in path.read_text(encoding="utf-8").split() if x.strip().isdigit()]


def already_done(jsonl_path: Path) -> set[int]:
    done: set[int] = set()
    if not jsonl_path.exists():
        return done
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "id" in row and not row.get("_error"):
                done.add(int(row["id"]))
    return done


def author_ids_from_monuments(path: Path) -> set[int]:
    ids: set[int] = set()
    if not path.exists():
        return ids
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            for aid in row.get("author_ids") or []:
                ids.add(int(aid))
            for a in row.get("authors") or []:
                if "id" in a:
                    ids.add(int(a["id"]))
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--rebuild-only", action="store_true")
    args = ap.parse_args()

    ensure_dirs()
    side = EXPORT / "author_ids.txt"
    ids = set()
    if side.exists():
        ids.update(load_ids(side))
    ids |= author_ids_from_monuments(EXPORT / "monuments.jsonl")
    ids_list = sorted(ids)
    if args.limit:
        ids_list = ids_list[: args.limit]

    out_path = EXPORT / "authors.jsonl"
    print(f"authors to fetch: {len(ids_list)}", flush=True)

    if args.rebuild_only:
        rows = []
        for aid in ids_list:
            html = (CACHE_HTML / "author" / f"{aid}.html").read_text(encoding="utf-8", errors="replace")
            rows.append(parse_author(html, aid))
        write_jsonl(out_path, rows)
        print(f"rebuilt {len(rows)} → {out_path}")
        return 0

    fetcher = ThrottledFetcher(delay_s=args.delay)
    done = already_done(out_path)
    todo = [i for i in ids_list if i not in done]
    print(f"done={len(done)} todo={len(todo)} delay={fetcher.delay_s}s", flush=True)

    t0 = time.time()
    ok = err = 0
    for n, aid in enumerate(todo, 1):
        try:
            html = fetcher.get(
                author_url(aid),
                cache_path=CACHE_HTML / "author" / f"{aid}.html",
                force=args.force,
            )
            row = parse_author(html, aid)
            append_jsonl(out_path, row)
            ok += 1
        except Exception as e:
            append_jsonl(out_path, {"id": aid, "_error": str(e)})
            err += 1
            print(f"  ERROR author={aid}: {e}", flush=True)

        if n % 25 == 0 or n == len(todo):
            elapsed = time.time() - t0
            rate = n / elapsed if elapsed else 0
            eta = (len(todo) - n) / rate if rate else 0
            print(
                f"  {n}/{len(todo)} ok={ok} err={err} "
                f"fetched={fetcher.fetched} cached={fetcher.cached} eta={eta/60:.1f}m",
                flush=True,
            )

    summary = {
        "authors": len(already_done(out_path)),
        "this_run_ok": ok,
        "this_run_err": err,
        "fetched": fetcher.fetched,
        "cached": fetcher.cached,
        "elapsed_s": round(time.time() - t0, 1),
    }
    (EXPORT / "phase2_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if err == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
