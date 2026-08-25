# SOURCES.md

Source list for `backend/data/transit_data.json`. This file did not
previously exist in this repository (see `docs/DATA_GAPS.md`'s header for
why) — recreated here, focused on **what changed this correction pass**.
For every source used before this pass (the CDA transit map PDF, the CDA
route-index page, Wikipedia, the 4 originally-fetched feeder timetables,
INCPak/rehbar.pk/icons.com.pk/Graana/metro-status.com, and OSRM as a
geometry-generation tool), see the original research package's
`SOURCES.md` — reproduced in full detail there; not re-typed here to
avoid the two documents silently drifting apart. Only the two new sources
below are documented fully in this file.

---

## New this pass

### CDA official per-route stop-level timetable PDF — FR-06
- **URL:** https://www.cda.gov.pk/Assets/metro_transit_route/FR-06_Forward.pdf
- **Publisher:** Capital Development Authority (CDA)
- **Source type:** Official, structured, stop-level timetable (Route ID,
  Short/Long Name, Direction, Total Trips, Average Headway, then
  per-trip Trip ID/Start Time + `stop_name`/`arrival_time`/`departure_time`
  rows) — same format as the 4 timetables fetched in the prior pass.
- **Information extracted:** Complete ordered stop list (26 stops, PIMS
  Metro Station → Golra Sharif) and one canonical trip's real
  arrival/departure offsets, confirmed by inspecting multiple consecutive
  trips to be exact time-shifts of each other by the printed 60-minute
  headway. 17 trips/day.
- **Reliability:** Very high (official, primary, structured).
- **Limitation:** stop names and times only — no coordinates, no route
  geometry.
- **Dataset elements depending on it:** `routes` (`fr_06`'s `coverage_tier:
  1`), `stops` (26 `cda_*`-keyed stops, coordinates null), `trips` (one
  `CANONICAL_PATTERN` record), `route_stops` (26 rows, derived from the
  trip pattern).

### CDA official per-route stop-level timetable PDF — FR-09
- **URL:** https://www.cda.gov.pk/Assets/metro_transit_route/FR-09_Forward.pdf
- **Publisher:** Capital Development Authority (CDA)
- **Source type:** Same format as above.
- **Information extracted:** Complete ordered stop list (27 stops; the
  "Forward" direction actually runs Khanna Pul → Golra Morh Metro
  Station — see `docs/DATA_GAPS.md` §1's naming note) and one canonical
  trip's real arrival/departure offsets, confirmed against multiple
  trips to repeat exactly every 15 minutes. 65 trips/day.
- **Reliability:** Very high (official, primary, structured).
- **Limitation:** stop names and times only — no coordinates, no route
  geometry.
- **Dataset elements depending on it:** `routes` (`fr_09`'s
  `coverage_tier: 1`), `stops` (27 `cda_*`-keyed stops, coordinates
  null — some may overlap with stops already added for FR-01, which
  shares part of the same corridor; verified no duplicate stop keys were
  created), `trips` (one `CANONICAL_PATTERN` record), `route_stops` (27
  rows, derived from the trip pattern).

## Fetch attempts that did NOT produce usable data this pass

Documented so a future pass doesn't waste time re-discovering the same
outcome without a different approach:

- **FR-08A** (`https://www.cda.gov.pk/Assets/metro_transit_route/FR-08A_Forward.pdf`)
  and **FR-08C** (`.../FR-08C_Forward.pdf`): both fetched, but the
  extracted content showed only repeated timestamps against what appears
  to be a single terminus stop label repeated across many trips, not a
  usable ordered multi-stop sequence. Not clear whether this reflects the
  PDF's actual structure (a genuinely very short shuttle route) or an
  extraction artifact. Endpoint/headway are still confirmed official from
  the CDA index page (`https://www.cda.gov.pk/cdaTransitMap`) regardless.
- **FR-03A, FR-06 (partial, superseded), FR-09 (partial, superseded),
  FRG-1**: partial stop-name fragments were seen (via earlier search-
  result snippets, not this pass's direct fetches) but not confirmed
  complete/correctly-ordered — FR-06 and FR-09's fragments were
  subsequently confirmed complete by this pass's direct fetch (now Tier
  1); FR-03A and FRG-1's fragments remain unconfirmed (still Tier 3) —
  see `docs/DATA_GAPS.md` §1 for the exact fragment content preserved for
  a future attempt.

## Tooling note

No new tools were used this pass beyond `web_search`/`web_fetch` against
the same `cda.gov.pk` domain as the prior pass. OSRM (route-geometry
generation) was not invoked — no live database/network access existed in
this session to run `scripts/generate_route_geometry.py` (if this
repository has that script — not otherwise inspected this pass, out of
scope per the correction-pass brief's "do not implement Phase 4+"
instruction).
