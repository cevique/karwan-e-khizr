# SOURCES.md

Source list for `backend/data/transit_data.json`. This file did not
previously exist in this repository (see `docs/DATA_GAPS.md`'s header for
why) — recreated here, focused on **what changed across the two
correction passes**. For every source used before pass 1 (the CDA
transit map PDF, the CDA route-index page, Wikipedia, the 4
originally-fetched feeder timetables, INCPak/rehbar.pk/icons.com.pk/
Graana/metro-status.com, and OSRM as a geometry-generation tool), see the
original research package's `SOURCES.md` — reproduced in full detail
there; not re-typed here to avoid the two documents silently drifting
apart. Only sources new to pass 1 and pass 2 are documented fully below.

---

## Pass 1 (prior correction pass)

### CDA official per-route stop-level timetable PDF — FR-06
- **URL:** https://www.cda.gov.pk/Assets/metro_transit_route/FR-06_Forward.pdf
- **Publisher:** Capital Development Authority (CDA)
- **Source type:** Official, structured, stop-level timetable (Route ID,
  Short/Long Name, Direction, Total Trips, Average Headway, then
  per-trip Trip ID/Start Time + `stop_name`/`arrival_time`/`departure_time`
  rows).
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
  `CANONICAL_PATTERN` record), `route_stops` (26 rows, derived).

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
  null), `trips` (one `CANONICAL_PATTERN` record), `route_stops` (27
  rows, derived).

---

## Pass 2 (this pass)

### CDA official per-route stop-level timetable PDF — FR-03A
- **URL:** https://www.cda.gov.pk/Assets/metro_transit_route/FR-03A_Forward.pdf
- **Publisher:** Capital Development Authority (CDA)
- **Source type:** Official, structured, stop-level timetable (same
  format as every other `metro_transit_route/*.pdf`).
- **Information extracted:** Complete ordered stop list (13 stops, PIMS
  Hospital → Flower Market) and one canonical trip's real
  arrival/departure offsets, confirmed against multiple consecutive
  trips to repeat exactly every 10 minutes. 97 trips/day.
- **Reliability:** Very high (official, primary, structured) for the
  stop sequence and timing; **the route's own "Long Name" field is
  internally inconsistent with its own stop sequence** — see
  `docs/DATA_GAPS.md` §1's FR-03A conflict note.
- **Limitation:** stop names and times only — no coordinates, no route
  geometry.
- **Dataset elements depending on it:** `routes` (`fr_03a`'s
  `coverage_tier: 1`), `stops` (13 `cda_*`-keyed stops, most shared with
  FR-04/FR-06/FR-07's overlapping corridor, coordinates null), `trips`
  (one `CANONICAL_PATTERN` record), `route_stops` (13 rows, derived).

### CDA official per-route stop-level timetable PDF — FR-10
- **URL:** https://www.cda.gov.pk/Assets/metro_transit_route/FR-10_Forward.pdf
- **Publisher:** Capital Development Authority (CDA)
- **Source type:** Same format as above.
- **Information extracted:** Complete ordered stop list (25 stops, Golra
  Morh → Taxila) and one canonical trip's real arrival/departure offsets.
  19 trips/day; the PDF's own "Average Headway" field (50 min) does not
  match the actual, alternating 30/60-min gaps between consecutive trip
  start times — recorded as printed, not corrected (see
  `docs/DATA_GAPS.md` §1).
- **Reliability:** Very high (official, primary, structured).
- **Limitation:** stop names and times only — no coordinates, no route
  geometry.
- **Dataset elements depending on it:** `routes` (`fr_10`'s
  `coverage_tier: 1`), `stops` (25 `cda_*`-keyed stops, some shared with
  FR-07's NUST Metro Station / A.K Bari Road / G-11 Markaz corridor
  segment, coordinates null), `trips` (one `CANONICAL_PATTERN` record),
  `route_stops` (25 rows, derived).

### CDA official per-route stop-level timetable PDF — FR-15
- **URL:** https://www.cda.gov.pk/Assets/metro_transit_route/FR-15_Forward.pdf
- **Publisher:** Capital Development Authority (CDA)
- **Source type:** Same format as above.
- **Information extracted:** Complete ordered stop list (16 stops,
  Khanna Pul → T-Chowk) and one canonical trip's real arrival/departure
  offsets, confirmed against multiple consecutive trips to repeat exactly
  every 30 minutes. 33 trips/day.
- **Reliability:** Very high (official, primary, structured) — and
  corroborates the CDA index page's "T-Chowk" endpoint over a
  conflicting secondary-source claim of "Rawat" (see
  `docs/DATA_GAPS.md` §2).
- **Limitation:** stop names and times only — no coordinates, no route
  geometry.
- **Dataset elements depending on it:** `routes` (`fr_15`'s
  `coverage_tier: 1`), `stops` (16 `cda_*`-keyed stops, coordinates
  null; shares "Khanna Pul" with FR-01/FR-09), `trips` (one
  `CANONICAL_PATTERN` record), `route_stops` (16 rows, derived).

### Punjab Masstransit Authority — Wikipedia article
- **URL:** https://en.wikipedia.org/wiki/Punjab_Masstransit_Authority
- **Source type:** Encyclopedic secondary source.
- **Information extracted:** Confirms PMTA is a province-wide statutory
  body (est. 2012) operating systems in Lahore, Multan, and the
  Islamabad/Rawalpindi twin cities — used only to confirm the existing
  `pmta` agency entry's scope, not to add anything new (Lahore/Multan
  are out of this project's geographic scope).
- **Dataset elements depending on it:** none directly — investigative
  only, see `docs/DATA_GAPS.md` §13.

### PMTA tender listings
- **URL:** https://pma.punjab.gov.pk/tenders (and `/tenders/archive`)
- **Source type:** Official government procurement listings.
- **Information extracted:** A listed tender for "Security and Safety
  Services For Metro Bus System In Rawalpindi-Islamabad (Saddar To PM
  Secretariat)" — confirms PMTA's operational involvement in the
  already-modeled Red Line corridor specifically; found no listing for
  any other Islamabad/Rawalpindi-specific service.
- **Dataset elements depending on it:** none directly — investigative
  only, see `docs/DATA_GAPS.md` §13.

### metro-status.com blog post — investigated, NOT used as a source
- **URL:** https://metro-status.com/blog/rawalpindi-metro/
- **Why it was checked:** describes a "Rawalpindi Metropolitan Transport
  System (RMTS)" and a "Green Line Electric Bus" running "Saddar to
  Airport" - potentially a transit system not yet in the dataset.
- **Why it was NOT incorporated:** single low-reliability aggregator
  source (already flagged low-tier in the original research pass),
  uncorroborated by any official CDA/PMTA/Wikipedia source, and its
  description conflicts with the already-documented CDA Green Line
  (PIMS↔Bhara Kahu, not Saddar↔Airport) in a way that suggests possible
  confusion with the existing Red Line rather than a genuinely distinct
  service. Does not meet the correction brief's "reliable source
  evidence" bar. See `docs/DATA_GAPS.md` §13 for the full reasoning.

## Fetch attempts that did NOT produce usable data (unchanged from pass 1, not re-attempted this pass)

- **FR-08A** and **FR-08C**: fetched in pass 1; extraction returned only
  repeated timestamps against an apparent single terminus label, not a
  usable ordered sequence. Not re-attempted in pass 2 — still open for a
  future pass with a different extraction approach.
- **FRG-1**: an 11-stop fragment was seen in pass 1 (search-result
  snippet, not a direct fetch) but never confirmed complete. Not
  re-attempted in pass 2.

## Tooling note

No new tools were used this pass beyond `web_search`/`web_fetch` against
`cda.gov.pk` and, for the "other transit systems" investigation,
`pma.punjab.gov.pk` and Wikipedia. OSRM (route-geometry generation) was
not invoked — no live database/network access existed in this session.

