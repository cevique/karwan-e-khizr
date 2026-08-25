# Karwan-e-Khizr Frontend ↔ Backend Integration

## 1. Purpose

Connect the completed frontend prototype to the existing backend without changing the established UI architecture.

The frontend must transition from:

```text
UI → Mock Data
```

to:

```text
UI → Transit Service → FastAPI → PostgreSQL/PostGIS
```

The frontend remains responsible for presentation and interaction. The backend remains responsible for real transit data and business logic.

---

## 2. Integration Rules

* Read `AGENTS.md` and existing backend documentation before making changes.
* Inspect the existing backend implementation before creating new endpoints.
* Do not invent API endpoints or response schemas when an existing backend implementation already provides them.
* Keep API communication behind a dedicated frontend service/data layer.
* Components must not directly perform arbitrary API requests.
* Keep TypeScript types aligned with backend response models.
* Preserve the existing mobile/web architecture and visual design.
* Do not rewrite working frontend components merely to connect data.
* Keep mock data available as a development fallback where practical.
* Do not implement routing intelligence, ETA prediction, ML, or telemetry ingestion in this phase.

---

## 3. Frontend Data Boundary

Use a service abstraction between UI and backend.

Conceptually:

```text
Screens / Components
        ↓
Hooks / State
        ↓
TransitService
        ↓
API Client
        ↓
FastAPI
```

The UI should depend on typed domain models rather than raw API responses.

Primary domain models:

* Route
* Stop
* Vehicle
* Journey
* JourneySegment
* Arrival
* Location

---

## 4. API Integration

Create or adapt a centralized API client responsible for:

* Base URL configuration
* HTTP requests
* Serialization/deserialization
* Authentication handling if required later
* Request cancellation where appropriate
* Consistent error handling

The service layer should expose operations conceptually similar to:

```text
getRoutes()
getRoute(id)
getStops()
getStop(id)
getVehicles()
getVehicle(id)
getRouteVehicles(routeId)
getArrivals(stopId)
searchJourneys(origin, destination)
```

Use the actual backend contract once inspected.

Do not duplicate API calls throughout screens.

---

## 5. Mock → Real Data

Existing mock services/data should be replaced progressively, not removed blindly.

Migration order:

```text
Static routes/stops
        ↓
Vehicle data
        ↓
Arrivals
        ↓
Journey results
        ↓
Journey details
```

The UI should continue functioning if a request fails.

Loading, error, and empty states must remain intentional and user-friendly.

---

## 6. MapLibre Data Flow

MapLibre should consume backend-derived transit data through the same service/state architecture.

```text
FastAPI
   ↓
Vehicles / Stops / Routes
   ↓
Frontend State
   ↓
MapLibre Sources/Layers
   ↓
Markers / Routes / Selected Objects
```

Do not fetch directly from MapLibre components.

Use map-layer/source rendering where appropriate rather than creating unnecessary React components for large numbers of vehicles.

The existing working basemap must not be broken while adding backend data.

---

## 7. Realtime Boundary

Realtime telemetry is a separate concern from ordinary REST data.

Initial integration should establish the architecture for:

```text
Backend realtime source
        ↓
Frontend realtime service
        ↓
Transit state
        ↓
MapLibre / UI
```

Do not implement MQTT ingestion or telemetry processing inside the frontend.

Use mock/replay data if realtime backend infrastructure is not yet available.

---

## 8. Journey Planning

The frontend should send journey-search parameters to the backend and render the returned journey model.

```text
Origin + Destination
        ↓
Frontend service
        ↓
Backend journey endpoint
        ↓
Journey results
        ↓
Journey cards
        ↓
Journey details + MapLibre
```

The frontend must not contain the routing algorithm.

It only presents the backend's results.

---

## 9. Configuration

Backend URLs and environment-specific configuration must not be hardcoded throughout the application.

Use a single configuration source for:

* Development API URL
* Production API URL
* Realtime endpoint when introduced
* Other environment-specific settings

Do not commit secrets.

---

## 10. Error Handling

Handle at minimum:

* Network failure
* Backend unavailable
* Timeout
* Invalid response
* Empty result
* Server error

Never expose raw backend exceptions or stack traces to users.

Development logs may contain technical details.

---

## 11. Scope

### Included

* Frontend API client
* Transit service layer
* Typed API/domain models
* Mock → real data migration
* Route/stop/vehicle retrieval
* Journey API integration
* MapLibre transit data integration
* Loading/error/empty handling
* Realtime integration boundary

### Not Included

* Database redesign
* Backend routing algorithms
* MQTT ingestion
* GPS processing
* ETA prediction
* ML
* Historical analytics
* Authentication system
* Deployment infrastructure

---

## 12. Definition of Done

The integration is complete when:

* Frontend runs independently against the configured backend.
* Routes and stops come from the backend.
* Vehicles can be displayed from backend data.
* Journey searches use backend results.
* Journey details render correctly.
* MapLibre displays backend-provided transit data.
* API failures produce proper UI states.
* Mobile and web layouts remain intact.
* No backend logic is duplicated in the frontend.
* Mock data can still be used for development where backend functionality is unavailable.
* TypeScript, lint, and build checks pass.

**Principle:**

> The frontend consumes transit data. The backend owns transit logic.
