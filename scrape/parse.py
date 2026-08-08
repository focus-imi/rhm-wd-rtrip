"""HTML / JSON parsers for registersofia.bg monuments and authors."""

from __future__ import annotations

import html as html_lib
import re
from typing import Any
from urllib.parse import unquote


def _clean(text: str) -> str:
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_tags(chunk: str) -> str:
    chunk = re.sub(r"<br\s*/?>", "\n", chunk, flags=re.I)
    chunk = re.sub(r"</p>", "\n", chunk, flags=re.I)
    chunk = re.sub(r"<[^>]+>", "", chunk)
    return _clean(chunk.replace("\n", " "))


def _field_value(html: str, label: str) -> str | None:
    """Extract text from a label / monument-type-desc row."""
    pat = re.compile(
        rf'{re.escape(label)}\s*:?\s*</div>\s*<div[^>]*class="[^"]*monument-type-desc[^"]*"[^>]*>(.*?)</div>',
        re.S | re.I,
    )
    m = pat.search(html)
    if not m:
        return None
    return _strip_tags(m.group(1)) or None


def parse_map_result(data: dict, monument_type: int) -> list[dict[str, Any]]:
    """Flatten mapResult dict into one row per monument id."""
    result = data.get("mapResult") or {}
    if isinstance(result, list):
        items = [(None, e) for e in result]
    else:
        items = list(result.items())

    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for key, elem in items:
        html = elem.get("html") or ""
        ids = sorted({int(x) for x in re.findall(r"formdata\[id\]=(\d+)", html)})
        lat = (elem.get("latitude") or "").strip().rstrip(".")
        lng = (elem.get("longitude") or "").strip().rstrip(".")
        media_codes = re.findall(r"media/monuments/(\d+)/", html)
        for i, mid in enumerate(ids):
            if mid in seen:
                continue
            seen.add(mid)
            media = media_codes[i] if i < len(media_codes) else (media_codes[0] if media_codes else None)
            rows.append(
                {
                    "id": mid,
                    "map_type": monument_type,
                    "title_map": elem.get("title"),
                    "lat_map": lat or None,
                    "lng_map": lng or None,
                    "cluster_key": key,
                    "counter": elem.get("counter"),
                    "media_code_map": media,
                    "icon": elem.get("icon"),
                }
            )
    return rows


def parse_list_ids(html: str) -> list[int]:
    return sorted({int(x) for x in re.findall(r"view=monument&option=com_monuments&formdata\[id\]=(\d+)", html)})


def parse_list_total(html: str) -> int | None:
    m = re.search(r"(\d+)\s+Обекта\s+от\s+(\d+)", html)
    if m:
        return int(m.group(2))
    return None


def parse_detail(html: str, monument_id: int) -> dict[str, Any]:
    mid_m = re.search(r'id="monument_ID"\s+value="([^"]*)"', html)
    lat_m = re.search(r'id="monument_lat"\s+value="([^"]*)"', html)
    lng_m = re.search(r'id="monument_lng"\s+value="([^"]*)"', html)

    h1_m = re.search(r'<div class="row monument">\s*<h1>\s*(.*?)\s*</h1>', html, re.S)
    if not h1_m:
        h1_m = re.search(r"<h1[^>]*>\s*(.*?)\s*</h1>", html, re.S)
    title = _strip_tags(h1_m.group(1)) if h1_m else None

    # Header chips: type, district, location short
    type_id = None
    type_name = None
    subtype = None
    district_id = None
    district_name = None
    location_header = None

    links = re.search(r'<div class="monument_links">(.*?)</div>\s*</div>', html, re.S)
    if links:
        chunk = links.group(1)
        tm = re.search(
            r'formdata\[monument_type\]=(\d+)[^>]*>\s*([^<]+)',
            chunk,
        )
        if tm:
            type_id = int(tm.group(1))
            type_name = _clean(tm.group(2))
        sm = re.search(r"</a>\s*-\s*([^<]+)", chunk)
        if sm:
            subtype = _clean(sm.group(1))
        dm = re.search(r"formdata\[field_t6\]=(\d+)[^>]*>\s*([^<]+)", chunk)
        if dm:
            district_id = int(dm.group(1))
            district_name = _clean(dm.group(2))
        # last bare span often location
        spans = re.findall(r"<span>\s*(.*?)\s*</span>", chunk, re.S)
        for sp in spans:
            if "formdata" in sp or "<a " in sp:
                continue
            location_header = _strip_tags(sp) or location_header

    # Description: first <p> after details heading
    description = None
    dm = re.search(r"Детайли за[^<]*</h3>\s*<p>(.*?)</p>", html, re.S)
    if dm:
        description = _strip_tags(dm.group(1))

    # Labeled rows
    type_row = _field_value(html, "Вид")
    date_created = _field_value(html, "Дата на създаване")
    period = _field_value(html, "Период")
    location = _field_value(html, "Местоположение") or location_header

    # Authors
    authors: list[dict[str, Any]] = []
    author_block = re.search(
        r"Автор на паметника:\s*</div>\s*<div[^>]*monument-type-desc[^>]*>(.*?)</div>",
        html,
        re.S,
    )
    if author_block:
        for am in re.finditer(
            r'view=author&(?:amp;)?id=(\d+)[^>]*>\s*([^<]+)',
            author_block.group(1),
        ):
            label = _clean(am.group(2))
            role = None
            rm = re.search(r"\(([^)]+)\)\s*$", label)
            if rm:
                role = rm.group(1).strip()
                name = _clean(label[: rm.start()])
            else:
                name = label
            authors.append({"id": int(am.group(1)), "name": name, "role": role, "label": label})

    # Photos / media
    media_codes = sorted(set(re.findall(r"media/monuments/(\d+)/", html)))
    photo_urls = sorted(
        set(
            re.findall(
                r"https?://radmin\.registersofia\.bg/media/monuments/\d+/images/[a-f0-9]+_[MS]\.jpg",
                html,
            )
        )
    )
    # Prefer full-size _M
    photos_m = [u for u in photo_urls if u.endswith("_M.jpg")]
    photos_s = [u for u in photo_urls if u.endswith("_S.jpg")]

    lat = (lat_m.group(1).strip().rstrip(".") if lat_m else "") or None
    lng = (lng_m.group(1).strip().rstrip(".") if lng_m else "") or None
    parsed_id = int(mid_m.group(1)) if mid_m and mid_m.group(1).strip().isdigit() else None

    media_code = media_codes[0] if media_codes else None
    media_id = int(media_code[6:]) if media_code and len(media_code) >= 11 else None

    return {
        "id": monument_id,
        "parsed_id": parsed_id,
        "id_match": parsed_id == monument_id,
        "title": title,
        "type_id": type_id,
        "type_name": type_name,
        "subtype": subtype,
        "type_row": type_row,
        "district_id": district_id,
        "district_name": district_name,
        "location": location,
        "description": description,
        "date_created": date_created,
        "period": period,
        "authors": authors,
        "author_ids": [a["id"] for a in authors],
        "lat": lat,
        "lng": lng,
        "media_code": media_code,
        "media_id_match": (media_id == monument_id) if media_id is not None else None,
        "photos": photos_m or photos_s,
        "photo_thumbs": photos_s,
        "url": f"https://registersofia.bg/?option=com_monuments&view=monument&formdata%5Bid%5D={monument_id}",
    }


def parse_print(html: str) -> dict[str, Any]:
    """Supplement fields from print layout."""
    h1_m = re.search(r"<h1[^>]*>\s*(.*?)\s*</h1>", html, re.S)
    title = _strip_tags(h1_m.group(1)) if h1_m else None

    # Print pages often put type/date in table-ish text
    text = _strip_tags(html)
    date_created = None
    m = re.search(r"Дата на създаване:\s*([^\n]+?)(?:Период|Автор|Местоположение|$)", text)
    if m:
        date_created = _clean(m.group(1))

    period = None
    m = re.search(r"Период:\s*([^\n]+?)(?:Автор|Местоположение|Дата|$)", text)
    if m:
        period = _clean(m.group(1))

    type_row = None
    m = re.search(r"Вид:\s*([^\n]+?)(?:Дата|Период|Автор|Местоположение|$)", text)
    if m:
        type_row = _clean(m.group(1))

    mid_m = re.search(r'id="monument_ID"\s+value="([^"]*)"', html)
    lat_m = re.search(r'id="monument_lat"\s+value="([^"]*)"', html)
    lng_m = re.search(r'id="monument_lng"\s+value="([^"]*)"', html)

    return {
        "title_print": title,
        "date_created_print": date_created,
        "period_print": period,
        "type_row_print": type_row,
        "lat_print": (lat_m.group(1).strip().rstrip(".") if lat_m and lat_m.group(1).strip() else None),
        "lng_print": (lng_m.group(1).strip().rstrip(".") if lng_m and lng_m.group(1).strip() else None),
        "parsed_id_print": int(mid_m.group(1)) if mid_m and mid_m.group(1).strip().isdigit() else None,
    }


def merge_detail_print(detail: dict[str, Any], print_data: dict[str, Any]) -> dict[str, Any]:
    out = dict(detail)
    out["print"] = print_data
    # Fill gaps from print
    if not out.get("date_created") and print_data.get("date_created_print"):
        out["date_created"] = print_data["date_created_print"]
    if not out.get("period") and print_data.get("period_print"):
        out["period"] = print_data["period_print"]
    if not out.get("lat") and print_data.get("lat_print"):
        out["lat"] = print_data["lat_print"]
    if not out.get("lng") and print_data.get("lng_print"):
        out["lng"] = print_data["lng_print"]
    return out


def parse_author(html: str, author_id: int) -> dict[str, Any]:
    h1_m = re.search(r"<h1[^>]*>\s*(.*?)\s*</h1>", html, re.S)
    label = _strip_tags(h1_m.group(1)) if h1_m else None
    name = label
    role = None
    if label:
        rm = re.search(r"\(([^)]+)\)\s*$", label)
        if rm:
            role = rm.group(1).strip()
            name = _clean(label[: rm.start()])

    monument_ids = sorted({int(x) for x in re.findall(r"formdata\[id\]=(\d+)", html)})

    # Optional bio paragraph
    bio = None
    # Heuristic: first substantial <p> in content
    for pm in re.finditer(r"<p>(.*?)</p>", html, re.S):
        t = _strip_tags(pm.group(1))
        if t and len(t) > 40 and "Powered by" not in t:
            bio = t
            break

    return {
        "id": author_id,
        "name": name,
        "role": role,
        "label": label,
        "monument_ids": monument_ids,
        "bio": bio,
        "url": f"https://registersofia.bg/index.php?option=com_monuments&view=author&id={author_id}&Itemid=120",
    }
