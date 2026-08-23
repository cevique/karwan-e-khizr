# Karwan-e-Khizr — Backend Architecture & Specification Package

This is the complete **backend** architecture and specification package
for Karwan-e-Khizr, built for the **Bano Qabil × Alibaba Cloud AI
Hackathon**. Implementation tooling is not a runtime dependency of the
system (see `docs/00_PROJECT_OVERVIEW.md`).

**This package is backend-only.** Frontend implementation (map
rendering, UI, client-side state, microphone/location capture, admin
dashboard UI) is owned by a separate team and is out of scope for these
documents. The backend's responsibility is the data and API contracts
the frontend consumes — see `docs/00_PROJECT_OVERVIEW.md`
§"Backend/frontend boundary".

## AI architecture summary

Every conversational/voice command uses **exactly two logical LLM
stages** — Request #1 (intent extraction) and Request #2 (response
generation) — around a fully deterministic journey engine. Each stage
may make at most one primary provider call and, if that fails, one
fallback provider call; no additional LLM stages or uncontrolled calls
are permitted. Speech-to-text (voice input only) uses Groq Whisper;
there is no text-to-speech anywhere in the system:

```
Command (typed or spoken)
  → [voice only] Groq Whisper: speech-to-text
  → Request #1 (Intent LLM): text → validated structured intent
    — My Gemini primary, My Groq fallback
  → Backend Journey Engine: intent → authoritative journey JSON
    (deterministic — geospatial resolution, Dijkstra, fares, realtime)
  → Request #2 (Response LLM): authoritative JSON → natural-language response
    — Friend's Gemini primary, Friend's Groq fallback
  → Response returned to client
```

**LLMs interpret and explain. The backend computes and decides.**
Request #1 never determines a route; Request #2 never invents or alters
a transit fact. All AI provider credentials are server-side project
secrets — end users never supply, see, or configure them. See
`docs/06_AI_AND_VOICE_ARCHITECTURE.md` for the complete specification.

## Reading order

1. `docs/00_PROJECT_OVERVIEW.md` — start here
2. `docs/01_PRODUCT_REQUIREMENTS.md`
3. `docs/02_SYSTEM_ARCHITECTURE.md`
4. `docs/03_BACKEND_ARCHITECTURE.md`
5. `docs/04_TRANSIT_DATA_AND_DOMAIN_MODEL.md`
6. `docs/05_ROUTING_AND_GEOSPATIAL.md`
7. `docs/06_AI_AND_VOICE_ARCHITECTURE.md`
8. `docs/07_REALTIME_SIMULATION_AND_ETA.md`
9. `docs/08_TICKETING_AUTH_AND_ADMIN.md`
10. `docs/09_TESTING_AND_QUALITY_REQUIREMENTS.md`
11. `docs/10_IMPLEMENTATION_HANDOFF.md` — build order, priorities, and
    the end-to-end flow; read this last, use it as the working checklist

## Labeling convention used throughout

- **REQUIRED** (the default — most content in these documents) — must
  be implemented for the backend to meet this specification.
- **FUTURE** — an explicit extension point, out of initial scope but
  architecturally anticipated so it can be added later without a
  redesign.
- **DECISION REQUIRED** — not finalized; a call to be made during
  implementation, with the relevant options and trade-offs stated. Used
  heavily in `docs/06_AI_AND_VOICE_ARCHITECTURE.md` for provider/quota
  specifics that must be verified against live documentation rather
  than assumed.

## One-line summary

> Build the backend according to these specifications only — the
> frontend is separate and out of scope. Every conversational command
> uses exactly two logical LLM stages (Request #1 for intent, Request
> #2 for response) around a fully deterministic journey engine: Gemini
> primary / Groq fallback for each, with entirely separate credential
> pairs, plus Groq Whisper for speech-to-text on voice input. There is
> no text-to-speech. End users never supply AI credentials — all
> provider keys are server-side project secrets. Implementation
> tooling is not a runtime dependency of the system.
