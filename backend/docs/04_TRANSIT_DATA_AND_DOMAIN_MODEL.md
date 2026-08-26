# 04 — Transit Data and Domain Model

This document specifies the domain model and, critically, the **data
provenance** for every transit dataset the system uses. Every figure
below reflects the actual currently-available data, not an aspiration
— treat coverage gaps stated here as real constraints to design around,
not as historical facts about a prior codebase.

## 1. Domain model

- **Agency** — a transit operator (e.g. PMTA, CDA/CMTA).
- **Route** — a named/numbered service, belongs to one Agency, has a
  color/label and an optional PostGIS `LineString` geometry (`path`)
  for map display.
- **Stop** — a physical location (`PostGIS geography(Point)`), may
  serve multiple routes. Carries coordinate provenance fields:
  `coordinate_source`, `coordinate_confidence`. Also carries
  `external_key` (added this pass) — the canonical dataset's stable slug
  (e.g. `"cda_pims_hospital"`), used for import matching/deduplication,
  kept deliberately separate from `name` (the human-readable display
  name, e.g. `"PIMS Hospital"`) after a bug where the importer wrote the
  slug into `name` and never used the dataset's actual `name` field at
  all — see `docs/DATA_GAPS.md`'s "Seeding/importer fixes" section.
- **RouteStop** — ordered association of a Stop to a Route
  (`sequence`), with optional `distance_along_route_m`.
- **Trip** — a scheduled run of a Route, with a status lifecycle
  (`scheduled → active → completed/cancelled`).
- **StopTime** — `arrival_offset_s`/`departure_offset_s` (seconds since
  `Trip.scheduled_start_time`) per stop of a Trip.
- **Vehicle** — a physical bus (simulated unless a real feed is
  connected).
- **VehiclePosition** — lat/lon, heading, timestamp, `source` field
  (`"simulated"` or `"realtime"`).
- **FareRule** — `base_fare`, `per_leg_fare`, `currency`, `name`.
- **User** — account with role (`passenger`/`admin`).
- **Ticket** — state machine `ACTIVE → USED | EXPIRED | REVOKED`,
  signed QR payload.

`Route.geometry_source` / `geometry_confidence` must track whether a
route's geometry is OSRM-derived (see §4 below) vs. absent.

## 2. Transit data — the honest inventory

**Do not present any figure in this section as higher than stated, and
do not fabricate data to fill a gap listed here.**

> **UPDATE (two correction passes, 2026-08-25):** this section
> originally reflected a data-collection pass that only fetched complete
> timetables for 4 of the 22 CDA feeder routes — a limitation of that
> pass, not the intended scope. Pass 1 fetched 2 more (FR-06, FR-09) and
> classified **all 22** feeder routes plus the 4 Metrobus lines into a
> 4-tier coverage system (see `docs/DATA_GAPS.md` for the full
> route-by-route table). Pass 2 (an audit + further-expansion pass)
> fetched 3 more (FR-03A, FR-10, FR-15 — 9 of 22 now fully supported),
> ran a full data-integrity audit (zero issues found), explained the
> `route_stops` count discrepancy raised during review (it was never a
> real inconsistency — see `docs/DATA_GAPS.md` §11), removed a dead
> top-level `stop_times` schema artifact, and investigated (but did not
> add) other Islamabad/Rawalpindi transit systems. See `plan.md`'s
> "Correction Pass" handoff sections for exact figures.

| Dataset | Coverage |
|---|---|
| Agencies/routes (names, endpoints, headways) | 4 Metrobus lines (Red/Orange/Blue/Green) + 22 confirmed CDA feeder route/direction pairs, all with `confidence: OFFICIAL` name/headway/endpoint data |
| Stop coordinates (in `transit_data.json` itself) | **17 of 200 stops** carry a curated coordinate in the canonical dataset file; **183 remain `UNKNOWN`** — no coordinate may be fabricated for these. (A prior Phase 2 pass separately geocoded 88 of the then-122 stops **directly against a live database**, via `scripts/geocode_stops.py` — that enrichment is NOT reflected back into `transit_data.json` and has NOT been re-run since two correction passes added 78 new stops combined; see `docs/DATA_GAPS.md` §9 for exact status.) |
| Route geometry (OSRM road-snap) | **0 real routes currently have complete geometry in the canonical dataset.** Unchanged by this pass — still blocked on stop-coordinate coverage, now for 9 timetabled routes instead of 4 (all still with unlocated stops) |
| Stop-level timetables | **9 of 22 CDA feeder routes** (was 4, then 6) have real, officially-sourced stop-level timetables: FR-01 (26 stops), **FR-03A (13 stops, new)**, FR-04 (25 stops), FR-06 (26 stops), FR-07 (23 stops), FR-09 (27 stops), **FR-10 (25 stops, new)**, FR-14 (18 stops), **FR-15 (16 stops, new)**. All 22 feeder routes are now explicitly classified into a 4-tier coverage system — see `docs/DATA_GAPS.md`. The 4 main Metrobus lines still have **no stop-level timetable** — headway/frequency only |
| Route topology (RouteStop ordering) | **Fixed this pass:** every route with a canonical timetable now has its `route_stops` sequence **mechanically derived** from that timetable's stop order (not a separately hand-maintained list) — eliminating the topology-ambiguity risk of the two representations silently drifting apart or contradicting each other. Red Line's independently-sourced 23-stop sequence (no timetable backing it) is unaffected |
| Fares | DB-driven, static, flat per-boarding formula (`base_fare + per_leg_fare × (legs−1)`) — **now sourced from `transit_data.json`'s `fare_rules` array** (previously hardcoded directly in `app/seeding/importer.py`, bypassing the dataset entirely) — not distance-based, not from an external API, and **explicitly `confidence: APPROXIMATE`**: no authoritative fare schedule or multi-leg formula was ever found in research; the flat per-boarding formula itself is an architectural choice, not sourced data (see `docs/DATA_GAPS.md` §8) |
| Real-time vehicle data | **Does not exist anywhere.** No official GPS feed exists for this transit system (see §5). All "live" vehicle data must be simulation until/unless one is connected |

## 2a. Route coverage tiers (added this pass)

Every route in `transit_data.json` now carries an explicit
`coverage_tier` (1–4) and `coverage_tier_label`, so "how supported is
this route" is never something a future pass has to re-derive from
scratch or guess at:

| Tier | Label | Meaning | Count |
|---|---|---|---|
| 1 | `FULLY_SUPPORTED` | Ordered topology + real, officially-sourced stop-level timetable | 9 (FR-01, FR-03A, FR-04, FR-06, FR-07, FR-09, FR-10, FR-14, FR-15) |
| 2 | `PARTIALLY_SUPPORTED_TOPOLOGY_ONLY` | Ordered topology from reliable (if secondary) sources, no timetable | 1 (Red Line) |
| 3 | `ROUTE_KNOWN_NO_TOPOLOGY` | Route identity/endpoints/headway confirmed from an official source, but no reliable ordered stop sequence | 16 (Orange, Blue, Green, and 13 of the 22 feeder routes) |
| 4 | `INSUFFICIENT_EVIDENCE` | Route mentioned in research but existence itself isn't reliably established | 0 — every CDA feeder route's *existence* is confirmed by the official CDA route-index page, so nothing in this dataset falls in tier 4 today |

See `docs/DATA_GAPS.md` for the full route-by-route breakdown, including
which routes have a *partial* stop-name fragment that was deliberately
**not** encoded as `route_stops` because it wasn't verified complete/
correctly-ordered from a direct source fetch (encoding an unverified
partial sequence risks exactly the "contradictory topology" problem this
pass was asked to eliminate, not reintroduce it under a different name).

## 3. Data provenance summary

| Source | Type | Reliability | What it supplies |
|---|---|---|---|
| CDA Transit Map of Islamabad (PDF, "V-06") | Official government, graphic map | High for what it contains, but not machine-tabular | Feeder route codes/names/endpoints, weekend special-trip services, unordered stop-name vocabulary |
| CDA feeder-route timetable PDFs (`cda.gov.pk/Assets/metro_transit_route/...`) | Official government, structured stop-level | High | The 4 imported real timetables (§2); 18 more confirmed-to-exist but not yet fetched |
| Wikipedia "Rawalpindi–Islamabad Metrobus" article | Secondary, well-cited | Medium-high for structural facts (lengths, opening dates, station *counts*); lower for ordered per-station name lists | Route lengths, official station counts, operator names |
| Secondary listicles (INCPak, rehbar.pk, icons.com.pk, Graana) | Secondary/SEO | Lower — used only for cross-checking, never as sole source for anything load-bearing | Ordered Red Line station-name reconstruction, fare/frequency cross-checks |
| Curated seed coordinates (17 of the 88 located stops) | Manually curated, labeled approximate | Low-medium (`confidence: APPROXIMATE`) | Usable only where the seed stop's name clearly matches a real, confirmed station |
| Nominatim (OpenStreetMap geocoder) | Automated geocoding | Variable, per-result confidence tracked | The majority of located stop coordinates |
| OSRM (public routing engine) | Automated road-snapping | High for road-snap fidelity, **not** a substitute for an official route alignment | Route geometry generation, once a route's stops are located |

**Known unresolved data conflicts (do not silently pick a side — carry
both readings forward):** Red Line station count (23 reconstructed vs.
24 official); Orange Line (7 vs. 14 in different sources); Blue Line
(13 vs. 14). Wikipedia's network-wide "52 stations" figure reconciles
against summed official per-line counts (24+7+13+8=52) but not against
the named-station lists reconstructable from other sources.

## 4. Route geometry — what it is and isn't

`Route.path` (a PostGIS `LineString`) must be generated by
**road-snapping the route's known stop coordinates through OSRM** — it
is a plausible road-following path, **not a verified official route
alignment**. This distinction matters for the map and for any
narration referencing route geometry: OSRM-derived geometry must never
be described as "the official route," only as "the road path connecting
these stops." A better future source (official BRT alignment data, OSM
transit relations) should take priority if it ever becomes available —
this is a documented extension point, not a current capability.

## 5. Real-time data — confirmed absence

No official real-time vehicle-tracking API exists for this transit
system today. A public CDA app announcement (mid-2026) describes an
in-app live-tracking feature via Google Maps integration, but **no
external API for third-party consumption is known to exist.** This is
why the simulation subsystem (`07_REALTIME_SIMULATION_AND_ETA.md`) is
required and why every vehicle position the system ever shows must be
labeled `source: "simulated"` unless a real feed is genuinely
connected.

## 6. Fares — explicit statement (do not overclaim)

Fares must be **DB-driven, flat, and static** — not hardcoded scattered
constants, but also not sourced from any external fare API or dataset
(none exists). The formula and its rationale are specified in
`08_TICKETING_AUTH_AND_ADMIN.md`.

## 7. Working with this data

The dataset described in §2–§3 must be imported using the schema in
§1. Expanding coverage (more geocoded stops, more fetched timetables,
more generated route geometry) is valuable but should be scoped as an
explicit, time-boxed task (see `10_IMPLEMENTATION_HANDOFF.md`), not
assumed to happen automatically.

**Do not claim, anywhere in the system or its documentation, that:**
routes have official-alignment geometry (they have OSRM road-snap
geometry, where present at all); all stops have coordinates (88/122);
all routes have real timetables (4 of ~22); any vehicle position is
real-time (unless a real feed is genuinely connected — by default all
positions are simulated).
