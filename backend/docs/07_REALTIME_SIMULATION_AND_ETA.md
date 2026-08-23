# 07 — Realtime, Simulation, and Predictive ETA

**Scope note:** this document specifies backend responsibilities only
— API data contracts and internal engine behavior. Any client-side
rendering of vehicles/ETAs on a map is a frontend responsibility, out
of scope here.

## 1. Why simulation is required

**No official real-time vehicle-tracking API exists** for the
Islamabad/Rawalpindi transit system (see
`04_TRANSIT_DATA_AND_DOMAIN_MODEL.md` §5). A simulation subsystem is
therefore required to provide live vehicle behavior in the absence of a
real feed — it must run buses along **real researched routes and,
where available, real timetables**, never arbitrary fake buses on fake
routes. This is a deliberate architectural choice, not a stopgap to be
hidden: it must be presented honestly as simulation, clearly labeled as
such, and built to swap out cleanly once/if a real feed becomes
available (§2).

## 2. Simulation architecture

```
Trip + StopTime (schedule, where real; else an estimate) + Route.path (optional geometry)
        |
        v
simulation.engine.compute_position_at(schedule, elapsed_s)   [pure, deterministic]
        |
        v
VehicleLocationProvider (Protocol)
        |
        +-- SimulatedVehicleLocationProvider  (default implementation)
        +-- [FUTURE] RealGpsVehicleLocationProvider — same interface,
             swappable with no caller changes
        |
        v
Realtime REST API (vehicle positions, per-vehicle ETA)
```

- **`compute_position_at`**: given an ordered stop schedule and elapsed
  seconds, must return exactly one position — parked at the first stop
  before departure, **interpolated along route geometry where it
  exists** (falling back to straight-line interpolation between stop
  coordinates where it doesn't), dwelling at intermediate stops,
  clamped at the last stop once complete. Must also compute bearing and
  speed. This function must be pure and deterministic (no side effects,
  same inputs always produce the same output) so simulation behavior is
  reproducible and testable.
- **Timing**: where real `StopTime` data exists (see `04` for current
  coverage), simulation must use it directly. Where it doesn't, offsets
  must be synthesized from an assumed average speed (route-specific,
  grounded in whatever real distance/journey-time data exists per route
  — e.g. a route's known dedicated-lane status materially affects a
  realistic assumed speed) and a flat dwell time per stop — **explicitly
  labeled as an estimate, never presented as a real schedule.**
- **`VehicleLocationProvider` Protocol**: the abstraction that allows a
  future real GPS feed to be swapped in without changing the realtime
  API, the map rendering, or the routing engine's ETA consumption. This
  interface must be stable from the outset so the simulated
  implementation and any future real implementation are
  interchangeable.

## 3. Realtime API requirements

Every vehicle-position response must include a `source` field
(`"simulated"` or `"realtime"`). **This field must never be omitted or
defaulted such that simulated data could be mistaken for real-time
data.** This labeling is not optional polish — it is a correctness
requirement for the whole product's honesty guarantee (see
`01_PRODUCT_REQUIREMENTS.md` §8.3).

## 4. What the simulation is built on (data provenance — see `04` for
full detail)

- Real ordered stop sequences and real headways for all researched
  routes (§`04` §2).
- Real stop-level timetables for the routes where they exist — genuine
  "07:10 → Stop A, 07:17 → Stop B" data, sourced from official CDA
  timetable PDFs.
- Real-derived (OSRM road-snap) route geometry, where a route's full
  stop sequence is located — see `04` §2 for current coverage; this is
  a data-coverage gap to design around, not something the simulation
  engine itself is responsible for filling.
- Where geometry doesn't exist, straight-line interpolation between
  known stop coordinates — visually less polished, still grounded in
  real stop positions, never fabricated waypoints.

## 5. Vehicle-data API requirements (backend responsibility only)

- Vehicle-position API responses must include position, bearing/
  heading, and status (`scheduled`/`active`/`completed`), source-
  labeled per §3. Rendering these as markers on a map is a frontend
  concern.
- A journey response's ride legs must include enough identifying data
  (route ID, trip ID) for a client to correlate a selected journey with
  its live vehicle, without the backend needing to know how that
  correlation is displayed.
- A single bundled "vehicle snapshot" endpoint (active vehicles + their
  route geometry) should be considered to avoid per-vehicle N+1 API
  calls for a client rendering a live map — additive to, not a
  replacement of, per-vehicle/per-route endpoints.

## 6. Predictive ETA — staged, provider-agnostic architecture

Predictive ETA must be specified behind a provider interface,
`ETAPredictor` (consistent with the `SpeechToTextProvider`/
`IntentLLMProvider`/`JourneyResponseLLMProvider` abstractions in
`06_AI_AND_VOICE_ARCHITECTURE.md` §3 — note `ETAPredictor` is entirely
independent of the two-stage conversational pipeline; it is invoked
by the Backend Journey Engine and realtime API, never by Request #1 or
Request #2 directly):

```
class ETAPredictor:
    def predict(self, features: ETAFeatures) -> ETAPrediction | None: ...
    # returns None if this predictor has no coverage for the given
    # route/time — never a low-confidence guess dressed up as a result
```

This keeps the ETA feature **provider/model-agnostic**: a local
statistical baseline, a locally-trained lightweight ML model, or a
cloud-hosted model can all satisfy the same interface with no change to
the caller. **No cloud ML infrastructure of any specific vendor is
required for this feature to exist.**

**Baseline (permanent fallback, never removed):** the simulation-
derived ETA (remaining distance along the route ÷ assumed/scheduled
speed). This must always be present and correct, and is the value shown
whenever the configured `ETAPredictor` is unavailable, cold, or has no
coverage for the requested route/time.

**Do not require sufficient historical telemetry to train a highly
accurate production model — none exists at the outset.** The staged
approach below is designed specifically to avoid needing it:

```
Stage 1 — Deterministic scheduled/simulation ETA. [Baseline, required]

Stage 2 — Synthetic/historical dataset generation.
    Run the simulation engine repeatedly across the full timetable
    (all routes, many service dates/times, varying assumed dwell/
    traffic-noise parameters) to generate a (route, stop, time-of-day,
    day-of-week, scheduled-duration, simulated-actual-duration)
    dataset. Uses only the simulation engine as a generator — no
    separate simulation logic. Stored as a training-data artifact, not
    an operational database table.

Stage 3 — Train an ML model on the Stage 2 dataset, wrapped behind the
    ETAPredictor interface above.
    RECOMMENDED initial implementation: a statistical/lightweight-ML
    baseline — e.g. a simple average-delay-by-(route, time-of-day,
    day-of-week) lookup, or gradient-boosted trees (e.g. LightGBM/
    XGBoost) on tabular features if time allows — explainable (feature
    importances can be shown directly), fast to train on a modest
    synthetic dataset, no GPU dependency, runs locally with no cloud ML
    platform required. A linear-regression baseline is worth keeping as
    an explicit "naive vs. improved" comparison artifact.
    NOT RECOMMENDED initially: neural models — the dataset size and
    explainability requirement both favor a statistical baseline or
    gradient-boosted trees, and a neural model would cost build time
    without a corresponding benefit at this data volume.

Stage 4 — [FUTURE] Real-observation feedback loop.
    When/if a real vehicle-position feed exists, actual observed travel
    times replace/augment Stage 2's synthetic data and the model is
    periodically retrained. Requires no change to the inference-serving
    contract (§7) — only the training-data source changes, because the
    feature schema is designed in Stage 3 to already accept fields both
    synthetic and real data can supply.
```

**Realistic initial target: Stage 1 (required) + Stage 2 + a Stage 3
statistical or gradient-boosted baseline.** Stage 4 is explicitly
future and must not be implied as already happening.

## 7. ETA serving contract

```
GET /transit/realtime/vehicles/{id}/eta
  -> baseline_eta   // always present — Stage 1
  -> predicted_eta?  // present only if the ETAPredictor is reachable AND
                        has coverage for this route/time; otherwise
                        explicitly absent, never silently equal to the
                        baseline dressed up as "predicted"
```

Both values, when present, must be returned together — the predicted
value must never silently replace the deterministic one. This preserves
the deterministic engine's authority while surfacing the ML
contribution honestly.

## 8. Deployment for the ETA model (provider-agnostic)

**RECOMMENDED default: local/in-process deployment.** Train the Stage 3
model locally/in a notebook (no GPU needed for this data volume, and no
cloud ML platform required at all), load the trained artifact directly
into the backend process (or a small local inference service it calls
over localhost), and serve it from the ETA endpoint. This has **zero
cloud infrastructure dependency** and is the safest default given
provider-access uncertainty (see `00_PROJECT_OVERVIEW.md` §"Provider
independence").

**Optional, if a cloud ML deployment platform is genuinely available
and verified (DECISION REQUIRED, implementation-time):** the same
trained artifact + a small inference wrapper (e.g. Flask/FastAPI around
a scikit-learn/LightGBM/XGBoost model) can be deployed to any platform
that accepts a custom container/model-serving workload — the
`ETAPredictor` interface is what makes this an implementation detail
rather than an architectural commitment. Do not plan build time around
a specific cloud deployment platform until its access is confirmed
working end-to-end.

**What does NOT need cloud deployment, regardless of the above:** the
deterministic backend (routing, simulation, ticketing) must run
locally/in a standard container — there is no architectural reason to
require any particular cloud platform for it.

## 9. Priority note

Predictive ETA is a strong differentiator but is ranked **below** the
core conversational-to-map pipeline for initial delivery — see
`10_IMPLEMENTATION_HANDOFF.md` for the full priority ranking. It is
architecturally independent of the AI conversational layers and can be
built in parallel or after the core pipeline is solid.
