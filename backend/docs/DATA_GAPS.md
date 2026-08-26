# DATA_GAPS.md

Everything the backend/importer must not assume, plus the authoritative
route-by-route classification for `backend/data/transit_data.json`. This
file did not previously exist in this repository (it was rebuilt/
restructured into `docs/00`–`docs/10` and this file was dropped) — it is
recreated here per the correction-pass brief, adapted for the current
dataset and codebase, not copied verbatim from the earlier repository's
version.

---

## 0. Correction-pass summary

### Pass 1 (2026-08-25, first correction pass)
The prior data-collection pass fetched complete, verified stop-level
timetables for only 4 of the 22 CDA feeder routes (FR-01, FR-04, FR-07,
FR-14). **That was a limitation of that pass, not the intended scope.**
Pass 1 fetched and verified 2 more (FR-06, FR-09), bringing the total to
6/22, and made the route-topology and `Stop.external_key` fixes
described below.

### Pass 2 (2026-08-25, this pass — audit + further expansion)
- Fetched and verified **3 more** complete feeder timetables:
  **FR-03A** (PIMS Hospital → Flower Market, 13 stops, 97 trips/day,
  10-min headway — see the endpoint-naming conflict noted in §1), **FR-10**
  (Golra Morh → Taxila, 25 stops, 19 trips/day, 50-min average headway),
  and **FR-15** (Khanna Pul → T-Chowk, 16 stops, 33 trips/day, 30-min
  headway). **Fully-supported feeder routes: 6 → 9 of 22.**
- Performed the full data-integrity audit requested in the correction
  brief (duplicate IDs, orphaned references, duplicate sequences,
  referential integrity across every table) — **zero issues found**; see
  §10.
- Explained and regression-tested the `route_stops` total (168 → now
  222 after this pass's 3 new routes) — see §11.
- Audited the top-level `transit_data.json` schema and found a real,
  fixed issue: a dead, always-empty, never-read top-level `stop_times`
  key — see §12.
- Investigated whether other Islamabad/Rawalpindi transit systems beyond
  CDA feeder routes and the existing Metrobus/Red-Line entry could be
  reliably added — **none were found that meet the evidence bar**; see
  §13.
- Re-audited fares — no new authoritative fare information was found;
  existing `fare_rules` entries are unchanged.

**What did NOT change:** the 13 feeder routes still without a verified
complete timetable are still without one — nothing was fabricated for
them (FR-08A/FR-08C's anomalous prior fetch was not re-attempted this
pass — still open, see §1). Stop-coordinate geocoding was not re-run (no
live database/network access in this session — see §9, now covering 200
stops instead of 158). Route geometry generation (OSRM) was not
attempted (out of this pass's explicit scope). No frontend files were
inspected or touched. No new operator/agency was added (see §13).

---

## 1. All 22 CDA feeder routes — explicit classification

Every route below exists officially per the CDA's own route-index page
(`https://www.cda.gov.pk/cdaTransitMap`) — an authoritative primary
source for existence, name, endpoints, and headway. **Tier reflects
topology + timetable support only, not whether the route itself is
real** (all 22 are real, confirmed routes).

### Tier 1 — FULLY_SUPPORTED (topology + real timetable): 9 routes

| Route | Endpoints | Stops | Trips/day | Headway | Source PDF |
|---|---|---|---|---|---|
| FR-01 | Khanna Pul ↔ NUST Metro Station | 26 | 16 | 60 min | `.../FR-01_Backward.pdf` |
| **FR-03A** *(new)* | PIMS Hospital → Flower Market | 13 | 97 | 10 min | `.../FR-03A_Forward.pdf` |
| FR-04 | PIMS Hospital → Bari Imam | 25 | 97 | 10 min | `.../FR-04_Forward.pdf` |
| FR-06 | PIMS Metro Station → Golra Sharif | 26 | 17 | 60 min | `.../FR-06_Forward.pdf` |
| FR-07 | PIMS Hospital → Police Foundation Metro Station | 23 | 97 | 10 min | `.../FR-07_Forward.pdf` |
| FR-09 | Khanna Pul → Golra Morh Metro Station | 27 | 65 | 15 min | `.../FR-09_Forward.pdf` |
| **FR-10** *(new)* | Golra Morh → Taxila | 25 | 19 | 50 min (avg, see note) | `.../FR-10_Forward.pdf` |
| FR-14 | Bara Kahu ↔ Mandi Morh | 18 confirmed | 65 | 15 min | `.../FR-14_Forward.pdf` |
| **FR-15** *(new)* | Khanna Pul → T-Chowk | 16 | 33 | 30 min | `.../FR-15_Forward.pdf` |

Each of these has: a real ordered stop-name sequence, real per-stop
arrival/departure offsets for one canonical trip (verified against
multiple consecutive trips on the same PDF to be exact time-shifts of
each other by the printed headway — except FR-10, see below), and a
`route_stops` sequence mechanically derived from that same canonical
pattern. No stop coordinates are present for any of these — the CDA PDFs
give names and times only (see §9).

**FR-03A conflict (new, unresolved):** this route's fetched timetable
gives THREE different endpoint descriptions across three sources: the
timetable PDF's own "Long Name" field says "PIMS Hospital to **Faisal
Masjid**" (which is only the 8th of 13 stops, not the actual terminus);
the route's real stop sequence actually ends at "**Flower Market**"
(used as the canonical endpoint in this dataset, since it's the most
concrete, directly-observed fact); and the CDA transit-map PDF's
route-detail caption says "PIMS Hospital to **Saidpur Village** via F-8"
(a fourth place name that doesn't appear anywhere in the fetched stop
sequence at all). None of these are resolved — all three are preserved
here rather than silently picking one.

**FR-10 headway note:** the PDF's own "Average Headway" field says 50
min, but consecutive trip start times actually alternate 30-min/60-min
gaps (06:00, 06:30, 07:00, 07:30, 08:00, ...) rather than a uniform
50-minute spacing. Recorded exactly as printed on the source document,
not corrected or recomputed.

**FR-15 conflict (new, unresolved):** a secondary news report (Daily
Times, 2025) describes this route's endpoint as "Rawat"; both the CDA
index page and this route's own fetched timetable PDF say "T-Chowk." The
official-source reading (T-Chowk) is used here, with the secondary
reading preserved in §2.

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

### Tier 3 — ROUTE_KNOWN_NO_TOPOLOGY: 16 routes

Official name, endpoints, and headway confirmed (CDA index page); no
verified ordered stop sequence or timetable encoded.

**3 Metrobus lines:** Orange, Blue, Green (unchanged from the prior
pass — partial/unordered station-name fragments exist for these but were
never verified complete or correctly ordered; not encoded as
`route_stops` for the same reason given below).

**13 feeder routes**, with what partial evidence exists noted explicitly
(so a future pass knows exactly what's already been tried, rather than
re-discovering it):

| Route | Endpoints (CDA index page) | Headway | Partial evidence (NOT encoded as topology) |
|---|---|---|---|
| FR-04A | Bari Imam ↔ Quaid-e-Azam University | 30 min | None fetched |
| FR-04B | Diplomatic Enclave Shuttle Service | — | Special-purpose shuttle, no per-route PDF URL pattern confirmed to exist in the same form as the numbered FR routes |
| FR-05 | Golra Morh ↔ Taxila | 5 min | None fetched this pass — note FR-10 (now Tier 1) also runs Golra Morh ↔ Taxila; FR-05's relationship to FR-10 (a faster/express variant? a different routing?) is unconfirmed |
| **FR-08A** | PIMS Hospital ↔ Capt. Naeem Tufail Shaheed Chowk (via Abpara) | 20 min | A direct fetch was attempted (pass 1); the extracted content showed only repeated timestamps at what appears to be a single terminus label across many trips, not a usable ordered multi-stop list — flagged as an extraction anomaly for a follow-up fetch, not re-attempted this pass |
| **FR-08C** | PIMS Hospital ↔ Capt. Naeem Tufail Shaheed Chowk (via Faizabad) | 20 min | Same anomaly as FR-08A |
| FR-11 | Golra Morh Metro Station ↔ I-16 (a secondary source says I-14 — unresolved conflict, see §2) | 60 min | None fetched |
| FR-12 | Taxila ↔ Hassan Abdal | 60 min | None fetched |
| FR-13 | Golra Morh Metro Station ↔ Fateh Jang | 60 min | None fetched |
| FR-14A | Bara Kahu ↔ Satra Meel | 15 min | None fetched |
| FRB-01 | PIMS ↔ Gulberg | 5 min | None fetched — likely corresponds to the Blue Line's Gulberg Green endpoint but this relationship is not confirmed |
| **FRG-1** | PIMS ↔ Barakahu | 5 min | An 11-stop fragment was seen for the Backward direction (Barakahu, Shahdara, Malpur, Lake View Park, Foreign Affairs Office, Abpara, CDA, TNT, Children Hospital, PIMS Metro Station, Tipu Market G-8, PIMS) but never confirmed complete/correctly-ordered from a direct fetch |
| ST-01 | PIMS ↔ Daman-e-Koh (Sat/Sun only) | 60 min | None fetched — weekend-only special service |
| ST-02 | PIMS ↔ Capt. Naeem Tufail Shaheed Chowk via Shakarparian Park (Sat/Sun only) | 60 min | None fetched — weekend-only special service |

**Note:** FR-03A, FR-10, and FR-15 were promoted from Tier 3 to Tier 1
this pass (their previously-partial or entirely-absent evidence is now a
confirmed, complete, fetched timetable) — see §1's Tier 1 table.

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
`transit_data.json`. The previously-reported "88 of 122 located" figure
describes a **live-database-only** enrichment from
`scripts/geocode_stops.py` that has never been reflected back into the
JSON file and has **not been re-run since either correction pass added
new stops** — 200 stops total as of this pass (was 158 after pass 1, 122
before that), of which **17 carry a curated coordinate and 183 are
`UNKNOWN`**. Treat post-pass located-stop coverage as **unknown** until
that script is run again against a live database that has this pass's
expanded dataset imported.

---

## 10. Data-integrity audit (this pass)

A full static audit was run against `transit_data.json` directly
(Python, no database needed) covering every category the correction
brief asked for:

| Check | Result |
|---|---|
| Duplicate IDs (stops, routes, operators, trips) | **0 found** |
| Duplicate stop `key`s | **0 found** |
| Duplicate route `key`s | **0 found** |
| Orphaned `route_stops` (invalid `route_id`) | **0 found** |
| Orphaned `route_stops` (invalid `stop_id`) | **0 found** |
| Orphaned `trips` (invalid `route_id`) | **0 found** |
| Invalid `stop_times[].stop_id` references | **0 found** |
| Duplicate `(route_id, sequence)` pairs in `route_stops` | **0 found** |
| A stop appearing twice within the same route's sequence | **0 found** |
| More than one `CANONICAL_PATTERN` trip for the same `(route_id, direction)` | **0 found** |
| Invalid `transfers[].stop_ids`/`route_ids` references | **0 found** |
| Fare-rule references | N/A — `fare_rules` carries no foreign keys to audit |

**Shared-stop verification**: 30 stops are legitimately referenced by
more than one route (e.g. "Khanna Pul" appears on FR-01, FR-09, and
FR-15; "NUST Metro Station" appears on FR-01, FR-07, and FR-10) —
confirmed these resolve to exactly **one** `Stop` record each, shared
correctly across routes via case-insensitive slug matching, not
duplicated per route. This is exactly the real-world behavior expected
of a genuine road network where multiple feeder routes share physical
corridor segments.

**No genuine inconsistencies were found to fix.** The only changes made
this pass are additive (new routes/stops/trips) and the schema cleanup
in §12.

---

## 11. The `route_stops` count, explained (168 → now 222)

The count reported after pass 1 was **168**, and the reported per-route
FR breakdown (26+25+26+23+27+18 = 145) does not match 168 on its own —
**this was never an inconsistency in the data**, only an incomplete
breakdown in the report that presented it. The missing 23 is **Red
Line's** `route_stops` count, which pass 1 didn't list in that summary
table (Red Line isn't a CDA feeder route, so it wasn't included in the
"FR-*" table shown) but which was, and still is, correctly present in
the database:

```
145 (six Tier-1 feeder routes' route_stops, pass 1)
+ 23 (Red Line, Tier 2, pre-existing, independently sourced)
= 168   <- matches the reported total exactly
```

**This pass's total (222) breaks down as:**

| Route | route_stops | Basis |
|---|---|---|
| FR-01 | 26 | Tier 1, canonical trip |
| FR-03A | 13 | Tier 1, canonical trip *(new)* |
| FR-04 | 25 | Tier 1, canonical trip |
| FR-06 | 26 | Tier 1, canonical trip |
| FR-07 | 23 | Tier 1, canonical trip |
| FR-09 | 27 | Tier 1, canonical trip |
| FR-10 | 25 | Tier 1, canonical trip *(new)* |
| FR-14 | 18 | Tier 1, canonical trip |
| FR-15 | 16 | Tier 1, canonical trip *(new)* |
| **Tier-1 subtotal** | **199** | = sum of all 9 canonical trips' `stop_times` lengths, exactly |
| Red Line | 23 | Tier 2, independently sourced (no canonical trip) |
| **Grand total** | **222** | |

Every other route (Tier 3/4) has **zero** `route_stops` rows — verified
directly, not assumed. `tests/test_phase3_seeding.py::TestDatasetParsing
::test_route_stop_total_matches_per_route_breakdown` (new this pass)
asserts all of the above programmatically — computed from the dataset,
not hardcoded — so this can never silently drift out of sync again, and
a future pass adding a 10th Tier-1 route doesn't require another
by-hand reconciliation like this one.

**Conclusion: the 168 figure was correct and internally consistent all
along.** The "discrepancy" was an artifact of an incomplete summary
table in a chat report, not a bug in the dataset or the importer. No fix
was needed for this specifically — only the regression test to make sure
a similar reporting gap doesn't cause real confusion again.

---

## 12. `transit_data.json` schema audit

Walked every top-level key's actual producer/consumer relationship in
the codebase (not just its presence in the JSON):

| Key | Populated by | Consumed by | Status |
|---|---|---|---|
| `operators` | this dataset | `app/seeding/adapters/agencies.py` | OK |
| `stops` | this dataset | `app/seeding/adapters/stops.py` | OK |
| `routes` | this dataset | `app/seeding/adapters/routes.py` | OK |
| `route_stops` | this dataset | `app/seeding/adapters/route_stops.py` | OK |
| `route_variants` | never populated (always `[]`) | never read by any adapter | Intentional placeholder for a future route-variant concept (e.g. modeling FR-08A/FR-08C as variants of a single logical route) — not a bug, just unused so far; left in place, not removed, since removing a genuinely-planned-for-later key is a different kind of change than removing a dead one (see next row) |
| `service_calendars` | this dataset | not yet consumed by any adapter found in `app/seeding/` | **Gap, not a bug**: the importer has no `service_calendars` adapter at all yet — these 2 records exist in the dataset but nothing imports them into the database. Not fixed this pass (adding a new adapter is more than the "genuine inconsistency" fix scope this pass was asked for; flagged here for Phase 4/a future pass instead) |
| `trips` | this dataset | `app/seeding/adapters/trips.py` (top-level trip fields) + `app/seeding/adapters/stop_times.py` (nested `trips[].stop_times`) | OK |
| ~~`stop_times`~~ (top-level) | **always `[]`, never populated** | **never read — confirmed by direct code inspection; the importer only ever reads `trips[].stop_times`, never `data["stop_times"]`** | **Accidental artifact. Removed this pass** (see below) |
| `transfers` | this dataset | not yet consumed by any adapter found in `app/seeding/` | Same situation as `service_calendars` — a real gap, not this pass's to fix |
| `fare_rules` | this dataset (pass 1) | `app/seeding/importer.py`'s `_import_fare_rules` | OK |

**Fix made:** the top-level `stop_times: []` key has been **removed**
from `transit_data.json`. It was a vestigial artifact from an earlier
schema draft (this project's very first dataset design considered a flat
top-level stop-times list before the actual importer implementation
settled on nesting `stop_times` under each `trips[]` entry instead) —
confirmed by direct inspection of `app/seeding/importer.py` and
`app/seeding/adapters/stop_times.py` that neither ever reads
`data["stop_times"]`, only `data["trips"][i]["stop_times"]`. Keeping an
always-empty key that looks like it should hold data is more confusing
than not having it at all, so it was deleted rather than documented as
"intentionally empty." `tests/test_phase3_seeding.py
::TestDatasetParsing::test_no_dead_top_level_stop_times_key` (new this
pass) is a regression test against it reappearing.

**Not fixed (explicitly out of scope):** the fact that `service_calendars`
and `transfers` are present in the dataset but have no corresponding
seeding adapter at all is a real gap — but it's a **missing feature**,
not an **inconsistency** to fix under this pass's "audit and fix genuine
inconsistencies, don't make cosmetic changes" instruction. Building a new
adapter is implementation work beyond a data/research audit's scope;
flagged here explicitly so it isn't mistaken for "already handled."

---

## 13. Other Islamabad/Rawalpindi transit systems investigated (this pass)

Per the correction brief's request to investigate whether the canonical
dataset should be broadened beyond CDA feeder routes, the following were
checked. **Nothing new was added** — the existing `pmta` (Punjab Mass
Transit Authority) agency and Red Line entry already cover the one
additional-operator relationship that turned out to be real:

- **Punjab Masstransit Authority (PMTA)** — confirmed (Wikipedia,
  `pma.punjab.gov.pk`) to be a real, province-wide statutory body that
  also operates systems in Lahore and Multan, in addition to the
  Rawalpindi–Islamabad corridor. Its own tender listings
  (`pma.punjab.gov.pk/tenders`) directly reference "Metro Bus System In
  Rawalpindi-Islamabad (Saddar To PM Secretariat)" — this **is** the
  already-modeled Red Line, not a separate/new service. Lahore and
  Multan systems are out of this project's Islamabad/Rawalpindi scope
  and were not investigated further.
- **A claimed "Rawalpindi Metropolitan Transport System (RMTS)" /
  "Rawalpindi Green Line Electric Bus"** — a single low-reliability
  aggregator source (`metro-status.com`, already flagged as low-tier in
  the original research pass) describes a "Green Line Electric Bus"
  running "Saddar to Airport" with a flat PKR 30 fare, described as
  *separate* from the CDA Green Line (which actually runs PIMS↔Bhara
  Kahu, not Saddar↔Airport). This claim is **not corroborated by any
  other source** — not CDA's own materials, not Wikipedia, not PMTA's
  site — and the description is internally confusable with the
  already-known Red Line (also PKR 30, also serving Saddar). **Not
  added.** Recorded here as an investigated-and-rejected candidate so a
  future pass doesn't need to re-discover and re-evaluate it from
  scratch, but treated as insufficiently reliable to incorporate per the
  brief's explicit evidence bar ("only add services for which we can
  establish reliable source evidence").
- **General Rawalpindi city bus / TMA services** — searched specifically;
  no official route/stop/timetable-level source was found for any
  Rawalpindi city-operated bus service distinct from the CDA feeder
  network and the PMTA-operated Red Line. Informal paratransit (wagons,
  Suzukis) remains excluded for the same reason given in the original
  research pass — real and heavily used, but with no authoritative
  source.

**Conclusion: no new operator/agency was added to `transit_data.json`
this pass.** The existing 2-operator model (`pmta`, `cda_cmta`) remains
accurate and complete relative to what reliable source material
supports for the Islamabad/Rawalpindi corridor specifically.

