# 03 — Backend Architecture

This document specifies the backend. **Scope note:** backend only — no
frontend framework, UI, or client-side architecture is specified here;
see `00_PROJECT_OVERVIEW.md` §"Backend/frontend boundary".

## 1. Overall shape

A modular backend service (Python/FastAPI recommended — see §6)
exposing a REST API, organized around a strict module-boundary
principle: **narrow interfaces between modules, no module reaching into
another's internals.** Specifically required:

- `routing` never imports from `ticketing`.
- `ticketing` calls into `payments` only through a `PaymentProvider`
  interface.
- `realtime`/`simulation` calls into vehicle-location logic only through
  a `VehicleLocationProvider` interface.
- Both LLM requests (Request #1 and Request #2, per
  `02_SYSTEM_ARCHITECTURE.md`) call the routing/geospatial layers
  **only through the same public API contract a direct client request
  would use** — never through internal function calls that bypass
  validation. Request #1's output must pass the same structured
  validation any client-supplied journey-search request would pass.

This module-boundary discipline is a hard requirement: it is what
allows different components to be built and modified independently
without cross-contamination, and it is what makes the AI/deterministic
boundary in `02_SYSTEM_ARCHITECTURE.md` §1 mechanically enforceable
rather than just a convention.

## 2. Module map

```
backend/
  api/              # HTTP routers — transit, journeys, ai, realtime,
                     # auth, users, fares, tickets, admin
  ai/               # Layer 1 (speech-to-text, via SpeechToTextProvider,
                     # Groq Whisper) + Request #1 (IntentLLMProvider) +
                     # Request #2 (JourneyResponseLLMProvider)
                     # integration, schemas, provider config
  geospatial/        # Layer 3 — wraps PostGIS/OSRM/geocoding as
                     # callable operations, invoked by the journey
                     # engine (not by either LLM)
  routing/          # Layer 4 — graph, search (Dijkstra), journey
                     # assembly, filtering
  simulation/       # Vehicle simulation engine and provider
                     # abstraction (VehicleLocationProvider)
  eta/              # Staged ETA prediction — training data generation,
                     # model inference wrapper (see 07)
  ticketing/        # Ticket state machine, QR issuance/validation,
                     # fares
  users/            # Registration, auth, roles
  seeding/          # Transit data import (agencies/routes/stops/trips)
  db/               # ORM models, Alembic migrations
  core/             # config, shared utilities
```

## 3. API surface

| Endpoint (indicative) | Layer | Notes |
|---|---|---|
| `GET /transit/agencies`, `/routes`, `/routes/{id}`, `/routes/{id}/geometry`, `/stops`, `/stops/{id}` | 3/data | Read-only transit data; includes GeoJSON geometry where available, for frontend map rendering |
| `POST /transit/journeys/search` | 4 | Direct structured journey search, bypassing the AI pipeline entirely. Supports filters and returns multiple ranked candidate journeys with full leg geometry — see `01_PRODUCT_REQUIREMENTS.md` §1 |
| `GET /transit/realtime/vehicles`, `/vehicles/{id}`, `/vehicles/{id}/eta` | Simulation | Must include a `source: "simulated"` or `source: "realtime"` field; optionally includes a predicted ETA once §07's ETA prediction component is available |
| `POST /ai/converse` | 1, 2, 5 | The two-stage AI pipeline. Request: `{message?, audio?}` — exactly one of `message` (text) or `audio` must be supplied. Response: `{text_response, structured_journeys?, clarification_needed?}`. No `audio_response` field — text-to-speech is not part of this system. |
| `GET /ai/health` | 1, 2, 5 | Reachability/mode status for the Intent LLM, Response LLM, and speech-to-text providers — feeds admin visibility and graceful-degradation behavior |
| `POST /auth/register`, `/auth/login`, `GET /auth/me` | Auth | See `08_TICKETING_AUTH_AND_ADMIN.md` |
| `POST /fares/quote` | Fares | See `08` |
| `POST /tickets`, `GET /tickets`, `/tickets/{id}`, `POST /tickets/{id}/revoke`, `POST /tickets/validate` | Ticketing | See `08` |
| `POST /admin/...` | Admin | Seed/import/graph-rebuild plus read/status endpoints — see `08` |

**Design rule:** `POST /transit/journeys/search` is the single point
through which both the AI pipeline (internally, after Request #1
produces a validated intent) and any direct client call reach the
routing engine. This is deliberate and load-bearing — see
`02_SYSTEM_ARCHITECTURE.md` §4.

## 4. Database

PostgreSQL + PostGIS, one schema, Alembic migrations. Core entity set
(full detail in `04_TRANSIT_DATA_AND_DOMAIN_MODEL.md`): `Agency`,
`Route`, `Stop`, `RouteStop`, `Trip`, `StopTime`, `Vehicle`,
`VehiclePosition`, `User`, `Ticket`, `FareRule`. No persisted tables are
required for the AI pipeline — conversational request/response state is
ephemeral per command (there is no multi-turn session state to persist,
per `02_SYSTEM_ARCHITECTURE.md`'s fixed two-stage-per-command design),
and ETA training data is a generated artifact, not an operational table.

## 5. Security

- Password hashing (bcrypt), JWT sessions, role-gated admin routes.
- Rate limiting is required on `/auth/login`, `/tickets/validate`, and
  `/ai/converse` (the most abuse-sensitive and most expensive endpoints
  respectively) — `/ai/converse` is particularly important to rate-limit
  since every call spends both LLM credential budgets.
- API keys for the four configured LLM credentials (§5.1) and for the
  Groq Whisper speech-to-text credential must be loaded from
  environment variables only, never hardcoded or logged.
- **End users never supply, see, or configure any AI provider
  credential.** Every credential in §5.1 is a server-side project
  secret, owned by the project/deployment, not the application user —
  see `06_AI_AND_VOICE_ARCHITECTURE.md` §"Credential ownership".
- No user PII beyond the current command's text is ever sent to an LLM
  prompt (no tokens, no ticket/payment data).
- Any endpoint that can mutate simulated vehicle/trip state must be
  authenticated for any hosted deployment. Unauthenticated developer/
  demo control endpoints, if provided for local development
  convenience, must never be exposed on any publicly reachable
  deployment.

### 5.1 Provider configuration

Every external AI dependency must be selected via configuration, not
hardcoded throughout the application. The **shape** of the AI pipeline
(exactly two logical LLM stages, each with at most one primary and one
fallback provider call; Groq Whisper for speech-to-text; no TTS) is
fixed architecture, per `02_SYSTEM_ARCHITECTURE.md`; only the
underlying provider client implementation is a swappable configuration
detail. Required configuration variables:

```
# Request #1 — Intent LLM (project owner's credentials)
REQUEST1_GEMINI_API_KEY=...   # primary
REQUEST1_GROQ_API_KEY=...     # fallback

# Request #2 — Response LLM (second project contributor's credentials)
REQUEST2_GEMINI_API_KEY=...   # primary
REQUEST2_GROQ_API_KEY=...     # fallback

# Speech-to-text (voice input only)
GROQ_WHISPER_API_KEY=...      # selected ASR provider — see 06

# Predictive ETA (unrelated to the two LLM requests above)
ETA_PROVIDER=local            # local statistical/ML baseline by default

# Deterministic routing/geometry (unrelated to AI configuration)
ROUTING_PROVIDER=osrm         # see 05_ROUTING_AND_GEOSPATIAL.md
```

**Request #1 and Request #2 must use entirely separate credential
pairs, even though both may point at the same underlying vendors
(Gemini and Groq).** This is a deliberate boundary, not a redundancy —
see `06_AI_AND_VOICE_ARCHITECTURE.md` §"Provider abstraction and the
four LLM credentials" for why. Do not consolidate `REQUEST1_*` and
`REQUEST2_*` into a single shared credential pair.

Exact variable names may be adjusted at implementation time for
consistency with the rest of the configuration system, but the
four-credential separation (Request #1 primary/fallback, Request #2
primary/fallback) and the single speech-to-text credential must be
preserved. See `06_AI_AND_VOICE_ARCHITECTURE.md` §"Provider
abstraction" for the `IntentLLMProvider`/`JourneyResponseLLMProvider`/
`SpeechToTextProvider` interface definitions this configuration selects
between, and `07_REALTIME_SIMULATION_AND_ETA.md` for `ETAPredictor`.

## 6. Technology stack

**Recommended:** Python + FastAPI (async support, automatic OpenAPI
schema — useful for integrating multiple components in parallel),
PostgreSQL + PostGIS (geographic queries are core to the domain),
Alembic for migrations.

**AI integration:** an `ai/` module implementing
`IntentLLMProvider`, `JourneyResponseLLMProvider`, and
`SpeechToTextProvider` (§5.1), with Gemini as the primary LLM
implementation for both requests, Groq as the fallback LLM
implementation for both requests, and Groq Whisper as the sole
speech-to-text implementation — see `06_AI_AND_VOICE_ARCHITECTURE.md`
for the full integration design.

**DECISION REQUIRED, frontend-owned, informational only:** the frontend
framework choice belongs to the separate frontend team and has no
bearing on this backend specification; the backend contract is
frontend-framework-agnostic.
