"""Fake Chalk Talk MCP server for developing the simulator and the views offline.

It speaks the contract from CONTRACTS.md section 6 (same six tools, same structuredContent shapes)
with fixture data, serves the five views with dev/court-stub.js inlined at the INLINE marker,
and serves the simulator itself at /sim/ so everything is same-origin.

Run:   python dev/fake_chalk_talk.py [--views ../backend/views] [--port 8765]
Needs: fastmcp==4.1.3, uvicorn (see README).
"""
import argparse
import copy
import json
import sys
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.apps import UI_MIME_TYPE
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
SIM_DIR = HERE.parent
DEFAULT_VIEWS = SIM_DIR.parent / "backend" / "views"
INLINE_MARKER = "<!-- INLINE:court.js -->"

TEAM = {"id": "team_demo00", "name": "Cambridge Comets U12"}
TV_CODE = "KQZT"

BASE_PLAY = {
    "id": "ply_7f3a9c",
    "sport": "basketball",
    "template": "pick_and_roll",
    "name": "Pick and roll, right wing",
    "description": "1 uses 5's screen on the right wing; 5 rolls to the rim.",
    "params": {"side": "right", "ball_handler": "P1", "screener": "P5", "players_per_side": 5, "age_group": "u12"},
    "defence": "man",
    "court": {"width": 50, "length": 47, "units": "ft"},
    "players": [
        {"id": "P1", "team": "offense", "label": "1"}, {"id": "P2", "team": "offense", "label": "2"},
        {"id": "P3", "team": "offense", "label": "3"}, {"id": "P4", "team": "offense", "label": "4"},
        {"id": "P5", "team": "offense", "label": "5"},
        {"id": "D1", "team": "defense", "label": "x1"}, {"id": "D2", "team": "defense", "label": "x2"},
        {"id": "D3", "team": "defense", "label": "x3"}, {"id": "D4", "team": "defense", "label": "x4"},
        {"id": "D5", "team": "defense", "label": "x5"},
    ],
    "beats": [
        {"index": 0, "t": 0.0, "title": "Setup",
         "read": "1 has the ball at the top. 5 comes up to set a screen on x1's left shoulder.",
         "positions": {"P1": [25, 38], "P2": [8, 30], "P3": [42, 30], "P4": [12, 12], "P5": [33, 30],
                       "D1": [25, 34], "D2": [11, 27], "D3": [39, 27], "D4": [15, 11], "D5": [31, 25]},
         "ball": "P1", "paths": {}},
        {"index": 1, "t": 2.0, "title": "Screen",
         "read": "1 waits for the screen, then goes shoulder to shoulder off it.",
         "positions": {"P1": [30, 34], "P2": [8, 30], "P3": [42, 30], "P4": [12, 12], "P5": [27, 36],
                       "D1": [26, 33], "D2": [11, 27], "D3": [39, 27], "D4": [15, 11], "D5": [27, 30]},
         "ball": "P1", "paths": {"P1": [[25, 38], [28, 37], [30, 34]]}},
        {"index": 2, "t": 4.0, "title": "Roll",
         "read": "5 turns and rolls to the rim. 1 looks at the roller first.",
         "positions": {"P1": [34, 28], "P2": [8, 30], "P3": [42, 30], "P4": [12, 12], "P5": [27, 16],
                       "D1": [31, 30], "D2": [11, 27], "D3": [39, 27], "D4": [15, 11], "D5": [26, 22]},
         "ball": "P1", "paths": {"P5": [[27, 36], [28, 26], [27, 16]]}},
        {"index": 3, "t": 6.0, "title": "Pass",
         "read": "If x5 is late, 1 hits 5 at the rim.",
         "positions": {"P1": [34, 28], "P2": [8, 30], "P3": [42, 30], "P4": [12, 12], "P5": [26, 9],
                       "D1": [31, 30], "D2": [11, 27], "D3": [39, 27], "D4": [15, 11], "D5": [28, 14]},
         "ball": {"from": "P1", "to": "P5"}, "pass": {"from": "P1", "to": "P5"}, "paths": {}},
    ],
    "validity": {"ok": True, "issues": []},
    "counters": ["switch", "hedge", "drop", "zone"],
    "parse": {"method": "rules", "confidence": 0.9, "input": "pick and roll on the right"},
    "created_at": "2026-10-22T12:00:00Z",
}

COUNTER_READS = {
    "switch": "x5 switches onto 1 and x1 takes 5. 1 attacks the big; 5 seals the small.",
    "hedge": "x5 jumps out hard to slow 1, then sprints back. 5 slips early.",
    "drop": "x5 sags to the paint. 1 pulls up for the mid-range shot.",
    "zone": "They play a 2-3. 1 hits the gap, 5 flashes to the high post.",
}

PLAYBOOK = [
    {"id": "ply_7f3a9c", "name": "Pick and roll, right wing", "template": "pick_and_roll", "defence": "man", "tags": ["go-to", "end of game"], "beats": 4, "saved_at": "2026-10-20T18:02:00Z"},
    {"id": "ply_1b22e0", "name": "Backdoor cut, left wing", "template": "backdoor_cut", "defence": "man", "tags": ["vs pressure"], "beats": 3, "saved_at": "2026-10-19T17:40:00Z"},
    {"id": "ply_c0ffee", "name": "Horns set", "template": "horns", "defence": "man", "tags": ["half court"], "beats": 5, "saved_at": "2026-10-18T19:10:00Z"},
    {"id": "ply_9a9a9a", "name": "Fast break 3 on 2", "template": "fast_break_3v2", "defence": "man", "tags": ["transition"], "beats": 3, "saved_at": "2026-10-17T18:30:00Z"},
]

plays = {BASE_PLAY["id"]: BASE_PLAY}


def build(views_dir: Path, renderer: Path):
    mcp = FastMCP("chalk-talk-fake")
    cors = Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                      allow_headers=["*"], expose_headers=["Mcp-Session-Id"])

    def view(name):
        html = (views_dir / f"{name}.html").read_text()
        if INLINE_MARKER in html:
            html = html.replace(INLINE_MARKER, renderer.read_text())
        return html

    for name in ["court", "playbook", "practice", "saved", "sent"]:
        def make(name=name):
            def resource() -> str:
                return view(name)
            return resource
        mcp.resource(f"ui://chalk-talk/{name}", name=f"{name}_view", mime_type=UI_MIME_TYPE,
                     app={"csp": {"connectDomains": [], "resourceDomains": []}, "prefersBorder": False})(make())

    @mcp.tool(app={"resourceUri": "ui://chalk-talk/court"})
    def draw_play(description: str, team_id: str = "team_demo00", defence: str = "man") -> dict:
        """Draw a basketball play from a description, for example "pick and roll on the right"
        or "backdoor cut from the left wing". Call when the coach says draw, sketch or show a play."""
        play = copy.deepcopy(BASE_PLAY)
        play["parse"]["input"] = description
        play["name"] = description[:1].upper() + description[1:]
        play["summary"] = f"Here is {play['name']}: 4 beats, 1 uses 5's screen and 5 rolls to the rim."
        plays[play["id"]] = play
        return play

    @mcp.tool(app={"resourceUri": "ui://chalk-talk/court"})
    def counter_play(play_id: str, defence: str) -> dict:
        """Re-plan the defence of a play that is already on screen. Call when the coach asks
        "what if they switch", "what if they hedge", "what if they drop" or "what if they go zone"."""
        base = plays.get(play_id)
        if base is None:
            raise ValueError(f"unknown play {play_id}")
        if defence not in COUNTER_READS:
            raise ValueError(f"unknown defence {defence}; use switch, hedge, drop or zone")
        play = copy.deepcopy(base)
        play["id"] = f"{play_id}-{defence}"
        play["defence"] = defence
        play["name"] = f"{base['name']} vs {defence}"
        for beat in play["beats"][1:]:
            beat["read"] = COUNTER_READS[defence]
            beat["positions"]["D5"] = [beat["positions"]["D5"][0] - 3, beat["positions"]["D5"][1] + 3]
        play["what_changed"] = f"Against a {defence}: {COUNTER_READS[defence]}"
        plays[play["id"]] = play
        return play

    @mcp.tool(app={"resourceUri": "ui://chalk-talk/saved"})
    def save_to_playbook(play_id: str, team_id: str = "team_demo00", tags: list[str] = []) -> dict:
        """Save the play on screen to the team's playbook. Call when the coach says "save it",
        "save that as our go-to play" or "add it to the playbook"."""
        play = plays.get(play_id)
        if play is None:
            raise ValueError(f"unknown play {play_id}")
        summary = {"id": play["id"], "name": play["name"], "template": play["template"], "defence": play["defence"],
                   "tags": tags, "beats": len(play["beats"]), "saved_at": "2026-10-22T12:30:00Z"}
        PLAYBOOK.insert(0, summary)
        return {"play": summary, "playbook_count": len(PLAYBOOK), "team_name": TEAM["name"],
                "summary": f"Saved {play['name']} to the {TEAM['name']} playbook. {len(PLAYBOOK)} plays now."}

    @mcp.tool(app={"resourceUri": "ui://chalk-talk/playbook"})
    def list_playbook(team_id: str = "team_demo00", filter: str = "") -> dict:
        """Show the team's saved plays. Call when the coach says "show me my playbook" or "what plays do we have"."""
        chosen = [p for p in PLAYBOOK if filter.lower() in p["name"].lower()][:5]
        return {"team_name": TEAM["name"], "plays": chosen, "total": len(PLAYBOOK), "tv_code": TV_CODE,
                "summary": f"{TEAM['name']} has {len(PLAYBOOK)} plays. The strongest is {chosen[0]['name']}." if chosen else "No plays saved yet."}

    @mcp.tool(app={"resourceUri": "ui://chalk-talk/practice"})
    def practice_plan(team_id: str = "team_demo00", minutes: int = 60, focus: str = "") -> dict:
        """Build a practice plan from the saved playbook. Call when the coach asks "what are we practising
        on Thursday" or "give me a 60 minute practice plan focused on screens"."""
        blocks = [
            {"start_min": 0, "minutes": 10, "title": "Warm up and ball handling", "notes": "Two lines, cones, both hands."},
            {"start_min": 10, "minutes": 15, "title": "Pick and roll, right wing", "play_id": "ply_7f3a9c", "notes": "Walk the 4 beats, then live 2 on 2."},
            {"start_min": 25, "minutes": 15, "title": "Backdoor cut, left wing", "play_id": "ply_1b22e0", "notes": "Read x2's eyes before the cut."},
            {"start_min": 40, "minutes": 15, "title": "Scrimmage 5 on 5", "notes": "Call the plays by name."},
            {"start_min": 55, "minutes": 5, "title": "Free throws and cool down", "notes": "Everyone shoots 10."},
        ]
        return {"minutes": minutes, "focus": focus, "blocks": blocks,
                "summary": f"A {minutes} minute practice: warm up, pick and roll, backdoor cut, scrimmage, free throws."}

    @mcp.tool(app={"resourceUri": "ui://chalk-talk/sent"})
    def send_to_tv(play_id: str, code: str) -> dict:
        """Send a play to the living-room TV. Call when the coach says "send it to the TV" or
        "put that on the TV", optionally with the 4-letter code shown on the TV."""
        play = plays.get(play_id)
        if play is None:
            raise ValueError(f"unknown play {play_id}")
        if code != TV_CODE:
            raise ValueError(f"no TV paired with code {code}")
        return {"tv_name": "Living room TV", "code": code, "play_name": play["name"], "beat_index": 0, "status": "showing",
                "summary": f"{play['name']} is on the living room TV. Use the remote to step through it."}

    async def sim_intents(_):
        return JSONResponse(json.loads((views_dir / "sim-intents.json").read_text()))

    async def sim_index(_):
        return FileResponse(SIM_DIR / "index.html")

    web = mcp.http_app(path="/mcp", stateless_http=True, json_response=False, middleware=[cors])
    web.router.routes.extend([
        Route("/sim-intents.json", sim_intents),
        Route("/sim", sim_index),
        Route("/", sim_index),
        Mount("/sim", StaticFiles(directory=str(SIM_DIR), html=True), name="sim"),
    ])
    return web


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", type=Path, default=DEFAULT_VIEWS)
    ap.add_argument("--renderer", type=Path, default=HERE / "court-stub.js")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    if not args.views.is_dir():
        sys.exit(f"views directory not found: {args.views}")
    import uvicorn
    uvicorn.run(build(args.views, args.renderer), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
