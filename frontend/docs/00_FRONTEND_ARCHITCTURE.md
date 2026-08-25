# Karwan-e-Khizr Frontend Plan

## 1. Frontend Mission

Build a polished, production-quality transit navigation frontend for **Karwan-e-Khizr**, inspired by modern transit applications such as DB Navigator, Transit, and eTransit.

The frontend must initially focus on:

* Excellent visual design
* Reliable MapLibre integration
* Transit-oriented map UI
* Clear navigation flows
* Responsive interactions
* Reusable components
* Clean React Native + Expo + TypeScript architecture

**Important:** This document covers **frontend only**.

No backend implementation, database design, API implementation, telemetry processing, routing algorithms, ML, or server infrastructure belongs in this plan.

---

# 2. Technology Stack

## Core

* React Native
* Expo
* TypeScript

## Mapping

* MapLibre
* MapLibre-compatible map style
* Vector/raster tile source compatible with the selected MapLibre setup

## Navigation

* React Navigation or Expo Router, depending on the existing project architecture
* Native navigation transitions where appropriate

## Styling

Use a centralized design system rather than scattered inline styling.

Recommended structure:

```text
src/
├── components/
├── screens/
├── navigation/
├── map/
├── theme/
├── assets/
├── hooks/
├── types/
├── utils/
└── constants/
```

The exact folder structure may be adjusted to match the existing project, but the separation of concerns must remain.

---

# 3. Design Direction

## Visual Identity

Karwan-e-Khizr should feel like a **modern public-transit application**, not a generic CRUD application wearing a map as a hat.

Design characteristics:

* Clean
* Minimal
* Highly legible
* Transit-focused
* Professional
* Modern
* Information-dense without being cluttered
* Strong hierarchy
* Smooth animations
* Clear touch targets

Avoid:

* Excessive gradients
* Giant cards everywhere
* Random rounded rectangles
* Excessive shadows
* Tiny text
* Unnecessary decorative elements
* Generic dashboard layouts
* AI-generated "startup SaaS" aesthetics

---

# 4. Design System

Create a centralized theme.

## 4.1 Colors

Define semantic colors rather than hard-coding colors throughout the application.

Example:

```ts
colors = {
  background,
  surface,
  surfaceElevated,

  textPrimary,
  textSecondary,
  textMuted,

  primary,
  primaryDark,
  primaryLight,

  success,
  warning,
  error,

  border,

  mapBackground,
  routePrimary,
  routeSecondary,
  busMarker,
  stopMarker,
}
```

The exact palette should be decided during UI implementation.

---

# 5. Typography

Create a typography system.

Example:

```text
display
headingLarge
headingMedium
headingSmall

bodyLarge
bodyMedium
bodySmall

labelLarge
labelMedium
labelSmall

caption
```

Typography should prioritize:

1. Readability
2. Hierarchy
3. Transit information visibility

The interface should remain readable outdoors and on smaller screens.

---

# 6. Spacing System

Use a consistent spacing scale.

Example:

```text
4
8
12
16
20
24
32
40
48
```

Components should not randomly use values such as:

```text
13px
17px
23px
29px
```

unless there is a deliberate design reason.

---

# 7. Component Architecture

Create reusable UI components.

## Core Components

```text
Button
IconButton
TextInput
SearchBar
Card
BottomSheet
Chip
Badge
Divider
LoadingIndicator
ErrorState
EmptyState
Modal
Toast
```

## Transit Components

```text
TransitLineBadge
BusCard
StopCard
RouteCard
RouteStep
JourneyCard
TransferCard
WalkingSegment
ArrivalTime
DelayBadge
VehicleMarker
StopMarker
RoutePolyline
```

## Map Components

```text
MapView
MapControls
UserLocationButton
ZoomControls
MapSearchOverlay
MapRouteLayer
BusLayer
StopLayer
SelectedRouteLayer
```

Components should receive data through typed props rather than directly depending on application state wherever possible.

---

# 8. Application Structure

The frontend should have clear primary navigation.

Recommended primary experience:

```text
                App
                 │
        ┌────────┼────────┐
        │        │        │
       Map     Search    Saved
        │
    Journey
     Planner
```

Potential bottom navigation:

```text
┌──────────┬──────────┬──────────┬──────────┐
│   Map    │ Journey  │  Saved   │ Settings │
└──────────┴──────────┴──────────┴──────────┘
```

The exact navigation can be finalized during UI implementation.

---

# 9. Screen 1: Map / Home

This is the primary screen.

The map should dominate the interface.

## Layout

```text
┌──────────────────────────────────────┐
│ Search destination...          ⚙     │
│                                      │
│                                      │
│              MAP                     │
│                                      │
│       ● Bus                          │
│                 ━━━━━ Route          │
│                                      │
│                         ⊕            │
│                                      │
│                         ◎            │
│                                      │
├──────────────────────────────────────┤
│        Nearby / journey information  │
├──────────┬──────────┬──────────┬─────┤
│   Map    │ Journey  │  Saved   │ More│
└──────────┴──────────┴──────────┴─────┘
```

## Required behavior

* Map loads immediately
* Camera starts at a sensible default location
* User can pan
* User can zoom
* User can rotate if supported
* User can return to current location
* Search remains accessible
* Transit overlays can be toggled
* Map controls remain accessible without covering important map content

---

# 10. MapLibre Baseline

This is the **first major frontend milestone**.

Before building complex transit UI, MapLibre must successfully display a real basemap.

## Requirements

The map must display:

* Roads
* Streets
* Geographic features
* Labels
* Relevant landmarks
* Correct geographic positioning
* Zoom levels
* Panning

## Critical distinction

User location permission is **not required** for the basemap.

The application should first prove:

```text
MapLibre
   ↓
Map Style
   ↓
Tile Source
   ↓
Rendered Basemap
```

Only after this works should user-location functionality be added.

---

# 11. Map Camera

Implement camera management.

Required states:

```text
Default location
User location
Selected stop
Selected bus
Selected route
Journey overview
```

Example interactions:

### Selecting a stop

```text
Tap Stop
   ↓
Camera moves toward stop
   ↓
Stop marker becomes selected
   ↓
Bottom sheet appears
```

### Selecting a bus

```text
Tap Bus
   ↓
Camera centers on bus
   ↓
Bus marker becomes selected
   ↓
Vehicle information appears
```

---

# 12. Map Controls

Controls should include:

### Location

```text
◎
```

Centers the map on the user's current location.

### Optional zoom

```text
+
−
```

Only use explicit zoom controls if the platform interaction doesn't already make zooming obvious.

### Layers

Allow users to toggle relevant transit overlays.

Example:

```text
Map
Transit
Stops
Buses
```

---

# 13. Search Interface

Search is one of the most important frontend interactions.

## Search Bar

Placeholder:

```text
Where do you want to go?
```

Possible states:

```text
Idle
Focused
Typing
Results
Selected
```

## Search results

Results may eventually contain:

```text
📍 Place
🚏 Stop
🚌 Station
```

Each result should clearly identify its type.

---

# 14. Journey Planner

The journey planner should have a dedicated interface.

## Origin / Destination

```text
┌─────────────────────────────┐
│ 📍 Current location         │
├─────────────────────────────┤
│ ↓                           │
├─────────────────────────────┤
│ 🔎 Destination              │
└─────────────────────────────┘
```

Include a swap button:

```text
      ⇅
```

---

# 15. Journey Search Screen

After entering origin and destination:

```text
From
Current Location

To
G-9 Markaz

        [Find journeys]
```

The frontend should then display journey options.

At this stage, the frontend may use **mock/static data**.

No backend is required for UI development.

---

# 16. Journey Results

Results should prioritize useful information.

Example:

```text
┌─────────────────────────────────┐
│ 18 min                           │
│ 🚌  101                          │
│    2 transfers                   │
│                                  │
│ Depart 8:42 PM                   │
│ Arrive 9:00 PM                   │
│                                  │
│ Walk 3 min                       │
└─────────────────────────────────┘
```

Alternative journeys:

```text
Fastest
Fewest transfers
Least walking
Most reliable
```

These can initially be frontend-only categories using mock data.

---

# 17. Journey Details

Selecting a journey opens a detailed journey view.

Example:

```text
CURRENT LOCATION
       │
       │ 🚶 3 min
       ▼
STOP A
       │
       │ 🚌 Route 101
       │ 8 min
       ▼
STOP B
       │
       │ 🚶 2 min
       ▼
DESTINATION
```

Each segment should be visually distinguishable.

---

# 18. Route Visualization

When a journey is selected:

```text
Map
 │
 ├── selected route
 ├── alternative routes
 ├── walking segments
 ├── stops
 └── vehicles
```

The selected route should have the strongest visual emphasis.

Alternative routes should be visually subordinate.

---

# 19. Transit Route Screen

Selecting a bus route should open a route overview.

Example:

```text
Route 101

● Stop A
│
│
● Stop B
│
│
● Stop C
│
│
● Stop D
```

Information:

* Route name
* Direction
* Stops
* Estimated journey time
* Service information
* Current vehicles when available

---

# 20. Stop Screen

Selecting a stop opens a stop detail interface.

Example:

```text
G-10 Stop

🚌 101     4 min
🚌 102     9 min
🚌 105    16 min
```

Sections:

```text
Arrivals
Routes
Location
```

Initially, arrival information can be mocked.

---

# 21. Vehicle Screen

Selecting a live bus marker should open a vehicle card.

Example:

```text
Bus 1047

Route 101
Towards Saddar

● On route

Current location
G-9

Next stop
G-10

Estimated arrival
3 min
```

The UI should be prepared for real-time updates later.

---

# 22. Bus Markers

Bus markers must be visually distinct from ordinary map points.

Requirements:

* Clearly recognizable as buses
* Small enough not to obstruct the map
* Selected state
* Unselected state
* Optional direction indicator
* Optional movement animation

Example:

```text
        🚌
```

The final marker should use a proper vector/icon asset rather than relying on emoji.

Because apparently emojis are not a serious cartographic rendering system. Humanity narrowly avoided disaster.

---

# 23. Stop Markers

Stops should use a separate visual language.

States:

```text
Normal
Selected
Nearby
Served by selected route
```

Selected stop:

```text
      ◉
```

Normal stop:

```text
      •
```

Exact design should follow the final map style.

---

# 24. Route Lines

Routes should be rendered as map overlays.

Required states:

```text
Normal route
Selected route
Alternative route
Inactive route
```

The selected route must visually dominate.

Route lines should remain readable against the basemap.

---

# 25. Bottom Sheets

Bottom sheets will be heavily used.

Examples:

```text
Stop details
Bus details
Journey results
Route information
Search results
```

States:

```text
Collapsed
Half-expanded
Expanded
```

They should support smooth gestures and transitions.

---

# 26. Loading States

Every major frontend operation needs a deliberate loading state.

Examples:

```text
Map loading
Search loading
Journey calculation
Route loading
Stop information loading
```

Avoid blank screens.

Use:

* Skeletons
* Subtle spinners
* Placeholder cards
* Map loading indicators

---

# 27. Error States

Errors must be designed rather than dumped directly onto the user.

Bad:

```text
TypeError: Cannot read properties of undefined
```

Good:

```text
Something went wrong

We couldn't load this information.

[Try again]
```

Developer details should remain available through development logs, not the primary UI.

---

# 28. Empty States

Examples:

### No journeys

```text
No journeys found

Try a different destination or
adjust your search.
```

### No nearby buses

```text
No buses nearby

Check again later.
```

### No saved routes

```text
No saved journeys yet.
```

---

# 29. Animations

Animations should communicate state changes rather than exist merely because someone's laptop has a GPU.

Recommended:

* Bottom-sheet transitions
* Marker selection
* Route selection
* Search transitions
* Navigation transitions
* Loading transitions
* Vehicle movement where applicable

Animations should be:

* Short
* Smooth
* Interruptible
* Purposeful

---

# 30. Responsive Design

The frontend should account for:

* Small phones
* Large phones
* Different aspect ratios
* Android navigation areas
* Safe areas
* Dynamic text sizes

Avoid fixed layouts that only work on the developer's device.

---

# 31. Accessibility

Implement:

* Adequate touch targets
* Accessible labels
* Sufficient text contrast
* Screen-reader-friendly controls
* Clear state communication
* Avoiding color as the only indicator

For example, a delayed route should not be represented solely by color.

Use:

```text
⚠ Delayed
```

alongside visual styling.

---

# 32. Urdu Localization

The frontend should be architected for localization from the beginning.

Do **not** hard-code every user-facing string.

Instead:

```ts
t("journey.findJourney")
t("map.currentLocation")
t("route.nextStop")
```

Initial languages:

```text
English
Urdu
```

Urdu support should account for:

* RTL layout
* Text direction
* Typography
* Number formatting
* Navigation labels
* Transit terminology

---

# 33. Mock Data Layer

Before the backend exists, the frontend must be fully testable using local mock data.

Create typed mock objects for:

```text
Bus
Stop
Route
Journey
JourneySegment
Arrival
Location
```

Example:

```ts
type Bus = {
  id: string;
  routeId: string;
  latitude: number;
  longitude: number;
  heading: number;
  status: "active" | "delayed" | "inactive";
};
```

The frontend should be able to operate against mock data without requiring a server.

---

# 34. Frontend State Management

Separate:

### UI state

Examples:

```text
selectedBus
selectedStop
selectedRoute
bottomSheetState
searchQuery
activeTab
```

from:

### Domain data

Examples:

```text
buses
routes
stops
journeys
```

Avoid creating a giant global state object containing literally everything.

That road leads directly to architectural regret.

---

# 35. API Boundary

Even though backend implementation is explicitly outside this plan, the frontend should establish clean interfaces for future data.

For example:

```ts
TransitService
```

with conceptual operations:

```ts
getRoutes()
getStops()
getVehicles()
getJourney()
getArrivals()
```

During frontend development these functions return mock data.

Later, the implementation can be replaced with real API calls without rewriting every screen.

---

# 36. Frontend Performance

Pay particular attention to the map.

Requirements:

* Avoid unnecessary map re-renders
* Avoid recreating large datasets unnecessarily
* Use memoized components where useful
* Keep marker rendering efficient
* Avoid rendering hundreds of React components over the map unnecessarily
* Prefer native/map-layer rendering where appropriate
* Keep animations lightweight

The frontend must remain usable on mid-range Android devices.

---

# 37. Map Performance Strategy

Do not treat every bus as an ordinary React component if hundreds of vehicles eventually exist.

Prefer:

```text
MapLibre Source
       ↓
Layer
       ↓
Vehicle features
```

rather than:

```text
React
 ├── Bus
 ├── Bus
 ├── Bus
 ├── Bus
 ├── Bus
 └── ...
```

This becomes especially important once live telemetry exists.

---

# 38. Development Milestones

## Milestone 1: Foundation

* [ ] Clean frontend architecture
* [ ] TypeScript configuration
* [ ] Theme system
* [ ] Typography system
* [ ] Spacing system
* [ ] Navigation skeleton
* [ ] Reusable component foundation

---

## Milestone 2: MapLibre Proof

* [ ] MapLibre successfully renders
* [ ] Real basemap visible
* [ ] Roads visible
* [ ] Labels visible
* [ ] Panning works
* [ ] Zooming works
* [ ] Camera works
* [ ] No GPS permission required for basemap
* [ ] No server dependency

**This milestone must be completed before building advanced map features.**

---

## Milestone 3: Home Map UI

* [ ] Search bar
* [ ] Map controls
* [ ] Bottom navigation
* [ ] User-location button
* [ ] Transit overlay controls
* [ ] Proper safe-area handling
* [ ] Loading state
* [ ] Error state

---

## Milestone 4: Transit Visualization

* [ ] Mock bus markers
* [ ] Mock stop markers
* [ ] Route polylines
* [ ] Selected bus state
* [ ] Selected stop state
* [ ] Selected route state
* [ ] Vehicle information sheet
* [ ] Stop information sheet

---

## Milestone 5: Journey Planner

* [ ] Search screen
* [ ] Origin selection
* [ ] Destination selection
* [ ] Swap locations
* [ ] Journey results
* [ ] Journey cards
* [ ] Journey details
* [ ] Route visualization
* [ ] Walking segments
* [ ] Transfers

---

## Milestone 6: Transit Information

* [ ] Route screen
* [ ] Stop screen
* [ ] Arrival board
* [ ] Vehicle screen
* [ ] Service status
* [ ] Route directions

---

## Milestone 7: Polish

* [ ] Animations
* [ ] Skeleton loaders
* [ ] Error states
* [ ] Empty states
* [ ] Accessibility
* [ ] Responsive layouts
* [ ] Performance optimization
* [ ] Urdu localization
* [ ] RTL support

---

# 39. Definition of Done

The frontend should be considered successful when a user can:

```text
Open Karwan-e-Khizr
        ↓
See a real map
        ↓
Pan/zoom around the map
        ↓
Search for a destination
        ↓
Select a journey
        ↓
See available journey options
        ↓
Open journey details
        ↓
See the journey visually on the map
        ↓
Inspect stops/routes/buses
        ↓
Navigate through the application naturally
```

Even when using mock data, this complete experience must feel like a **real transit application**.

---

# 40. What Is Explicitly NOT Included

This frontend plan does **not** implement:

* FastAPI
* PostgreSQL
* PostGIS
* MQTT
* GPS ingestion
* ESP32 integration
* Telemetry processing
* Backend routing
* ML models
* ETA prediction
* Delay prediction
* Historical analytics
* Authentication backend
* Server deployment
* Database migrations

The frontend only defines the interfaces and visual states necessary to eventually consume those systems.

---

# 41. Final Frontend Architecture

The intended architecture should ultimately resemble:

```text
                    KARWAN-E-KHIZR
                           │
                    React Native
                           │
              ┌────────────┴────────────┐
              │                         │
          Navigation                 Theme
              │                         │
       ┌──────┴──────┐                  │
       │             │                  │
     Screens      Components            │
       │             │                  │
       └──────┬──────┘                  │
              │                         │
        Frontend State                  │
              │                         │
       ┌──────┴───────────┐             │
       │                  │             │
   Transit Data       UI State          │
       │                  │             │
       └─────────┬────────┘             │
                 │                      │
           Transit Service              │
                 │                      │
        ┌────────┴─────────┐            │
        │                  │            │
     Mock Data         Future API       │
        │                  │            │
        └──────────────────┘            │
                                        │
                  ┌─────────────────────┘
                  │
              MapLibre
                  │
          ┌───────┴────────┐
          │                │
       Basemap        Transit Layers
          │                │
      Streets          Buses
      Roads            Stops
      Labels           Routes
                       Journey
```

## The governing principle

**Build the frontend as if the backend already exists, while using mock data until it actually does.**

That lets us develop the entire user experience independently, prevents backend/frontend coupling, and most importantly means we can stop blaming the database whenever a button is ugly. 🚌
