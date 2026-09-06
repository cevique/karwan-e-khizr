# QA Test Results — Karwan-e-Khizr Frontend

Tested on: 2026-09-06
Tested by: Razi
Environment: Windows, Chrome, localhost:5173

---

## Critical (Core features broken)

| # | Screen | Bug | Details |
|---|---|---|---|
| C1 | Home | Buses don't move | Vehicle positions are static — same data for 30+ min. Speed values are random (0, 56, 118, 138 km/h). Details only change on reload. |
| C2 | Home | "Unknown" next stop | Some buses show "Next: Unknown" — simulation or API returning null next_stop |
| C3 | Routes | Routes are unclickable | 20+ routes listed but can't tap to see stops/path |
| C4 | Mobile (375px) | Map completely gone | No map visible on any screen — only Nearby Buses list shows |
| C5 | Journey Planning | No route found for many stop pairs | "F-8 to Saddar", "Blue Area to Saddar", "G-9 Markaz to Saddar" all fail |
| C6 | Saved | No way to save a journey | No bookmark/save button exists anywhere in journey detail view |

## Medium (Usability issues)

| # | Screen | Bug | Details |
|---|---|---|---|
| M1 | Home | Bus card click doesn't center map | Only shows popup, no map focus on bus location |
| M2 | Home | Locate Me button is placeholder | Does nothing |
| M3 | Home | Map Layers button is placeholder | Does nothing |
| M4 | Home | Search bar navigates away | Clicking search goes to Plan Journey instead of inline autocomplete |
| M5 | Home | "DEMO DATA" label visible | Should be hidden in production |
| M6 | Home | Bus card border color bug | Grey → green (clicked) → black (stays black after deselect) |
| M7 | Settings | Settings layout broken on desktop | Content centered in narrow mobile-width column, empty sides |
| M8 | Settings | Only Sign In is clickable | Language, Theme, Notifications, Privacy, About all non-functional |
| M9 | Plan Journey | "Ammar Chowk" hardcoded | Pre-filled in From field, not based on actual location |
| M10 | Plan Journey | PKR 0.00 on most routes | Fares always zero |
| M11 | Journey Detail | Live Tracking button does nothing | Placeholder |
| M12 | Routes | Clicking bus/stops on Routes tab shows no popup | Only highlights, no info shown |
| M13 | App | Doesn't remember last screen on refresh | Always goes to Home |

## Low (Polish)

| # | Screen | Bug | Details |
|---|---|---|---|
| L1 | Mobile | Bus card popup text overflow | Text extends beyond card bounds |
| L2 | Mobile | Search bar misshapen | Text outside input bounds |
| L3 | Journey | "G-9 Markaz" duplicate warning | "could mean several places: G-9 Markaz, G-9 Markaz" |
| L4 | All | No error feedback for failed searches | Just says "No transit route found" with no suggestion |

## New bugs (reported 2026-09-07)

| # | Screen | Bug | Details |
|---|---|---|---|
| N1 | Home | Bus popup card doesn't update on poll | When bus popup is open, the card data (next stop, speed, ETA) doesn't refresh on 8s interval — only nearby buses list updates |
| N2 | All | Buses/stops/routes not on roads | Straight lines between stops instead of following actual road geometry |
| N3 | Routes | Some routes show 0 stops | Routes with no route_stops data in DB show empty stop list |
| N4 | Mobile | Nav bar hidden on Home/Routes | Bottom nav not visible because bottom sheet overlay covers it (z-index issue) |
| N5 | Home | Locate Me goes to Peru | After granting permission, second click flies to wrong location (Peru) instead of Rawalpindi |
| N6 | Home | "Next: Unknown" still appearing | Some buses still show Unknown for next stop name |

---

## Fix Progress

- [x] C1+C2: Vehicle simulation fix
- [x] C4: Mobile map layout fix
- [x] C3: Routes clickable
- [x] C5: Journey routing failures
- [x] C6: Save journey feature
- [x] M7: Settings layout
- [x] M1+M6: Bus card interaction
- [x] M2+M3: Locate Me + Layers
- [x] M5: DEMO DATA hidden
- [x] M12: Routes tab — bus/stops only highlight, no popup
- [ ] N1: Bus popup card doesn't update on poll
- [ ] N2: Buses/stops/routes not on roads
- [ ] N3: Some routes show 0 stops
- [ ] N4: Mobile nav bar hidden
- [ ] N5: Locate Me goes to Peru
- [ ] N6: "Next: Unknown" still appearing
- [ ] M4: Search bar navigates away
- [ ] M8: Settings items non-functional
- [ ] M10: PKR 0.00 fares
- [ ] M11: Live Tracking placeholder
- [ ] M13: Doesn't remember last screen on refresh
- [ ] L1-L4: Polish items
