# RHM ↔ Wikidata ↔ OSM round-trip

[Data round-tripping](https://www.wikidata.org/wiki/Wikidata:Data_round-tripping) between the [Sofia monument register](https://registersofia.bg/) (RHM Sofia), Wikidata, and OpenStreetMap.

This project proposes establishing a lasting reciprocal synchronisation between the [Regional History Museum – Sofia](https://registersofia.bg/) (RHM) register of public monuments (memorial plaques, monuments, sculptures) and the Wikidata–Wikipedia–OSM open-data ecosystem.

The round-trip aims to improve the quality of *both* the RHM register and the open-data ecosystem, establish a lasting GLAM partnership between RHM and the Wikimedia/OSM communities, and make Sofia's cultural and historical memory more discoverable.

Each platform owns what it does best:
* **RHM** holds the canonical inventory (names, types, dates, authors, photos, administrative location). It is also the principal authority and source of truth. 
* **Wikidata** carries structured semantics and stable cross-identifiers (instance-of typing, who/what each object commemorates, creator links, Commons images, OSM IDs, identifiers to external authority files);
* **OpenStreetMap** carries precise geometry and map-facing tags, with `wikidata=*` linking features to monument items. Its active mapper community also makes OSM a key channel for finding objects not yet in the register.

**Reverse enrichment on the register:**

- **Live UI Wikipedia links:** monument pages pull Wikipedia sitelinks for the monument, its subject(s), and its author(s) from Wikidata via live SPARQL, plus a subtle Wikidata icon link. Language follows the register UI language (Bulgarian interface → `bg.wikipedia`; English interface → `en.wikipedia` where available).
- **Project synchronisation feeds the register:** the round-trip process gradually contributes both new objects missing from the RHM inventory and additional information for existing objects, so improvements discovered in Wikidata and OpenStreetMap flow back into the register.

---

## Scope

- **Geography:** full Sofia Municipality
- **Objects:** all register types — memorial plaque, monument, sculpture, fountain, free-standing memorial sign, decorative element; plus **new objects** added to the register via project-driven gap filling (expected to exceed the current ~1,121 count over time).
- **Partnership:** full cooperation from RHM Sofia.
- **Out of scope (for now):** automated Stage 5 sync rules; photo legal edge cases. Register intake workflow for new objects is **in scope** (Stage 4) but not yet defined.

---

## Example

**„Братската могила“, architectural-sculptural ensemble, Borisova Gradina**. Thе object already exists across the sources and is a useful round-trip test case:

- **RHM register:** [object 629](https://registersofia.bg/index.php?view=monument&option=com_monuments&formdata%5Bid%5D=629&Itemid=140)
- **Wikidata:** [Q899761](https://www.wikidata.org/wiki/Q899761)
- **OpenStreetMap:** [way 867938756](https://www.openstreetmap.org/way/867938756), tagged `wikidata=Q899761`
- **Wikipedia:** [Братска могила (София)](https://bg.wikipedia.org/wiki/Братска_могила_(София))

Also see [osm_borisova.png](img/osm_borisova.png) for an example of detailed OSM coverage of busts in Sofia's parks.

## Register fields → targets

The register detail page exposes a consistent field set. This table is the field-level contract for the round-trip (refine once the canonical export schema is fixed in Stage 1).

| Register field (BG) | Example | Wikidata | OSM |
|---------------------|---------|----------|-----|
| Заглавие / title | „Братската могила“… | label `bg`/`en` | `name:bg` / `name:en` |
| Вид / type | Паметник | `P31` (see mapping) | `historic=*` + `memorial=*` |
| Подвид / subtype | архитектурно-скулптурен ансамбъл | `P31` refinement / `P136` | `memorial=*` refinement |
| Район / district | Средец | `P131` | implicit via geometry |
| Местоположение / location text | парк „Борисова градина“ | `P276` (location) | position |
| Описание / description | narrative text | `description` (short) / `P973` to register | — |
| Дата на създаване / creation date | 1956 г. | `P571` (inception) | `start_date` |
| Период / period | 1944–1989 г. | qualifier on `P571` | — |
| Автор(и) / author(s) + role | Йордан Кръчмаров (скулптор) | `P170` / `P84` → existing person item | `artist:wikidata` / `artist_name` |
| Снимки / photos | gallery | `P18` (via Commons) | `image` / `wikimedia_commons` |
| Карта / map pin | lat/lon | `P625` | node/way/area geometry |
| Каноничен ID / register ID | (Stage 1) | **new external-ID property** + `P856` | `ref:registersofia` and `website`  |

---

## Stages

### Stage 1 — RHM infrastructure (prerequisite)

Work on the register side before bulk Wikidata import.

| Deliverable | Status | Notes |
|-------------|--------|-------|
| **Canonical identifier** | TBD at RHM | Resolve current ID ambiguity (URL `formdata[id]`, media path prefix, PDF/QR ID). One stable ID everywhere. |
| **Clean URIs** | TBD | Prefer flat IDs without type/district infix, e.g. `registersofia.bg/object/{id}`. Author entities need their own IDs and URIs too. |
| **Periodic open-data export** | - | Static releases on [urbandata.sofia.bg](https://urbandata.sofia.bg/) (CKAN). Format TBD (JSON / CSV / RDF). |
| **Photo licence** | negotiate | Target **CC BY 4.0** — mandatory for project; legal sign-off pending. |
| **Commons upload pipeline** | - | Register photos uploaded to Commons; linked from Wikidata `P18` and register page. |

**Stage 1 exit criteria:** every object has one canonical ID, one stable URI, a row in the CKAN dump, and at least metadata for Commons upload (even if upload runs in Stage 2).

---

### Stage 2 — Wikidata property and import

| Deliverable | Status | Notes |
|-------------|--------|-------|
| **New Wikidata property** |  | External-ID property for Sofia monument register (proposal on Wikidata). No Mix'n'Match catalog — alignment done in-house with AI assistance. |
| **Bulk import from CKAN dump** |  | Create or **merge** items (prefer existing Q-items, e.g. well-known monuments already in Wikidata). |
| **Modeling** | | See [Wikidata modeling](#wikidata-modeling) below. |

**Stage 2 exit criteria:** every register object has a Wikidata item with register ID + `P856`; Commons photos on high-value subset at minimum.

---

### Stage 3 — OSM matching

Match register/Wikidata objects to OSM features and align tagging.

| Deliverable | Status | Notes |
|-------------|--------|-------|
| **OSM matching** | TBD | Strategy, tolerance, facade-plaque tagging — to be defined. Edits by OSM community + project team. |
| **Tag mapping** | TBD | Register type → `historic=*` / `memorial=*` convention. |

**Stage 3 exit criteria:** all register objects matched to OSM features; `wikidata=*` and related tags applied per convention. 

---

### Stage 4 — Gap analysis and growing the register

Monuments present in Wikidata and/or OSM but **missing from the register** — the project will grow RHM beyond the existing ~1,121, not only mirror them.

| Step | Direction |
|------|-----------|
| 1 | Identify orphans (SPARQL + [Overpass QC query](https://overpass-turbo.eu/s/2r7f) — register-relevant public monuments and artworks in Sofia Municipality). |
| 2 | Open **RHM ticket** to add / correct register entry. |
| 3 | After RHM accepts → propagate to Wikidata (and OSM if needed). |

**Open:** scope of orphans (decorative public art only in OSM? `historic=memorial` only?) — TBD.

**Stage 4 exit criteria:** documented orphan backlog; defined intake workflow with RHM; first batch of back-contributed entries live in register.

---

### Stage 5 — Automated alignment maintenance

**TBD** — sync triggers, field-level source-of-truth rules, conflict resolution. Deferred until Stages 1–4 produce stable IDs and mappings.

---

## Wikidata modeling

### Monument item (one per register row, merged if Q-item exists)

Minimum claims on import:

| Claim | Property | Source |
|-------|----------|--------|
| Instance of | `P31` | Mapped from register type (see table below) |
| Genre | `P136` → public art (`Q557141`) | For objects with an artistic component (relief, sculpture) |
| Country | `P17` → Bulgaria (`Q219`) | Fixed |
| Coordinates | `P625` | Register map pin and/or OSM once matched |
| Location | `P131` / `P276` | Sofia district / park / street from register |
| Official page | `P856` | Stable register URI |
| Register ID | **new external-ID property** | Canonical ID from Stage 1 |
| OSM ID | `P11693` (node), `P10689` (way), or `P402` (relation) — pick per geometry | After OSM match |
| Image | `P18` | Commons file from register photo |
| Inception | `P571` | Register creation date |
| Inscription | `P1684` | Register inscription text where present |

**`P31` mapping** (per [WikiProject Public Art](https://www.wikidata.org/wiki/Wikidata:WikiProject_Public_art/Data_model) — prefer the specific `memorial (Q5003624)` over generic `monument (Q4989906)`):

| Register type (BG) | `P31` value |
|--------------------|-------------|
| Паметна плоча (memorial plaque) | commemorative plaque `Q721747` |
| Паметник (monument) | memorial `Q5003624` (+ subtype, e.g. architectural-sculptural ensemble) |
| Скулптура (sculpture) | sculpture `Q860861` |
| Чешма / фонтан (fountain) | fountain `Q483453` |
| Свободно-стоящ паметен знак (free-standing sign) | memorial `Q5003624` |
| Декоративен елемент (decorative element) | work of art `Q838948` / case-by-case |

Labels: **Bulgarian + English** on every item. References on imported statements should use the stable register page as `reference URL (P854)` plus `retrieved (P813)`; for dump-sourced imports, also record the CKAN dump version/date.

### Subject relations (person, event, …)

Case-by-case; **multiple subjects allowed** (e.g. plaque naming two people).

`commemorates (P547)` is the **primary** relation for what/whom a memorial honours — its purpose. `named after (P138)` is reserved for genuine etymology (the object's *name* derives from the entity) and can co-exist with P547.

| Situation | Property |
|-----------|----------|
| Person/event the object honours | `P547` (commemorates) — primary |
| Object's name derives from the entity | `P138` (named after) — etymology only |
| Physically depicts (figurative statue) | `P180` (depicts) |
| Topic of a long descriptive narrative | `P921` (main subject) |

Do not auto-link every name in free text; curate with AI assist + human review.

### Authors / creators

Register-listed authors/creators are treated as **Wikidata-notable**: link to existing person items where available, otherwise create new person items with register references and reconciled name/role data.

| Register role | Candidate property |
|---------------|-------------------|
| `(скулптор)` | `P170` (creator) |
| `(арх.)` | `P84` (architect) |
| `(худ.)` | `P170` (creator) |

Role qualifiers and multi-author statements as needed. Register author ID stored only if a dedicated author property is justified later — otherwise a register-page reference on the creator/architect statement (`P854` + `P813`) suffices.

---

## OSM tagging (draft — matching TBD)

Target pattern once Wikidata item exists:

```
historic=memorial | monument
memorial=plaque | statue | …
wikidata=Q…
subject:wikidata=Q…        # person / event commemorated
artist:wikidata=Q…          # if creator known
name:bg=…
name:en=…
```

Facade plaques, fountains, and decorative elements: tagging rules **TBD** (Stage 3).

---

## RHM page enrichment (live SPARQL)

Each monument detail page queries Wikidata for:

1. **Monument** — Wikipedia sitelinks (if any).
2. **Subject(s)** — Wikipedia sitelinks per linked entity.
3. **Author(s)** — Wikipedia sitelinks per linked person.

Display rules:

- Show links only where a Wikipedia article exists.
- Language follows register UI locale (`bg` / `en`).
- Add a small **Wikidata icon** linking to the monument Q-item (no prominent banner).

Implementation: server-side or client-side SPARQL against `query.wikidata.org`, keyed by register ID → Q-item via the new external-ID property. See [this Strazha.bg example](https://www.strazha.bg/mps/nikolay-denkov-denkov/) showing social media profiles of MPs.

---

## Open-data export (urbandata.sofia.bg)

Periodic static dataset on [Sofia Municipality’s CKAN portal](https://urbandata.sofia.bg/):

- **Publisher:** RHM Sofia / Sofia Municipality.
- **Cadence:** TBD (monthly or on register release).
- **Contents:** full object table, author table, type/district vocabularies, photo URLs or Commons filenames once uploaded.
- **Licence:** dataset metadata should declare object field licence; photos **CC BY 4.0** once negotiated.

This dump is the **input artifact** for Wikidata import scripts and QC — not a live API dependency.
Photos may be handled by a separate pipeline.

---

## Tooling (planned)

| Task | Tool |
|------|------|
| Reconciliation / merge | AI-assisted matching against existing Wikidata items |
| Bulk Wikidata writes | QuickStatements or pywikibot |
| OSM edits | Community mappers + project account; changesets documented |
| QC maps | SPARQL + Kartographer (same pattern as [Sofia street-names project](../events/2026-07-streetnames-imi/)) |
| SPARQL QC / federation | [QLever](https://qlever.dev/wikidata) SPARQL twins — project queries on the Wikidata mirror alongside [WDQS](https://query.wikidata.org/); federated `SERVICE` where needed |
| OSM gap QC (Stage 4) | [Overpass Turbo — Sofia monuments by register type](https://overpass-turbo.eu/s/2r7f) |
| Register enrichment | Live SPARQL widget on registersofia.bg |

No Mix'n'Match catalog.

---

## Open decisions log

| # | Topic | Status |
|---|-------|--------|
| D1 | Canonical register ID (resolve multi-ID issue) | Stage 1 / RHM |
| D2 | URI pattern for objects and authors | Stage 1 / RHM |
| D3 | CKAN export format and cadence | Stage 1 |
| D4 | CC BY 4.0 legal approval | Negotiation |
| D5 | Photo restriction policy | Legal / RHM |
| D6 | OSM matching strategy and GPS tolerance | Stage 3 |
| D7 | OSM tag mapping per register type | Stage 3 |
| D8 | Facade plaque / interior relief OSM geometry | Stage 3 |
| D9 | Orphan scope for Stage 4 gap analysis | Stage 4 |
| D10 | RHM ticket workflow for new entries | Stage 4 |
| D11 | Stage 5 sync rules and automation | Stage 5 |
| D12 | Timeline, team roles, deliverable milestones | Meta |

---

## Related work

- [registersofia.bg](https://registersofia.bg/) — current register (~1,121 objects, six types, 24 districts).
- [urbandata.sofia.bg](https://urbandata.sofia.bg/) — target host for open-data exports.

**Modeling references**

- [Wikidata:WikiProject Public art / Data model](https://www.wikidata.org/wiki/Wikidata:WikiProject_Public_art/Data_model) — `P31` choices, `commemorates`, `genre=public art`.
- [Wikidata:OpenStreetMap](https://www.wikidata.org/wiki/Wikidata:OpenStreetMap) — OSM ID properties (`P11693` node, `P10689` way, `P402` relation).
- [OSM Key:memorial](https://wiki.openstreetmap.org/wiki/Key:memorial) / [Tag:historic=monument](https://wiki.openstreetmap.org/wiki/Tag:historic=monument) — `subject:wikidata`, `artist:wikidata` conventions.
- [Overpass Turbo — Sofia register-type QC](https://overpass-turbo.eu/s/2r7f) — Stage 4 orphan discovery within Sofia Municipality (relation 7276261).
- [OSM BG tools](https://osm-bg.github.io/qa/) — Bulgarian OSM QA tooling.
- [Wikidata:Data round-tripping](https://www.wikidata.org/wiki/Wikidata:Data_round-tripping) — general Wikidata guidance for reciprocal data flows.
---

## Next steps

1. **RHM kickoff** — agree Stage 1 scope: canonical ID scheme, URI design, EN UI scope, CKAN dataset metadata.
2. **Draft property proposal** — Sofia monument register ID (can proceed in parallel once ID format is fixed).
3. **Pilot batch** — import ~20 diverse objects (plaque, monument, fountain, multi-subject, merged Q-item) to validate modeling before full 1,121 run.
4. **SPARQL prototype** — Wikipedia + Wikidata widget on one register detail page.
