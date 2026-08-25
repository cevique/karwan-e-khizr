# DATA_GAPS.md

Everything the backend/importer must not assume, plus the authoritative
route-by-route classification for `backend/data/transit_data.json`. This
file did not previously exist in this repository (it was rebuilt/
restructured into `docs/00`–`docs/10` and this file was dropped) — it is
recreated here per the correction-pass brief, adapted for the current
dataset and codebase, not copied verbatim from the earlier repository's
version.

---

## 0. Correction-pass summary (2026-08-25)

The prior data-collection pass fetched complete, verified stop-level
timetables for only 4 of the 22 CDA feeder routes (FR-01, FR-04, FR-07,
FR-14). **That was a limitation of that pass, not the intended scope.**
This correction pass:

- Fetched and verified **2 more** complete feeder timetables: **FR-06**
  (PIMS Metro Station → Golra Sharif, 26 stops, 17 trips/day, 60-min
  headway) and **FR-09** (Khanna Pul → Golra Morh Metro Station, 27
  stops, 65 trips/day, 15-min headway) — bringing the fully-supported
  count to **6 of 22**.
- Explicitly classified **all 22** CDA feeder routes (plus the 4 Metrobus
  lines) into the 4-tier system below, so no route's support level is
  ever silently ambiguous.
- Fixed a real route-topology bug: routes with a canonical timetable
  previously had **no explicit `RouteStop` sequence at all** in
  `transit_data.json` — their topology existed only implicitly inside
  `trips[].stop_times`. `route_stops` for these routes is now
  **mechanically derived** from the canonical trip pattern (single source
  of truth), eliminating the risk of two independently-maintained,
  potentially-contradictory sequences for the same route.
- Fixed a real importer bug (`app/seeding/adapters/stops.py`): the
  dataset's stop `key` (a slug, e.g. `"cda_pims_hospital"`) was being
  written into `Stop.name` — the *display* name column — while the
  dataset's actual human-readable `name` (e.g. `"PIMS Hospital"`) was
  never read at all. Added `Stop.external_key` (migration
  `a1b2c3d4e5f7`) so matching/deduplication uses the stable slug while
  `Stop.name` now holds the real display name.
- Moved fare rules out of a Python-hardcoded default in
  `app/seeding/importer.py` into `transit_data.json`'s new `fare_rules`
  array, with explicit `source`/`confidence: "APPROXIMATE"` provenance —
  see §8.

**What did NOT change:** the 16 feeder routes still without a verified
complete timetable are still without one — this pass did not fabricate
anything for them. Stop-coordinate geocoding was not re-run (no live
database/network access in this session — see §9). Route geometry
generation (OSRM) was not attempted (still correctly blocked on
coordinate coverage, and out of this pass's scope per the brief). No
frontend files were inspected or touched.

---

## 1. All 22 CDA feeder routes — explicit classification

Every route below exists officially per the CDA's own route-index page
(`https://www.cda.gov.pk/cdaTransitMap`) — an authoritative primary
source for existence, name, endpoints, and headway. **Tier reflects
topology + timetable support only, not whether the route itself is
real** (all 22 are real, confirmed routes).

### Tier 1 — FULLY_SUPPORTED (topology + real timetable): 6 routes

| Route | Endpoints | Stops | Trips/day | Headway | Source PDF |
|---|---|---|---|---|---|
| FR-01 | Khanna Pul ↔ NUST Metro Station | 26 | 16 | 60 min | `.../FR-01_Backward.pdf` |
| FR-04 | PIMS Hospital → Bari Imam | 25 | 97 | 10 min | `.../FR-04_Forward.pdf` |
| **FR-06** *(new)* | PIMS Metro Station → Golra Sharif | 26 | 17 | 60 min | `.../FR-06_Forward.pdf` |
| FR-07 | PIMS Hospital → Police Foundation Metro Station | 23 | 97 | 10 min | `.../FR-07_Forward.pdf` |
| **FR-09** *(new)* | Khanna Pul → Golra Morh Metro Station | 27 | 65 | 15 min | `.../FR-09_Forward.pdf` |
| FR-14 | Bara Kahu → Mandi Morh | 18 confirmed | 65 | 15 min | `.../FR-14_Forward.pdf` |

Each of these has: a real ordered stop-name sequence, real per-stop
arrival/departure offsets for one canonical trip (verified against
multiple consecutive trips on the same PDF to be exact time-shifts of
each other by the printed headway), and a `route_stops` sequence
mechanically derived from that same canonical pattern. No stop
coordinates are present for any of these — the CDA PDFs give names and
times only (see §9).

**FR-14 caveat (carried over, unresolved):** one intermediate stop's
("CDA Stop") departure time was truncated in the original fetch and is
recorded as `null` rather than guessed.

**FR-09 naming note:** the "Forward" PDF (used here) actually runs
Khanna Pul → Golra Morh Metro Station, the *reverse* of the route's own
printed Long Name "Golra Mor to Khanna Pul" — the same Forward/Backward-
vs-Long-Name naming inversion already observed on other CDA route PDFs
in the prior pass. Recorded exactly as printed, not silently "corrected."

### Tier 2 — PARTIALLY_SUPPORTED_TOPOLOGY_ONLY: 1 route

| Route | Basis |
|---|---|
| Red Line (Metrobus, not a feeder — included here for completeness of the tier system) | 23-stop ordered sequence reconstructed from a secondary source (rehbar.pk), cross-checked against Wikipedia's station-name list — reliable enough to encode as `route_stops`, but not a timetable and not from an official source |

### Tier 3 — ROUTE_KNOWN_NO_TOPOLOGY: 19 routes

Official name, endpoints, and headway confirmed (CDA index page); no
verified ordered stop sequence or timetable encoded.

**3 Metrobus lines:** Orange, Blue, Green (unchanged from the prior
pass — partial/unordered station-name fragments exist for these but were
never verified complete or correctly ordered; not encoded as
`route_stops` for the same reason given below).

**16 feeder routes**, with what partial evidence exists noted explicitly
(so a future pass knows exactly what's already been tried, rather than
re-discovering it):

| Route | Endpoints (CDA index page) | Headway | Partial evidence (NOT encoded as topology) |
|---|---|---|---|
| FR-03A | PIMS Hospital ↔ Saidpur Village | 20 min | A 13-stop fragment was seen (PIMS Hospital, PIMS Metro Station, Katchery, F-8 Markaz, F-9 Park, Shaheen Chowk, Bahria University, Naval Complex, Faisal Masjid, Parveen Shakir Road, Kohsar Road, F-7 Markaz, Flower Market) but never confirmed complete/reaching the actual endpoint from a direct fetch |
| FR-04A | Bari Imam ↔ Quaid-e-Azam University | 30 min | None fetched |
| FR-04B | Diplomatic Enclave Shuttle Service | — | Special-purpose shuttle, no per-route PDF URL pattern confirmed to exist in the same form as the numbered FR routes |
| FR-05 | Golra Morh ↔ Taxila | 5 min | None fetched |
| **FR-08A** | PIMS Hospital ↔ Capt. Naeem Tufail Shaheed Chowk (via Abpara) | 20 min | A direct fetch was attempted; the extracted content showed only repeated timestamps at what appears to be a single terminus label across many trips, not a usable ordered multi-stop list — flagged as an extraction anomaly for a follow-up fetch, not resolved in this pass |
| **FR-08C** | PIMS Hospital ↔ Capt. Naeem Tufail Shaheed Chowk (via Faizabad) | 20 min | Same anomaly as FR-08A |
| FR-10 | Golra Morh Metro Station ↔ Taxila | 60 min | None fetched |
| FR-11 | Golra Morh Metro Station ↔ I-16 (a secondary source says I-14 — unresolved conflict, see §2) | 60 min | None fetched |
| FR-12 | Taxila ↔ Hassan Abdal | 60 min | None fetched |
| FR-13 | Golra Morh Metro Station ↔ Fateh Jang | 60 min | None fetched |
| FR-14A | Bara Kahu ↔ Satra Meel | 15 min | None fetched |
| FR-15 | Khanna Pul ↔ T-Chowk (a secondary source says Khanna Pul-Rawat — unresolved conflict, see §2) | 30 min | None fetched |
| FRB-01 | PIMS ↔ Gulberg | 5 min | None fetched — likely corresponds to the Blue Line's Gulberg Green endpoint but this relationship is not confirmed |
| **FRG-1** | PIMS ↔ Barakahu | 5 min | An 11-stop fragment was seen for the Backward direction (Barakahu, Shahdara, Malpur, Lake View Park, Foreign Affairs Office, Abpara, CDA, TNT, Children Hospital, PIMS Metro Station, Tipu Market G-8, PIMS) but never confirmed complete/correctly-ordered from a direct fetch |
| ST-01 | PIMS ↔ Daman-e-Koh (Sat/Sun only) | 60 min | None fetched — weekend-only special service |
| ST-02 | PIMS ↔ Capt. Naeem Tufail Shaheed Chowk via Shakarparian Park (Sat/Sun only) | 60 min | None fetched — weekend-only special service |

**Why partial fragments were NOT encoded as `route_stops`:** the
correction-pass brief explicitly warned against creating "multiple
competing RouteStop sequences ... without a documented reason" and
against encoding data that isn't verified. A fragment that's missing its
start, its end, or whose completeness/correctness can't be confirmed
against a second read of the same source is exactly the kind of thing
that could later turn out wrong-ordered or incomplete — encoding it now
would trade one topology-ambiguity problem (routes with no explicit
sequence) for a worse one (routes with an explicit but possibly-wrong
sequence, silently presented as reliable). These are Tier 3, not Tier 2,
specifically because of this.

### Tier 4 — INSUFFICIENT_EVIDENCE: 0 routes

No CDA feeder route falls here. All 22 have their existence, name,
endpoints, and headway confirmed directly from the CDA's own official
route-index page — a primary source. Nothing in the research encountered
a route mentioned only in an unreliable/unverifiable context.

---

## 2. Conflicts carried over, unresolved (unchanged by this pass)

- **Red Line station count**: 24 (official, multiple sources) vs. 23
  (the one ordered list found).
- **Orange Line station count**: 7 (Wikipedia's summary table) vs. 14
  (multiple independent listicles).
- **Blue Line**: 14 names found vs. 13 official count.
- **"Faizabad" vs. "Faiz Ahmed Faiz"**: two distinct real Red Line
  stations with confusingly similar names — resolved as: Faiz Ahmed Faiz
  is the Red↔Orange interchange (per Wikipedia's article body text).
  Both are separate stops in `transit_data.json`; **must never be
  merged**.
- **"PIMS" vs. "Ibn-e-Sina"**: ambiguous — both names appear as apparent
  Red Line/feeder-route station labels near the same hospital complex.
  Kept as separate stop candidates; not merged.
- **FR-11 endpoint**: "I-16" (CDA index page) vs. "I-14" (a secondary
  news report).
- **FR-15 endpoint**: "T-Chowk" (CDA index page) vs. "Rawat" (a secondary
  news report).

None of these are resolved by picking a side — both readings are
preserved in the relevant route's `notes` field in `transit_data.json`.

---

## 3. Seeding/importer fixes made this pass

1. **`Stop.external_key` added** (migration `a1b2c3d4e5f7`,
   `app/db/models/stop.py`). The importer previously matched/deduplicated
   stops by writing the dataset's `key` slug into `Stop.name` and never
   reading the dataset's actual `name` field — every stop's display name
   in the database was a slug like `"cda_pims_hospital"`, never
   `"PIMS Hospital"`. Fixed in `app/seeding/adapters/stops.py`: matching
   now uses `external_key`; `Stop.name` now holds the real display name
   and is correctly updated on re-import (the prior `_update` path never
   touched `name` at all, so even a corrected dataset re-import wouldn't
   have fixed an existing row's name).
2. **`app/seeding/importer.py`'s `_build_stop_key_maps`** updated to key
   off `Stop.external_key` instead of `Stop.name`, matching the above.
3. **Fare rules moved out of hardcoded Python** into
   `transit_data.json`'s new `fare_rules` array (`app/seeding/
   importer.py` now calls `data.get("fare_rules") or
   self._get_default_fare_rules()` — falls back to the old hardcoded
   pair only if a dataset omits the key entirely, for backward
   compatibility with any other dataset file that might exist). See §8.
4. **`route_stops` derivation for Tier-1 routes**: previously absent
   entirely for FR-01/04/07/14 (topology existed only inside
   `trips[].stop_times`); now present for all 6 Tier-1 routes,
   mechanically derived from their canonical trip pattern — see §0.

**Not changed / explicitly out of scope this pass:**
- No migration was added to give `FareRule` its own `source`/
  `confidence` columns — the provenance lives in `transit_data.json`'s
  `fare_rules[].source`/`.confidence` only, not in the database row
  itself. A future pass could add this if fare-rule provenance needs to
  be queryable/displayable from the API.
- The hardcoded route-UUID→key lookup maps in `app/seeding/adapters/
  route_stops.py`, `trips.py`, and `stop_times.py` were **not modified**
  — verified that all 26 routes' deterministic UUIDs (computed the same
  way as the original research dataset's `uuid5` scheme) were already
  present in all three maps before this pass began, so no route added or
  reclassified here required a code change to become importable.

---

## 4. Missing data (still absent — unchanged unless noted)

Everything below still applies exactly as originally documented, with
the specific counts updated:

1. **No stop-level scheduled timetable exists for the 4 main Metrobus
   lines** (Red, Orange, Blue, Green) — confirmed absent in every source
   checked across both research passes, not just unfetched.
2. **16 of 22 CDA feeder routes still have no verified stop-level
   timetable** — either not yet fetched (most), or fetched but returning
   an unusable extraction (FR-08A, FR-08C — see §1).
3. **No official route geometry/polyline exists anywhere.** The CDA PDFs
   (timetables and the graphic transit map) give names and times only —
   confirmed explicitly, no coordinates or geometry of any kind.
4. **No public GTFS/GTFS-Realtime feed exists** for this network.
5. **No confirmed public developer API** for real-time vehicle positions
   exists.
6. **No authoritative fare schedule or multi-leg formula was ever
   found** — see §8.

---

## 5. Uncertain coordinates

Every coordinate in `transit_data.json` (17 of 158 stops) traces back to
the original repository's own seed dataset, already self-described as
"geographically plausible... NOT surveyed/GTFS-grade." Treat every
coordinate as `APPROXIMATE` at best. The 36 new stops added this pass
(from FR-06 and FR-09) have **no coordinates at all** — the CDA PDFs
that sourced them give names and times only.

---

## 6. What OpenCode/Phase 4 must not assume

- Must not assume all 22 CDA feeder routes have real timetables — only 6
  do (§1, Tier 1).
- Must not assume a Tier-3 route's endpoint/headway implies anything
  about its stop sequence — Tier 3 explicitly means "no reliable
  ordered topology," even when endpoints are officially confirmed.
- Must not treat FR-08A/FR-08C's fetch attempts as "route doesn't have a
  real timetable" — the evidence is genuinely ambiguous (extraction
  anomaly, not a confirmed absence); a re-fetch with a different
  extraction approach is a reasonable next step, not a dead end.
- Must not assume `Stop.name` is a stable machine key anymore — use
  `Stop.external_key` for that; `Stop.name` is display text and may
  legitimately be edited/corrected without changing a stop's identity.
- Must not assume `FareRule` rows carry any provenance metadata in the
  database — that lives only in `transit_data.json`'s `fare_rules[]`.
- Must not assume geocoding coverage is still 88/122 — that figure
  predates this pass's 36 new stops and has not been re-run (§9).

---

## 7. Route topology — explicit statement (per correction-pass requirement)

For every route where an ordered stop sequence is supported by source
data (Tier 1 and Tier 2), `Route → ordered RouteStop` is now
**deterministic and explicit** in `transit_data.json`, and for Tier-1
routes specifically it is **mechanically derived** from that route's
canonical trip pattern rather than independently maintained — the two
representations cannot drift apart or contradict each other because
there is only one source of truth (the trip pattern) and `route_stops`
is regenerated from it. No route in the dataset has more than one
`RouteStop` sequence for the same route/direction. No route has
competing/contradictory sequences. Routes without reliable topology
(Tier 3) simply have no `route_stops` entries at all — never a guessed
or partial one.

---

## 8. Fares

No authoritative fare schedule was found in either research pass.
Secondary sources (INCPak, icons.com.pk) report conflicting rough
one-way figures (~PKR 30 for Red Line, ~PKR 100 for CDA feeder routes as
of a mid-2025 update per INCPak; ~PKR 40 per icons.com.pk) with no
multi-leg/transfer formula documented anywhere. `transit_data.json`'s
`fare_rules` array retains the same two flat-rate tiers the codebase
already had (Standard Metrobus: base 50 + 20/leg; Feeder Route: base 30
+ 15/leg, both PKR) — **not re-invented, just made data-driven and
explicitly labeled `confidence: "APPROXIMATE"`** with a `source` field
stating plainly that the flat base+per-leg formula itself is an
architectural assumption (no zone/distance-based system was found), not
sourced data. Student/special fares, an integrated multi-route fare, and
a documented transfer discount were all considered per the correction-
pass brief and **not added** — no research evidence supports any of
them existing as a distinct fare product for this network.

---

## 9. Geocoding and geometry status (explicit, since this pass touched neither)

This session had **no live database and no outbound network access** to
either a geocoding service or OSRM (same sandbox constraint documented in
the prior Phase 2/3 handoffs). Nothing about stop-coordinate coverage or
route geometry was attempted or changed beyond what's already inside
`transit_data.json` (17 curated coordinates, unchanged; 36 new
coordinateless stops added). The previously-reported "88 of 122 located"
figure describes a **live-database-only** enrichment from
`scripts/geocode_stops.py` that has never been reflected back into the
JSON file and has **not been re-run since this pass's 36 new stops were
added** — treat post-pass located-stop coverage as **unknown** until
that script is run again against a live database that has this pass's
expanded dataset imported.
