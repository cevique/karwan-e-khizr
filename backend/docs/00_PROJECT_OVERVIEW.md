# 00 — Project Overview

## Document set purpose

This document, and the ten that follow it, are the **complete backend
architecture and specification for Karwan-e-Khizr**. They define what
the backend system is, what it must do, and how its components fit
together, in enough technical detail that the backend can be
implemented directly from this specification.

**Scope note: this is a backend-only specification.** Frontend
implementation (map rendering, UI, client-side state management,
browser/device location handling, admin dashboard UI, voice-control UI)
is owned separately and is out of scope for this document set. Wherever
a capability has both a backend and a frontend half (e.g. "the map"),
these documents specify only the backend's responsibility: the data and
API contracts the frontend consumes. See §"Backend/frontend boundary"
below.

**Read this first, in this order:**
`00` (this file) → `01` (requirements) → `02` (architecture) → then
whichever of `03`–`08` is relevant to the component being built → `09`
(testing and quality requirements) → `10` (implementation priorities).

## What Karwan-e-Khizr is

A public-transit journey-planning and ticketing backend for the
**Islamabad–Rawalpindi (Twin Cities) region of Pakistan**. A client
sends an origin and destination — typed, or transcribed from speech —
and the backend returns one or more realistic multi-leg journeys (walk
→ bus/metro → transfer → bus/metro → walk), plus live vehicle
positions, ETAs, and a QR-ticket purchase/validation flow. Everything
the frontend needs to render a map, a chat interface, and an admin
dashboard is exposed through backend APIs; how it is rendered is not
this backend's concern.

## Backend/frontend boundary

- The backend is responsible for: journey search, route/stop data,
  GeoJSON route geometry, vehicle positions, ETAs, delays,
  authentication, ticket/QR issuance and validation, admin data
  operations, and the conversational/voice AI pipeline (speech-to-text
  integration, intent understanding, and natural-language response
  generation).
- The frontend (owned by a separate team) is responsible for: the map
  UI, journey-result presentation, admin dashboard UI, microphone
  capture and audio upload, device/browser geolocation capture, and all
  client-side state.
- The backend must never assume a specific frontend framework, map
  library, or rendering approach. It communicates exclusively through
  documented API contracts (see `03`, `05`, `06`, `08`).
- Where earlier drafts of this specification described frontend
  concerns (e.g. "the map shows...", "the user's browser obtains
  location..."), those have been rephrased throughout this document set
  as backend data/API requirements only.

## Context

- **Competition:** built for the Bano Qabil × Alibaba Cloud AI
  Hackathon 2026 — Alkhidmat Foundation's Bano Qabil initiative, in
  partnership with Alibaba Cloud.
- **Development tooling:** implementation tooling is not a runtime
  dependency of the system — see §"AI development tooling vs. runtime
  architecture" below.

## AI architecture at a glance

Every conversational/voice command follows exactly one linear pipeline,
using **exactly two logical LLM stages** per command — Request #1
(intent extraction) and Request #2 (response generation). Each stage
may make at most one primary provider call and, if that fails, one
fallback provider call; no additional LLM stages or uncontrolled calls
are permitted. (Plus, for voice input only, one speech-to-text call):

```
User command (typed, or spoken)
  → [voice only] Groq Whisper: speech-to-text
  → Request #1 (Intent LLM): text → validated structured intent JSON
  → Backend Journey Engine: intent JSON → authoritative journey JSON
    (geospatial resolution + deterministic routing + fares + realtime)
  → Request #2 (Response LLM): authoritative JSON → natural-language response
  → User
```

**Fundamental rule: LLMs interpret and explain. The backend computes
and decides.** Request #1 only ever produces a structured request for
the backend to act on; Request #2 only ever narrates what the backend
already computed. Neither LLM call may invent a route, stop, fare, ETA,
delay, or timetable. This rule governs every AI-related document in
this set — see `02_SYSTEM_ARCHITECTURE.md` §1 and
`06_AI_AND_VOICE_ARCHITECTURE.md` for the full specification.

Text-to-speech is explicitly **not** part of this system. Voice input
is supported (speech is transcribed to text via Groq Whisper); all
responses are text, returned to the frontend for the frontend to
present however it chooses.

## Provider independence, within the fixed two-stage design

Speech-to-text and both LLM stages must be built behind provider
interfaces rather than hardcoded inline, so an individual provider can
be swapped without an architecture change — but the **shape** of the AI
pipeline itself (exactly two logical LLM stages, each with at most one
primary and one fallback provider call; Groq Whisper for ASR; no TTS)
is a fixed architectural decision, not a configuration option:

- **Speech-to-text:** Groq Whisper is the selected provider. The
  integration must sit behind a clean interface so it could
  theoretically be replaced, but Groq Whisper is what must be
  implemented — see `06_AI_AND_VOICE_ARCHITECTURE.md`.
- **Request #1 (Intent LLM):** Gemini as primary, Groq as fallback,
  using the project owner's own server-side credentials — see `06`.
- **Request #2 (Response LLM):** Gemini as primary, Groq as fallback,
  using a second, separate set of server-side credentials — see `06`.
- **Predictive ETA:** a provider-agnostic `ETAPredictor` interface,
  starting from a local statistical/lightweight-ML baseline — see
  `07_REALTIME_SIMULATION_AND_ETA.md`. This is unrelated to the two
  conversational LLM requests above.

No AI/ML component may require a specific cloud vendor beyond what is
specified above. End users of the application never supply, see, or
configure any AI provider credentials — every credential is a
server-side project secret. See `03_BACKEND_ARCHITECTURE.md` §5.1 for
the full configuration variable list.

## AI development tooling vs. runtime architecture

Implementation tooling is not a runtime dependency of the system. This
document set is the architecture/specification source of truth,
independent of what tooling is used to implement it.

## Goals

- A client can plan a real, multi-leg public-transit journey between
  two points in the Twin Cities, via typed or transcribed natural
  language in English, Urdu, or Roman Urdu (or mixed), and receive a
  complete, map-ready journey response.
- The journey planner is **deterministic and explainable** underneath —
  AI never invents a route, stop, fare, timetable, or delay.
- A speech-to-text stage and two clearly bounded LLM stages sit around
  that deterministic core: one to understand the request, one to
  explain the result. Providers are configurable within the fixed
  two-stage shape described above.
- Live buses are exposed via API, generated by simulation where no live
  vehicle feed exists, with ETA information, honestly labeled as
  simulated or real depending on data source.
- A client can purchase a ticket for a chosen journey via API and
  receive a QR code payload that a validator endpoint can check, backed
  by a real purchase→validate→used ticket lifecycle.
- The system distinguishes what is **demonstrable today** from what is
  **planned/future**, at every layer, and never overclaims data
  coverage or capability it does not have.

## Non-goals (initial scope)

- Any frontend implementation work — out of scope for this document
  set entirely (see §"Backend/frontend boundary").
- Text-to-speech / spoken responses — explicitly not part of this
  system.
- National coverage of all Pakistani transit systems — Islamabad/
  Rawalpindi only.
- Real integration with an official government GPS feed, an official
  ticketing database, or a production payment provider — none of these
  credentials are assumed to exist; nothing is fabricated to pretend
  otherwise.
- Production-grade scale, multi-region deployment, or high availability.
- A general-purpose chatbot — the conversational AI's role is narrowly
  the two-stage journey-planning pipeline described in this document
  set, not an open-ended assistant, and not a multi-turn tool-calling
  agent.
- A fully custom neural routing model replacing deterministic
  pathfinding — evaluated and explicitly rejected; see
  `05_ROUTING_AND_GEOSPATIAL.md` and `06_AI_AND_VOICE_ARCHITECTURE.md`
  for the reasoning.

## Core differentiators

1. **Voice-first, multilingual journey planning** — English, Urdu, and
   Roman Urdu, spoken or typed, transcribed by Groq Whisper (voice
   only) and understood by a single, tightly-scoped intent-extraction
   LLM request.
2. **A real, explainable deterministic transit engine underneath** —
   the two LLM stages understand and explain; a PostGIS/OSRM-backed
   geospatial layer and a deterministic routing/optimization layer
   compute and guarantee the actual journey facts.
3. **Real transit data, honestly labeled** — genuine researched CDA/
   PMTA route, stop, and timetable data, with every gap and
   approximation documented rather than hidden (see
   `04_TRANSIT_DATA_AND_DOMAIN_MODEL.md`).
4. **A working ticket-to-QR API** — not just a route planner, a backend
   with a real transaction at the end.
5. **Graceful degradation** — every AI-dependent feature has a defined,
   working fallback, so the backend remains functional even if a cloud
   AI service is unreachable.

## Primary API consumers

- **The frontend application** (owned by a separate team) — the
  primary consumer of every backend API in this document set: journey
  search, transit data, realtime/ETA, the conversational endpoint,
  ticketing, and authentication.
- **An admin-facing client** (frontend-owned) — consumes the backend's
  admin APIs (`08_TICKETING_AUTH_AND_ADMIN.md` §5) for data/ticket/
  simulation oversight.
- **A ticket validator client** (frontend-owned) — consumes the ticket
  validation API (`08` §2).

## How to read the rest of this package

Every subsequent document distinguishes what is required now from what
is planned for later, using two labels applied consistently throughout
the whole set:

- **REQUIRED** — must be implemented for the backend to meet this
  specification.
- **FUTURE** — an explicit extension point, out of initial scope but
  architecturally anticipated so it can be added later without a
  redesign.

Where a decision genuinely isn't finalized, it is labeled
**DECISION REQUIRED**, with the options and trade-offs stated, rather
than silently resolved one way.
