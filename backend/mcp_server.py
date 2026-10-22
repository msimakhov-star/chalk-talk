"""The MCP server: 6 voice-friendly tools and 5 MCP Apps views (backend/views/*.html).

Views are served as resources with the court renderer (renderer/court.js) inlined
where a view contains the marker <!-- INLINE:court.js -->. The marker sits inside the
view's own <script type="module">, so the raw module text (exports included) is legal there.
"""

import logging
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.apps import UI_MIME_TYPE
from fastmcp.exceptions import ToolError

from backend import playbook, plays, tv
from backend.state import DEMO_TEAM_ID

log = logging.getLogger("chalk.mcp")
ROOT = Path(__file__).resolve().parent.parent
VIEWS_DIR = Path(__file__).resolve().parent / "views"
RENDERER = ROOT / "renderer" / "court.js"
INLINE_MARKER = "<!-- INLINE:court.js -->"

VIEWS = {  # resource uri -> file in backend/views
    "ui://chalk-talk/court": "court.html",
    "ui://chalk-talk/saved": "saved.html",
    "ui://chalk-talk/playbook": "playbook.html",
    "ui://chalk-talk/practice": "practice.html",
    "ui://chalk-talk/sent": "sent.html",
}
VIEW_META = {"csp": {"connectDomains": [], "resourceDomains": []}, "prefersBorder": False}

FALLBACK_VIEW = """<!doctype html><meta charset=utf-8><body style="font:20px system-ui;background:#111;color:#eee;margin:16px">
<h1 style="font-size:28px">{name}</h1><pre id=o style="white-space:pre-wrap;font-size:18px">waiting for tool result...</pre>
<script>
const send=m=>parent.postMessage({{jsonrpc:"2.0",...m}},"*");
addEventListener("message",e=>{{const m=e.data;if(m&&m.method==="ui/notifications/tool-result"){{document.getElementById("o").textContent=JSON.stringify(m.params.structuredContent,null,1);send({{method:"ui/notifications/size-changed",params:{{height:document.body.scrollHeight}}}})}}}});
send({{id:1,method:"ui/initialize",params:{{protocolVersion:"2026-01-26",appInfo:{{name:"{name}",version:"0"}},appCapabilities:{{}}}}}});
send({{method:"ui/notifications/initialized",params:{{}}}});
</script>"""


def load_view(uri):
    """The view HTML with court.js inlined; a plain fallback view if the file is not written yet."""
    path = VIEWS_DIR / VIEWS[uri]
    if not path.exists():
        log.warning("view %s missing, serving fallback", path.name)
        return FALLBACK_VIEW.format(name=uri.rsplit("/", 1)[-1])
    renderer = RENDERER.read_text() if RENDERER.exists() else "/* renderer/court.js missing */"
    return path.read_text().replace(INLINE_MARKER, renderer)


def build_mcp(store, engine):
    mcp = FastMCP("chalk-talk", instructions="Chalk Talk draws youth basketball plays, keeps a team playbook, "
                  "builds practice plans and sends plays to the living-room TV. Unknown team: use team_demo00.")
    COURT, SAVED, PLAYBOOK, PRACTICE, SENT = VIEWS

    @mcp.tool(app={"resourceUri": COURT})
    def draw_play(description: str, team_id: str = DEMO_TEAM_ID, defence: str = "man") -> dict:
        """Draw a basketball play from the coach's words and animate it on the court.
        Call this when the user describes a play or asks to draw, show, run or diagram one,
        for example "draw a pick and roll on the right", "show me a backdoor cut from the left wing"
        or "what does a give and go look like". Returns the play with its beats and a one-sentence summary."""
        try:
            play = plays.create_play(store, engine, text=description, team_id=team_id, defence=defence)
        except ValueError as exc:
            raise ToolError(str(exc))
        return {**play, "summary": f"{play['name']}: {play['beats'][0]['read']}"}

    @mcp.tool(app={"resourceUri": COURT})
    def counter_play(play_id: str, defence: str) -> dict:
        """Re-plan the defence of a play the user is looking at and explain the new read.
        Call this for "what if they switch", "what if they hedge", "what if they drop" or
        "what if they play zone" (defence is switch, hedge, drop or zone). Needs the play_id of the
        play on screen. Returns the counter play and what changed."""
        base = store.get_play(play_id.split("-")[0])
        if base is None:
            raise ToolError(f"unknown play {play_id!r}")
        try:
            counter = plays.counter(store, engine, play_id, defence)
        except ValueError as exc:
            raise ToolError(str(exc))
        return {**counter, "what_changed": plays.what_changed(base, counter)}

    @mcp.tool(app={"resourceUri": SAVED})
    def save_to_playbook(play_id: str, team_id: str = DEMO_TEAM_ID, tags: list[str] = []) -> dict:
        """Save the play on screen into the team's playbook so it is there next practice.
        Call this for "save that", "add it to the playbook" or "keep this one for Thursday".
        Returns the saved play summary, the playbook size and the team name."""
        play = store.get_play(play_id)
        team = store.get_team(team_id)
        if play is None or team is None:
            raise ToolError("unknown play or team")
        saved = playbook.save_to_playbook(store, team_id, play, tags)
        return {"play": saved["play"], "playbook_count": saved["count"], "team_name": team["name"],
                "summary": f"Saved {play['name']} to the {team['name']} playbook. {saved['count']} plays saved."}

    @mcp.tool(app={"resourceUri": PLAYBOOK})
    def list_playbook(team_id: str = DEMO_TEAM_ID, filter: str = "") -> dict:
        """Show the team's saved plays, strongest first, optionally filtered by a word like
        "screens", "cuts" or a play name. Call this for "what plays do we have", "show the playbook"
        or "which plays use screens". Returns 3 to 5 plays with ids for sending to the TV."""
        team = store.get_team(team_id)
        if team is None:
            raise ToolError(f"unknown team {team_id!r}")
        entries = store.get_playbook(team_id)
        top = playbook.rank_plays(entries, filter)
        return {"team_name": team["name"], "plays": top, "total": len(entries),
                "summary": f"{team['name']} has {len(entries)} plays saved: " + ", ".join(e["name"] for e in top) + "."}

    @mcp.tool(app={"resourceUri": PRACTICE})
    def practice_plan(team_id: str = DEMO_TEAM_ID, minutes: int = 60, focus: str = "") -> dict:
        """Build a practice plan from the team's playbook: warm-up, two or three plays, scrimmage,
        cool-down. Call this for "what are we practising Thursday", "plan a 45 minute practice" or
        "practice plan on screens". Returns timed blocks and a one-sentence summary."""
        team = store.get_team(team_id)
        if team is None:
            raise ToolError(f"unknown team {team_id!r}")
        return playbook.build_practice_plan(team, store.get_playbook(team_id), minutes, focus)

    @mcp.tool(app={"resourceUri": SENT})
    def send_to_tv(play_id: str, code: str) -> dict:
        """Put a play on the living-room TV. Call this for "send it to the TV", "show that on the
        telly" or "put the pick and roll on the big screen"; code is the 4-letter pairing code shown
        on the TV. Returns the TV name and the play now showing."""
        play = store.get_play(play_id)
        if play is None:
            raise ToolError(f"unknown play {play_id!r}")
        code = code.strip().upper()
        try:
            tv.apply_command(store, engine, code, {"type": "show_play", "play_id": play_id})
        except KeyError:
            raise ToolError(f"no TV paired with code {code}")
        return {"tv_name": tv.TV_NAME, "code": code, "play_name": play["name"], "beat_index": 0,
                "status": "showing", "summary": f"{play['name']} is on the {tv.TV_NAME}."}

    for uri in VIEWS:
        def make(uri=uri):
            def view() -> str:
                return load_view(uri)
            view.__name__ = "view_" + uri.rsplit("/", 1)[-1]
            return view
        mcp.resource(uri, mime_type=UI_MIME_TYPE, app=VIEW_META)(make())
    return mcp
