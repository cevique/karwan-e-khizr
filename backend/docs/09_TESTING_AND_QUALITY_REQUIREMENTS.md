# 09 — Testing and Quality Requirements

**Scope note:** backend only — see `00_PROJECT_OVERVIEW.md`
§"Backend/frontend boundary". This document specifies the testing and
quality bar the backend must meet. It applies across every component
described in `03`–`08`.

## 1. General testing requirements

- The system must have comprehensive automated test coverage across
  every module: transit data import, geospatial resolution, routing,
  simulation, ticketing, fares, authentication, and the AI/voice
  pipeline.
- Database-dependent tests must run against a live PostgreSQL/PostGIS
  instance, not a mocked or SQLite-only substitute — spatial query
  correctness cannot be verified without a real spatial database
  engine.
- Migrations (Alembic or equivalent) must be kept clean — a single
  linear history with no branch conflicts — and this must be checked as
  part of the test/CI process.
- Integration tests must cover full request/response contracts for
  every public API endpoint, not just unit-level logic.
- At least one end-to-end smoke test must exercise the full journey
  planning → ticket purchase → QR validation flow against a running
  instance of the system.

## 2. Routing and geospatial testing requirements

- Deterministic pathfinding correctness: given a known graph and known
  origin/destination, the routing engine must return the expected
  shortest path under each objective (`fastest`, `fewest_transfers`,
  `least_walking`).
- Filter correctness: each supported filter (`max_walking_distance`,
  `max_transfers`) must be tested to confirm it excludes journeys that
  violate the constraint.
- Time-dependent routing correctness (where schedule data exists): a
  journey search at a time just before and just after a scheduled
  departure must be tested to confirm the returned boarding time
  reflects the correct next scheduled trip.
- Geospatial candidate generation: stop-snapping and nearby-stop
  queries must be tested against known coordinate fixtures with
  expected candidate sets.
- Route geometry generation (where OSRM road-snapping is used) must be
  tested against known stop sequences with expected geometry
  properties (e.g. the generated path passes near all input stops).

## 3. Simulation and realtime testing requirements

- `compute_position_at` (or equivalent) must be tested for determinism:
  identical inputs must always produce identical outputs.
- Simulation must be tested at several points along a trip's schedule
  (before departure, mid-trip, at completion) to confirm correct
  position, bearing, and status transitions.
- The `source` field on every vehicle-position response must be tested
  to confirm it is always present and correctly set.
- Regression tests must cover the fallback behavior when route geometry
  is absent (straight-line interpolation) versus present (geometry-
  following interpolation).

## 4. Ticketing testing requirements

- The full ticket lifecycle (`ACTIVE → USED`, `ACTIVE → EXPIRED`,
  `ACTIVE → REVOKED`) must be tested for every valid and invalid
  transition.
- **Concurrency requirement:** a test must simulate two near-simultaneous
  validation attempts against the same ticket and confirm exactly one
  succeeds — this is the single correctness property in the whole
  system where a race condition would be a real product bug (double-
  boarding on one ticket), and it must not be assumed correct without
  an explicit concurrent test.
- QR signing/verification must be tested against tampering scenarios
  (modified payload, mismatched owner) to confirm rejection.
- Fare calculation must be tested against known leg counts with
  expected fare outputs, and must be tested to confirm client-supplied
  fare data is never trusted.

## 5. AI and voice testing requirements (see also
`06_AI_AND_VOICE_ARCHITECTURE.md` §11, §13)

- **Groundedness testing is required, not optional.** Automated tests
  must sample Request #2 outputs and verify every number/time/place
  mentioned traces back to a value present in the authoritative JSON
  the Backend Journey Engine produced for that command. This is the
  concrete, checkable version of "Request #2 must never invent a
  transit fact."
- **Request #1 output validation must be tested**: malformed or
  incomplete structured output from Request #1 must be tested to
  confirm it is rejected before reaching the Backend Journey Engine,
  never silently coerced or passed through.
- **Two-stage behavior must be tested**: a test must confirm that a
  single command results in exactly one Request #1 stage and exactly
  one Request #2 stage (each stage internally attempting at most one
  primary provider call and, on failure, one fallback provider call),
  and that no additional LLM stage or uncontrolled call is made during
  normal processing.
- **Provider separation must be tested**: a test must confirm Request
  #1 and Request #2 use their respective, independently configured
  credential pairs, and that a credential/configuration change to one
  has no effect on the other.
- Preference classification must be tested: vague natural-language
  input must be tested to confirm it resolves to the correct fixed
  filter bucket, and explicit numeric input must be tested to confirm
  it passes through unchanged rather than being reclassified.
- Clarification behavior must be tested: ambiguous location resolution
  or missing required intent fields must be tested to confirm the
  backend returns a clarification-needed result (narrated via Request
  #2) rather than guessing.
- At least one basic prompt-injection test case must be included,
  confirming that instructions embedded in user input passed to Request
  #1 cannot cause fabricated data to bypass the Backend Journey
  Engine's validation boundary.
- **Fallback-chain testing must be explicit per request**: with
  Request #1's primary (Gemini) provider deliberately made unreachable,
  confirm it falls back to Request #1's fallback (Groq) and succeeds;
  repeat for Request #2's primary/fallback pair; and confirm that when
  both providers in a chain fail, the defined controlled error response
  (`06_AI_AND_VOICE_ARCHITECTURE.md` §8.2, §8.3) is returned rather than
  an uncontrolled failure or a silent substitution.
- **Direct-path testing must be included**: with the entire AI pipeline
  unreachable or unconfigured, confirm `POST /transit/journeys/search`
  still functions correctly end-to-end.
- Speech-to-text testing: confirm the `SpeechToTextProvider`
  (Groq Whisper) integration correctly hands its transcript to Request
  #1 unchanged, and that a transcription failure produces a controlled
  error rather than proceeding with empty/corrupted text.

## 6. Data quality testing requirements

- Import idempotency must be tested: re-running the transit data import
  against the same source data must be tested to confirm it does not
  create duplicate records.
- Coordinate/geometry provenance fields must be tested to confirm they
  are always populated (never null-and-unlabeled) for any stop/route
  that has location data.
- A test or reporting mechanism must exist to surface current data
  coverage (stops with/without coordinates, routes with/without
  geometry, routes with/without real timetables) so coverage gaps are
  visible rather than silently present.

## 7. Security testing requirements

- Authentication/authorization boundary tests are required for every
  protected endpoint: confirm the correct 401/403 behavior when a
  request is unauthenticated or under-privileged.
- Rate-limiting behavior must be tested: confirm that exceeding the
  configured threshold on `/auth/login`, `/tickets/validate`, and
  `/ai/converse` produces the expected rejection.
- Admin-only endpoints must be tested to confirm a non-admin,
  authenticated user cannot access them.

## 8. Acceptance bar

A component is considered complete only when:
1. It has automated test coverage for its core behavior and its known
   edge cases (per §1–§7 above, as applicable).
2. It behaves correctly when its data dependencies are incomplete (a
   missing coordinate, an absent timetable, an unavailable AI provider)
   — degrading gracefully and honestly, never fabricating a substitute
   value.
3. Its public contract (API shape, schema) matches what is specified
   in `03`, `05`, `06`, `07`, or `08` as applicable.
