#!/usr/bin/env python3
"""Run Phase 0 → 1 → 2 with polite throttling."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(script: str, extra: list[str]) -> None:
    cmd = [sys.executable, str(ROOT / script), *extra]
    print(f"\n=== {script} ===", flush=True)
    subprocess.check_call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=1.25)
    ap.add_argument("--skip-list", action="store_true", help="Skip list pagination cross-check")
    ap.add_argument("--limit", type=int, default=None, help="Limit monuments (testing)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    common = ["--delay", str(args.delay)]
    if args.force:
        common.append("--force")

    run("fetch_map.py", common)
    if not args.skip_list:
        run("fetch_list.py", common)

    detail_args = list(common)
    if args.limit:
        detail_args += ["--limit", str(args.limit)]
    run("fetch_detail.py", detail_args)
    run("fetch_authors.py", common)
    return 0


if __name__ == "__main__":
    sys.exit(main())
