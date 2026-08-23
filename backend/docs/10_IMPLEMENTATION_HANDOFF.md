# 10 — Implementation Priorities and Constraints

**Scope note:** this document specifies backend implementation
priorities only. Frontend build order, priorities, and UI work are
owned separately and are not covered here — see
`00_PROJECT_OVERVIEW.md` §"Backend/frontend boundary". This document
turns `00`–`09` into a build order, priorities, and constraints for
implementing the backend. Implementation tooling is not a runtime
dependency of the system (see `00_PROJECT_OVERVIEW.md` §"AI
development tooling vs. runtime architecture").

## 1. Component classification (quick reference)

| Component | Classification |
|---|---|
| Agencies/routes/stops/timetables/import | Deterministic |
| PostGIS spatial queries, Nominatim geocoding | Geospatial (Layer 3) |
| OSRM route geometry | Geospatial (Layer 3) |
| Bus simulation engine | Deterministic |
| Dijkstra / journey search | Deterministic (Layer 4) |
| Fares | Deterministic |
| Ticketing + QR | Deterministic |
| Authentication | Deterministic |
| Admin API | Deterministic |
| Speech-to-text (Groq Whisper) | AI/ML (`SpeechToTextProvider`) |
| Request #1 — Intent LLM | AI/ML (`IntentLLMProvider`) |
| Request #2 — Response LLM | AI/ML (`JourneyResponseLLMProvider`) |
| Location/place resolution logic | Geospatial (Layer 3, invoked internally by the journey engine) |
| Predictive ETA (`ETAPredictor`) | AI/ML |
| Map rendering, live location capture, mic UI, admin dashboard UI | Frontend — **out of scope for this backend** |
| Realtime vehicle rendering | Frontend, consuming backend vehicle-position API |

## 2. Build order (recommended)

1. **Transit data and domain model** (`04_TRANSIT_DATA_AND_DOMAIN_MODEL.md`):
   import the transit dataset into the specified PostgreSQL/PostGIS
   schema. This underlies everything else.
2. **Layer 4 (deterministic routing)** (`05_ROUTING_AND_GEOSPATIAL.md`
   §3–4): graph construction, Dijkstra pathfinding, filters, and
   multi-candidate responses on `POST /transit/journeys/search`. This
   unblocks everything downstream that depends on a real filtering
   contract, and is directly consumable by a frontend team building in
   parallel.
3. **Layer 3 (geospatial resolution)** (`05` §2): location resolution,
   spatial candidate queries, walking-distance computation, invoked
   internally by the Backend Journey Engine.
4. **Ticketing, fares, and authentication** (`08_TICKETING_AUTH_AND_ADMIN.md`):
   these are independent of the AI pipeline and should be built early
   so a complete, working backend (search → ticket → validate) exists
   before any AI work begins. This is the single most important
   sequencing decision in this document: it guarantees the backend is
   fully functional via direct API calls regardless of what happens
   with the AI pipeline or external provider access.
5. **Request #1 — Intent LLM** (`06_AI_AND_VOICE_ARCHITECTURE.md` §5):
   `IntentLLMProvider` with Gemini primary / Groq fallback, validated
   output feeding directly into step 2's existing
   `POST /transit/journeys/search` contract.
6. **Backend Journey Engine wiring**: connect Request #1's validated
   output → Layer 3/4 → authoritative JSON, including the
   clarification-needed and no-route-found result shapes
   (`06` §8.1).
7. **Request #2 — Response LLM** (`06` §7): `JourneyResponseLLMProvider`
   with Gemini primary / Groq fallback (a separate credential pair from
   step 5), consuming the authoritative JSON from step 6.
8. **Speech-to-text** (`06` §4): Groq Whisper integration behind
   `SpeechToTextProvider`, feeding transcripts into step 5's existing
   pipeline unchanged. This can be built in parallel with steps 5–7
   since its contract (plain text out) is simple and stable.
9. **Predictive ETA** (staged, `07_REALTIME_SIMULATION_AND_ETA.md`) —
   build in parallel with or after step 4 lands; architecturally
   independent of the AI pipeline, never a blocker for it. Default to a
   local/in-process `ETAPredictor` implementation — no cloud ML
   platform required.
10. **Admin API polish** (`08` §5) and security hardening (§4 below)
    fill in as time allows.

## 3. Priority ranking

### P0 — required for a functioning backend
1. Real transit stops/routes, importable and queryable via API
2. Route geometry API (coverage-limited, honestly labeled)
3. Geospatial location resolution (Layer 3)
4. Journey planning API (Layer 4, with filters)
5. Route filtering
6. `POST /transit/journeys/search` — direct structured journey search,
   fully functional independent of the AI pipeline
7. Request #1 (Intent LLM) — text in, validated structured intent out
8. Speech-to-text (Groq Whisper) — voice commands transcribed into the
   same pipeline as typed text
9. Request #2 (Response LLM) — authoritative journey JSON in,
   natural-language response out
10. Simulation and realtime vehicle-position API
11. ETA API — **deterministic baseline**, not the predicted one
12. Ticket purchase + QR ticket API
13. Authentication API

### P1 — major differentiators, build once P0 is solid
- Predictive ETA (a partial result — a trained local model without any
  cloud deployment, served via local inference — is a fully acceptable
  outcome, not just a fallback)
- Urdu/Roman Urdu voice transcription quality validated and, if needed,
  tuned against Groq Whisper's actual capability
- Richer admin API (AI/ETA health panel, data-quality view)
- Fare integration into Request #2's narration (already implied by the
  authoritative JSON contract — mostly a prompt/testing task once §5's
  fare API exists)

### P2 — stretch / future
- Per-user saved routes/favorites/history-informed suggestions
- Real-observation ETA feedback loop (needs a real vehicle feed that
  doesn't exist)
- Additional transit operators, WebSocket realtime, production-scale
  hardening, full admin CRUD, advanced analytics
- Multi-turn conversational follow-up spanning multiple commands
  (explicitly out of scope for the fixed two-stage-per-command
  pipeline specified in `06`)

## 4. Critical constraints (non-negotiable)

- **AI never produces an authoritative route, fare, ETA, walking
  distance, timetable, or delay value.** Request #1 only produces a
  structured request; Request #2 only narrates backend output. This is
  enforced mechanically (schema validation at every AI/backend
  boundary) and tested (groundedness checks per
  `06_AI_AND_VOICE_ARCHITECTURE.md` §11 and
  `09_TESTING_AND_QUALITY_REQUIREMENTS.md` §5), not just prompted.
- **Exactly two logical LLM stages per command, no more.** Request #1
  (intent extraction) and Request #2 (response generation), each
  making at most one primary provider call and, if that fails, one
  fallback provider call. No agentic tool-calling loop, no additional
  LLM stages or uncontrolled calls beyond that fixed chain. This is
  fixed architecture, not a tunable default — see
  `02_SYSTEM_ARCHITECTURE.md` §1 and §4.
- **No fabricated transit data, ever** — not a coordinate, not a route
  geometry, not a timetable entry, not a fare. A documented gap is
  always preferable to an invented value, including inside Request #2's
  narration.
- **The backend must remain functional via direct API calls if the AI
  pipeline is unreachable, unconfigured, or rate-limited** —
  `POST /transit/journeys/search` never depends on Request #1 or
  Request #2 succeeding.
- **No AI/ML component requires a specific cloud vendor beyond the
  fixed Gemini-primary/Groq-fallback shape and Groq Whisper for ASR.**
  Each provider interface (`IntentLLMProvider`,
  `JourneyResponseLLMProvider`, `SpeechToTextProvider`, `ETAPredictor`)
  must isolate its vendor-specific client behind a clean boundary.
- **Simulated data is always source-labeled** — never presented as
  real-time.
- **Rate limiting is required** on auth, ticket validation, and the
  conversational endpoint before any deployment.
- **Implementation tooling is not a runtime dependency of the
  system.** No coding tool used to write the backend may appear as a
  runtime dependency, import, or service call anywhere in the shipped
  backend.
- **End users never supply, see, or configure any AI provider
  credential.** All five AI-related credentials (Request #1's pair,
  Request #2's pair, Groq Whisper) are server-side project secrets —
  see `03_BACKEND_ARCHITECTURE.md` §5.1.
- **No text-to-speech anywhere in the backend.**
- **No frontend implementation work belongs in this backend's
  codebase or its priorities.**

## 5. Things not to fabricate

- Any AI-provider service name, endpoint, capability, pricing, or quota
  not specified in `06_AI_AND_VOICE_ARCHITECTURE.md` — if something is
  needed that isn't specified there, treat it as **DECISION REQUIRED**
  and verify against the relevant provider's current documentation
  before building on it.
- Transit facts (routes, stops, coordinates, timetables, fares) beyond
  what `04_TRANSIT_DATA_AND_DOMAIN_MODEL.md` documents as available.
- Claims of real-time data, official route alignment, or ML-model
  accuracy not actually achieved.
- Any implication that Request #2 determines or alters a routing
  result — it narrates only.

## 6. What "done" means for initial delivery

All of P0 (§3) working end-to-end via API: a client can send a typed or
spoken journey command to `POST /ai/converse` and receive a validated,
ranked set of journeys plus a natural-language explanation, generated
via exactly two logical LLM stages (Request #1, then Request #2) around
a fully deterministic journey
engine; a client can also bypass the AI pipeline entirely via
`POST /transit/journeys/search` and get the same underlying journey
data; live (simulated) vehicle positions and ETAs are available via
API; a client can purchase a ticket and receive a QR payload, and
validate it via API — with every AI-touching step able to fall back to
the direct/deterministic path if needed, and every simulated/estimated
value honestly labeled as such.

## 7. End-to-end flow (reference sequence for the backend, independent
of any specific frontend)

1. Client sends a command to `POST /ai/converse`: typed text, or an
   audio payload.
2. [Voice only] Groq Whisper transcribes the audio to text.
3. Request #1 (My Gemini primary / My Groq fallback) extracts
   structured intent from the text.
4. The backend validates the intent. If required fields are missing or
   ambiguous, the backend produces a clarification-needed result and
   skips to step 6.
5. The Backend Journey Engine resolves locations (Layer 3), searches
   the transit graph (Layer 4, Dijkstra), applies filters, computes
   fares, and attaches realtime/ETA data, producing an authoritative
   journey JSON (or an authoritative no-route-found result).
6. Request #2 (Friend's Gemini primary / Friend's Groq fallback)
   converts the backend's authoritative JSON into a natural-language
   response.
7. The backend returns `{structured_journeys, text_response, ...}` to
   the client.
8. Separately, the client can query vehicle-position/ETA endpoints for
   any journey's live (simulated) bus, and can call the ticketing API
   to purchase and later validate a QR ticket for a selected journey.
9. An authenticated admin client can query admin status endpoints
   (live simulation state, ticket status, AI/ETA pipeline health) at
   any point.

This flow deliberately keeps the boundary explicit at every step:
**which part is an LLM stage and which part is the deterministic
backend** — this is the backend's core architectural property: a
credible, explainable, gracefully-degrading system where the journey
engine remains the sole source of truth for every transit fact, and
exactly two clearly-scoped LLM stages make it usable via natural
language and voice, in Urdu and English, without either request ever
being trusted to invent a fact.
