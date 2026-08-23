# 02 — System Architecture

**Scope note:** this is the backend system architecture only. The
frontend (map rendering, UI, client state) is owned separately and
consumes the APIs this architecture exposes — see
`00_PROJECT_OVERVIEW.md` §"Backend/frontend boundary".

This document specifies the backend's architecture. Component
responsibilities are separated deliberately so different components can
be built independently against stable contracts (defined per-layer in
documents `03`–`08`).

## 1. The AI / deterministic boundary (read this first)

This is the single governing rule of the whole architecture:

> **LLMs interpret and explain. The backend computes and decides.**

Concretely:

- **Request #1 (Intent LLM)** understands what the user wants and
  converts it into a strict, validated structured JSON object. It does
  not determine an actual route, and must not fabricate stops,
  schedules, fares, vehicle positions, ETAs, delays, or route geometry.
- **The Backend Journey Engine** (Layers 3–4 below, plus fares/
  realtime) actually determines what journey the user should take,
  using only real transit data. It is the sole authority for every
  transit fact in the system.
- **Request #2 (Response LLM)** explains the backend's authoritative
  result naturally. It must not independently calculate or invent a
  route, stop, fare, ETA, delay, walking distance, schedule, vehicle
  position, or route geometry — it may only restate, in natural
  language, values already present in the backend's output.

**Mechanical enforcement, not just intention:** Request #1's output is
schema-validated before it is allowed to reach the Backend Journey
Engine; Request #2's input is the Backend Journey Engine's own
authoritative JSON, treated as ground truth the model may only narrate.
There is no code path by which either LLM's own generated text becomes
an authoritative route, fare, ETA, walking distance, timetable, or
delay value. This is tested (see `06_AI_AND_VOICE_ARCHITECTURE.md`
§"Hallucination prevention" and `09_TESTING_AND_QUALITY_REQUIREMENTS.md`
§5), not assumed.

## 2. High-level component diagram

```
                    ┌──────────────────┐
                    │       User       │            (frontend-owned;
                    └────────┬─────────┘             backend receives
                             │                        typed text or
                   text OR spoken command             an audio payload
                             │                        via POST /ai/converse)
                    ┌────────▼─────────┐
                    │   Groq Whisper   │   Layer 1 — Speech-to-Text
                    │  (voice only)    │   (skipped entirely for typed input)
                    └────────┬─────────┘
                             │
                       normalized text
                             │
                    ┌────────▼─────────┐
                    │    REQUEST #1    │   Layer 2 — Intent LLM
                    │ Intent / NLP LLM │   (IntentLLMProvider)
                    └────────┬─────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
          My Gemini API             My Groq API
            PRIMARY                  FALLBACK
                 │                       │
                 └───────────┬───────────┘
                             │
                  validated intent JSON
                             │
                    ┌────────▼─────────┐
                    │ Backend Journey  │   Layers 3-4 — Geospatial
                    │     Engine       │   Transit Intelligence +
                    │                  │   Deterministic Routing/
                    │ geospatial model │   Optimization, plus fares
                    │ route planning   │   and realtime/simulation
                    │ transit data     │   state
                    │ schedules        │
                    │ fares            │
                    │ realtime         │
                    │ ETA/delays       │
                    │ constraints      │
                    └────────┬─────────┘
                             │
                    authoritative JSON
                             │
                    ┌────────▼─────────┐
                    │    REQUEST #2    │   Layer 5 — Response LLM
                    │ Journey Response │   (JourneyResponseLLMProvider)
                    │       LLM        │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
       Friend's Gemini API           Friend's Groq API
            PRIMARY                      FALLBACK
              │                             │
              └──────────────┬──────────────┘
                             │
                     final response
                             │
                    ┌────────▼─────────┐
                    │       User       │            (frontend-owned)
                    └──────────────────┘


Parallel, independent components:

  Ticketing / Fares / Auth / Admin  ──────────────►  same backend, first-
  (deterministic, first-class API surfaces —          class API surfaces
  see 08_TICKETING_AUTH_AND_ADMIN.md)

  Realtime / Simulation  ──────────────────────────►  feeds the Backend
  (deterministic, provider-abstracted — see          Journey Engine's ETA/
  07_REALTIME_SIMULATION_AND_ETA.md)                 delay data

  Predictive ETA component  ─────────────────────────► augments (never
  (staged, independent of the two-stage AI            replaces) the
  pipeline — see 07_REALTIME_SIMULATION_AND_ETA.md)  deterministic
                                                       simulation ETA
```

**Exactly two logical LLM stages occur per user command: Request #1
(intent extraction) and Request #2 (response generation).** Each stage
may make at most one primary provider call and, if that fails, one
fallback provider call; no additional LLM stages or uncontrolled calls
are permitted (plus, for voice input only, one Groq Whisper
transcription call). This is a fixed architectural decision, not a
tunable default — see `06_AI_AND_VOICE_ARCHITECTURE.md` for the full
specification of why no additional LLM stages (e.g. multi-step
tool-calling loops) are part of this pipeline.

## 3. Component responsibility table

| Component | Layer type | Responsible for | Must never do |
|---|---|---|---|
| Speech-to-text (Layer 1, Groq Whisper) | AI/ML (`SpeechToTextProvider`) | Transcribing voice input to text, voice input only | Any interpretation of meaning; typed input never touches this layer |
| Intent LLM / Request #1 (Layer 2) | AI/ML (`IntentLLMProvider`) | Converting user text into one validated structured intent JSON object | Determine an actual route; call further tools; make a second LLM request within the same command |
| Geospatial Transit Intelligence (Layer 3) | Geospatial, deterministic | Place resolution, spatial candidate queries, walking-distance computation, route geometry retrieval — invoked by the Backend Journey Engine, not by either LLM | Choose a final journey; apply user preferences/ranking |
| Deterministic Routing/Optimization (Layer 4) | Deterministic | Pathfinding (Dijkstra), transfers, filtering/ranking, fare application — invoked by the Backend Journey Engine | Accept an unvalidated/AI-composed request; use AI reasoning internally |
| Response LLM / Request #2 (Layer 5) | AI/ML (`JourneyResponseLLMProvider`) | Turning the Backend Journey Engine's authoritative JSON into a natural-language response | Compute or alter a route, fare, ETA, or timetable value; call any tool; make a second LLM request within the same command |
| Realtime/Simulation | Deterministic, provider-abstracted | Vehicle position, delay, baseline ETA | Present simulated data as real without labeling |
| Predictive ETA (`ETAPredictor`) | AI/ML, staged, provider-abstracted | Refined ETA prediction, additive | Replace the deterministic baseline silently |
| Ticketing/Fares/Auth/Admin | Deterministic | Purchase, QR, validation, accounts, admin visibility | Trust client-supplied ticket data; skip server-side fare recomputation |

## 4. Data flow (single command, end to end)

```
1. Client sends a command via POST /ai/converse: typed text, or an
   audio payload.
2. [Voice only] Layer 1 (Groq Whisper) transcribes the audio to text.
3. Request #1 (Intent LLM, IntentLLMProvider: My Gemini primary / My
   Groq fallback) converts the text into a structured intent object.
4. The backend validates Request #1's output against a strict schema.
   If validation fails or required fields are missing/ambiguous, the
   backend produces a clarification-needed result (no route is
   guessed) and proceeds directly to step 6.
5. The Backend Journey Engine (Layers 3-4, plus fares/realtime) uses
   the validated intent to resolve locations, search the transit graph,
   apply filters, and compute an authoritative journey result — or an
   authoritative "no route found" result.
6. Request #2 (Response LLM, JourneyResponseLLMProvider: Friend's
   Gemini primary / Friend's Groq fallback) converts the backend's
   authoritative JSON (a journey result, a no-route result, or a
   clarification-needed result) into a natural-language response.
7. The backend returns `{structured_journeys, text_response, ...}` to
   the client.
```

A client may also call `POST /transit/journeys/search` directly with a
structured request, bypassing the AI pipeline (steps 1–4, 6) entirely
and going straight to step 5. This is the mechanical proof, referenced
throughout this document set, that AI cannot bypass the deterministic
engine: the AI pipeline's only path into the journey engine is the same
structured contract a direct API call would use. It is also the
backend's primary resilience path: if neither LLM provider is reachable
at all, this direct path is fully functional on its own.

## 5. Cross-cutting concerns

- **Authentication:** JWT-based, applies uniformly to conversational and
  direct API paths — see `08_TICKETING_AUTH_AND_ADMIN.md`.
- **Rate limiting:** required on auth, ticket-validation, and the
  conversational endpoint (the most expensive per-request operation in
  the system, and the one most exposed to third-party LLM/ASR provider
  quotas) — see `10_IMPLEMENTATION_HANDOFF.md` §"Security must-haves".
- **Provider configuration:** which concrete provider fulfills each
  role (`IntentLLMProvider`, `JourneyResponseLLMProvider`,
  `SpeechToTextProvider`, `ETAPredictor`) and which credentials back it
  is a deployment-time configuration concern, not a code-level
  dependency — see `03_BACKEND_ARCHITECTURE.md` §5.1 and
  `06_AI_AND_VOICE_ARCHITECTURE.md` §"Provider abstraction". Note that,
  per §1 and §4 above, the *number and sequence* of LLM stages —
  exactly two (Request #1, then Request #2), each with at most one
  primary and one fallback provider call — is architecture, not
  configuration.
- **Observability of AI decisions:** every Request #1 and Request #2
  call, its input, and its output should be logged per command — this
  is both a debugging necessity and the concrete mechanism that makes
  "grounded, not hallucinated" a testable claim rather than an
  assertion.
- **Data provenance discipline:** every transit fact surfaced anywhere
  in the system (a stop coordinate, a route geometry, a timetable, a
  fare) carries or traces back to a documented source/confidence level
  — see `04_TRANSIT_DATA_AND_DOMAIN_MODEL.md`. This discipline extends
  into Request #2's narration: it narrates what the backend gives it,
  and the backend's own honesty about data quality is what keeps the
  narration honest.

## 6. Why this shape, briefly (full reasoning in `05` and `06`)

- **Exactly two logical LLM stages, not an open-ended tool-calling
  agent.** Understanding a request and explaining a result are
  different, boundable tasks; giving each its own dedicated stage (with
  its own credentials, prompt, and schema, and at most one primary and
  one fallback provider call) keeps the pipeline's cost, latency, and
  failure modes fully predictable per command, and makes it
  structurally impossible for an LLM to iteratively "reason its way"
  into fabricating transit facts through an extended tool-use loop.
  This is a deliberate, stricter alternative to an agentic
  multi-tool-call design.
- **Speech and reasoning are split.** A model specialized in turning
  audio into accurate text is not the model that should be reasoning
  about travel preferences — conflating them either wastes the
  reasoning model's budget or lets transcription noise get silently
  "corrected" into something the user didn't say. Layer 1 (Groq
  Whisper) produces clean, auditable text; Request #1 reasons over it.
- **Geospatial reasoning is invoked by the backend engine, not by
  either LLM.** "Which stops are near this point, resolved against real
  spatial data" is a database/geometry problem (PostGIS/OSRM); "which
  sequence of stops/rides is optimal under these constraints" is a
  graph-search/optimization problem. Neither is an LLM's job, and
  neither LLM ever calls into these layers directly — only the Backend
  Journey Engine does, deterministically.
- **No learned/neural router replaces Layer 4.** Evaluated explicitly
  and rejected — see `05_ROUTING_AND_GEOSPATIAL.md` §"Evaluation: does a
  learned routing model belong here?" for the full technical reasoning.
  Dijkstra remains, as an implementation detail of Layer 4, not as the
  project's AI story.
- **No layer is tied to a specific AI vendor beyond the fixed Gemini-
  primary/Groq-fallback shape.** Each of the two LLM requests, and the
  ASR call, is specified as a provider interface precisely so an
  individual credential or provider outage changes a configuration
  value and a fallback path, never the architecture.
