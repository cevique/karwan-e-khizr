# Karwan-e-Khizr — UI/UX Design System

## 1. Design Philosophy

Karwan-e-Khizr should feel like it sits between two references:

* **Apple** — restraint, clarity, physicality of motion, generous whitespace, content-first hierarchy.
* **Uber** — confidence, map-as-hero, bold single-purpose actions, no ambiguity about what to tap next.

The result should never look like a dashboard, a form builder, or a generic "startup SaaS" template. Every screen should read as **one thing at a time, done clearly** — a map, a journey, a stop, an arrival.

Guiding rules:

* The map is the app. UI floats on top of it; it never competes with it.
* One primary action per screen. Everything else is secondary or tertiary.
* Motion explains state changes — it is never decoration.
* Silence (whitespace, restraint) is a design tool, not empty space to fill.

---

## 2. Theming Model

The app is **adaptive** — it follows the system color scheme (light/dark) rather than forcing one mode.

* Both palettes are first-class, designed independently, not just inverted.
* Dark mode is not "black backgrounds with the same colors" — surfaces, elevation, and accent saturation are re-tuned per mode, the way Apple's system apps do it.
* Map style switches with the theme (light basemap in light mode, dark/muted basemap in dark mode).
* No user-facing toggle is required in v1; theme follows `useColorScheme()`.

---

## 3. Color System

### 3.1 Accent roles

* **Primary accent — Green.** Live/active transit meaning: current location, active journey, live vehicle tracking, primary CTAs ("Find journeys", "Start", confirmations). Green is the color of *movement and availability*.
* **Secondary accent — Navy Blue.** Structural and selection meaning: selected states, links, informational badges, map route lines when not "live," headers/branding moments. Navy is the color of *information and structure*, not action.
* Green and Navy are never used interchangeably — if both could apply, ask "is this live/actionable (green) or informational/structural (navy)?"

### 3.2 Semantic tokens (per theme)

```ts
colors = {
  // Surfaces
  background,
  surface,
  surfaceElevated,
  surfaceOverlay,        // bottom sheets, modals over the map

  // Text
  textPrimary,
  textSecondary,
  textMuted,
  textInverse,           // text on top of accent-filled surfaces

  // Brand / accent
  accentPrimary,         // green
  accentPrimaryMuted,
  accentSecondary,       // navy
  accentSecondaryMuted,

  // Feedback
  success,                // may reuse accentPrimary
  warning,
  error,

  // Structure
  border,
  divider,
  hairline,

  // Map
  mapBackground,
  routeSelected,          // green
  routeAlternative,       // navy, reduced opacity
  routeInactive,          // neutral gray
  busMarker,               // green
  busMarkerDelayed,        // warning tone
  stopMarker,               // navy
  stopMarkerSelected,       // green
}
```

### 3.3 Behavior in dark mode

* True black (`#000000`) is reserved for the base `background` — full-bleed map screens can go edge-to-edge black, matching OLED-friendly Apple conventions.
* `surface` and `surfaceElevated` use dark navy-tinted grays (not pure gray) so the navy accent feels native to the palette rather than bolted on.
* Green is desaturated slightly in dark mode to avoid neon/glow artifacts against black.

---

## 4. Typography

**Typeface: Inter**, used across both platforms for consistency and legibility at small sizes (critical for arrival times, stop names, transit codes).

```text
display        34 / 41   Bold      — onboarding, empty states
headingLarge   28 / 34   Semibold  — screen titles
headingMedium  22 / 28   Semibold  — section headers, journey card totals
headingSmall   17 / 22   Semibold  — card titles, stop names

bodyLarge      17 / 24   Regular   — primary reading text
bodyMedium     15 / 20   Regular   — secondary reading text
bodySmall      13 / 18   Regular   — metadata, timestamps

labelLarge     15 / 20   Medium    — buttons, tabs
labelMedium    13 / 16   Medium    — badges, chips
labelSmall     11 / 14   Medium    — micro-labels (delay tags, units)

caption        11 / 14   Regular   — fine print, disclaimers
```

Rules:

* Numerals (arrival times, minutes, route numbers) use **tabular figures** so they don't jitter as live data updates.
* Minimum on-map/on-card text size is `bodySmall` (13pt) — nothing smaller, for outdoor legibility.
* Route numbers and critical transit codes use `headingSmall` or larger even inside compact components (e.g., `TransitLineBadge`).

---

## 5. Spacing, Radius & Elevation

### 5.1 Spacing scale (unchanged from architecture doc)

`4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48`

### 5.2 Corner radius scale

```text
radiusSmall    8    — chips, badges, small buttons
radiusMedium   14   — cards, inputs, journey cards
radiusLarge    20   — bottom sheets, modals
radiusFull     999  — pills, avatar-style markers
```

Apple-style consistent rounding — never mix arbitrary radii (e.g., 6 next to 18) within the same component family.

### 5.3 Elevation

Uber/Apple both favor **flat elevation via subtle contrast**, not heavy drop shadows.

```text
elevation0   flush with background (map controls, ghost buttons)
elevation1   surface cards — 1px hairline border + minimal shadow
elevation2   bottom sheets, floating action controls — soft shadow, no border
elevation3   modals, alerts — stronger shadow, dimmed backdrop
```

Shadows are soft, low-opacity, and cool-toned (never warm/yellow shadows) — consistent with a navy-tinted neutral palette.

---

## 6. Iconography

* Line icons, consistent stroke weight (~1.5–2px), rounded joins — matching Inter's rounded terminals.
* No filled icons except for **selected/active states**, where a filled variant communicates "on" the way Apple's tab bar icons do.
* Transit-specific icons (bus, walk, transfer, stop pin) are custom-drawn to a shared 24×24 grid — never mixed emoji or mismatched icon packs in production UI.
* Icon-only touch targets are a minimum 44×44pt hit area regardless of visual icon size.

---

## 7. Motion & Animation

Apple-inspired motion principles govern the entire app:

* **Physical, not linear.** Spring-based easing (`damping`, not fixed-duration ease-in-out) for anything the user directly touches — bottom sheets, marker selection, card drags.
* **Continuity.** Elements animate *from* their trigger point (e.g., a tapped stop marker grows into the bottom sheet header) rather than cross-fading unrelated states.
* **Short.** 150–300ms for most UI transitions; map camera moves are the exception (400–700ms eased) since they cover physical distance.
* **Interruptible.** Any in-progress animation (sheet expanding, camera flying) must be cancelable by a new user gesture without jank.
* **Restrained.** No bounce/elastic overshoot on informational elements (arrival times, lists) — reserve springiness for direct-manipulation gestures (drag, swipe, sheet resize).

Named motion patterns:

```text
sheetPresent      spring, slides up from bottom, backdrop fades in
sheetDismiss      spring, slides down, backdrop fades out
markerSelect      scale 1.0 → 1.15 → 1.0, color shift, ~200ms
cameraFlyTo       eased fly/ease-to camera transition, 400–700ms
tabSwitch         crossfade + slight vertical shift, 150ms
cardEnter         fade + slide-up 8px, staggered per item, 200ms
routeDraw         polyline "draws on" progressively when a journey is selected
```

---

## 8. Component Design Language

Applies visual rules on top of the component inventory already defined in the architecture doc — this section does not redefine which components exist, only how they should look and feel.

* **Buttons:** filled-green for the single primary action per screen; navy or outline/ghost for everything else. Full-radius pill shape for primary CTAs (Uber-style "Find journeys" bar), medium-radius rectangle for secondary/inline buttons.
* **Cards** (`JourneyCard`, `RouteCard`, `StopCard`): elevation1, `radiusMedium`, generous internal padding (16–20), never text touching edges.
* **Bottom sheets:** the dominant interaction surface, matching Uber's ride-selection sheets — persistent handle, `radiusLarge` top corners, `elevation2`, content scrolls independently of the sheet's drag gesture.
* **Badges/chips** (`TransitLineBadge`, `DelayBadge`): filled pill, high-contrast text, color communicates meaning (green = on time/live, warning tone + icon = delayed — never color alone, per accessibility rules in the architecture doc).
* **Map markers:** custom vector assets, not emoji or default pins. Selected state = scale up + green ring; unselected = compact navy or neutral dot. Buses always visually distinct in shape from stops (e.g., rounded-square vehicle icon vs. circular stop dot).
* **Inputs/search bar:** large, pill-shaped, `elevation1`, icon-led ("Where do you want to go?"), sits above the map rather than inside a boxed header — Uber's floating-search convention.

---

## 9. Light vs. Dark Reference

| Token | Light | Dark |
|---|---|---|
| background | Off-white | True black |
| surface | White | Navy-tinted dark gray |
| accentPrimary (green) | Saturated green | Slightly desaturated green |
| accentSecondary (navy) | Deep navy | Brighter navy (for contrast on black) |
| routeSelected | Green | Green (glow avoided via reduced saturation) |
| mapBackground | Light/muted basemap style | Dark/muted basemap style |
| shadows | Soft cool gray, low opacity | Rarely used; rely on surface contrast instead |

Exact hex values are finalized during implementation/token generation, not hardcoded in this document — this table defines *relationships*, not final swatches.

---

## 10. What This Document Does Not Cover

Screen-by-screen layout, navigation structure, component inventory, and state/data architecture are defined in `00_FRONTEND_ARCHITECTURE.md` and are not repeated here. This document governs **how things look and move**, not what exists or where it lives.
