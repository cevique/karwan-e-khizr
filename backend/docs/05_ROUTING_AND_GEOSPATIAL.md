# 05 — Routing and Geospatial Architecture

**Scope note:** this document specifies backend geospatial and routing
responsibilities only. Basemap rendering, map UI, and all other visual
map concerns are a frontend responsibility, owned separately — see
`00_PROJECT_OVERVIEW.md` §"Backend/frontend boundary". This document
specifies Layers 3 and 4 of `02_SYSTEM_ARCHITECTURE.md` (Geospatial
Transit Intelligence and Deterministic Routing/Optimization), and
contains an explicit evaluation of whether a learned/neural routing
model belongs in this system.

## 1. Separation of concerns (deliberately distinct responsibilities)

| Concern | What it does | Technology | Owner |
|---|---|---|---|
| **Basemap** | Renders map tiles | Frontend's choice | Frontend (out of scope here) |
| **Geocoding** | Turns a free-text place name into a coordinate | Nominatim, plus a fast in-memory fuzzy match against known `Stop.name` values first | Backend |
| **Transit route geometry** | The road-following path a route's vehicles travel | OSRM road-snap of known stop coordinates (this system's own PostGIS data) | Backend |
| **Road routing** | Computing a road-following path between two coordinates (used only to *generate* route geometry, not for end-user turn-by-turn navigation) | OSRM | Backend |
| **Transit/journey routing** | Finding the optimal sequence of transit rides + walks between an origin and destination | This system's own deterministic graph search (Layer 4) | Backend |
| **Live transit data** | Vehicle positions, ETAs, delays | This system's own simulation (see `07`), never any of the above | Backend |

These must remain architecturally distinct: **no external map/basemap
provider may ever become the source of truth for the transit
network** — the system's own PostGIS data always is. The backend's
responsibility ends at emitting coordinates and GeoJSON (§6); it never
renders anything.

## 2. Layer 3 — Geospatial Transit Intelligence

This layer must be built as an explicit, internally callable module
within the Backend Journey Engine — invoked deterministically by Layer
4's journey search, never called directly by either LLM request (see
`02_SYSTEM_ARCHITECTURE.md` §1: neither Request #1 nor Request #2 calls
any backend function directly; Request #1 only produces a structured
intent object, and the backend engine is what invokes Layer 3/4
internally).

### Responsibilities

- **Location/place-name resolution**: free text (as extracted into
  `origin`/`destination` fields by Request #1) → candidate stop(s)/
  coordinate. Two-tier: (1) fast fuzzy match against `Stop.name` and
  curated landmark aliases (instant, no external dependency); (2)
  fallback to live Nominatim geocoding for unmatched names.
- **PostGIS spatial candidate queries**: given a coordinate, find
  candidate boarding/alighting stops within a configurable walking
  radius (default: 400m).
- **Nearby-stop discovery**: general "what's near this point" queries,
  usable by the journey engine and exposable via a direct read-only API
  endpoint for the frontend.
- **Pedestrian/walking-distance analysis**: real walking distance/time
  between a point and a stop.
- **Route geometry retrieval**: `Route.path` as GeoJSON, exposed via
  API for frontend map rendering.
- **Transit candidate-set generation**: origin/destination →
  candidate stop pairs/edges for Layer 4 to search over. Layer 3
  produces *candidates*; Layer 4 produces the *authoritative path*.

### Internal interface (called by the Backend Journey Engine — Layer 4
— not by either LLM request)

```
resolve_location(text: string)
  -> { candidates: [{stop_id, name, lat, lon, match_confidence,
       match_type: "exact_stop"|"fuzzy_stop"|"geocoded"}] }

nearby_stops(lat, lon, radius_m)
  -> { stops: [{stop_id, name, lat, lon, distance_m}] }

walking_distance(from_lat, from_lon, to_lat, to_lon)
  -> { distance_m, duration_s }

route_geometry(route_id)
  -> GeoJSON LineString | null   // null if not yet generated — never fabricated
```

If `resolve_location` returns multiple ambiguous, similarly-confident
candidates for a location Request #1 could not disambiguate on its own,
the Backend Journey Engine must produce a clarification-needed result
(listing the candidates) rather than guessing — see
`06_AI_AND_VOICE_ARCHITECTURE.md` §"Ambiguous input and failure
handling".

## 3. Layer 4 — Deterministic Routing / Optimization

### Responsibilities

- Transit graph construction from Agency/Route/Stop/RouteStop data
  (walking edges + riding edges).
- Pathfinding: Dijkstra over the graph (see §6 for why this is the
  right algorithm).
- Objectives: `fastest`, `fewest_transfers`, `least_walking`.
- Transfer computation, walking-leg computation, travel-time totals.
- Route filtering (`max_walking_distance`, `max_transfers`) and
  multi-candidate ranked responses — see §4.
- Fare application: annotate/filter candidates with fare via the fares
  service.
- Time-dependent routing where real schedule data exists (see `04` for
  current coverage): use actual next-scheduled-departure timing rather
  than a flat duration estimate.
- Orchestrating Layer 3 internally: resolving the validated intent's
  origin/destination into concrete stop candidates before searching.

### Contract

Public HTTP contract: `POST /transit/journeys/search`, with filter
fields and multi-candidate responses:

```
Request:  { origin, destination, objective, max_walk_m?, max_transfers?, departure_time? }
Response: { journeys: [ { legs, total_duration_s, total_walk_m,
                           transfer_count, route_geometry, fare?, ... } ] }
```

This is the **same endpoint** both a direct API client and the AI
pipeline (internally, after Request #1 produces and the backend
validates a structured intent) use to reach the routing engine — see
`02_SYSTEM_ARCHITECTURE.md` §4 for why this single-contract design is
architecturally load-bearing (it's what makes "AI cannot bypass the
deterministic engine" true in code, not just in principle).

## 4. Journey search requirements

The journey planner must support:
1. Real filters (`max_walking_distance`, `max_transfers`) — applied to
   candidate journeys, not a new search algorithm.
2. Multi-candidate responses — up to 3 results per search: fastest,
   fewest transfers, least walking.
3. Time-dependent routing for schedule-covered routes (an
   earliest-arrival Dijkstra variant keyed on `(node, time)` is
   proportionate at this network's scale — a full RAPTOR/CSA
   implementation is not warranted).

None of this requires a fundamentally different graph-construction or
pathfinding approach from what's described in §3 — filters and
multi-candidate ranking are additive to the core search.

## 5. Backend responsibility boundary for map data

The backend must expose only plain lat/lng and GeoJSON via its APIs
(stops, route geometry, journey-leg geometry, vehicle positions) — it
must never emit screen coordinates, zoom levels, or tile URLs, and it
must never select or embed a specific basemap/tile provider. Map
rendering, panning, tile management, and basemap provider selection are
entirely a frontend concern, out of scope for this document set.

## 6. Evaluation: does a learned routing model belong here?

**Question:** should Dijkstra (or the whole routing layer) be replaced
by a learned/neural geospatial routing model, to make the "AI" story
more central?

**Answer: No.** Reasoning:

- Current research on learned routing (graph neural networks predicting
  travel times or edge-weight corrections, e.g. recent GNN-based
  shortest-path-approximation and dynamic-routing work) consistently
  uses the learned component to predict **edge weights or travel-time
  corrections that feed into a classical shortest-path search** — not
  to replace pathfinding itself. Even the most advanced production and
  research systems keep a Dijkstra/A\*-family search as the actual
  pathfinding mechanism.
- This system already has exactly that shape planned, correctly
  scoped as a separate, staged component: the predictive ETA model
  (`07_REALTIME_SIMULATION_AND_ETA.md`), which predicts travel-time/
  delay values. A second "geospatial routing model" would duplicate
  that role without adding a new capability.
- A GNN-based router needs substantial real historical trajectory data
  to train meaningfully. **No real vehicle telemetry exists for this
  system** (§04 §5) — training on synthetic simulation data alone would
  not be learning anything a deterministic, transparent
  simulation-derived cost function doesn't already encode more
  honestly.
- Transit routing has a hard, non-negotiable requirement: **never
  invent a road, stop, transfer, route, walking distance, or
  timetable.** A neural router is fundamentally a plausible-answer
  generator, not a constraint-satisfying one — the wrong tool for this
  guarantee regardless of data availability.

**What genuinely is "geospatial intelligence" here, and is worth
building:** Layer 3 as described in §2 — real PostGIS spatial queries,
real OSRM road-snap geometry, real walking-distance computation,
invoked deterministically by the Backend Journey Engine. This is
legitimate geospatial computation, entirely separate from and never
delegated to either LLM request.

**Decision, stated explicitly:** no learned/neural routing model is
part of this architecture. Dijkstra is the pathfinding algorithm inside
Layer 4, correctly understood as an implementation detail — not the
product's AI differentiator, which instead comes from Request #1/#2's
language understanding and explanation plus the separately-staged
predictive ETA component.

## 7. Origin/destination coordinates

The backend must accept an origin and destination as either free text
(resolved via §2) or as raw coordinates supplied directly by the
client. The backend must never infer a client's location from its IP
address for routing purposes (imprecise at the walking-radius scale
that matters here) — if coordinates are not supplied, the backend must
rely on Layer 3's place-name resolution rather than any location
inference of its own. How a client obtains a coordinate (device GPS,
manual entry, a map tap) is entirely a frontend concern.
