"""Shared HTTP helpers for the registersofia.bg scraper."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPORT = ROOT / "export"
CACHE = ROOT / "cache"
CACHE_HTML = CACHE / "html"
CACHE_MAP = CACHE / "map"

BASE = "https://registersofia.bg"
UA = "focus-imi-rhm-scraper/0.1 (+https://github.com/focus-imi; research; contact via project)"

# Polite default: ~0.8 req/s. Override with RHM_SCRAPE_DELAY.
DEFAULT_DELAY_S = 1.25

TYPE_NAMES = {
    1: "plaque",
    2: "freestanding",
    3: "monument",
    4: "sculpture",
    5: "decorative",
    6: "fountain",
    7: "other",
}

DISTRICT_NAMES = {
    1: "Средец",
    2: "Красно село",
    3: "Възраждане",
    4: "Оборище",
    5: "Сердика",
    6: "Подуяне",
    7: "Слатина",
    8: "Изгрев",
    9: "Лозенец",
    10: "Триадица",
    11: "Красна поляна",
    12: "Илинден",
    13: "Надежда",
    14: "Искър",
    15: "Младост",
    16: "Студентски",
    17: "Витоша",
    18: "Овча купел",
    19: "Люлин",
    20: "Връбница",
    21: "Нови Искър",
    22: "Кремиковци",
    23: "Панчарево",
    24: "Банкя",
}


class ThrottledFetcher:
    def __init__(self, delay_s: float | None = None):
        self.delay_s = DEFAULT_DELAY_S if delay_s is None else float(delay_s)
        self._last = 0.0
        self.fetched = 0
        self.cached = 0

    def _wait(self) -> None:
        now = time.monotonic()
        wait = self.delay_s - (now - self._last)
        if wait > 0:
            time.sleep(wait)

    def get(self, url: str, cache_path: Path | None = None, force: bool = False) -> str:
        if cache_path is not None and cache_path.exists() and not force:
            self.cached += 1
            return cache_path.read_text(encoding="utf-8", errors="replace")

        self._wait()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "bg,en;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            self._last = time.monotonic()
            self.fetched += 1
            body = e.read().decode("utf-8", errors="replace")
            if cache_path is not None:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(body, encoding="utf-8")
            raise

        # charset
        text = raw.decode("utf-8", errors="replace")
        self._last = time.monotonic()
        self.fetched += 1

        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(text, encoding="utf-8")
        return text

    def get_json(self, url: str, cache_path: Path | None = None, force: bool = False) -> dict:
        text = self.get(url, cache_path=cache_path, force=force)
        return json.loads(text)


def detail_url(monument_id: int) -> str:
    q = urllib.parse.urlencode(
        {
            "option": "com_monuments",
            "view": "monument",
            "formdata[id]": str(monument_id),
        }
    )
    return f"{BASE}/?{q}"


def print_url(monument_id: int) -> str:
    q = urllib.parse.urlencode(
        {
            "option": "com_monuments",
            "view": "monument",
            "layout": "print",
            "formdata[id]": str(monument_id),
            "tmpl": "print",
        }
    )
    return f"{BASE}/index.php?{q}"


def author_url(author_id: int) -> str:
    q = urllib.parse.urlencode(
        {
            "option": "com_monuments",
            "view": "author",
            "id": str(author_id),
            "Itemid": "120",
        }
    )
    return f"{BASE}/index.php?{q}"


def map_url(monument_type: int) -> str:
    q = urllib.parse.urlencode(
        {
            "option": "com_monuments",
            "task": "monumentsmap.getMonuments",
            "view": "monumentsmap",
            "format": "json",
            "tmpl": "none",
            "Itemid": "139",
            "lang": "bg",
            "formdata[searchType]": "map",
            "formdata[page]": "-1",
            "formdata[monument_type]": str(monument_type),
            "formdata[field_t6]": "0",
            "formdata[title]": "",
            "formdata[field_d22]": "",
            "formdata[period]": "",
        }
    )
    return f"{BASE}/index.php?{q}"


def list_url(page: int) -> str:
    q = urllib.parse.urlencode(
        {
            "option": "com_monuments",
            "view": "monuments",
            "Itemid": "120",
            "page": str(page),
        }
    )
    return f"{BASE}/index.php?{q}"


def ensure_dirs() -> None:
    for p in (
        EXPORT,
        CACHE_MAP,
        CACHE_HTML / "detail",
        CACHE_HTML / "print",
        CACHE_HTML / "author",
        CACHE_HTML / "list",
    ):
        p.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
