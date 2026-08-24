# Karwan-e-Khizr Backend — Master Implementation Plan

> **Authoritative source of truth for backend implementation.** Every
> phase, module, API, test, and acceptance criterion below is derived
> directly from `backend/README.md` and the 11 specification documents
> under `backend/docs/`. Nothing here invents requirements; nothing
> documented is omitted.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Dependency Graph](#3-dependency-graph)
4. [Phase 1 — Foundation & Configuration](#4-phase-1--foundation--configuration)
5. [Phase 2 — Database Models & Migrations](#5-phase-2--database-models--migrations)
6. [Phase 3 — Transit Data Seeding](#6-phase-3--transit-data-seeding)
7. [Phase 4 — Geospatial Infrastructure (Layer 3)](#7-phase-4--geospatial-infrastructure-layer-3)
8. [Phase 5 — Deterministic Routing Engine (Layer 4)](#8-phase-5--deterministic-routing-engine-layer-4)
9. [Phase 6 — Authentication & User Accounts](#9-phase-6--authentication--user-accounts)
10. [Phase 7 — Fares & Ticketing](#10-phase-7--fares--ticketing)
11. [Phase 8 — Realtime & Simulation](#11-phase-8--realtime--simulation)
12. [Phase 9 — AI Pipeline (Request #1, #2, Speech-to-Text)](#12-phase-9--ai-pipeline-request-1-2-speech-to-text)
13. [Phase 10 — Conversational Endpoint Wiring](#13-phase-10--conversational-endpoint-wiring)
14. [Phase 11 — Admin APIs & Health Panel](#14-phase-11--admin-apis--health-panel)
15. [Phase 12 — Predictive ETA](#15-phase-12--predictive-eta)
16. [Phase 13 — Rate Limiting, Security Hardening & Finalization](#16-phase-13--rate-limiting-security-hardening--finalization)
17. [Cross-Phase Contracts](#17-cross-phase-contracts)
18. [Parallelization Opportunities](#18-parallelization-opportunities)
19. [Risks & Ambiguities](#19-risks--ambiguities)
20. [Final Implementation Order](#20-final-implementation-order)
21. [Definition of Done](#21-definition-of-done)

---

## 1. Architecture Overview

### Core Principle

> **LLMs interpret and explain. The backend computes and decides.**

Every conversational/voice command follows **exactly two logical LLM
stages** — Request #1 (intent extraction) and Request #2 (response
generation) — around a fully deterministic journey engine. Each stage
may make at most one primary provider call and, if that fails, one
fallback provider call. No additional LLM stages or uncontrolled calls
are permitted.

### Pipeline Flow

```
Command (typed or spoken)
  → [voice only] Groq Whisper: speech-to-text
  → Request #1 (Intent LLM): text → validated structured intent JSON
    — My Gemini PRIMARY, My Groq FALLBACK
  → Backend Journey Engine: intent → authoritative journey JSON
    (deterministic — geospatial resolution, Dijkstra, fares, realtime)
  → Request #2 (Response LLM): authoritative JSON → natural-language response
    — Friend's Gemini PRIMARY, Friend's Groq FALLBACK
  → Response returned to client
```

### Module Map (from `03_BACKEND_ARCHITECTURE.md` §2)

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
                     # model inference wrapper
  ticketing/        # Ticket state machine, QR issuance/validation,
                     # fares
  users/            # Registration, auth, roles
  seeding/          # Transit data import (agencies/routes/stops/trips)
  db/               # ORM models, Alembic migrations
  core/             # config, shared utilities
```

### Module Boundary Rules (from `03_BACKEND_ARCHITECTURE.md` §1)

- `routing` never imports from `ticketing`.
- `ticketing` calls into `payments` only through a `PaymentProvider`
  interface.
- `realtime`/`simulation` calls into vehicle-location logic only through
  a `VehicleLocationProvider` interface.
- Both LLM requests call the routing/geospatial layers **only through
  the same public API contract a direct client request would use** —
  never through internal function calls that bypass validation.

---

## 2. Technology Stack

| Component | Technology | Source |
|---|---|---|
| Language | Python 3.11+ | `03_BACKEND_ARCHITECTURE.md` §6 |
| Web framework | FastAPI (async, auto OpenAPI) | `03_BACKEND_ARCHITECTURE.md` §6 |
| Database | PostgreSQL 15+ with PostGIS | `03_BACKEND_ARCHITECTURE.md` §4 |
| ORM | SQLAlchemy 2.0+ (async) | Derived from PostGIS requirement |
| Migrations | Alembic | `03_BACKEND_ARCHITECTURE.md` §4 |
| Password hashing | bcrypt | `08_TICKETING_AUTH_AND_ADMIN.md` §4 |
| JWT | python-jose or PyJWT | `08_TICKETING_AUTH_AND_ADMIN.md` §4 |
| Geospatial queries | PostGIS extension | `05_ROUTING_AND_GEOSPATIAL.md` |
| Geocoding | Nominatim (OpenStreetMap) | `05_ROUTING_AND_GEOSPATIAL.md` §1 |
| Route geometry | OSRM (public routing engine) | `05_ROUTING_AND_GEOSPATIAL.md` §1 |
| AI — Intent LLM | Gemini PRIMARY / Groq FALLBACK | `06_AI_AND_VOICE_ARCHITECTURE.md` |
| AI — Response LLM | Gemini PRIMARY / Groq FALLBACK | `06_AI_AND_VOICE_ARCHITECTURE.md` |
| AI — Speech-to-text | Groq Whisper | `06_AI_AND_VOICE_ARCHITECTURE.md` §4 |
| ETA prediction | Local statistical/lightweight ML | `07_REALTIME_SIMULATION_AND_ETA.md` |
| Testing | pytest + pytest-asyncio | `09_TESTING_AND_QUALITY_REQUIREMENTS.md` |
| Test database | Live PostgreSQL/PostGIS | `09_TESTING_AND_QUALITY_REQUIREMENTS.md` §1 |
| HTTP client | httpx (async) | For Nominatim, OSRM, AI providers |

---

## 3. Dependency Graph

```
Phase 1 — Foundation & Configuration
    ↓
Phase 2 — Database Models & Migrations
    ↓
Phase 3 — Transit Data Seeding
    ↓
Phase 4 — Geospatial Infrastructure (Layer 3)
    ↓
Phase 5 — Deterministic Routing Engine (Layer 4)
    ↓                         ↓
Phase 6 — Auth & Users   Phase 8 — Realtime & Simulation
    ↓                         ↓
Phase 7 — Fares & Ticketing   Phase 12 — Predictive ETA (P1, parallel)
    ↓
Phase 9 — AI Pipeline
    ↓
Phase 10 — Conversational Endpoint Wiring
    ↓
Phase 11 — Admin APIs & Health Panel
    ↓
Phase 13 — Rate Limiting, Security Hardening & Finalization
```

### Mandatory Sequential Dependencies

```
1 → 2 → 3 → 4 → 5
5 → 6 → 7
5 → 8
6, 7 → 9 → 10
5, 8 → 11
10, 11 → 13
```

### Parallelizable Within Phases

- Phase 6 (auth) and Phase 8 (simulation) can run in parallel after Phase 5
- Phase 12 (predictive ETA) can run in parallel with Phases 9-11 after Phase 8
- Within Phase 4: geocoding and PostGIS queries can be built in parallel
- Within Phase 9: SpeechToTextProvider can be built in parallel with Request #1 and Request #2

---

## 4. Phase 1 — Foundation & Configuration

### Objective

Establish the project skeleton, configuration system, and development
infrastructure that all subsequent phases build on.

### Scope

- Project directory structure (per module map above)
- Python project metadata (pyproject.toml or equivalent)
- FastAPI application factory with lifespan management
- Configuration system loading from environment variables
- Core configuration variables (all AI provider keys, database URL, JWT
  secret, routing provider, ETA provider)
- Database connection/session management
- Alembic migration infrastructure
- Health-check endpoint (basic liveness)
- Logging setup (structured, configurable level)
- CORS configuration for frontend
- Docker Compose for local development (PostgreSQL + PostGIS)
- Python virtual environment (`.venv`) for isolated dependency management

### Development Setup

```bash
# Create and activate virtual environment
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate      # Linux/macOS

# Install dependencies (editable mode with dev extras)
.venv/Scripts/pip install -e .[dev]

# Start PostgreSQL + PostGIS
docker-compose up -d

# Run database initialization
.venv/Scripts/python -c "import asyncio; from app.core.database import init_db; asyncio.run(init_db())"

# Run tests
.venv/Scripts/python -m pytest tests/ -v

# Start development server
.venv/Scripts/python -m app.main
```

All subsequent phases assume commands are run from within the `.venv` environment.

### Files/Modules Expected

```
backend/
  pyproject.toml
  alembic.ini
  alembic/
    env.py
    versions/
  app/
    __init__.py
    main.py                  # FastAPI app factory
    core/
      __init__.py
      config.py              # Pydantic Settings — all env vars
      database.py            # AsyncEngine, SessionLocal, get_db
      logging.py             # Structured logging setup
      security.py            # JWT helpers (Phase 6 fleshed out here)
      exceptions.py          # Custom exception classes
      constants.py           # Walking radius defaults, speed estimates
    api/
      __init__.py
      router.py              # Root API router aggregating sub-routers
      health.py              # GET /health
    db/
      __init__.py
      base.py                # Declarative base
  docker-compose.yml         # PostgreSQL + PostGIS
  .env.example               # All required env vars documented
  .venv/                     # Python virtual environment (created at setup)
  .gitignore                 # Excludes .venv, __pycache__, .env, etc.
```

### Configuration Variables (from `03_BACKEND_ARCHITECTURE.md` §5.1)

```python
# Database
DATABASE_URL                    # postgresql+asyncpg://...

# JWT / Auth
SECRET_KEY                      # JWT signing key — from environment, never hardcoded
JWT_ALGORITHM                   # HS256 (default)
JWT_EXPIRATION_MINUTES          # 30 (default)

# Request #1 — Intent LLM (project owner's credentials)
REQUEST1_GEMINI_API_KEY         # primary
REQUEST1_GROQ_API_KEY           # fallback

# Request #2 — Response LLM (second contributor's credentials)
REQUEST2_GEMINI_API_KEY         # primary
REQUEST2_GROQ_API_KEY           # fallback

# Speech-to-text (voice input only)
GROQ_WHISPER_API_KEY            # selected ASR provider

# Predictive ETA
ETA_PROVIDER                    # "local" (default)

# Routing
ROUTING_PROVIDER                # "osrm" (default)
OSRM_BASE_URL                   # public OSRM endpoint

# Nominatim
NOMINATIM_BASE_URL              # https://nominatim.openstreetmap.org
NOMINATIM_USER_AGENT            # application identifier

# Rate limiting
RATE_LIMIT_LOGIN                # per-minute limit
RATE_LIMIT_VALIDATE             # per-minute limit
RATE_LIMIT_CONVERSE             # per-minute limit

# QR signing
QR_SIGNING_KEY                  # server-side secret for QR payload signing
```

### Database Changes

- No models yet — only Alembic infrastructure and connection pooling.

### APIs

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | None | Liveness probe, returns `{"status": "ok"}` |

### Services/Components

- `core/config.py`: Pydantic `Settings` class loading from env
- `core/database.py`: async SQLAlchemy engine + session factory
- `core/exceptions.py`: domain exception hierarchy

### Dependencies

None — this is the first phase.

### Tests

- Unit: configuration loads correctly from environment
- Unit: missing required configuration raises clear errors
- Integration: Docker Compose PostgreSQL+PostGIS container starts and is
  reachable
- Integration: Alembic can connect to the database

### Acceptance Criteria

1. `docker-compose up` starts a PostgreSQL+PostGIS container accepting
   connections on the configured port.
2. `python -m venv .venv && .venv/Scripts/pip install -e .[dev]` creates an
   isolated virtual environment with all dependencies.
3. `.venv/Scripts/python -m app.main` starts a FastAPI server with auto-generated
   OpenAPI docs at `/docs`.
4. `GET /health` returns HTTP 200 with `{"status": "ok"}`.
5. All configuration variables are loadable from `.env` with clear
   error messages for missing required vars.
6. No AI provider credentials are hardcoded — all loaded from
   environment.

---

## 5. Phase 2 — Database Models & Migrations

### Objective

Define every persistent entity from `04_TRANSIT_DATA_AND_DOMAIN_MODEL.md`
§1 as SQLAlchemy ORM models with PostGIS column types, and generate the
initial Alembic migration.

### Scope

All models from `04` §1 plus `08` §4 (User, Ticket):

#### Agency

```python
class Agency(Base):
    __tablename__ = "agencies"
    id: Mapped[int]                     # PK, autoincrement
    name: Mapped[str]                   # e.g. "PMTA", "CDA/CMTA"
    short_name: Mapped[Optional[str]]
    url: Mapped[Optional[str]]
    timezone: Mapped[str]               # default: "Asia/Karachi"
```

#### Route

```python
class Route(Base):
    __tablename__ = "routes"
    id: Mapped[int]                     # PK
    agency_id: Mapped[int]              # FK → agencies.id
    short_name: Mapped[str]             # e.g. "Red Line", "FR-01"
    long_name: Mapped[Optional[str]]
    route_type: Mapped[str]             # "bus" | "metro" | "feeder"
    color: Mapped[Optional[str]]        # hex color for map display
    text_color: Mapped[Optional[str]]
    path: Mapped[Optional[Geometry]]    # PostGIS LineString — OSRM-derived
    geometry_source: Mapped[Optional[str]]  # "osrm" | null
    geometry_confidence: Mapped[Optional[str]]  # "HIGH" | "APPROXIMATE" | null
```

#### Stop

```python
class Stop(Base):
    __tablename__ = "stops"
    id: Mapped[int]                     # PK
    name: Mapped[str]                   # station/stop name
    location: Mapped[Optional[Geometry]]  # PostGIS geography(Point, 4326)
    coordinate_source: Mapped[Optional[str]]  # "nominatim" | "curated" | "UNKNOWN"
    coordinate_confidence: Mapped[Optional[str]]  # "HIGH" | "APPROXIMATE" | "UNKNOWN"
    zone_id: Mapped[Optional[str]]
```

#### RouteStop (association)

```python
class RouteStop(Base):
    __tablename__ = "route_stops"
    id: Mapped[int]                     # PK
    route_id: Mapped[int]              # FK → routes.id
    stop_id: Mapped[int]               # FK → stops.id
    sequence: Mapped[int]              # ordered position within route
    distance_along_route_m: Mapped[Optional[float]]
    __table_args__ = (UniqueConstraint("route_id", "stop_id"),)
```

#### Trip

```python
class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[int]                     # PK
    route_id: Mapped[int]              # FK → routes.id
    direction_id: Mapped[Optional[int]]  # 0/1 for outbound/return
    headsign: Mapped[Optional[str]]
    scheduled_start_time: Mapped[datetime]
    status: Mapped[str]                 # "scheduled" | "active" | "completed" | "cancelled"
```

#### StopTime

```python
class StopTime(Base):
    __tablename__ = "stop_times"
    id: Mapped[int]                     # PK
    trip_id: Mapped[int]               # FK → trips.id
    stop_id: Mapped[int]               # FK → stops.id
    sequence: Mapped[int]
    arrival_offset_s: Mapped[int]      # seconds since trip.scheduled_start_time
    departure_offset_s: Mapped[int]
    __table_args__ = (UniqueConstraint("trip_id", "stop_id"),)
```

#### Vehicle

```python
class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int]                     # PK
    label: Mapped[str]                  # human-readable ID
    route_id: Mapped[Optional[int]]    # FK → routes.id
    trip_id: Mapped[Optional[int]]     # FK → trips.id
    status: Mapped[str]                 # "scheduled" | "active" | "completed"
```

#### VehiclePosition

```python
class VehiclePosition(Base):
    __tablename__ = "vehicle_positions"
    id: Mapped[int]                     # PK
    vehicle_id: Mapped[int]            # FK → vehicles.id
    latitude: Mapped[float]
    longitude: Mapped[float]
    bearing: Mapped[Optional[float]]   # 0-360 degrees
    speed: Mapped[Optional[float]]     # m/s
    timestamp: Mapped[datetime]        # when this position was computed/observed
    source: Mapped[str]                # "simulated" | "realtime"
```

#### FareRule

```python
class FareRule(Base):
    __tablename__ = "fare_rules"
    id: Mapped[int]                     # PK
    name: Mapped[str]                   # e.g. "Standard Metrobus"
    base_fare: Mapped[float]           # in PKR
    per_leg_fare: Mapped[float]        # per additional boarding
    currency: Mapped[str]              # "PKR"
    is_active: Mapped[bool]            # default True
```

#### User

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int]                     # PK
    email: Mapped[str]                  # unique, indexed
    hashed_password: Mapped[str]
    full_name: Mapped[Optional[str]]
    role: Mapped[str]                   # "passenger" | "admin"
    is_active: Mapped[bool]            # default True
    created_at: Mapped[datetime]
```

#### Ticket

```python
class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int]                     # PK
    user_id: Mapped[int]               # FK → users.id
    journey_data: Mapped[JSON]          # snapshot of the journey at purchase time
    ride_leg_count: Mapped[int]
    fare_charged: Mapped[float]
    currency: Mapped[str]              # "PKR"
    status: Mapped[str]                # "ACTIVE" | "USED" | "EXPIRED" | "REVOKED"
    qr_payload: Mapped[str]            # signed opaque token
    created_at: Mapped[datetime]
    used_at: Mapped[Optional[datetime]]
    expires_at: Mapped[Optional[datetime]]
```

### Database Changes

- All tables created via single Alembic migration
- Spatial indexes on `stops.location` (GiST)
- GiST index on `routes.path`
- B-tree indexes on `routes.agency_id`, `route_stops.route_id`,
  `route_stops.stop_id`, `trips.route_id`, `stop_times.trip_id`,
  `vehicles.route_id`, `vehicle_positions.vehicle_id`,
  `tickets.user_id`, `tickets.status`, `users.email`
- Unique constraints on `route_stops(route_id, stop_id)`,
  `stop_times(trip_id, stop_id)`, `users.email`

### Indexes

```sql
-- Spatial
CREATE INDEX idx_stops_location ON stops USING GIST (location);
CREATE INDEX idx_routes_path ON routes USING GIST (path);

-- B-tree
CREATE INDEX idx_routes_agency_id ON routes(agency_id);
CREATE INDEX idx_route_stops_route_id ON route_stops(route_id);
CREATE INDEX idx_route_stops_stop_id ON route_stops(stop_id);
CREATE INDEX idx_trips_route_id ON trips(route_id);
CREATE INDEX idx_stop_times_trip_id ON stop_times(trip_id);
CREATE INDEX idx_vehicles_route_id ON vehicles(route_id);
CREATE INDEX idx_vehicle_positions_vehicle_id ON vehicle_positions(vehicle_id);
CREATE INDEX idx_tickets_user_id ON tickets(user_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_users_email ON users(email) UNIQUE;
```

### Files/Modules Expected

```
backend/app/db/
  base.py              # declarative base (extended from Phase 1)
  models/
    __init__.py        # re-exports all models
    agency.py
    route.py
    stop.py
    route_stop.py
    trip.py
    stop_time.py
    vehicle.py
    vehicle_position.py
    fare_rule.py
    user.py
    ticket.py
  alembic/
    env.py             # configured for async + PostGIS
    versions/
      001_initial_schema.py
```

### APIs

No new API endpoints — models only.

### Services/Components

- `db/base.py`: SQLAlchemy declarative base with common mixins (timestamps, PK)

### Dependencies

- Phase 1 (database connection, Alembic infrastructure)

### Tests

- Unit: each model instantiates correctly with required fields
- Integration: Alembic migration applies cleanly on a fresh database
- Integration: Alembic migration is idempotent (re-apply produces no changes)
- Integration: all spatial columns accept and return PostGIS geometry
- Integration: unique constraints enforced (duplicate email rejected,
  duplicate route_stop rejected)

### Acceptance Criteria

1. `alembic upgrade head` creates all 11 tables on a fresh PostGIS
   database without errors.
2. `alembic downgrade base` drops all tables cleanly.
3. Re-running `alembic upgrade head` on an already-migrated database
   produces no changes (idempotent).
4. All spatial columns are queryable with PostGIS functions
   (e.g., `ST_Distance`, `ST_DWithin`).
5. Every model's required fields reject NULL values.

---

## 6. Phase 3 — Transit Data Seeding

### Objective

Import the researched Islamabad/Rawalpindi transit dataset into the
database with honest provenance tracking, covering agencies, routes,
stops, route-stops, trips, stop-times, and fare rules.

### Scope

#### Data Import Pipeline

- Seed data files (JSON or CSV) for:
  - 4 Metrobus lines (Red/Orange/Blue/Green) + 22 CDA feeder routes
  - 122 known stops (88 with coordinates, 34 with `UNKNOWN` location)
  - Route-stop associations with sequence ordering
  - 4 imported real timetables (FR-01, FR-04, FR-07, FR-14)
  - Fare rules (DB-driven, flat per-boarding formula)

#### Import Adapters

```python
class TransitDataImporter:
    """Idempotent import of transit data from seed files."""
    def import_agencies(self, data: list[dict]) -> int
    def import_routes(self, data: list[dict]) -> int
    def import_stops(self, data: list[dict]) -> int
    def import_route_stops(self, data: list[dict]) -> int
    def import_trips(self, data: list[dict]) -> int
    def import_stop_times(self, data: list[dict]) -> int
    def import_fare_rules(self, data: list[dict]) -> int
```

#### Import Rules (from `04` §7)

- **Idempotent**: re-running import does not create duplicates
  (upsert by natural key: route `short_name`, stop `name`, etc.)
- **Provenance preserved**: every stop's `coordinate_source` and
  `coordinate_confidence` populated; every route's `geometry_source`
  and `geometry_confidence` populated
- **No fabrication**: 34 stops remain `UNKNOWN` location — no coordinate
  may be fabricated
- **Honest timetable labeling**: routes without real timetable data
  receive headway-based estimates, explicitly labeled

#### Seed Data Structure

```
backend/
  seeding/
    __init__.py
    importer.py              # TransitDataImporter
    adapters/
      __init__.py
      agencies.py
      routes.py
      stops.py
      route_stops.py
      trips.py
      stop_times.py
      fare_rules.py
  data/
    agencies.json
    routes.json
    stops.json
    route_stops.json
    trips/
      fr_01.json             # real timetable
      fr_04.json             # real timetable
      fr_07.json             # real timetable
      fr_14.json             # real timetable
    fare_rules.json
```

### Database Changes

- No schema changes — data only.
- Import writes to existing tables.

### APIs

No public API endpoints yet (admin seed endpoint added in Phase 11).

### Services/Components

- `seeding/importer.py`: orchestrates the import, calls adapters
- `seeding/adapters/*.py`: per-entity import logic with upsert semantics
- CLI command or admin endpoint to trigger import

### Dependencies

- Phase 2 (all models exist)

### Tests

- Integration: import runs without errors on the actual seed data
- Integration: re-running import is idempotent (record counts unchanged)
- Integration: 88 stops have coordinates, 34 have `UNKNOWN` location
- Integration: 4 Metrobus lines + 22 feeder routes present
- Integration: 4 timetable routes have StopTime records
- Integration: fare rules loaded with correct `base_fare` and
  `per_leg_fare` values
- Unit: each adapter correctly maps input fields to model columns
- Edge case: import with empty/missing optional fields succeeds

### Acceptance Criteria

1. Running the import script populates all 11 tables with the documented
   transit data counts.
2. Re-running the import produces identical record counts (idempotent).
3. No stop outside the 88 located stops has a non-null `location`.
4. Every route has correct `agency_id`, `short_name`, and `route_type`.
5. FR-01, FR-04, FR-07, FR-14 have `StopTime` records with correct
   `arrival_offset_s`/`departure_offset_s` values.

---

## 7. Phase 4 — Geospatial Infrastructure (Layer 3)

### Objective

Build Layer 3 (Geospatial Transit Intelligence) as specified in
`05_ROUTING_AND_GEOSPATIAL.md` §2 — the geospatial operations invoked
internally by the Backend Journey Engine, never by either LLM request
directly.

### Scope

#### Location Resolution

```python
class GeospatialService:
    async def resolve_location(self, text: str) -> LocationResolutionResult:
        """
        Two-tier resolution:
        1. Fast fuzzy match against Stop.name and curated aliases
        2. Fallback to Nominatim geocoding
        """
```

Returns:
```python
class LocationResolutionResult(BaseModel):
    candidates: list[LocationCandidate]

class LocationCandidate(BaseModel):
    stop_id: int | None
    name: str
    lat: float
    lon: float
    match_confidence: float           # 0.0 - 1.0
    match_type: Literal["exact_stop", "fuzzy_stop", "geocoded"]
```

#### Nearby Stops

```python
async def nearby_stops(self, lat: float, lon: float, radius_m: float = 400.0) -> list[NearbyStop]:
    """
    PostGIS ST_DWithin query — find stops within walking radius.
    """
```

Returns:
```python
class NearbyStop(BaseModel):
    stop_id: int
    name: str
    lat: float
    lon: float
    distance_m: float
```

#### Walking Distance

```python
async def walking_distance(self, from_lat: float, from_lon: float,
                           to_lat: float, to_lon: float) -> WalkingResult:
    """
    OSRM walking profile for real pedestrian distance/duration.
    Falls back to haversine if OSRM unavailable.
    """
```

Returns:
```python
class WalkingResult(BaseModel):
    distance_m: float
    duration_s: float
```

#### Route Geometry Retrieval

```python
async def route_geometry(self, route_id: int) -> dict | None:
    """
    Returns Route.path as GeoJSON, or null if not yet generated.
    Never fabricated.
    """
```

#### Ambiguity Handling (from `05` §2, `06` §8.1)

If `resolve_location` returns multiple ambiguous, similarly-confident
candidates, the Backend Journey Engine must produce a
clarification-needed result rather than guessing.

### Files/Modules Expected

```
backend/app/geospatial/
  __init__.py
  service.py              # GeospatialService — main entry point
  location_resolver.py    # fuzzy match + Nominatim fallback
  nearby.py               # PostGIS spatial queries
  walking.py              # OSRM walking distance/duration
  route_geometry.py       # Route.path GeoJSON retrieval
  nominatim.py            # Nominatim API client
  osrm.py                 # OSRM API client
  schemas.py              # LocationCandidate, NearbyStop, WalkingResult
  aliases.py              # Curated landmark/stop name aliases
```

### Database Changes

- No schema changes — reads from existing tables.

### APIs

These are internal service methods, not public API endpoints (though
`nearby_stops` is also exposed as a read-only endpoint in Phase 11).

### Services/Components

- `geospatial/service.py`: orchestrates all Layer 3 operations
- `geospatial/nominatim.py`: async Nominatim client with caching
- `geospatial/osrm.py`: async OSRM client with caching
- `geospatial/location_resolver.py`: fuzzy matching + geocoding
- `geospatial/nearby.py`: PostGIS `ST_DWithin` queries
- `geospatial/walking.py`: OSRM walking profile
- `geospatial/aliases.py`: curated stop name aliases for fast matching

### Dependencies

- Phase 2 (models exist)
- Phase 3 (data seeded — stops with coordinates)

### Tests

- Unit: fuzzy matching resolves known stop names to correct candidates
- Unit: fuzzy matching returns empty for unrecognized names
- Unit: curated aliases resolve correctly
- Integration: `nearby_stops` returns correct stops within radius using
  PostGIS
- Integration: `resolve_location` falls back to Nominatim for
  unrecognized names (with mocked HTTP or integration test)
- Integration: `walking_distance` returns plausible values (mocked OSRM
  or integration test with real OSRM)
- Integration: `route_geometry` returns GeoJSON for routes with geometry,
  null for routes without
- Edge case: `resolve_location` with ambiguous input returns multiple
  candidates with similar confidence
- Edge case: `nearby_stops` with no stops in radius returns empty list

### Acceptance Criteria

1. `resolve_location("Saddar Bus Terminal")` returns a candidate with
   `match_type: "exact_stop"` or `"fuzzy_stop"`.
2. `resolve_location("some random gibberish")` returns a geocoded
   candidate or empty list (not fabricated stops).
3. `nearby_stops(33.6941, 73.0479, 400)` returns stops within 400m
   using PostGIS `ST_DWithin`.
4. `route_geometry(route_id_with_geometry)` returns valid GeoJSON
   LineString.
5. `route_geometry(route_id_without_geometry)` returns `None`.
6. No fabricated coordinates appear in any result.

---

## 8. Phase 5 — Deterministic Routing Engine (Layer 4)

### Objective

Build the core journey planning engine — graph construction, Dijkstra
pathfinding, filters, multi-candidate ranked responses, and fare
application. This is the **central backend capability** as specified in
`05_ROUTING_AND_GEOSPATIAL.md` §3-4.

### Scope

#### Transit Graph Construction

```python
class TransitGraph:
    """
    Builds a graph from Agency/Route/Stop/RouteStop data.
    Nodes: stops + origin/destination points
    Edges: walking edges (origin→stops, stops→destination, stops↔transfers)
            + riding edges (stop→stop along a route)
    """
    def build(self) -> None
    def add_origin_destination(self, origin: LocationCandidate,
                               dest: LocationCandidate) -> None
```

#### Dijkstra Pathfinding

```python
class JourneySearchEngine:
    async def search(
        self,
        origin: str | CoordinatePair,
        destination: str | CoordinatePair,
        objective: Literal["fastest", "fewest_transfers", "least_walking"],
        max_walk_m: float | None = None,
        max_transfers: int | None = None,
        departure_time: datetime | None = None,
    ) -> JourneySearchResponse:
        """
        1. Resolve origin/destination via Layer 3
        2. Build transit graph
        3. Run Dijkstra with objective-specific edge weights
        4. Apply filters (max_walk_m, max_transfers)
        5. Rank and return up to 3 candidates
        6. Annotate with fares via FaresService
        """
```

#### Journey Response Schema (from `05` §3)

```python
class JourneySearchResponse(BaseModel):
    journeys: list[Journey]

class Journey(BaseModel):
    legs: list[Leg]
    total_duration_s: int
    total_walk_m: float
    transfer_count: int
    fare: FareQuote | None

class Leg(BaseModel):
    type: Literal["walk", "ride"]
    route_id: int | None
    trip_id: int | None
    start_stop_id: int
    end_stop_id: int
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    duration_s: int
    distance_m: float | None        # for walk legs
    geometry: GeoJSON | None        # GeoJSON LineString for map rendering
    departure_time: datetime | None
    arrival_time: datetime | None
```

#### Multi-Candidate Ranking (from `05` §4)

- Up to 3 results per search: fastest, fewest transfers, least walking
- Each candidate scored by its objective
- Filters applied to all candidates before ranking

#### Time-Dependent Routing (from `05` §4)

- Earliest-arrival Dijkstra variant keyed on `(node, time)`
- Where real schedule data exists (FR-01, FR-04, FR-07, FR-14), use
  actual next-scheduled-departure timing
- Where no timetable exists, use route-length / assumed average speed

#### Fare Annotation

- After pathfinding, annotate each candidate journey with fare via
  `FaresService.get_fare_quote(journey)`
- Server-authoritative pricing — never trust client-supplied fares

### Files/Modules Expected

```
backend/app/routing/
  __init__.py
  engine.py              # JourneySearchEngine — main entry point
  graph.py               # TransitGraph — graph construction
  dijkstra.py            # Dijkstra implementation with objectives
  filters.py             # max_walk_m, max_transfers filters
  ranking.py             # Multi-candidate ranking
  time_aware.py          # Time-dependent routing logic
  schemas.py             # JourneySearchResponse, Journey, Leg, FareQuote
  objectives.py          # Edge weight functions per objective
```

### Database Changes

- No schema changes — reads from existing tables.

### APIs

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/transit/journeys/search` | POST | None | Direct structured journey search |

#### `POST /transit/journeys/search`

**Request:**
```json
{
  "origin": "Saddar Bus Terminal",
  "destination": "NUST",
  "objective": "fastest",
  "max_walk_m": 600,
  "max_transfers": 2,
  "departure_time": "2026-08-23T08:00:00+05:00"
}
```

**Response (200):**
```json
{
  "journeys": [
    {
      "legs": [...],
      "total_duration_s": 2400,
      "total_walk_m": 350,
      "transfer_count": 1,
      "fare": {"base_fare": 50, "per_leg_fare": 20, "total": 70, "currency": "PKR"}
    }
  ],
  "origin_resolved": {"name": "Saddar Bus Terminal", "lat": 33.6941, "lon": 73.0479},
  "destination_resolved": {"name": "NUST", "lat": 33.6425, "lon": 72.9750}
}
```

**Error (400):**
```json
{
  "error": "ambiguous_origin",
  "candidates": [
    {"name": "Saddar Terminal A", "lat": 33.694, "lon": 73.048},
    {"name": "Saddar Terminal B", "lat": 33.695, "lon": 73.047}
  ]
}
```

**Error (404):**
```json
{
  "error": "no_route_found",
  "message": "No transit route found between the specified origin and destination."
}
```

### Services/Components

- `routing/engine.py`: orchestrates the full search pipeline
- `routing/graph.py`: builds the transit graph from database
- `routing/dijkstra.py`: core pathfinding with objective-specific weights
- `routing/filters.py`: post-search filtering
- `routing/ranking.py`: multi-candidate ranking
- `routing/time_aware.py`: time-dependent edge weight calculation

### Dependencies

- Phase 2 (models)
- Phase 3 (seeded transit data)
- Phase 4 (geospatial Layer 3 — location resolution, walking distance)
- Phase 7 must provide `FaresService` interface (can be a stub initially)

### Tests

- Unit: graph construction from known fixtures produces expected nodes/edges
- Unit: Dijkstra returns shortest path on a known small graph
- Unit: `fastest` objective minimizes total duration
- Unit: `fewest_transfers` objective minimizes transfer count
- Unit: `least_walking` objective minimizes walking distance
- Unit: `max_walk_m` filter excludes journeys exceeding the limit
- Unit: `max_transfers` filter excludes journeys exceeding the limit
- Unit: time-dependent routing selects correct next-scheduled trip
- Integration: `POST /transit/journeys/search` with known origin/destination
  returns valid journey with correct leg structure
- Integration: search returns up to 3 ranked candidates
- Integration: fare annotation present on each candidate
- Integration: all legs have GeoJSON geometry where available
- Edge case: search with origin === destination returns error
- Edge case: search with no possible route returns `no_route_found`
- Edge case: search with ambiguous origin returns candidates list
- Security: malformed request body returns 422 with validation error

### Acceptance Criteria

1. `POST /transit/journeys/search` with a known origin and destination
   returns HTTP 200 with at least 1 valid journey.
2. Each journey has `legs`, `total_duration_s`, `total_walk_m`,
   `transfer_count`, and `fare`.
3. Every walk leg has `distance_m` and GeoJSON geometry.
4. Every ride leg has `route_id`, `trip_id`, and GeoJSON geometry
   (where route has geometry).
5. Applying `max_transfers: 0` excludes all journeys with transfers.
   6. A search at a time just before a scheduled departure returns the
      correct boarding time.
   7. An ambiguous origin returns HTTP 400 with candidate list.

---

## 9. Phase 6 — Authentication & User Accounts

### Objective

Implement registration, login, JWT-based sessions, and role-based
authorization as specified in `08_TICKETING_AUTH_AND_ADMIN.md` §4.

### Scope

#### Registration

```python
class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None

class RegisterResponse(BaseModel):
    id: int
    email: str
    role: str
```

#### Login

```python
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
```

#### JWT Configuration

- Secret key from `SECRET_KEY` environment variable
- Algorithm: HS256
- Token expiration: 30 minutes (configurable)
- Payload: `{"sub": user_id, "role": role, "exp": datetime}`

#### Roles

- `passenger`: default role for registered users
- `admin`: elevated role for admin endpoints

#### Authorization Dependencies

```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
async def require_admin(user: User = Depends(get_current_user)) -> User
async def require_role(role: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role != role:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return dependency
```

### Files/Modules Expected

```
backend/app/users/
  __init__.py
  service.py              # UserService — registration, login
  schemas.py              # RegisterRequest, LoginRequest, LoginResponse, UserPublic
  dependencies.py         # get_current_user, require_admin, require_role
  router.py               # POST /auth/register, POST /auth/login, GET /auth/me

backend/app/core/
  security.py             # hash_password, verify_password, create_token, decode_token
```

### Database Changes

- None — `users` table already created in Phase 2.

### APIs

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/auth/register` | POST | None | Register new user |
| `/auth/login` | POST | None | Login, returns JWT |
| `/auth/me` | GET | JWT required | Get current user profile |

#### `POST /auth/register`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "Test User"
}
```

**Response (201):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "role": "passenger"
}
```

**Error (409):**
```json
{
  "detail": "Email already registered"
}
```

#### `POST /auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Test User",
    "role": "passenger"
  }
}
```

**Error (401):**
```json
{
  "detail": "Invalid email or password"
}
```

#### `GET /auth/me`

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "Test User",
  "role": "passenger"
}
```

**Error (401):**
```json
{
  "detail": "Not authenticated"
}
```

### Services/Components

- `users/service.py`: registration, login, profile retrieval
- `core/security.py`: bcrypt hashing, JWT creation/verification
- `users/dependencies.py`: FastAPI dependency injection for auth

### Dependencies

- Phase 2 (User model exists)

### Tests

- Unit: password hashing produces verifiable hashes
- Unit: JWT creation and decode round-trips correctly
- Unit: expired JWT is rejected
- Integration: registration creates user with hashed password
- Integration: registration with duplicate email returns 409
- Integration: login with correct credentials returns JWT
- Integration: login with incorrect credentials returns 401
- Integration: `GET /auth/me` with valid JWT returns user profile
- Integration: `GET /auth/me` without JWT returns 401
- Security: `require_admin` rejects non-admin users with 403
- Security: SQL injection in email field is rejected

### Acceptance Criteria

1. `POST /auth/register` with valid input returns HTTP 201 and creates
   a user with `role: "passenger"`.
2. `POST /auth/login` with valid credentials returns a JWT that is
   decodable and contains the correct `user_id` and `role`.
3. `GET /auth/me` with a valid JWT returns the user's profile.
4. `GET /auth/me` without a token returns HTTP 401.
5. `GET /auth/me` with an expired token returns HTTP 401.
6. Passwords are stored as bcrypt hashes, never plaintext.

---

## 10. Phase 7 — Fares & Ticketing

### Objective

Implement fare calculation, ticket purchase, QR generation, ticket
validation, and the complete ticket lifecycle as specified in
`08_TICKETING_AUTH_AND_ADMIN.md` §1-3.

### Scope

#### Fares

```python
class FaresService:
    def get_fare_quote(self, ride_leg_count: int) -> FareQuote:
        """
        Server-authoritative pricing:
        - 0 for all-walking journey
        - base_fare + per_leg_fare x (ride_leg_count - 1)
        """

class FareQuote(BaseModel):
    base_fare: float
    per_leg_fare: float
    total: float
    currency: str  # "PKR"
```

#### PaymentProvider Interface

```python
class PaymentProvider(Protocol):
    async def process_payment(self, user_id: int, amount: float,
                              currency: str) -> PaymentResult: ...

class MockPaymentProvider:
    """Always succeeds — no real transaction."""
    async def process_payment(self, user_id: int, amount: float,
                              currency: str) -> PaymentResult:
        return PaymentResult(success=True, transaction_id="mock_tx_123")
```

#### Ticket Purchase Flow

```python
class TicketService:
    async def purchase_ticket(self, user_id: int,
                              journey_data: dict,
                              ride_leg_count: int) -> Ticket:
        """
        1. Compute fare server-side
        2. Process payment via PaymentProvider
        3. Generate signed QR payload
        4. Persist ticket with ACTIVE status
        """
```

#### QR Generation

```python
class QRService:
    def generate_payload(self, ticket_id: int, user_id: int) -> str:
        """Signed opaque token — ticket_id + user_id + HMAC signature."""

    def verify_payload(self, payload: str) -> QRVerificationResult:
        """Verify signature, extract ticket_id and user_id."""
```

- QR payload is a signed JWT or HMAC-signed JSON — **never raw ticket
  data**
- Signing key from `QR_SIGNING_KEY` environment variable
- Payload contains only `ticket_id` and `user_id` — no fare, no route,
  no other ticket fields

#### Ticket Validation

```python
class TicketService:
    async def validate_ticket(self, qr_payload: str,
                              validator_user_id: int) -> ValidationResult:
        """
        Atomic validation:
        1. Verify QR signature
        2. Extract ticket_id, user_id
        3. Check ownership (QR user_id matches ticket owner)
        4. Check ticket status (must be ACTIVE)
        5. Transition to USED in a single transaction
        6. Return VALID/INVALID
        """
```

#### Ticket Lifecycle (from `08` §2)

```
ACTIVE → USED        (on successful validation)
ACTIVE → EXPIRED     (lazy, evaluated at read/validate time)
ACTIVE → REVOKED     (admin action)
```

Lazy expiry: tickets past `expires_at` are treated as EXPIRED on read
or validate, not by a background sweep.

### Files/Modules Expected

```
backend/app/ticketing/
  __init__.py
  service.py              # TicketService — purchase, validate, history
  fares.py                # FaresService — fare calculation
  qr.py                   # QRService — payload generation/verification
  schemas.py              # TicketPurchaseRequest, TicketResponse, FareQuote, ValidationResult
  router.py               # POST /tickets, GET /tickets, POST /tickets/validate

backend/app/payments/
  __init__.py
  provider.py             # PaymentProvider protocol
  mock.py                 # MockPaymentProvider — always succeeds
```

### Database Changes

- None — `tickets` and `fare_rules` tables already created in Phase 2.

### APIs

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/fares/quote` | POST | None | Get fare quote for a journey |
| `/tickets` | POST | JWT required | Purchase ticket for a journey |
| `/tickets` | GET | JWT required | List current user's tickets |
| `/tickets/{id}` | GET | JWT required | Get specific ticket details |
| `/tickets/{id}/revoke` | POST | JWT required | Revoke a ticket |
| `/tickets/validate` | POST | JWT required | Validate a QR ticket |

#### `POST /fares/quote`

**Request:**
```json
{
  "ride_leg_count": 2
}
```

**Response (200):**
```json
{
  "base_fare": 50,
  "per_leg_fare": 20,
  "total": 70,
  "currency": "PKR"
}
```

#### `POST /tickets`

**Request:**
```json
{
  "journey_data": { },
  "ride_leg_count": 2
}
```

**Response (201):**
```json
{
  "id": 1,
  "status": "ACTIVE",
  "fare_charged": 70,
  "currency": "PKR",
  "qr_payload": "eyJ...",
  "created_at": "2026-08-23T08:30:00Z",
  "expires_at": "2026-08-23T12:30:00Z"
}
```

#### `POST /tickets/validate`

**Request:**
```json
{
  "qr_payload": "eyJ..."
}
```

**Response (200):**
```json
{
  "valid": true,
  "ticket_id": 1,
  "status": "USED"
}
```

**Response (200) — invalid:**
```json
{
  "valid": false,
  "reason": "Ticket already used"
}
```

### Services/Components

- `ticketing/fares.py`: DB-driven fare calculation
- `ticketing/qr.py`: HMAC-signed QR payload generation/verification
- `ticketing/service.py`: ticket lifecycle management
- `payments/mock.py`: mock payment provider

### Dependencies

- Phase 2 (Ticket, FareRule models)
- Phase 6 (User model, auth dependencies for ticket purchase)

### Tests

- Unit: fare calculation with known leg counts returns correct amounts
- Unit: fare calculation with 0 ride legs returns 0
- Unit: QR payload generation and verification round-trips
- Unit: QR verification rejects tampered payloads
- Unit: QR verification rejects mismatched owner
- Integration: ticket purchase creates ACTIVE ticket with correct fare
- Integration: ticket purchase calls PaymentProvider (mock)
- Integration: successful validation transitions ticket to USED
- Integration: double-validation of same ticket returns INVALID
- Integration: validation of EXPIRED ticket returns INVALID
- Integration: validation of REVOKED ticket returns INVALID
- Integration: concurrent validation of same ticket — exactly one succeeds
- Integration: `GET /tickets` returns current user's tickets only
- Security: ticket purchase without auth returns 401
- Security: ticket validation without auth returns 401

### Acceptance Criteria

1. `POST /fares/quote` with `ride_leg_count: 2` returns total = `base_fare + per_leg_fare * 1`.
2. `POST /tickets` with valid journey data returns HTTP 201 with
   `status: "ACTIVE"` and a `qr_payload`.
3. `POST /tickets/validate` with a valid QR payload returns
   `valid: true` and transitions the ticket to `USED`.
4. A second `POST /tickets/validate` with the same QR payload returns
   `valid: false`.
5. `GET /tickets` returns only the authenticated user's tickets.
6. All ticket state transitions are atomic (no race conditions on
   validation).

---

## 11. Phase 8 — Realtime & Simulation

### Objective

Implement the vehicle simulation engine, vehicle position API, and ETA
endpoints as specified in `07_REALTIME_SIMULATION_AND_ETA.md`.

### Scope

#### Simulation Engine

```python
class SimulationEngine:
    """Pure, deterministic simulation — same inputs always produce same output."""

    def compute_position_at(
        self,
        schedule: list[StopTimeEntry],
        route_geometry: GeoJSON | None,
        elapsed_s: float,
    ) -> VehiclePosition:
        """
        Given an ordered stop schedule and elapsed seconds, return exactly one position:
        - Parked at first stop before departure
        - Interpolated along route geometry where it exists
        - Falling back to straight-line between stop coordinates where no geometry
        - Dwelling at intermediate stops
        - Clamped at last stop once complete
        Also computes bearing and speed.
        """
```

#### VehicleLocationProvider Protocol

```python
class VehicleLocationProvider(Protocol):
    async def get_all_positions(self) -> list[VehiclePosition]: ...
    async def get_vehicle_position(self, vehicle_id: int) -> VehiclePosition | None: ...
    async def get_vehicle_eta(self, vehicle_id: int) -> VehicleETA | None: ...

class SimulatedVehicleLocationProvider:
    """Default implementation using SimulationEngine."""
    def __init__(self, engine: SimulationEngine, db: AsyncSession): ...
```

#### Timing (from `07` §2)

- Where real `StopTime` data exists (FR-01, FR-04, FR-07, FR-14): use
  it directly
- Where no timetable: synthesize offsets from route length / assumed
  average speed + flat dwell time per stop, **explicitly labeled as
  estimates**

#### Position Interpolation (from `07` §2)

- With route geometry: interpolate along the LineString
- Without route geometry: straight-line interpolation between stop
  coordinates

### Files/Modules Expected

```
backend/app/simulation/
  __init__.py
  engine.py              # SimulationEngine — pure, deterministic
  provider.py            # SimulatedVehicleLocationProvider
  schemas.py             # VehiclePosition, VehicleETA, VehicleSnapshot
  router.py              # GET /transit/realtime/vehicles, /vehicles/{id}, /vehicles/{id}/eta
  trip_generator.py      # Generate active trips from schedule + current time
```

### Database Changes

- No schema changes — writes to `vehicles` and `vehicle_positions`
  tables (created in Phase 2).

### APIs

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/transit/realtime/vehicles` | GET | None | All active vehicle positions |
| `/transit/realtime/vehicles/{id}` | GET | None | Single vehicle position |
| `/transit/realtime/vehicles/{id}/eta` | GET | None | Vehicle ETA at next stop |

#### `GET /transit/realtime/vehicles`

**Response (200):**
```json
{
  "vehicles": [
    {
      "id": 1,
      "label": "Bus-001",
      "route_id": 5,
      "trip_id": 123,
      "latitude": 33.6941,
      "longitude": 73.0479,
      "bearing": 45.0,
      "speed": 12.5,
      "status": "active",
      "source": "simulated",
      "timestamp": "2026-08-23T08:15:00Z",
      "next_stop_id": 15,
      "eta_seconds": 180
    }
  ]
}
```

#### `GET /transit/realtime/vehicles/{id}/eta`

**Response (200):**
```json
{
  "vehicle_id": 1,
  "next_stop_id": 15,
  "baseline_eta_seconds": 180,
  "predicted_eta_seconds": 165,
  "delay_seconds": 15,
  "source": "simulated"
}
```

### Services/Components

- `simulation/engine.py`: pure deterministic position computation
- `simulation/provider.py`: `SimulatedVehicleLocationProvider` implementation
- `simulation/trip_generator.py`: creates Vehicle + Trip records for current service window
- `simulation/router.py`: FastAPI router for vehicle-position endpoints

### Dependencies

- Phase 2 (Vehicle, VehiclePosition, Trip, StopTime, Route models)
- Phase 3 (seeded transit data — routes, stops, timetables)

### Tests

- Unit: `compute_position_at` is deterministic (same inputs → same output)
- Unit: before departure, vehicle parked at first stop
- Unit: mid-trip, vehicle interpolated correctly along geometry
- Unit: mid-trip, vehicle interpolated correctly without geometry (straight-line)
- Unit: at completion, vehicle clamped at last stop
- Unit: bearing computed correctly between consecutive positions
- Unit: speed computed correctly
- Integration: `GET /transit/realtime/vehicles` returns active vehicles with `source: "simulated"`
- Integration: `GET /transit/realtime/vehicles/{id}` returns single vehicle
- Integration: `GET /transit/realtime/vehicles/{id}/eta` returns baseline ETA
- Integration: `source` field is always present and correctly set
- Regression: fallback behavior when geometry absent vs. present

### Acceptance Criteria

1. `compute_position_at` with identical inputs always returns identical output.
2. `GET /transit/realtime/vehicles` returns at least 1 active vehicle
   with `source: "simulated"`.
3. Every vehicle position has `latitude`, `longitude`, `bearing`, `speed`,
   `status`, and `source`.
4. ETA endpoint returns `baseline_eta_seconds` (always present).
5. `source` is never omitted — simulated data is never mistaken for
   real-time.

---

## 12. Phase 9 — AI Pipeline (Request #1, #2, Speech-to-Text)

### Objective

Implement the three AI provider interfaces — `SpeechToTextProvider`,
`IntentLLMProvider`, and `JourneyResponseLLMProvider` — with their
Gemini-primary/Groq-fallback implementations, as specified in
`06_AI_AND_VOICE_ARCHITECTURE.md`.

### Scope

#### Provider Interfaces (from `06` §3)

```python
class SpeechToTextProvider:
    def transcribe(self, audio_bytes: bytes) -> Transcript: ...

class Transcript(BaseModel):
    text: str
    confidence: float | None = None

class IntentLLMProvider:
    def extract_intent(self, text: str) -> IntentResult: ...

class IntentResult(BaseModel):
    """Request #1 output — validated structured intent."""
    origin: str
    destination: str
    objective: Literal["fastest", "fewest_transfers", "least_walking"]
    departure_time: str | None = None
    arrival_time: str | None = None
    max_transfers: int | None = None
    max_walking_distance_class: Literal["strict", "moderate", "relaxed"] | float | None = None
    accessibility: str | None = None
    ambiguous_fields: list[str] = []

class JourneyResponseLLMProvider:
    def generate_response(self, authoritative_json: dict) -> str: ...
```

#### Request #1 — Intent LLM (from `06` §5)

- Converts user text to structured intent JSON
- Must not determine routes, fabricate stops/schedules/fares/ETAs
- Output validated against strict schema before reaching journey engine
- `ambiguous_fields` signals missing/unclear required fields

#### Request #2 — Response LLM (from `06` §7)

- Converts authoritative journey JSON to natural-language response
- Must not independently calculate or invent any transit fact
- Input is always backend-authoritative data
- May only restate values present in the authoritative JSON

#### Speech-to-Text (from `06` §4)

- Groq Whisper, exclusively
- Invoked only for audio payloads
- Output plain text, handed directly to Request #1

#### Provider Implementations

```python
# Request #1 — Gemini PRIMARY, Groq FALLBACK
class GeminiIntentLLM(IntentLLMProvider): ...
class GroqIntentLLM(IntentLLMProvider): ...

# Request #2 — Gemini PRIMARY, Groq FALLBACK
class GeminiResponseLLM(JourneyResponseLLMProvider): ...
class GroqResponseLLM(JourneyResponseLLMProvider): ...

# Speech-to-text — Groq Whisper
class GroqWhisperSTT(SpeechToTextProvider): ...
```

#### Fallback Chain (from `06` §8.2, §8.3)

```
Request #1:
  My Gemini (primary) → failure → My Groq (fallback) → failure → controlled error

Request #2:
  Friend's Gemini (primary) → failure → Friend's Groq (fallback) → failure → controlled error
```

Each request uses its own credential pair. A failure in one request's
chain never affects the other.

#### Hallucination Prevention (from `06` §11)

- Request #1 output is schema-validated before reaching journey engine
- Request #2 input is the authoritative JSON — its prompt instructs it
  to state only facts present in that input
- Automated tests must verify every number/time/place in Request #2
  output traces back to the authoritative JSON

### Files/Modules Expected

```
backend/app/ai/
  __init__.py
  speech_to_text.py       # SpeechToTextProvider — Groq Whisper implementation
  intent_llm.py           # IntentLLMProvider — orchestrator with fallback
  response_llm.py         # JourneyResponseLLMProvider — orchestrator with fallback
  providers/
    __init__.py
    gemini_intent.py      # Gemini implementation for Request #1
    groq_intent.py        # Groq implementation for Request #1
    gemini_response.py    # Gemini implementation for Request #2
    groq_response.py      # Groq implementation for Request #2
    groq_whisper.py       # Groq Whisper implementation
  schemas.py              # IntentResult, Transcript, etc.
  prompts.py              # System prompts for Request #1 and Request #2
  config.py               # Provider selection based on config
```

### Database Changes

- No database changes — conversational state is ephemeral per command.

### APIs

No new API endpoints yet — providers are consumed by Phase 10.

### Services/Components

- `ai/speech_to_text.py`: Groq Whisper integration
- `ai/intent_llm.py`: orchestrator with primary→fallback chain
- `ai/response_llm.py`: orchestrator with primary→fallback chain
- `ai/providers/gemini_intent.py`: Gemini client for Request #1
- `ai/providers/groq_intent.py`: Groq client for Request #1
- `ai/providers/gemini_response.py`: Gemini client for Request #2
- `ai/providers/groq_response.py`: Groq client for Request #2
- `ai/providers/groq_whisper.py`: Groq Whisper client
- `ai/prompts.py`: system prompts (Request #1: intent extraction instructions;
  Request #2: narration-only instructions with authority constraint)

### Dependencies

- Phase 1 (configuration — API keys)

### Tests

- Unit: IntentResult schema validation accepts valid intent
- Unit: IntentResult schema validation rejects missing required fields
- Unit: IntentResult schema validation rejects invalid objective values
- Unit: IntentResult with `ambiguous_fields` signals clarification needed
- Unit: provider fallback — primary failure triggers fallback provider
- Unit: provider fallback — both failures return controlled error
- Unit: Request #1 and Request #2 use separate credential pairs
- Unit: Groq Whisper transcript handed to Request #1 unchanged
- Integration: Request #1 with real Gemini (if configured) returns valid intent
- Integration: Request #2 with real Gemini (if configured) returns natural language
- Integration: grounding test — Request #2 output numbers trace back to authoritative JSON
- Security: prompt injection in user input does not bypass journey engine validation
- Security: no PII beyond command text sent to LLM prompts

### Acceptance Criteria

1. `IntentLLMProvider.extract_intent` with valid text returns a
   schema-valid `IntentResult`.
2. When the primary provider is unreachable, the fallback provider is
   called automatically.
3. When both providers fail, a controlled error is returned (not an
   exception).
4. `JourneyResponseLLMProvider.generate_response` with authoritative
   JSON returns a natural-language string.
5. Request #1 and Request #2 are fully separate services with independent
   credentials, prompts, and error handling.
6. `SpeechToTextProvider.transcribe` returns plain text.
7. Groq Whisper is the only speech-to-text implementation.

---

## 13. Phase 10 — Conversational Endpoint Wiring

### Objective

Wire the complete conversational pipeline: `POST /ai/converse` endpoint
that accepts text or audio, runs the two-stage AI pipeline around the
Backend Journey Engine, and returns structured journeys plus natural
language response.

### Scope

#### The Complete Pipeline (from `06` §1)

```
POST /ai/converse
  → { message?: str, audio?: bytes }
  → [voice only] Groq Whisper: speech → text
  → Request #1: text → validated IntentResult
  → Backend Journey Engine: IntentResult → authoritative JourneySearchResponse
  → Request #2: authoritative JSON → natural-language text_response
  → { structured_journeys, text_response, clarification_needed? }
```

#### Clarification Flow (from `06` §8.1)

When Request #1 signals ambiguous fields or Layer 3 resolution returns
multiple ambiguous candidates:

```
Clarification-needed result → Request #2 → natural-language clarifying question
```

#### Error Flows (from `06` §8.2-8.4)

```
Request #1 failure (both providers fail):
  → return controlled error (no route guessed)

Request #2 failure (both providers fail):
  → return structured_journeys with text_response = error placeholder
  → authoritative journey result remains intact

AI pipeline unreachable/unconfigured:
  → POST /transit/journeys/search remains fully functional
```

### Files/Modules Expected

```
backend/app/ai/
  pipeline.py             # Full conversational pipeline orchestrator

backend/app/api/
  ai_router.py            # POST /ai/converse, GET /ai/health
```

### Database Changes

- No database changes.

### APIs

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/ai/converse` | POST | Optional (JWT) | Conversational journey planning |
| `/ai/health` | GET | None | AI provider reachability status |

#### `POST /ai/converse`

**Request:**
```json
{
  "message": "How do I get from Saddar to NUST? I want the fastest route.",
  "audio": null
}
```

OR (voice):
```multipart/form-data
audio: <binary audio data>
```

Exactly one of `message` or `audio` must be provided.

**Response (200):**
```json
{
  "structured_journeys": {
    "journeys": [...],
    "origin_resolved": {...},
    "destination_resolved": {...}
  },
  "text_response": "The fastest route from Saddar to NUST is to take the Red Line Metrobus...",
  "clarification_needed": null
}
```

**Response (200) — clarification:**
```json
{
  "structured_journeys": null,
  "text_response": "I found two locations named 'Saddar'. Did you mean Saddar Bus Terminal or Saddar Bazaar?",
  "clarification_needed": {
    "field": "origin",
    "candidates": ["Saddar Bus Terminal", "Saddar Bazaar"]
  }
}
```

**Response (200) — AI failure, journey available:**
```json
{
  "structured_journeys": { "journeys": [...] },
  "text_response": null,
  "text_response_error": "response_generation_failed"
}
```

**Response (422) — validation error:**
```json
{
  "detail": "Exactly one of 'message' or 'audio' must be provided."
}
```

#### `GET /ai/health`

**Response (200):**
```json
{
  "speech_to_text": {"provider": "groq_whisper", "status": "configured"},
  "intent_llm": {"primary": "gemini", "fallback": "groq", "status": "configured"},
  "response_llm": {"primary": "gemini", "fallback": "groq", "status": "configured"}
}
```

### Services/Components

- `ai/pipeline.py`: orchestrates the full conversational flow
- `api/ai_router.py`: FastAPI router for `/ai/converse` and `/ai/health`

### Dependencies

- Phase 4 (geospatial — location resolution)
- Phase 5 (routing engine — `POST /transit/journeys/search` contract)
- Phase 9 (AI providers — IntentLLM, ResponseLLM, SpeechToText)
- Phase 7 (fares — for fare annotation in journey results)

### Tests

- Integration: text input → full pipeline → structured_journeys + text_response
- Integration: audio input → Whisper → full pipeline → structured_journeys + text_response
- Integration: clarification-needed flow returns clarifying question
- Integration: Request #1 failure returns controlled error, no route guessed
- Integration: Request #2 failure returns journey data with null text_response
- Integration: direct `POST /transit/journeys/search` works without AI pipeline
- Integration: `GET /ai/health` returns provider status
- Security: prompt injection in user text does not bypass journey engine
- Security: no PII beyond command text sent to LLMs
- Edge case: missing both message and audio returns 422
- Edge case: ambiguous origin returns clarification-needed

### Acceptance Criteria

1. `POST /ai/converse` with `message: "test"` returns HTTP 200 with
   either `structured_journeys` or `clarification_needed`.
2. When audio is provided, it is transcribed before processing.
3. Exactly one of `message` or `audio` is required — missing both
   returns 422.
4. When Request #1 fails, no route is guessed — a controlled error
   is returned.
5. When Request #2 fails, the authoritative journey data is still
   returned with a null/error `text_response`.
6. `GET /ai/health` returns the configured provider status for all
   three AI services.
7. The direct `POST /transit/journeys/search` path works independently
   of the AI pipeline.

---

## 14. Phase 11 — Admin APIs & Health Panel

### Objective

Implement admin-gated endpoints for data operations, simulation
oversight, ticket inspection, data-quality views, and AI/ETA pipeline
health, as specified in `08_TICKETING_AUTH_AND_ADMIN.md` §5.

### Scope

#### Admin Endpoints

```python
# Data status / quality view
GET /admin/data/status          # stops with/without coordinates,
                                # routes with/without geometry,
                                # routes with/without timetables

# Realtime/simulation status
GET /admin/simulation/status    # active trips, vehicle count,
                                # simulation engine state

# Ticket inspection
GET /admin/tickets              # list/search tickets by code/status
GET /admin/tickets/{id}         # ticket details

# AI/ETA pipeline health
GET /ai/health                  # (already built in Phase 10 —
                                # exposed here for admin consumption)

# Seed/import/graph rebuild (trigger)
POST /admin/seed/run            # trigger data import
POST /admin/simulation/start    # start simulation for a time window
POST /admin/simulation/stop     # stop simulation
```

#### Authorization

All admin endpoints require `require_role("admin")` — a dependency
that checks the JWT's `role` field.

### Files/Modules Expected

```
backend/app/api/
  admin_router.py          # All /admin/* endpoints

backend/app/admin/
  __init__.py
  service.py               # AdminService — data status, simulation control
  schemas.py               # DataStatusResponse, SimulationStatusResponse, TicketSearchResult
```

### Database Changes

- No schema changes — reads from existing tables.

### APIs

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/admin/data/status` | GET | admin | Data quality overview |
| `/admin/simulation/status` | GET | admin | Simulation engine status |
| `/admin/tickets` | GET | admin | Search/list tickets |
| `/admin/tickets/{id}` | GET | admin | Ticket details |
| `/admin/seed/run` | POST | admin | Trigger data import |
| `/admin/simulation/start` | POST | admin | Start simulation |
| `/admin/simulation/stop` | POST | admin | Stop simulation |

#### `GET /admin/data/status`

**Response (200):**
```json
{
  "stops": {
    "total": 122,
    "with_coordinates": 88,
    "without_coordinates": 34
  },
  "routes": {
    "total": 26,
    "with_geometry": 0,
    "without_geometry": 26,
    "with_timetable": 4,
    "without_timetable": 22
  },
  "agencies": {
    "total": 2
  }
}
```

#### `GET /admin/simulation/status`

**Response (200):**
```json
{
  "running": true,
  "active_vehicles": 15,
  "active_trips": 12,
  "simulation_time": "2026-08-23T08:30:00Z"
}
```

#### `GET /admin/tickets`

**Query params:** `?status=ACTIVE&code=TICK-001`

**Response (200):**
```json
{
  "tickets": [
    {
      "id": 1,
      "user_id": 5,
      "status": "ACTIVE",
      "fare_charged": 70,
      "created_at": "2026-08-23T08:30:00Z"
    }
  ]
}
```

### Services/Components

- `admin/service.py`: data quality queries, simulation control
- `admin/schemas.py`: response schemas
- `api/admin_router.py`: FastAPI router with admin auth dependency

### Dependencies

- Phase 2 (all models)
- Phase 6 (auth — `require_role("admin")`)
- Phase 8 (simulation — for simulation control endpoints)
- Phase 3 (seeding — for seed/run endpoint)

### Tests

- Integration: admin endpoint with admin JWT returns 200
- Integration: admin endpoint with passenger JWT returns 403
- Integration: admin endpoint without JWT returns 401
- Integration: `/admin/data/status` returns correct counts
- Integration: `/admin/simulation/status` returns simulation state
- Integration: `/admin/tickets` filters by status correctly
- Security: non-admin user cannot access any admin endpoint
- Security: unauthenticated user cannot access any admin endpoint

### Acceptance Criteria

1. `GET /admin/data/status` with admin JWT returns correct stop/route
   counts.
2. `GET /admin/simulation/status` returns current simulation state.
3. Any admin endpoint with a passenger-role JWT returns HTTP 403.
4. Any admin endpoint without a JWT returns HTTP 401.
5. Data quality view accurately reflects the seeded data coverage gaps.

---

## 15. Phase 12 — Predictive ETA

### Objective

Implement the staged predictive ETA component as specified in
`07_REALTIME_SIMULATION_AND_ETA.md` §6-8. This is architecturally
independent of the AI conversational pipeline and can be built in
parallel with Phases 9-11.

### Scope

#### ETAPredictor Interface (from `07` §6)

```python
class ETAPredictor:
    def predict(self, features: ETAFeatures) -> ETAPrediction | None:
        """Returns None if no coverage — never a low-confidence guess."""
```

#### Feature Schema

```python
class ETAFeatures(BaseModel):
    route_id: int
    stop_id: int
    time_of_day: str          # "08:00"
    day_of_week: str          # "monday"
    scheduled_duration_s: int
    distance_remaining_m: float
    delay_seconds: int | None
```

#### Prediction Output

```python
class ETAPrediction(BaseModel):
    predicted_eta_seconds: float
    confidence: float
    model_version: str
```

#### Staged Architecture (from `07` §6)

**Stage 1 — Deterministic baseline (required, permanent):**
- Remaining distance / assumed or scheduled speed
- Always present, always correct
- This is the fallback when no ML model is available

**Stage 2 — Synthetic dataset generation:**
- Run simulation repeatedly across full timetable
- Generate (route, stop, time-of-day, day-of-week, scheduled-duration, simulated-actual-duration) tuples
- Stored as training artifact, not operational table

**Stage 3 — ML model training:**
- Statistical/lightweight-ML baseline (recommended: average-delay-by-route/time-of-day lookup, or LightGBM/XGBoost on tabular features)
- Explainable, fast to train, no GPU, no cloud ML platform
- Linear regression baseline kept as naive comparison

**Stage 4 — [FUTURE] Real-observation feedback loop:**
- When real vehicle feed exists, actual observed times replace synthetic data

### Files/Modules Expected

```
backend/app/eta/
  __init__.py
  predictor.py            # ETAPredictor interface + LocalETAPredictor implementation
  training.py             # Stage 2: synthetic dataset generation
  model.py                # Stage 3: model training wrapper
  features.py             # Feature extraction from vehicle/route state
  schemas.py              # ETAFeatures, ETAPrediction
  config.py               # ETA provider selection
```

### Database Changes

- No operational table changes — training data is a generated artifact.
- Optional: a `models/` directory for persisted model artifacts.

### APIs

No new API endpoints — `ETAPredictor` is consumed by the realtime API
(`/transit/realtime/vehicles/{id}/eta`) which was built in Phase 8.

### Services/Components

- `eta/predictor.py`: `LocalETAPredictor` — statistical baseline
- `eta/training.py`: generates synthetic training data from simulation
- `eta/model.py`: trains and loads the predictive model
- `eta/features.py`: extracts features from vehicle/route state

### Dependencies

- Phase 8 (simulation engine — for synthetic data generation and baseline ETA)

### Tests

- Unit: `LocalETAPredictor.predict` returns `None` when no coverage
- Unit: `LocalETAPredictor.predict` returns prediction with confidence
- Unit: training data generation produces expected feature schema
- Unit: model training on synthetic data produces a loadable artifact
- Integration: predictor integrated with vehicle ETA endpoint — when
  predictor available, `predicted_eta_seconds` present in response
- Integration: when predictor unavailable, only `baseline_eta_seconds` present
- Regression: predicted ETA never silently replaces baseline

### Acceptance Criteria

1. `ETAPredictor.predict` with known features returns a prediction or `None`.
2. When no model is loaded, `predict` returns `None` (not a guess).
3. Training data generation runs without errors on seeded data.
4. Model training produces a loadable artifact.
5. The vehicle ETA endpoint returns `baseline_eta_seconds` (always)
   and `predicted_eta_seconds` (only when predictor has coverage).

---

## 16. Phase 13 — Rate Limiting, Security Hardening & Finalization

### Objective

Add rate limiting to sensitive endpoints, perform security hardening,
and finalize the system for deployment.

### Scope

#### Rate Limiting (from `03` §5, `08` §6)

Required on:
- `/auth/login`
- `/auth/register`
- `/tickets/validate`
- `/ai/converse`

Implementation: in-memory sliding window rate limiter (sufficient for
single-instance deployment). Provider-agnostic interface for future
replacement.

```python
class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int): ...
    async def check(self, key: str) -> bool: ...
```

#### Security Checklist (from `03` §5, `08` §6, `10` §4)

- [ ] `SECRET_KEY` from environment, never hardcoded
- [ ] `QR_SIGNING_KEY` from environment, never hardcoded
- [ ] All AI provider credentials from environment, never hardcoded or logged
- [ ] Passwords hashed with bcrypt, never plaintext
- [ ] JWT tokens have expiration
- [ ] Admin endpoints gated by `require_role("admin")`
- [ ] Rate limiting on auth, validation, and converse endpoints
- [ ] No PII beyond command text sent to LLMs
- [ ] Simulated vehicle/trip mutation endpoints authenticated
- [ ] Unauthenticated demo endpoints never exposed publicly
- [ ] CORS configured for frontend origin
- [ ] SQL injection protection via ORM parameterized queries
- [ ] No fabricated transit data anywhere in the system

#### Final API Router Assembly

All sub-routers assembled into the root `api/router.py`:
- `/health` — liveness
- `/transit/*` — stops, routes, geometry, journeys, realtime
- `/ai/*` — converse, health
- `/auth/*` — register, login, me
- `/fares/*` — quote
- `/tickets/*` — purchase, list, validate, revoke
- `/admin/*` — data status, simulation, ticket inspection

### Files/Modules Expected

```
backend/app/core/
  rate_limiter.py          # Rate limiter implementation

backend/app/api/
  router.py                # Root router — all sub-routers assembled
```

### Database Changes

- No schema changes.

### APIs

No new endpoints — rate limiting is added to existing endpoints.

### Services/Components

- `core/rate_limiter.py`: sliding window rate limiter

### Dependencies

- All previous phases (finalization step)

### Tests

- Unit: rate limiter blocks after threshold
- Unit: rate limiter resets after window expires
- Integration: `/auth/login` returns 429 after rate limit exceeded
- Integration: `/tickets/validate` returns 429 after rate limit exceeded
- Integration: `/ai/converse` returns 429 after rate limit exceeded
- Security: all checklist items verified in tests
- Integration: full end-to-end smoke test — journey search → ticket
  purchase → QR validation

### Acceptance Criteria

1. Rate limiting returns HTTP 429 after configured threshold.
2. Rate limiting window resets correctly.
3. All security checklist items pass automated verification.
4. Full end-to-end smoke test passes: journey search → ticket purchase
   → QR validation → ticket shows as USED.
5. All API routers are assembled and documented in OpenAPI schema.

---

## 17. Cross-Phase Contracts

These are the critical interfaces between phases that must remain
stable. Later implementation agents must not independently redefine
these contracts.

### AI Intent JSON → Journey Engine

```
IntentResult (Request #1 output)
    ↓
Validated against JourneySearchRequest schema
    ↓
POST /transit/journeys/search contract
    ↓
JourneySearchResponse (authoritative)
```

- `IntentResult.origin` and `IntentResult.destination` are strings
  passed to `GeospatialService.resolve_location()`
- `IntentResult.objective` maps directly to routing objective enum
- `IntentResult.max_walking_distance_class` maps to `max_walk_m` meters
  (strict=300, moderate=600, relaxed=1000)
- `IntentResult.max_transfers` passes through directly
- `IntentResult.departure_time` passes through as ISO datetime

### Journey Engine → Response LLM

```
JourneySearchResponse (or clarification-needed, or no-route-found)
    ↓
Serialized as JSON
    ↓
JourneyResponseLLMProvider.generate_response(authoritative_json)
    ↓
Natural-language text_response
```

- The authoritative JSON is the **exact same shape** returned by
  `POST /transit/journeys/search`
- Request #2 receives this as its sole input — never raw user text
- Every fact in `text_response` must trace to a value in this JSON

### Routing → Journey API

```
POST /transit/journeys/search
    ↓
JourneySearchEngine.search()
    ↓
JourneySearchResponse
```

- Both the AI pipeline (internally) and direct client calls use this
  same endpoint/contract
- This is architecturally load-bearing: it's what makes "AI cannot
  bypass the deterministic engine" mechanically true

### Simulation → Realtime API

```
SimulatedVehicleLocationProvider
    ↓
GET /transit/realtime/vehicles
GET /transit/realtime/vehicles/{id}
GET /transit/realtime/vehicles/{id}/eta
```

- Every response includes `source: "simulated"` (or `"realtime"` if
  a real feed is ever connected)
- ETA endpoint includes `baseline_eta_seconds` (always) and
  `predicted_eta_seconds` (when ETAPredictor has coverage)

### Realtime → ETA

```
VehiclePosition (current state)
    ↓
ETAFeatures extraction
    ↓
ETAPredictor.predict(features)
    ↓
ETAPrediction | None
```

- Predictor returns `None` when no coverage — never a low-confidence
  guess
- Baseline ETA is always present; predicted ETA is additive

### Journey → Fare

```
Journey.legs (ride legs counted)
    ↓
FaresService.get_fare_quote(ride_leg_count)
    ↓
FareQuote { base_fare, per_leg_fare, total, currency }
```

- Fare is computed server-side from ride_leg_count only
- Client-supplied fare data is never trusted

### Journey → Ticketing

```
JourneySearchResponse.journeys[selected]
    ↓
TicketService.purchase_ticket(user_id, journey_data, ride_leg_count)
    ↓
Ticket { id, status: "ACTIVE", qr_payload }
```

- Journey data is snapshotted in the ticket at purchase time
- Ride leg count determines the fare
- QR payload contains only ticket_id + user_id (signed)

### Authentication → Protected APIs

```
JWT token → get_current_user() → User
    ↓
require_role("admin") → admin-only access
```

- Every protected endpoint uses these same dependencies
- Admin endpoints additionally check `role == "admin"`

### PostGIS → Geospatial Services

```
GeospatialService.resolve_location()
    ↓
Fuzzy match on Stop.name (in-memory)
    ↓ (fallback)
Nominatim geocoding (HTTP)
    ↓
LocationCandidate { stop_id, lat, lon, match_type, confidence }

GeospatialService.nearby_stops()
    ↓
PostGIS ST_DWithin query
    ↓
list[NearbyStop] { stop_id, lat, lon, distance_m }

GeospatialService.walking_distance()
    ↓
OSRM walking profile (HTTP)
    ↓
WalkingResult { distance_m, duration_s }
```

---

## 18. Parallelization Opportunities

### Fully Parallelizable After Phase 5

```
Phase 5 (Routing Engine) complete
    ├── Phase 6 (Auth & Users)        — no dependency on routing internals
    ├── Phase 8 (Realtime/Simulation) — no dependency on auth
    └── Phase 12 (Predictive ETA)     — depends on simulation, can start after Phase 8
```

### Parallelizable Within Phases

**Phase 4 (Geospatial):**
- `nominatim.py` (geocoding) and `nearby.py` (PostGIS queries) can be
  built in parallel
- `osrm.py` (walking distance) can be built in parallel with both

**Phase 9 (AI Pipeline):**
- `speech_to_text.py` (Groq Whisper) can be built in parallel with
  `intent_llm.py` and `response_llm.py`
- `intent_llm.py` and `response_llm.py` can be built in parallel
  (independent interfaces, independent credentials)

**Phase 11 (Admin):**
- Data status endpoints can be built in parallel with simulation
  control endpoints

### Must Remain Sequential

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
(database must exist before models, models before data, data before queries)

Phase 5 → Phase 7 → Phase 9 → Phase 10
(routing must exist before fares, fares before AI wiring)

Phase 10 → Phase 11 → Phase 13
(conversational endpoint before admin panel before finalization)
```

### Parallelization Map

```
Phase 1 ──────────────────────────────────────────────────────────────┐
Phase 2 ──────────────────────────────────────────────────────────────┤
Phase 3 ──────────────────────────────────────────────────────────────┤
Phase 4 ──────────────────────────────────────────────────────────────┤
Phase 5 ──────────────────────────────────────────────────────────────┤
    │                                                                 │
    ├── Phase 6 (Auth) ─────────────────────┐                       │
    │                                        │                       │
    ├── Phase 8 (Simulation) ────────┐      │                       │
    │                                │      │                       │
    │   Phase 12 (ETA) ◄────────────┘      │                       │
    │                                       │                       │
    └── Phase 7 (Fares/Tickets) ◄───────────┘                       │
            │                                                        │
            ├── Phase 9 (AI Providers) ───────────┐                 │
            │                                      │                 │
            └── Phase 10 (Converse Endpoint) ◄─────┘                 │
                    │                                                 │
                    ├── Phase 11 (Admin) ─────────────┐              │
                    │                                  │              │
                    └── Phase 13 (Security/Finalize) ◄─┘              │
                                                                      │
Total sequential critical path: 1→2→3→4→5→7→9→10→11→13              │
Estimated parallel speedup: ~30-40% vs fully sequential               │
─────────────────────────────────────────────────────────────────────┘
```

---

## 19. Risks & Ambiguities

### Architectural Risks

| Risk | Impact | Mitigation |
|---|---|---|
| PostGIS extension not available in deployment | Cannot do spatial queries | Docker Compose includes PostGIS; verify at Phase 1 |
| OSRM public instance rate-limited or unavailable | Cannot compute walking distances or route geometry | Cache aggressively; fallback to haversine; document as data gap |
| Nominatim rate-limited | Location resolution degraded | Cache results; fuzzy-match covers most known stops; geocoding is fallback only |

### External API Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Gemini API key not configured | Request #1 and #2 fail | Fallback to Groq for each; core backend works via direct API |
| Groq API key not configured | Fallback unavailable | Primary Gemini must work; or direct API path remains functional |
| Groq Whisper API key not configured | Voice commands fail | Typed commands unaffected; `/ai/health` reports status |
| Gemini/Groq rate limits exceeded mid-request | Single request fails | Primary→fallback chain handles this; rate limit /ai/converse |
| Gemini/Groq API changes or deprecations | Provider integration breaks | Provider abstraction interface isolates changes; verify at implementation time |

### Data-Quality Risks

| Risk | Impact | Mitigation |
|---|---|---|
| 34 stops without coordinates | Some routes cannot have full geometry | Honest labeling; journeys through these stops may have degraded results |
| No route geometry for any route (0 of 26) | Map rendering incomplete | OSRM road-snap is straightforward once stops are located; geometry generation is a priority task |
| Only 4 of 22 routes have real timetables | Most routes use estimated timing | Labeled as estimates; headway-based estimates documented |
| No real vehicle feed exists | All vehicle positions are simulated | Source always labeled "simulated"; architecture supports swap to real feed |

### Geospatial Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Fuzzy stop-name matching accuracy | Incorrect location resolution | Curated aliases cover known cases; ambiguous results trigger clarification |
| OSRM road-snap produces implausible geometry | Map display looks wrong | Validate generated geometry passes near all input stops; document as OSRM-derived |
| Walking distance from OSRM diverges from actual pedestrian paths | Fare/timing slightly off | Acceptable for initial scope; document limitation |

### AI Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Request #1 produces invalid JSON | Pipeline fails | Schema validation rejects; controlled error returned |
| Request #1 fabricates stops/schedules in intent | Journey engine receives invalid data | Schema validation catches most; journey engine validates against real data |
| Request #2 narrates facts not in authoritative JSON | User receives incorrect information | Groundedness tests verify; prompt instructs narration-only |
| Urdu/Roman Urdu transcription quality with Groq Whisper | Voice commands in Urdu may fail | Must be verified at implementation time; typed Urdu unaffected |
| Prompt injection via user text | LLM may attempt to bypass constraints | Schema validation at AI/backend boundary; tests required |

### Security Risks

| Risk | Impact | Mitigation |
|---|---|---|
| JWT secret key weak or leaked | Token forgery | Use strong random key from environment; never log it |
| QR signing key weak or leaked | Ticket forgery | Use strong random key from environment; HMAC verification |
| Rate limiting bypassed | Abuse of expensive endpoints | In-memory rate limiter; for production use Redis-backed |
| Admin role escalation | Unauthorized data access | Role checked server-side; JWT role cannot be self-modified |
| SQL injection via user input | Database compromise | SQLAlchemy ORM parameterized queries; no raw SQL |

### Performance Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Dijkstra on full transit graph is slow | Journey search latency high | Network is small (26 routes, 122 stops); graph is tiny for Dijkstra |
| Two sequential LLM calls per conversational request | High latency per request | Budget for 2-4s per LLM call; direct API path available as fallback |
| Nominatim/OSRM external calls slow | Location resolution latency | Cache results; fuzzy-match covers most stops without external calls |

### Implementation Ambiguities

| Ambiguity | Resolution | Source |
|---|---|---|
| Exact Nominatim rate-limit policy | Verify at implementation time; default to 1 req/s | `06` §12 |
| Groq Whisper Urdu transcription quality | Must be verified against real audio samples | `06` §4 — DECISION REQUIRED |
| Exact Gemini/Groq free-tier quotas | Verify against live provider documentation | `06` §12 |
| Whether to use httpx or aiohttp for HTTP clients | httpx preferred (sync/async compatible) | Implementation choice |
| Exact walking-distance class thresholds | strict=300m, moderate=600m, relaxed=1000m+ | `06` §6 |
| Whether refresh tokens are needed | FUTURE per `08` §4; not required for initial delivery | `08` §4 |
| Full admin CRUD vs. read-only | Read-only for initial delivery; CRUD is FUTURE | `08` §5, `10` §3 |

---

## 20. Final Implementation Order

### Dependency-Oriented Roadmap

```
Phase 1 — Foundation & Configuration                    [MANDATORY]
   │
   ↓
Phase 2 — Database Models & Migrations                  [MANDATORY]
   │
   ↓
Phase 3 — Transit Data Seeding                          [MANDATORY]
   │
   ↓
Phase 4 — Geospatial Infrastructure (Layer 3)           [MANDATORY]
   │
   ↓
Phase 5 — Deterministic Routing Engine (Layer 4)        [MANDATORY]
   │
   ├──→ Phase 6 — Authentication & Users                [MANDATORY] ←─┐
   │                                                               │
   ├──→ Phase 8 — Realtime & Simulation                  [MANDATORY] ←─┤
   │        │                                                        │
   │        └──→ Phase 12 — Predictive ETA                [P1]        │
   │                                                                │
   └──→ Phase 7 — Fares & Ticketing                     [MANDATORY] ←┘
            │
            ↓
Phase 9 — AI Pipeline                                  [MANDATORY]
   │
   ↓
Phase 10 — Conversational Endpoint Wiring               [MANDATORY]
   │
   ↓
Phase 11 — Admin APIs & Health Panel                   [MANDATORY]
   │
   ↓
Phase 13 — Rate Limiting, Security & Finalization       [MANDATORY]
```

### Phase Classification

| Phase | Classification | Requires External Credentials | Requires PostGIS | Requires Transit Data | Requires Network |
|---|---|---|---|---|---|
| 1 — Foundation | MANDATORY | No | Yes (Docker) | No | No |
| 2 — Models | MANDATORY | No | Yes | No | No |
| 3 — Seeding | MANDATORY | No | Yes | Yes | No |
| 4 — Geospatial | MANDATORY | No | Yes | Yes | Yes (Nominatim, OSRM) |
| 5 — Routing | MANDATORY | No | Yes | Yes | No |
| 6 — Auth | MANDATORY | No | No | No | No |
| 7 — Fares/Tickets | MANDATORY | No | No | No | No |
| 8 — Simulation | MANDATORY | No | No | Yes | No |
| 9 — AI Pipeline | MANDATORY | Yes (Gemini, Groq) | No | No | Yes |
| 10 — Converse | MANDATORY | Yes (Gemini, Groq, Whisper) | No | No | Yes |
| 11 — Admin | MANDATORY | No | No | No | No |
| 12 — Predictive ETA | P1 | No | No | Yes | No |
| 13 — Security | MANDATORY | No | No | No | No |

### What Can Run Without External Credentials

Phases 1-8, 11-13 are fully functional without any AI provider
credentials. The core backend (`POST /transit/journeys/search`,
simulation, ticketing, auth) works entirely on local data. This is a
deliberate resilience property.

### What Requires Real Transit Data

Phases 3, 4, 5, 8, 12 all depend on the seeded transit dataset
(Phase 3). Without it, the backend has no stops, routes, or timetables
to work with.

### What Requires External Network Access

- Phase 4: Nominatim geocoding and OSRM walking distance (can be
  mocked for testing)
- Phase 9-10: Gemini, Groq, Groq Whisper API calls (can use mock
  providers for development)

---

## 21. Definition of Done

The backend is considered complete when ALL of the following are true:

### APIs Implemented

- [ ] `GET /health` — liveness probe
- [ ] `POST /transit/journeys/search` — direct structured journey search
- [ ] `GET /transit/stops` — list stops
- [ ] `GET /transit/stops/{id}` — stop details with routes
- [ ] `GET /transit/routes` — list routes
- [ ] `GET /transit/routes/{id}` — route details
- [ ] `GET /transit/routes/{id}/geometry` — route GeoJSON geometry
- [ ] `GET /transit/realtime/vehicles` — all active vehicle positions
- [ ] `GET /transit/realtime/vehicles/{id}` — single vehicle position
- [ ] `GET /transit/realtime/vehicles/{id}/eta` — vehicle ETA
- [ ] `POST /ai/converse` — conversational journey planning
- [ ] `GET /ai/health` — AI provider status
- [ ] `POST /auth/register` — user registration
- [ ] `POST /auth/login` — user login
- [ ] `GET /auth/me` — current user profile
- [ ] `POST /fares/quote` — fare quote
- [ ] `POST /tickets` — purchase ticket
- [ ] `GET /tickets` — list user's tickets
- [ ] `GET /tickets/{id}` — ticket details
- [ ] `POST /tickets/{id}/revoke` — revoke ticket
- [ ] `POST /tickets/validate` — validate QR ticket
- [ ] `GET /admin/data/status` — data quality overview
- [ ] `GET /admin/simulation/status` — simulation status
- [ ] `GET /admin/tickets` — ticket inspection
- [ ] `POST /admin/seed/run` — trigger data import
- [ ] `POST /admin/simulation/start` — start simulation
- [ ] `POST /admin/simulation/stop` — stop simulation

### Database Complete

- [ ] All 11 tables created via Alembic migration
- [ ] Spatial indexes (GiST) on `stops.location` and `routes.path`
- [ ] B-tree indexes on all foreign keys
- [ ] Unique constraints enforced
- [ ] Seed data imported (agencies, routes, stops, timetables, fares)

### Geospatial Functionality Complete

- [ ] Location resolution (fuzzy match + Nominatim fallback)
- [ ] Nearby stops (PostGIS ST_DWithin)
- [ ] Walking distance (OSRM)
- [ ] Route geometry retrieval (GeoJSON)
- [ ] Ambiguity detection and clarification

### Journey Planning Complete

- [ ] Transit graph construction
- [ ] Dijkstra pathfinding with 3 objectives
- [ ] Multi-candidate ranked responses (up to 3)
- [ ] Filter support (max_walk_m, max_transfers)
- [ ] Time-dependent routing for scheduled routes
- [ ] Fare annotation on all candidates

### Realtime/Simulation Complete

- [ ] `compute_position_at` — pure, deterministic
- [ ] Position interpolation along route geometry
- [ ] Position interpolation without geometry (straight-line)
- [ ] Bearing and speed computation
- [ ] `VehicleLocationProvider` protocol implemented
- [ ] `source: "simulated"` always present

### ETA Complete

- [ ] Baseline ETA always present
- [ ] Predictive ETA available when ETAPredictor has coverage
- [ ] Both values returned together in ETA response

### Predictive ETA Complete (P1)

- [ ] ETAPredictor interface implemented
- [ ] Synthetic training data generation
- [ ] Statistical/lightweight ML model trained
- [ ] Model serves predictions via ETAPredictor

### Authentication Complete

- [ ] Registration with bcrypt password hashing
- [ ] Login returns JWT
- [ ] `/auth/me` returns user profile
- [ ] JWT expiration enforced
- [ ] Two roles: passenger, admin
- [ ] `require_role("admin")` dependency

### User Accounts Complete

- [ ] User model with email, hashed_password, role
- [ ] Ticket ownership enforced server-side
- [ ] Ticket list scoped to authenticated user

### Admin APIs Complete

- [ ] Data quality view (stop/route coverage)
- [ ] Simulation status view
- [ ] Ticket inspection (list/lookup)
- [ ] AI/ETA pipeline health panel
- [ ] Seed/import trigger endpoint
- [ ] Simulation start/stop endpoints

### Fares Complete

- [ ] DB-driven fare rules
- [ ] Server-authoritative pricing (base_fare + per_leg_fare x (legs-1))
- [ ] 0 fare for all-walking journeys
- [ ] Never trust client-supplied fare

### Ticketing Complete

- [ ] Ticket purchase flow (fare → payment → QR → persist)
- [ ] QR payload is signed, opaque (ticket_id + user_id only)
- [ ] Ticket validation is atomic (no double-use)
- [ ] Ticket lifecycle: ACTIVE → USED | EXPIRED | REVOKED
- [ ] Lazy expiry at read/validate time
- [ ] PaymentProvider interface with MockPaymentProvider

### AI Request #1 Complete

- [ ] IntentLLMProvider interface
- [ ] Gemini primary implementation
- [ ] Groq fallback implementation
- [ ] Primary→fallback chain with controlled error
- [ ] Schema validation of output
- [ ] Ambiguous fields signal clarification needed
- [ ] Separate credential pair from Request #2

### AI Request #2 Complete

- [ ] JourneyResponseLLMProvider interface
- [ ] Gemini primary implementation
- [ ] Groq fallback implementation
- [ ] Primary→fallback chain with controlled error
- [ ] Input is authoritative JSON only
- [ ] Narration-only instructions in prompt
- [ ] Separate credential pair from Request #1

### Groq Whisper Complete

- [ ] SpeechToTextProvider interface
- [ ] Groq Whisper implementation
- [ ] Transcription handed to Request #1 unchanged
- [ ] Transcription failure returns controlled error

### Security Complete

- [ ] Rate limiting on /auth/login, /tickets/validate, /ai/converse
- [ ] JWT secret from environment
- [ ] QR signing key from environment
- [ ] All AI credentials from environment
- [ ] No hardcoded secrets
- [ ] Admin endpoints gated by role
- [ ] SQL injection protection (ORM)
- [ ] CORS configured

### Tests Passing

- [ ] Unit tests for all modules
- [ ] Integration tests against live PostGIS
- [ ] Database tests (migration, idempotency)
- [ ] API tests for all endpoints
- [ ] Provider tests (fallback chains)
- [ ] Security tests (auth, rate limiting, injection)
- [ ] Geospatial tests (PostGIS, fuzzy matching)
- [ ] AI groundedness tests (Request #2 narration)
- [ ] Concurrent ticket validation test
- [ ] End-to-end smoke test (search → ticket → validate)

### Documentation Complete

- [ ] OpenAPI schema auto-generated and accurate
- [ ] `.env.example` documents all required variables
- [ ] README with setup instructions
- [ ] Data provenance documented in seed data

### Docker/Deployment Complete

- [ ] Docker Compose for local development (PostgreSQL + PostGIS)
- [ ] Application starts with `docker-compose up`
- [ ] All environment variables configurable via `.env`
- [ ] No runtime dependency on implementation tooling
