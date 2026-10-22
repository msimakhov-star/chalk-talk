# Chalk Talk: shared contracts

Every component is built against this file. If you must change a contract, change it here first and say so in your report.

## 0. What Chalk Talk is

A volunteer youth basketball coach sketches a play on their phone or says it out loud ("backdoor cut from the left wing"). The living-room TV (Fire TV / Android TV) animates it as a step-by-step play: the D-pad steps through the beats, a caption explains "the read" at each beat, and "what if they switch?" re-plans the defence live. From the kitchen Echo Show (simulated Alexa+ client speaking real MCP), the coach asks "what are we practising Thursday?", gets a practice plan card built from the saved playbook, and sends a play to the TV.

The LLM never draws freehand. It picks one of 8 parameterised templates and fills parameters; a validator guarantees every play is physically legal. Plays persist in the team's playbook across sessions.

Monorepo layout (one component per directory, agents never edit another component's directory):

```
engine/      Python package `chalk_engine`: templates, keyframes, validator, counters, narration, rules parser
backend/     Modal app: FastAPI (+ fastmcp mounted at /mcp), LLM service, state, MCP Apps views, static hosting
renderer/    court.js: browser ES module that draws a Play on a <canvas> and interpolates between beats
phone/       static phone page: sketch canvas + voice + text, pairing code, talks to backend
tv/          react-native-tvos app for Android TV / Fire TV
eval/        evaluation harness (freehand LLM vs template engine) and its results
echo-show-mcp-sim/   generic MCP Apps host in an Echo Show frame (separate open-source repo, vendored here)
docs/        FOR_JUDGES.md, FRICTION_LOG.md, PRODUCT_FEEDBACK.md, STATUS.md
```

Python 3.12 everywhere (Modal image) and 3.14 locally; keep code 3.12-compatible. Node 24 for tooling.

## 1. Court and coordinates

Half court, basketball, feet. Origin (0,0) is the left corner of the baseline when looking from the baseline toward half court. `x` runs 0..50 across the court (left to right), `y` runs 0..47 from the baseline (y=0) to the half-court line (y=47). The basket is at (25, 5.25). Free-throw line y=19, lane is x 17..33 (16 ft wide), three-point arc radius 23.75 ft from the basket (NBA) but we draw a 19.75 ft arc (youth / FIBA-ish) and nothing depends on it.

Players are points. Offense ids `P1..P5` (labels "1".."5": 1 point guard, 2 shooting guard, 3 wing, 4 forward, 5 centre). Defense ids `D1..D5` (labels "x1".."x5"), `Dn` guards `Pn` by default. Ball is held by exactly one offense player at each beat, or is "in_flight" between two players.

## 2. Play JSON (the one object everything exchanges)

```json
{
  "id": "ply_7f3a9c",
  "sport": "basketball",
  "template": "pick_and_roll",
  "name": "Pick and roll, right wing",
  "description": "1 uses 5's screen on the right wing; 5 rolls to the rim.",
  "params": {"side": "right", "ball_handler": "P1", "screener": "P5", "players_per_side": 5, "age_group": "u12"},
  "defence": "man",
  "court": {"width": 50, "length": 47, "units": "ft"},
  "players": [
    {"id": "P1", "team": "offense", "label": "1"},
    {"id": "D1", "team": "defense", "label": "x1"}
  ],
  "beats": [
    {
      "index": 0,
      "t": 0.0,
      "title": "Setup",
      "read": "1 has the ball at the top. 5 comes up to set a screen on x1's left shoulder.",
      "positions": {"P1": [25, 38], "P5": [33, 30], "D1": [25, 34], "D5": [31, 25]},
      "ball": "P1",
      "paths": {}
    },
    {
      "index": 1,
      "t": 2.0,
      "title": "Screen",
      "read": "1 waits for the screen, then goes shoulder to shoulder off it.",
      "positions": {"P1": [30, 34], "P5": [27, 36], "D1": [26, 33], "D5": [27, 30]},
      "ball": "P1",
      "paths": {"P1": [[25, 38], [28, 37], [30, 34]]},
      "pass": null
    }
  ],
  "validity": {"ok": true, "issues": []},
  "counters": ["switch", "hedge", "drop", "zone"],
  "parse": {"method": "llm", "confidence": 0.82, "input": "pick and roll on the right"},
  "created_at": "2026-10-22T12:00:00Z"
}
```

Rules:
- `beats[0].t == 0`, `t` strictly increasing, measured in seconds. Clients animate linearly from beat i to i+1 over `t[i+1]-t[i]` seconds along `paths[player]` if present (polyline of waypoints starting at the previous position and ending at the new one), else a straight line.
- `positions` must list every player in `players` at every beat.
- `ball` is a player id, or `{"from": "P1", "to": "P3"}` for a pass in flight that completes at this beat (the pass line is drawn from `from`'s previous position to `to`'s position). A beat with a pass also sets `pass: {"from":"P1","to":"P3"}` for convenience.
- `read` is one or two short sentences a 10-year-old understands, under 140 characters. `title` under 24 characters.
- `defence` is `"man"` for the base play; a counter play copies the base play with `defence` set to the counter and `id` suffixed `-switch` etc., re-planned defensive positions, and `read` text explaining the new read. `template` and `params` are unchanged; `name` gets " vs switch" appended.
- `validity.issues` entries: `{"beat": 1, "player": "P5", "code": "out_of_bounds" | "overlap" | "too_fast" | "ball_orphan" | "missing_player", "detail": "..."}`. `ok` is true only when `issues` is empty.
- IDs: `ply_` plus 6 lowercase hex. Team ids `team_` plus 6 hex. TV pairing codes are 4 uppercase letters excluding I and O.

## 3. Templates (exactly these 8, ids fixed)

| id | name | params (beyond side, players_per_side, age_group) | counters that change the defence |
|---|---|---|---|
| `pick_and_roll` | Pick and roll | ball_handler, screener | switch, hedge, drop, zone |
| `pick_and_pop` | Pick and pop | ball_handler, screener | switch, hedge, drop, zone |
| `backdoor_cut` | Backdoor cut | passer, cutter | switch, zone |
| `give_and_go` | Give and go | passer, receiver | switch, zone |
| `dribble_handoff` | Dribble handoff | handler, receiver | switch, hedge, zone |
| `flare_screen` | Flare screen | shooter, screener, passer | switch, zone |
| `horns` | Horns set | ball_handler, screen_side | switch, hedge, drop, zone |
| `fast_break_3v2` | Fast break 3 on 2 | ball_handler | none (defence is already 2) |

`side` is `"left"` or `"right"` (mirror x across 25 for left). `players_per_side` is 3, 4 or 5 (3v3 drops P4/P5 and D4/D5 unless the template needs a role; the engine remaps roles to existing players and says so in `description`). `age_group` is `u8`, `u10`, `u12`, `u14`, `u16`; it scales beat durations (younger = slower) and the max-speed limit.

Each template has 3 to 6 beats. The base play includes a plausible man-to-man defence. Counters: `switch` (defenders swap assignments at the screen), `hedge` (screener's defender jumps out, recovers), `drop` (screener's defender sags to the paint), `zone` (2-3 zone positions, defenders guard areas). A counter re-plans only defensive positions and reads; offense is unchanged except for the `read` text telling the kids what to look for.

Validator limits: positions inside `[0,50]x[0,47]`; no two players closer than 3 ft at any beat (overlap); per-beat speed `distance / dt` under 20 ft/s for u16 (scaled: u8 12, u10 14, u12 16, u14 18); the ball holder must exist and a pass must have both ends present (`ball_orphan`).

## 4. Engine API (Python, `engine/chalk_engine`)

```python
from chalk_engine import TEMPLATES, build_play, counter_play, validate, parse_rules, narrate, mirror
build_play(template: str, params: dict) -> dict        # Play JSON with validity filled in, defence "man"
counter_play(play: dict, defence: str) -> dict          # new Play JSON (copy), defence set, id suffixed
validate(play: dict) -> dict                            # {"ok": bool, "issues": [...]}
parse_rules(text: str) -> dict | None                   # {"template","params","confidence"} from keywords, or None
template_catalog() -> list[dict]                        # [{"id","name","summary","params_schema","counters"}]
TEMPLATES: dict[str, Template]
```
`engine/tests/test_engine.py` (plain `python -m pytest` or `python -m unittest`) must assert: every template x side x players_per_side x age_group builds a valid play; every declared counter builds a valid play; the rules parser maps the 40 fixture phrasings in `engine/tests/phrasings.json` to the right template; `mirror` is an involution.

## 5. Backend HTTP API (FastAPI on Modal, JSON, CORS `*`)

Base URL in production: `https://m-simakhov--chalk-talk-web.us-east.modal.run` (Modal app name `chalk-talk`, function `web`). Local dev: `uvicorn backend.app:app --port 8000`.

| Method and path | Body | Returns |
|---|---|---|
| `POST /api/plays` | `{"text": str?, "sketch": {"strokes": [[[x,y],...]]}?, "team_id": str?, "players_per_side": int?, "age_group": str?}` | Play JSON. `parse.method` is `"llm"`, `"rules"` or `"sketch"`. At least one of text/sketch required. 422 on neither. |
| `GET /api/plays/{id}` | | Play JSON, 404 if unknown |
| `POST /api/plays/{id}/counter` | `{"defence": "switch"|"hedge"|"drop"|"zone"}` | Play JSON (counter variant, stored under its own id) |
| `POST /api/teams` | `{"name": str, "sport": "basketball", "age_group": str, "players_per_side": int}` | `{"id","name","age_group","players_per_side","created_at"}` |
| `GET /api/teams/{id}` | | Team |
| `GET /api/teams/{id}/playbook` | | `{"plays": [PlaySummary], "count": n}`; PlaySummary = `{"id","name","template","defence","tags","beats":n,"saved_at"}` |
| `POST /api/teams/{id}/playbook` | `{"play_id": str, "tags": [str]}` | `{"count": n, "play": PlaySummary}` |
| `POST /api/teams/{id}/practice_plan` | `{"minutes": int, "focus": str?}` | `{"minutes", "focus", "blocks": [{"start_min","minutes","title","play_id"?, "notes"}], "summary": str}` |
| `POST /api/tv/pair` | `{}` | `{"code": "KQZT", "tv_id": "tv_...", "expires_at": iso}` (TV calls on launch) |
| `GET /api/tv/{code}/state?cursor=n&wait=1` | | `{"cursor": n, "play": Play|null, "beat_index": int, "defence": str, "updated_at": iso}`; with `wait=1` long-polls up to 10 s for a cursor change, else returns immediately. 404 unknown code. |
| `POST /api/tv/{code}/command` | `{"type": "show_play", "play_id": str}` or `{"type": "set_beat", "index": int}` or `{"type": "counter", "defence": str}` or `{"type": "play"}` / `{"type": "pause"}` | `{"ok": true, "cursor": n}` |
| `GET /api/templates` | | `template_catalog()` |
| `GET /api/health` | | `{"ok": true, "llm": "ready"|"cold"|"off", "version": str}` |
| `GET /` | | landing page (links to /phone, /mcp info, repo) |
| `GET /phone` | | the phone page (from `phone/index.html`) |
| `GET /renderer/court.js` | | the renderer module (from `renderer/court.js`) |
| `GET /sim` | | the Echo Show simulator pointed at this server (from `echo-show-mcp-sim/index.html`) |

Errors: `{"error": {"code": str, "message": str}}` with proper HTTP status.

State lives in a `modal.Dict.from_name("chalk-talk-state", create_if_missing=True)` with keys `play:{id}`, `team:{id}`, `playbook:{team_id}` (list), `tv:{code}` and a `demo` team seeded on first use (`team_demo00`, "Cambridge Comets U12", 5v5, u12) with 4 saved plays so every judge sees a filled playbook. Local dev falls back to an in-memory dict when Modal is unavailable.

LLM: `backend/llm.py` exposes `parse_play_text(text, context) -> {"template","params","confidence"}|None` and `enrich_reads(play) -> play` (optional, must be fast and skippable). Implementation: an open-weights model served on Modal (llama.cpp server container `ghcr.io/ggml-org/llama.cpp:server` or `server-cuda`, model cached in a `modal.Volume`), called with a JSON schema so output is always a valid template choice; on any failure or latency over 6 s, fall back to `parse_rules`. Local dev may use Ollama at `http://localhost:11434` (model `gemma4:12b-nvfp4` or `llama3.2:3b`) via the same OpenAI-compatible shape. `GET /api/health` reports which is active.

## 6. MCP server (mounted at `/mcp`, Streamable HTTP, spec 2025-11-25, stateless)

fastmcp 4.1.3 with `mcp.http_app(path="/mcp", stateless_http=True, middleware=[cors])`. CORS: allow all origins, methods GET/POST/DELETE/OPTIONS, headers `*`, expose `Mcp-Session-Id`.

Tools (one per customer intent; every tool returns rich `structuredContent`, never a bare success):

| tool | arguments | returns (structuredContent) | view |
|---|---|---|---|
| `draw_play` | `description: str`, `team_id: str = "team_demo00"`, `defence: str = "man"` | the Play JSON plus `summary: str` | `ui://chalk-talk/court` |
| `counter_play` | `play_id: str`, `defence: str` | the counter Play JSON plus `what_changed: str` | `ui://chalk-talk/court` |
| `save_to_playbook` | `play_id: str`, `team_id: str`, `tags: list[str] = []` | `{"play": PlaySummary, "playbook_count": n, "team_name": str}` | `ui://chalk-talk/saved` |
| `list_playbook` | `team_id: str`, `filter: str = ""` | `{"team_name", "plays": [PlaySummary] (3 to 5, strongest first), "total": n}` | `ui://chalk-talk/playbook` |
| `practice_plan` | `team_id: str`, `minutes: int = 60`, `focus: str = ""` | PracticePlan JSON | `ui://chalk-talk/practice` |
| `send_to_tv` | `play_id: str`, `code: str` | `{"tv_name": "Living room TV", "code", "play_name", "beat_index": 0, "status": "showing"}` | `ui://chalk-talk/sent` |

Tool descriptions are written for a voice assistant: say when to call the tool and what the user would say. If `team_id` is unknown, use `team_demo00` (no elicitation required; elicitation is a stretch goal).

Views are single self-contained HTML files in `backend/views/*.html` with the court renderer inlined at build time (read `renderer/court.js` and inject). Each view implements the MCP Apps handshake exactly as in `echo-show-mcp-sim/PROTOCOL.md`: send `ui/initialize` (protocolVersion `2026-01-26`), then `ui/notifications/initialized`, then render on `ui/notifications/tool-result` using `params.structuredContent`, report `ui/notifications/size-changed`, and call host `tools/call` for in-view buttons (court view: "Step", "Back", "What if they switch?" calling `counter_play`; playbook view: "Send to TV" calling `send_to_tv`). Views are designed for a 10-inch far-field screen: one title, large type, one or two actions, dark theme by default, honour `hostContext.theme`.

Resource `_meta.ui`: `{"csp": {"connectDomains": [], "resourceDomains": []}, "prefersBorder": false}`.

## 7. Renderer (`renderer/court.js`)

ES module, no dependencies:
```js
export function drawCourt(ctx, w, h, opts = {})            // court lines, scaled to canvas
export function interpolate(play, tSec)                     // -> {positions: {id:[x,y]}, ball: {holder|from,to,progress}, beatIndex}
export function drawFrame(ctx, w, h, play, tSec, opts = {}) // court + players + ball + optional path hints
export function beatStart(play, i)                          // -> seconds
export function totalDuration(play)
export function playerColor(player)                         // offense orange #f28c28, defense blue #3b82f6; ball white
```
Canvas is landscape; map x 0..50 to width and y 0..47 to height with y=0 (baseline) at the BOTTOM of the canvas. Player circle diameter is 7% of canvas height, label centred. The ball is a small filled circle offset to the holder's top-right.

## 8. Phone page (`phone/index.html`, served at `/phone`)

Plain HTML/JS, mobile-first, works at 390 px wide. Sections: pairing code input (4 letters, saved in localStorage); "Say it" button using the Web Speech API (fallback: visible textarea); "Sketch it" canvas (court background from the renderer; strokes recorded as polylines in court coordinates); "Draw the play" button → `POST /api/plays`; result preview with the renderer; "Send to TV" → `POST /api/tv/{code}/command show_play`; "What if they switch / hedge / drop / zone" buttons → counter + send. Server base URL = same origin (or `?api=` override for local dev).

## 9. TV app (`tv/`)

react-native-tvos (latest 0.7x tvos release that supports Android TV), Android target only. Screens: Pair (shows the 4-letter code in 120 pt type plus a one-line instruction "Open <phone URL> and enter this code"), Court (full-screen court drawn with absolutely positioned Views; players are 56 px circles; animation with `Animated` between beats; caption bar at the bottom with `title` and `read`; top bar with play name and a badge for `defence`). D-pad: right = next beat, left = previous beat, select = play/pause auto-advance, up = toggle paths, down = cycle counters (requests `counter` via the backend), back = return to Pair. Polls `GET /api/tv/{code}/state?wait=1` continuously. Configure the backend URL in `tv/src/config.ts` (production Modal URL by default; `adb reverse` not needed because the emulator can reach the internet). Build: `cd tv && npm i && npx react-native run-android` with the emulator running. Also produce a release APK at `tv/release/chalk-talk.apk`.

Label the demo honestly: the video says "Android TV emulator (Fire OS equivalent)".

## 10. Echo Show simulator (`echo-show-mcp-sim/`, separate MIT repo)

A generic MCP Apps host: one `index.html` (no build), query `?server=https://.../mcp`. Renders an Echo Show 8 frame (1280x800 bezel, dark UI, time in the corner), a text box styled as a voice transcript ("Alexa, ...") with Web Speech input when available, a router that picks a tool by a simple LLM-free strategy: it calls `tools/list`, scores each tool's description against the utterance (keyword overlap + a tiny intent table loaded from `?intents=` JSON or the server's `GET /sim-intents.json` if present), fills arguments from the utterance with named-entity regexes, calls `tools/call`, speaks a one-sentence summary with `speechSynthesis` (`structuredContent.summary` if present), and renders the tool's MCP App view in a sandboxed iframe with the full host protocol (`ui/initialize` reply with hostContext `{platform:"web", theme:"dark", displayMode:"inline", containerDimensions}`, `tool-input`, `tool-result`, `size-changed`, proxying `tools/call`, `ping`). Includes a "far-field lint" panel: flags text under 24 px, more than two actions, more than five carousel items, and `summary` over 200 characters. Documented in `README.md` and `PROTOCOL.md` (the exact message sequence) so other hackathon entrants can use it with their own servers. The backend serves a copy at `/sim` with `server` preset.

## 11. Video and docs

`docs/FOR_JUDGES.md`: 60-second try-it path (open `/sim`, type "draw a pick and roll on the right", then "what if they switch", then "send it to the TV" with the demo code), APK sideload steps, local run steps. `docs/STATUS.md`: honest table (feature, status: built / tested on emulator / simulated / not done). `docs/FRICTION_LOG.md`: entries in the Devpost format (task, steps, expected vs actual, severity, workaround, suggestion). `docs/PRODUCT_FEEDBACK.md`: per tool used (react-native-tvos, Android TV emulator as Fire OS stand-in, MCP spec + MCP Apps, fastmcp, Modal, Amazon docs), what it was used for, what worked, what needs work, onboarding, would build again.
