# Why Chalk Talk, and why these tracks

Written Thu 22 Oct 2026 before the build started, so the reasoning can be checked against what shipped.

## The annoyance

Volunteer youth basketball coaches explain plays on a whiteboard. Ten-year-olds do not read X's and O's; they watch. A play they can see move, stop, and replay on the living-room TV, with one sentence per beat saying what to look for, is the thing a coach actually wants on a Thursday evening before practice.

## Options compared

About 60 ideas were generated across the four tracks and scored on the hackathon's four criteria plus feasibility for the time left (about 30 hours) and crowding in the field (roughly 680 projects were already submitted on 20 Oct). Highlights of what was rejected and why:

| Idea | Track | Why it lost |
|---|---|---|
| Cheapest/greenest hour to run appliances | Alexa+ | Already exists as several Alexa skills and the Energy Dashboard; the rules penalise existing features |
| House-viewing dossier from flood, crime and transport data | Alexa+ | Used once every few years, on a phone, not on a kitchen screen |
| Hands-free repair guides | Alexa+ | Any assistant can talk through a repair; third-party guide content complicates the video |
| Delivery reconciliation, access control, appointment arrivals | Ring | Ring's Playground needs an Amazon developer sign-in that was not available; a Ring entry that never touched Ring's servers would score poorly on Tech |
| Scavenger hunt, drawing-to-cartoon | Fire TV | Both need a real child in the demo |
| Add-on test bench for Alexa+ developers | Alexa+ | Original, but no consumer, and a developer tool may fail the "fits the theme" gate |

## Why Chalk Talk won

- Sports, multi-modal UX (voice and drawing on the phone, D-pad on the TV, animated visuals) and family entertainment are three of the Fire TV track's named priorities.
- All content is original by construction: dots on a generic court. No footage, no logos.
- The AI part is honest. The model chooses and parameterises one of eight templates; a validator guarantees every play is physically legal. That is testable and measurable, and it avoids glossy demos of things that do not work.
- The same engine serves two tracks. The Fire TV app and the Alexa+ MCP server share one backend, and the Echo Show simulator built to demo the MCP server is useful to other developers, so it is published as its own open-source project.
- Field size: about 111 Fire TV entries for the same first prize as about 472 Alexa+ entries.

## What was decided against, inside the project

- No freehand coordinate generation by the model, ever. The evaluation in `eval/` shows why.
- No Vega OS build: the SDK needs more disk than this machine had and its virtual device starts only from a GUI. The Android TV emulator is the organiser-accepted stand-in for Fire OS, and the app is plain React Native for TV so it can be ported to Vega.
- No Ring track.
