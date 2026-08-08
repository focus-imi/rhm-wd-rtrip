#!/usr/bin/env python3
"""Phase 1: detail + print harvest for canonical monument ids."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from common import (
    CACHE_HTML,
    EXPORT,
    ThrottledFetcher,
    append_jsonl,
    detail_url,
    ensure_dirs,
    print_url,
    write_jsonl,
)
from parse import merge_detail_print, parse_detail, parse_print


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=None, help="Seconds between HTTP requests")
    ap.add_argument("--force", action="store_true", help="Refetch HTML even if cached")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids-file", type=Path, default=EXPORT / "canonical_ids.txt")
    ap.add_argument("--skip-print", action="store_true")
    ap.add_argument("--rebuild-only", action="store_true", help="Reparse from cache, no network")
    args = ap.parse_args()

    ensure_dirs()
    if not args.ids_file.exists():
        print(f"missing {args.ids_file}; run fetch_map.py first", file=sys.stderr)
        return 1

    ids = load_ids(args.ids_file)
    if args.limit:
        ids = ids[: args.limit]

    out_path = EXPORT / "monuments.jsonl"
    photo_path = EXPORT / "photo_urls.txt"
    authors_side = EXPORT / "author_ids.txt"

    if args.rebuild_only:
        rows = []
        author_ids: set[int] = set()
        photos: list[str] = []
        for mid in ids:
            detail_html = (CACHE_HTML / "detail" / f"{mid}.html").read_text(encoding="utf-8", errors="replace")
            detail = parse_detail(detail_html, mid)
            print_data = {}
            print_file = CACHE_HTML / "print" / f"{mid}.html"
            if print_file.exists() and not args.skip_print:
                print_data = parse_print(print_file.read_text(encoding="utf-8", errors="replace"))
                detail = merge_detail_print(detail, print_data)
            rows.append(detail)
            author_ids.update(detail.get("author_ids") or [])
            photos.extend(detail.get("photos") or [])
        write_jsonl(out_path, rows)
        photo_path.write_text("\n".join(sorted(set(photos))) + "\n", encoding="utf-8")
        authors_side.write_text("\n".join(map(str, sorted(author_ids))) + "\n", encoding="utf-8")
        print(f"rebuilt {len(rows)} rows → {out_path}")
        return 0

    fetcher = ThrottledFetcher(delay_s=args.delay)
    done = already_done(out_path)
    todo = [i for i in ids if i not in done]
    print(f"canonical={len(ids)} done={len(done)} todo={len(todo)} delay={fetcher.delay_s}s", flush=True)

    author_ids: set[int] = set()
    if authors_side.exists():
        author_ids.update(int(x) for x in authors_side.read_text().split() if x.strip().isdigit())

    photo_urls: set[str] = set()
    if photo_path.exists():
        photo_urls.update(x for x in photo_path.read_text().splitlines() if x.strip())

    t0 = time.time()
    ok = err = 0
    for n, mid in enumerate(todo, 1):
        try:
            detail_html = fetcher.get(
                detail_url(mid),
                cache_path=CACHE_HTML / "detail" / f"{mid}.html",
                force=args.force,
            )
            detail = parse_detail(detail_html, mid)

            if not args.skip_print:
                print_html = fetcher.get(
                    print_url(mid),
                    cache_path=CACHE_HTML / "print" / f"{mid}.html",
                    force=args.force,
                )
                detail = merge_detail_print(detail, parse_print(print_html))

            append_jsonl(out_path, detail)
            author_ids.update(detail.get("author_ids") or [])
            photo_urls.update(detail.get("photos") or [])
            ok += 1
        except Exception as e:
            append_jsonl(out_path, {"id": mid, "_error": str(e)})
            err += 1
            print(f"  ERROR id={mid}: {e}", flush=True)

        if n % 25 == 0 or n == len(todo):
            elapsed = time.time() - t0
            rate = n / elapsed if elapsed else 0
            eta = (len(todo) - n) / rate if rate else 0
            print(
                f"  {n}/{len(todo)} ok={ok} err={err} "
                f"http_fetched={fetcher.fetched} cached={fetcher.cached} "
                f"eta={eta/60:.1f}m",
                flush=True,
            )
            # checkpoint side files
            authors_side.write_text("\n".join(map(str, sorted(author_ids))) + "\n", encoding="utf-8")
            photo_path.write_text("\n".join(sorted(photo_urls)) + "\n", encoding="utf-8")

    authors_side.write_text("\n".join(map(str, sorted(author_ids))) + "\n", encoding="utf-8")
    photo_path.write_text("\n".join(sorted(photo_urls)) + "\n", encoding="utf-8")

    # Final summary
    all_done = already_done(out_path)
    summary = {
        "requested": len(ids),
        "jsonl_ok": len(all_done),
        "this_run_ok": ok,
        "this_run_err": err,
        "author_ids": len(author_ids),
        "photo_urls": len(photo_urls),
        "fetched": fetcher.fetched,
        "cached": fetcher.cached,
        "elapsed_s": round(time.time() - t0, 1),
    }
    (EXPORT / "phase1_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if err == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
