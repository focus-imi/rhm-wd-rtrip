# Scrape of RHIM page

Target site: [registersofia.bg](https://registersofia.bg/) (Joomla `com_monuments`).

Example detail URL:

https://registersofia.bg/index.php?view=monument&option=com_monuments&formdata[id]=664&Itemid=140

---

## Verdict on the canonical ID

**Use `formdata[id]` / `#monument_ID` as the Wikidata external ID.**

| Signal | Example (object 664) | Role |
|--------|----------------------|------|
| URL `formdata[id]` | `664` | Primary key of the detail view |
| Hidden `#monument_ID` | `664` | Same value, reliable in HTML |
| Media folder | `00302200664` | **Derived path**, not a separate ID |
| Print / PDF / QR `formdata[id]` | often `565` or `1` | **Template bug** — ignore |

### Media folder encoding

`radmin.registersofia.bg/media/monuments/{code}/images/...`

`{code}` = `TTT` + `DDD` + `IIIII`

| Part | Meaning | Example |
|------|---------|---------|
| `TTT` | type code (= `monument_type`, zero-padded) | `003` = Паметник |
| `DDD` | district `field_t6`, zero-padded | `022` = Кремиковци |
| `IIIII` | same as URL id, 5-digit padded | `00664` → **664** |

Type codes match the filter vocabulary: `001` plaque, `002` freestanding sign, `003` monument, `004` sculpture, `005` decorative, `006` fountain.

**Do not** propose the 11-digit media code as the Wikidata property value — it embeds type/district and would break if either is corrected. Store type and district as separate fields; keep the property as the bare integer string (`664`).

### ID ambiguity from the project README (D1)

Observed resolution:

1. **URL / `#monument_ID`** — real primary key; this should become the external-ID property.
2. **Media path** — composite filesystem key derived from type + district + id.
3. **Print / PDF / QR** — broken in the public template (hardcoded wrong ids on many pages). Print layout works if you pass the **correct** id yourself (`layout=print&formdata[id]=664`).

No inventory number / `№` is shown on the public page.

### Ghost / orphan detail pages

Numeric ids are sparse in `10…1231` (~101 holes). Some hole ids still render a detail page (e.g. `100` “Антон Безеншек” with empty coords and no media) while the live register entry is a neighbour (`99`, in map, with coords + media).

**Canonical set = ids present in the published list/map (≈1121), not every id that returns HTTP 200.**

---

## Site shape

| Surface | URL pattern | Notes |
|---------|-------------|-------|
| Register list | `/registar` or `view=monuments` | **1121** objects; **10 per page**; `page=N` |
| By type | `formdata[monument_type]=1…6` | Counts e.g. plaques 479, monuments 280, … |
| By district | `formdata[field_t6]=1…24` | 24 Sofia districts |
| Detail | `view=monument&formdata[id]=N&Itemid=140` | Full record + gallery + map pin |
| Author | `view=author&id=N` | Separate id space; linked from detail |
| Map UI | `/карта` | Filters → JSON (below) |
| Print | `view=monument&layout=print&formdata[id]=N&tmpl=print` | Cleaner HTML for some fields |
| PDF | same with `tmpl=pdf` | Same id as print |

English `lang=en` does **not** currently yield English labels (title stays BG).

User-Agent required — bare `curl` without a browser UA gets a stub page.

---

## Best discovery API (map JSON)

One request per type dumps essentially the full published set:

```
GET https://registersofia.bg/index.php
  ?option=com_monuments
  &task=monumentsmap.getMonuments
  &view=monumentsmap
  &format=json
  &tmpl=none
  &Itemid=139
  &lang=bg
  &formdata[searchType]=map
  &formdata[page]=-1          # all results
  &formdata[monument_type]=T  # 1..6; type 0 is flaky
  &formdata[field_t6]=0
  &formdata[title]=
  &formdata[field_d22]=
  &formdata[period]=
```

Headers: normal browser `User-Agent` + `X-Requested-With: XMLHttpRequest`.

Response shape:

```json
{
  "status": 1,
  "status_txt": "",
  "mapResult": {
    "42.68…-23.33…": {
      "html": "<div class=\"cluster-infoWindow\">…formdata[id]=922…</div>",
      "title": "…",
      "latitude": "42.68…",
      "longitude": "23.33…",
      "icon": "http://radmin…/icon1.png",
      "counter": 1
    }
  }
}
```

`mapResult` is a **dict keyed by `lat-lng`**, not an array (same-address clusters share a key; `counter` > 1). Parse **all** `formdata[id]=(\\d+)` from each `html` blob.

Observed per-type unique-id union: **1121** (matches list total). Prefer querying types `1…6` separately (`monument_type=0` sometimes returns an empty `mapResult`).

---

## Detail page fields to scrape

From `#monument_ID`, hidden map inputs, and the “Детайли” block (BG labels):

| Field | Source | Wikidata target (from main README) |
|-------|--------|-------------------------------------|
| **id** | `#monument_ID` / URL | new external-ID property |
| title | `<h1>` | labels `bg` (+ `en` later) |
| type | link `monument_type` + subtype text after “-” | `P31` |
| district | link `field_t6` | `P131` |
| location text | “Местоположение” | `P276` |
| description | prose under details | description / `P973` |
| creation date | “Дата на създаване” (+ `field_d24` in links) | `P571` |
| period | “Период” | qualifier on `P571` |
| authors | links `view=author&id=N` + role in `(…)` | `P170` / `P84` + author register id |
| photos | `radmin…/media/monuments/{code}/images/*_{M,S}.jpg` | Commons → `P18` |
| lat/lng | `#monument_lat` / `#monument_lng` | `P625` |
| stable URL | detail URL (or future clean URI) | `P856` |

Authors are first-class: e.g. object 629 links author ids `148, 257–261` with roles `(скулптор)`, `(худ.)`, `(арх.)`.

Sparse fields are common (many plaques lack date/period/authors; some lack coords).

---

## Recommended scrape plan

### Phase 0 — ID census (do this first)

1. Pull map JSON for `monument_type` ∈ `{1,2,3,4,5,6}` with `page=-1`.
2. Extract the set of published ids → `ids_map` (~1121).
3. Crawl list pages `page=1…ceil(1121/10)` **without** type filter; extract ids → `ids_list`.
4. Reconcile: `ids_canonical = ids_map ∪ ids_list`. Diff and inspect any list-only / map-only rows (likely no-coords or filter quirks).
5. Optionally probe `1…max(id)+margin` and mark **ghost** ids (HTTP 200 + `#monument_ID` set but ∉ canonical). Keep them out of Wikidata import.

**Output:** `canonical_ids.csv` with `id` only — this is the candidate value space for the Wikidata property.

### Phase 1 — Detail harvest

For each canonical id:

1. GET detail HTML (browser UA; polite rate limit, e.g. 1–2 req/s).
2. Parse structured fields listed above.
3. Also GET print layout for the same id (often cleaner date/type text).
4. Validate: `#monument_ID` == requested id; media code suffix == id when media exists.
5. Collect author ids into a side set.

**Output:** `monuments.jsonl` (one object per id) + `photos/` URL list (download later / licence-gated).

### Phase 2 — Authors

Deduplicate author ids; scrape `view=author&id=N` (name, role text, linked monument ids). Separate table `authors.jsonl` — needed for creator reconciliation, even if Wikidata only stores a reference URL at first.

### Phase 3 — QC against project contract

- Count by type / district vs list UI totals.
- Coords coverage; empty lat/lng rate.
- Duplicate titles (ghosts vs renames).
- Media code ↔ type/district consistency.
- Spot-check against known round-trip case: id **629** ↔ Wikidata [Q899761](https://www.wikidata.org/wiki/Q899761).

### Phase 4 — Wikidata handoff

- Property proposal: external id = **decimal integer string**, formatter URL ideally `https://registersofia.bg/…formdata[id]=$1…` until RHM ships clean `/object/{id}` URIs (Stage 1).
- Do **not** wait for media-code or QR ids.
- Import only `ids_canonical`; attach `P856` to the scraped detail URL; reference with `P854` + `P813`.

---

## Implementation sketch

```
scrape/
  README.md          ← this plan
  fetch_map.py       # Phase 0 map JSON → id index
  fetch_list.py      # Phase 0 list pagination cross-check
  fetch_detail.py    # Phase 1 + print layout
  fetch_authors.py   # Phase 2
  parse.py           # HTML parsers (detail / print / author / map html)
  export/            # jsonl + csv snapshots (gitignored binaries)
```

### Run (implemented)

```bash
cd scrape
python3 run.py --delay 1.25 --skip-list   # Phase 0 map → 1 detail+print → 2 authors
# or stepwise:
python3 fetch_map.py --delay 1.25
python3 fetch_detail.py --delay 1.25      # resumes; uses cache/
python3 fetch_authors.py --delay 1.25
```

- Throttle default **1.25 s** between HTTP requests (`--delay`).
- UA: `focus-imi-rhm-scraper/0.1`.
- HTML cached under `cache/html/{detail,print,author}/`; re-runs skip network when cached.
- Outputs in `export/`: `canonical_ids.csv`, `monuments.jsonl`, `authors.jsonl`, `photo_urls.txt`, `scrape_summary.json`.

**First full harvest (2026-08-08):** 1121 monuments, 204 authors, 1119 with coords, ~1.25 s throttle (~59 min detail + ~9 min authors). One timeout on id 942 — retried OK.

Stdlib only (no extra deps). Prefer the future CKAN dump (main README Stage 1) once it exists; this scrape is the interim source of truth.

---

## Open points to confirm with RHM

1. Confirm **`formdata[id]`** is the long-term inventory key (vs an internal CMS row id that could be renumbered).
2. Fix print/QR template so public artefacts show the same id.
3. Whether ghost ids (live HTML, absent from list/map) are retired objects that should be excluded or historically preserved.
4. Author id stability and whether authors need their own Wikidata external-id property later.
5. Photo licence before any Commons upload (CC BY 4.0 target in main README).
