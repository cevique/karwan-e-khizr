# 06 — AI and Voice Architecture

This document is the complete specification of the backend's AI
pipeline: speech-to-text, and the two bounded LLM stages that
surround the deterministic Backend Journey Engine. **Scope note:**
backend only — this document specifies APIs and server-side behavior,
not any client UI (microphone capture, chat display, etc.), which is a
frontend responsibility.

## 1. The fixed pipeline shape (read this first)

Every user command follows exactly this sequence: **exactly two
logical LLM stages per command — Request #1 (intent extraction) and
Request #2 (response generation). Each stage may make at most one
primary provider call and, if that fails, one fallback provider call.
No additional LLM stages or uncontrolled calls are permitted.** (Plus,
for voice input only, one speech-to-text call.) This is a fixed
architectural decision — not a configuration option, and not to be
collapsed, expanded, or turned into an open-ended agent loop:

```
User command (typed, or spoken)
  → [voice only] Groq Whisper: speech-to-text
  → Request #1 (Intent LLM): text → validated structured intent JSON
  → Backend Journey Engine: intent JSON → authoritative journey JSON
  → Request #2 (Response LLM): authoritative JSON → natural-language response
  → User
```

**Fundamental rule: LLMs interpret and explain. The backend computes
and decides.** (the backend authority principle)

- **Request #1** understands what the user wants and converts it into
  a strict, validated structured JSON object. It must not determine an
  actual route, and must not fabricate stops, schedules, fares, vehicle
  positions, ETAs, delays, or route geometry.
- **The Backend Journey Engine** (Layers 3–4 of
  `02_SYSTEM_ARCHITECTURE.md`, plus fares/realtime) actually determines
  the journey, using only real transit data. It is the sole authority
  for every transit fact.
- **Request #2** explains the backend's authoritative result naturally.
  It must not independently calculate or invent a route, stop, fare,
  ETA, delay, walking distance, schedule, vehicle position, or route
  geometry — it may only restate values already present in the
  backend's output, in natural language.

**No additional LLM calls occur within the normal journey-command
cycle.** There is no multi-step tool-calling loop, no agent that
iteratively decides which backend function to call next, and no
LLM-initiated retries beyond the fixed primary→fallback chain specified
in §3.

## 2. Voice and text converge into the same pipeline

```
Typed command ──────────────────────────────┐
                                              │
Spoken command → Groq Whisper → transcript ──┴──→ Request #1 → ...
```

There is exactly one journey-planning pipeline. Speech-to-text is a
preprocessing step that exists only for voice input; once a command is
text (typed directly, or transcribed from audio), it is indistinguishable
to Request #1 and everything downstream. The backend must not implement
a separate code path for voice-originated versus typed commands beyond
the transcription step itself.

## 3. Provider abstraction and the four LLM credentials

Speech-to-text and both LLM stages must be built behind clean
provider interfaces so an individual vendor client could theoretically
be swapped without touching calling code — but the fixed shape (Groq
Whisper for ASR; two separate LLM stages, each with a Gemini-primary/
Groq-fallback pair) is architecture, not a runtime choice.

```
class SpeechToTextProvider:
    def transcribe(self, audio_bytes) -> Transcript: ...
    # Transcript: { text, confidence? }
    # Selected implementation: Groq Whisper.

class IntentLLMProvider:
    def extract_intent(self, text: str) -> IntentResult: ...
    # Used ONLY for Request #1. Backed by the project owner's
    # credentials: Gemini primary, Groq fallback.

class JourneyResponseLLMProvider:
    def generate_response(self, authoritative_json: dict) -> str: ...
    # Used ONLY for Request #2. Backed by a second, separate set of
    # credentials (a second project contributor's): Gemini primary,
    # Groq fallback.
```

**`IntentLLMProvider` and `JourneyResponseLLMProvider` must be
implemented as fully separate services, never a single shared/generic
"LLM client" configured twice.** Each must have its own:

- credentials (see §10 and `03_BACKEND_ARCHITECTURE.md` §5.1)
- primary and fallback provider client
- system prompt / instructions
- input schema
- output schema
- error handling
- logging/observability

This separation is deliberate: it makes it structurally unambiguous
which credential pair is responsible for which behavior, keeps each
request's prompt narrowly scoped to one job, and means a failure,
prompt change, or credential rotation in one request can never silently
affect the other.

**No `TextToSpeechProvider` exists in this architecture.**
Text-to-speech is explicitly not part of this system — see §9.

**Do not hard-code current pricing, quotas, or rate limits into the
architecture or into any code comment.** Free-tier and rate-limit
details for Gemini, Groq, and Groq Whisper all change over time; state
in configuration/documentation only that a provider is configured, and
that its current quota/availability must be checked against the
provider's own current documentation at implementation/deploy time.

## 4. Speech-to-text — Groq Whisper

- **Selected provider: Groq Whisper**, exclusively. No other
  speech-to-text provider is part of this architecture.
- Speech-to-text is invoked only when the client submits an audio
  payload to `POST /ai/converse`; typed text submissions skip this
  layer entirely.
- The `SpeechToTextProvider` interface (§3) must isolate the Groq
  Whisper integration behind a clean boundary so it could theoretically
  be replaced later, but Groq Whisper is the implementation that must
  ship.
- Output is plain transcribed text, handed directly into Request #1 —
  no separate language-detection or normalization stage is required
  beyond what Groq Whisper itself provides; Request #1's prompt is
  responsible for understanding the transcript's language (English,
  Urdu, Roman Urdu, or mixed) directly.
- Urdu/Roman Urdu transcription quality is subject to Groq Whisper's
  actual current language support and must be verified at
  implementation time (**DECISION REQUIRED / verify at implementation
  time** — do not assume a specific quality level without testing
  against real Urdu audio samples). Typed Urdu/Roman Urdu input is
  entirely unaffected by this, since it never reaches this layer.

## 5. Request #1 — Intent LLM

### 5.1 Responsibility

Convert the user's text (typed, or transcribed by Groq Whisper) into
one strict, validated structured JSON object describing the journey
request. This is the **only** thing Request #1 does. It does not call
any backend function, does not query the transit graph, and does not
produce a second output.

### 5.2 What Request #1 may interpret

- origin
- destination
- routing objective (fastest / fewest transfers / least walking —
  matching the fixed filter set in `01_PRODUCT_REQUIREMENTS.md` §1.4)
- departure/arrival time preference
- transfer preferences (e.g. "no transfers" → `max_transfers: 0`)
- walking preferences, classified into fixed buckets (see §6) rather
  than an invented exact number, unless the user gave one explicitly
- accessibility preferences, **only** where the underlying data model
  actually supports an accessibility field (currently: none — see
  `04_TRANSIT_DATA_AND_DOMAIN_MODEL.md`; do not fabricate support)
- other supported journey constraints already defined in
  `01_PRODUCT_REQUIREMENTS.md` §1.4
- the language/script the request was made in, where relevant to
  producing a usable `origin`/`destination` string for Layer 3 to
  resolve

### 5.3 What Request #1 must never do

- Determine an actual bus route, stop sequence, or path.
- Fabricate bus stops, schedules, fares, vehicle positions, ETAs,
  delays, or route geometry.
- Call any backend tool, function, or a second LLM request.
- Return anything other than the structured intent object (or an error)
  — no free-text commentary mixed into its output.

### 5.4 Output schema (indicative — exact field set should follow
`01_PRODUCT_REQUIREMENTS.md` §1.4's supported filters rather than
inventing new ones)

```json
{
  "origin": "Saddar Bus Terminal",
  "destination": "NUST",
  "objective": "least_walking",
  "departure_time": null,
  "arrival_time": null,
  "max_transfers": null,
  "max_walking_distance_class": "strict",
  "accessibility": null,
  "ambiguous_fields": []
}
```

`ambiguous_fields` (or an equivalent signal) must be used when Request
#1 cannot confidently extract a required field (e.g. no destination
mentioned at all) — the backend must treat this as a
clarification-needed case (§8) rather than proceeding with a guessed
value.

### 5.5 Validation

The backend must validate Request #1's output against a strict schema
**before** it is allowed to reach the Backend Journey Engine — the same
class of validation a direct, manually-constructed
`POST /transit/journeys/search` request would undergo. Malformed or
schema-invalid output must not be silently coerced; it must be treated
as a Request #1 failure (§8).

## 6. Preference classification (never invents a number)

Vague language must be classified into a small, fixed set of backend-
supported buckets; explicit numbers given by the user must pass through
unchanged.

- `objective`: `fastest` | `fewest_transfers` | `least_walking`
- `max_walking_distance_class`: `strict` (≈300m) | `moderate` (≈600m) |
  `relaxed` (≈1000m+), OR an explicit number if the user gave one
  ("under 500m")
- `max_transfers`: explicit integer if stated ("no bus changes" → `0`),
  otherwise unconstrained

**Not implemented, and Request #2 must not claim it happened:** any
filter class not actually backed by the Backend Journey Engine's
current capability.

## 7. Request #2 — Journey Response LLM

### 7.1 Responsibility

Convert the Backend Journey Engine's authoritative JSON output into a
natural-language response for the user. This is the **only** thing
Request #2 does. Its input is always backend-authoritative data — never
the raw user text, and never Request #1's intermediate output directly.

### 7.2 What Request #2 can explain

- which journey/route was selected
- where to walk, and how far
- which bus/route to take
- where to transfer
- expected arrival time
- current delay, if any
- fare
- why a particular candidate was ranked first, when multiple candidates
  are returned
- alternatives returned by the backend
- warnings or caveats already present in the backend's output (e.g. a
  route with no generated geometry, or an estimated rather than
  scheduled time)

### 7.3 What Request #2 must never do

Independently calculate or invent: routes, stops, fares, ETAs, delays,
walking distances, schedules, vehicle positions, or route geometry.
**If the backend says the fare is a specific amount, Request #2 must
state that exact amount. If the backend says a vehicle is a specific
number of minutes late, Request #2 must state that exact delay. If the
backend found no route, Request #2 must say so — it must never
fabricate an alternative.**

### 7.4 Input contract

Request #2 must receive the Backend Journey Engine's authoritative JSON
as-is (the same `JourneySearchResponse` shape a direct API client would
receive, or a structured no-route/clarification-needed result — see
§8), treated as ground truth. It must not receive unvalidated intent
data or raw user text as its primary input.

## 8. Ambiguous input and failure handling

### 8.1 Ambiguous or incomplete intent

If Request #1 signals ambiguous/missing required fields (§5.4), or the
Backend Journey Engine's Layer 3 resolution (`05_ROUTING_AND_GEOSPATIAL.md`
§2) returns multiple similarly-confident candidates for a location, the
backend must produce a structured clarification-needed result (naming
what's missing or ambiguous) and pass **that** result into Request #2,
which explains it as a natural-language clarifying question. This still
counts as the same two logical LLM stages for the command — Request
#2's job in this case is explaining "what's missing," not explaining a
journey.

### 8.2 Request #1 failure

```
My Gemini (Request #1 primary)
   ↓ failure
My Groq (Request #1 fallback)
   ↓ failure
return a controlled AI/provider error
```

If Request #1 fails entirely (both primary and fallback unreachable or
erroring), **the backend must not attempt to guess the user's intent.**
The conversational endpoint must return a defined error response
indicating the intent-understanding step failed, distinct from a
"no route found" result. A direct `POST /transit/journeys/search` call
remains available as a fallback path for the client.

### 8.3 Request #2 failure

```
Friend's Gemini (Request #2 primary)
   ↓ failure
Friend's Groq (Request #2 fallback)
   ↓ failure
return a controlled response-generation error
```

If Request #2 fails entirely, **the authoritative backend journey
result must remain intact and must still be returned to the client** —
the API's response contract must include the structured journey data
independently of whether natural-language narration succeeded, with a
defined error/placeholder value for `text_response` rather than an
absent or corrupted response. An LLM failure must never corrupt or
withhold the authoritative journey result.

### 8.4 What must never happen

- Silently substituting a different, unconfigured provider.
- Making an uncontrolled extra LLM request beyond the specified
  primary→fallback chain for the request that failed.
- Retrying Request #1 or Request #2 indefinitely, or looping between
  them.
- Falling back to a guessed or fabricated journey when either request
  fails.

## 9. No text-to-speech

Text-to-speech is **not** part of this architecture — no
`TextToSpeechProvider`, no TTS API field, no TTS configuration, and no
TTS implementation task exists anywhere in this system. Every response
from `POST /ai/converse` is text (`text_response`). If a client wishes
to speak a response aloud, that is a frontend concern using
frontend-side technology, entirely outside this backend's
responsibility and outside this document set's scope.

## 10. Credential ownership

**End users of the application never provide, see, or configure any AI
provider API key.** All four LLM credentials (Request #1's Gemini/Groq
pair, Request #2's Gemini/Groq pair) and the Groq Whisper credential are
server-side project secrets, owned by the project/deployment — see
`03_BACKEND_ARCHITECTURE.md` §5.1 for the exact configuration variables.
Terminology must be precise in code, configuration, and documentation:

- Request #1's credentials are **the project owner's API keys**.
- Request #2's credentials are **a second project contributor's API
  keys**.
- Neither pair is ever referred to as "user API keys" — that phrasing
  would incorrectly imply application users must supply their own
  Gemini/Groq credentials. They do not, and must never be asked to.

## 11. Hallucination prevention (mechanical, not just prompted)

- Request #1's output is schema-validated before it reaches the Backend
  Journey Engine — there is no path by which its free-form reasoning
  becomes an authoritative transit fact.
- Request #2's input is always the Backend Journey Engine's own
  authoritative JSON; its system prompt must instruct it to state only
  facts present in that input, never to compute or add a new one.
- **Testable requirement, not just a hope:** automated tests must
  sample Request #2's outputs and verify every number/time/place
  mentioned traces back to a value present in the authoritative JSON it
  was given. See `09_TESTING_AND_QUALITY_REQUIREMENTS.md` §5.
- If the backend's authoritative result indicates a capability isn't
  supported (e.g. a requested filter the routing engine doesn't apply),
  Request #2 must be instructed to say so honestly rather than imply
  the request was fully honored.

## 12. Integration details

- **Dev vs. production config:** local development should default to a
  clear "AI pipeline not configured" state (direct
  `POST /transit/journeys/search` calls remain fully functional without
  any LLM credentials) so the core backend can be run and tested without
  live provider credentials; only a deployed environment needs all five
  credentials (four LLM, one Groq Whisper) configured.
- **Latency:** budget for two sequential LLM stages per conversational
  command (Request #1, then — after the Backend Journey Engine runs —
  Request #2), each contributing at least one provider round-trip (and,
  if the primary provider fails, a second round-trip to the fallback
  within that same stage), plus one Groq Whisper call for voice input.
  This is a fixed, predictable structure per command rather than a
  variable number of agentic tool-call round-trips.
- **Fallback if the AI pipeline is unreachable, unconfigured, or
  rate-limited:** `POST /transit/journeys/search` (direct structured
  request, bypassing Request #1/#2 entirely) remains fully functional.
  **No feature in this architecture makes the core journey-planning-
  and-ticketing backend non-functional if the AI pipeline is
  unavailable** — this is a deliberate resilience property, not an
  afterthought.

## 13. Provider verification checklist (do before relying on any
provider in a deployed environment)

| Item | Action |
|---|---|
| Request #1 credentials | Obtain and configure `REQUEST1_GEMINI_API_KEY` / `REQUEST1_GROQ_API_KEY`; confirm current rate limits directly from each provider's live documentation |
| Request #2 credentials | Obtain and configure `REQUEST2_GEMINI_API_KEY` / `REQUEST2_GROQ_API_KEY`, as a fully separate credential pair from Request #1's |
| Groq Whisper | Obtain and configure `GROQ_WHISPER_API_KEY`; confirm current supported languages and quota directly from Groq's live documentation, especially for Urdu |
| Fallback behavior | Test that each request's primary→fallback chain (§8.2, §8.3) behaves correctly when the primary provider is deliberately made unreachable |
