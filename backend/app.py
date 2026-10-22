"""Chalk Talk web app: FastAPI JSON API + fastmcp at /mcp + static pages.

The fastmcp Starlette app is the outer app (so POST /mcp answers without a redirect
and one CORS middleware covers everything); the FastAPI API is mounted under it at "/".
Local run: cd <repo> && uvicorn backend.app:app --port 8000
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from backend import llm, playbook, plays, tv
from backend.engine_loader import ENGINE_NAME, ROOT, engine
from backend.mcp_server import build_mcp
from backend.state import Store, ensure_demo, new_id, now_iso

VERSION = "0.1.0"
log = logging.getLogger("chalk.app")

LANDING = """<!doctype html><meta charset=utf-8><title>Chalk Talk</title>
<body style="font:18px system-ui;max-width:640px;margin:40px auto;padding:0 16px;background:#111;color:#eee">
<h1>Chalk Talk</h1>
<p>Sketch or say a youth basketball play; the TV animates it beat by beat.</p>
<ul>
<li><a href="/phone" style="color:#f28c28">/phone</a>: the coach's phone page</li>
<li><a href="/sim" style="color:#f28c28">/sim</a>: Echo Show simulator (an MCP Apps host) talking to this server</li>
<li><code>/mcp</code>: MCP server, Streamable HTTP, stateless (6 tools, 5 views)</li>
<li><a href="/docs" style="color:#f28c28">/docs</a>: HTTP API</li>
<li><a href="https://github.com/m-simakhov/chalk-talk" style="color:#f28c28">source on GitHub</a></li>
</ul>"""


class PlayRequest(BaseModel):
    text: str | None = None
    sketch: dict[str, Any] | None = None
    team_id: str | None = None
    players_per_side: int | None = None
    age_group: str | None = None


class CounterRequest(BaseModel):
    defence: str


class TeamRequest(BaseModel):
    name: str
    sport: str = "basketball"
    age_group: str = "u12"
    players_per_side: int = 5


class SaveRequest(BaseModel):
    play_id: str
    tags: list[str] = Field(default_factory=list)


class PracticeRequest(BaseModel):
    minutes: int = 60
    focus: str | None = ""


class CommandRequest(BaseModel):
    type: str
    play_id: str | None = None
    index: int | None = None
    defence: str | None = None


def error(status, code, message):
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def build_api(store):
    api = FastAPI(title="Chalk Talk API", version=VERSION)

    @api.exception_handler(HTTPException)
    async def on_http_error(_, exc):
        return error(exc.status_code, getattr(exc, "code", "http_error"), str(exc.detail))

    @api.exception_handler(RequestValidationError)
    async def on_validation_error(_, exc):
        return error(422, "validation_error", str(exc.errors()[0].get("msg", "invalid request")))

    def team_or_404(team_id):
        team = store.get_team(team_id)
        if team is None:
            raise HTTPException(404, f"unknown team {team_id}")
        return team

    def play_or_404(play_id):
        play = store.get_play(play_id)
        if play is None:
            raise HTTPException(404, f"unknown play {play_id}")
        return play

    @api.get("/api/health")
    def health():
        return {"ok": True, "llm": llm.status(), "version": VERSION, "engine": ENGINE_NAME, "state": store.backend}

    @api.get("/api/templates")
    def templates():
        return engine.template_catalog()

    @api.post("/api/plays")
    def create_play(body: PlayRequest):
        if not body.text and not body.sketch:
            raise HTTPException(422, "give text or a sketch")
        try:
            return plays.create_play(store, engine, body.text, body.sketch, body.team_id, body.players_per_side, body.age_group)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @api.get("/api/plays/{play_id}")
    def get_play(play_id: str):
        return play_or_404(play_id)

    @api.post("/api/plays/{play_id}/counter")
    def counter(play_id: str, body: CounterRequest):
        play_or_404(play_id)
        try:
            return plays.counter(store, engine, play_id, body.defence)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @api.post("/api/teams")
    def create_team(body: TeamRequest):
        return store.put_team({"id": new_id("team"), **body.model_dump(), "created_at": now_iso()})

    @api.get("/api/teams/{team_id}")
    def get_team(team_id: str):
        return team_or_404(team_id)

    @api.get("/api/teams/{team_id}/playbook")
    def get_playbook(team_id: str):
        team_or_404(team_id)
        entries = store.get_playbook(team_id)
        return {"plays": entries, "count": len(entries)}

    @api.post("/api/teams/{team_id}/playbook")
    def save_play(team_id: str, body: SaveRequest):
        team_or_404(team_id)
        return playbook.save_to_playbook(store, team_id, play_or_404(body.play_id), body.tags)

    @api.post("/api/teams/{team_id}/practice_plan")
    def practice_plan(team_id: str, body: PracticeRequest):
        team = team_or_404(team_id)
        return playbook.build_practice_plan(team, store.get_playbook(team_id), body.minutes, body.focus or "")

    @api.post("/api/tv/pair")
    def tv_pair():
        return tv.pair(store)

    @api.get("/api/tv/{code}/state")
    async def tv_state(code: str, cursor: int = -1, wait: int = 0):
        state = await tv.wait_state(store, code.upper(), cursor, bool(wait))
        if state is None:
            raise HTTPException(404, f"unknown TV code {code}")
        return state

    @api.post("/api/tv/{code}/command")
    def tv_command(code: str, body: CommandRequest):
        try:
            return tv.apply_command(store, engine, code.upper(), body.model_dump(exclude_none=True))
        except KeyError:
            raise HTTPException(404, f"unknown TV code {code}")
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    # Static pages from sibling component directories, read at request time.
    def static_file(path: Path, media_type=None):
        if not path.exists():
            raise HTTPException(404, f"{path.name} is not built yet")
        return FileResponse(path, media_type=media_type)

    @api.get("/", response_class=HTMLResponse, include_in_schema=False)
    def landing():
        return LANDING

    @api.get("/phone", include_in_schema=False)
    def phone():
        return static_file(ROOT / "phone" / "index.html", "text/html")

    @api.get("/renderer/court.js", include_in_schema=False)
    def renderer():
        return static_file(ROOT / "renderer" / "court.js", "text/javascript")

    @api.get("/sim-intents.json", include_in_schema=False)
    def sim_intents():  # the simulator's intent table, kept next to the views by the simulator component
        return static_file(Path(__file__).resolve().parent / "views" / "sim-intents.json", "application/json")

    @api.get("/sim", include_in_schema=False)
    def sim(request: Request):
        if "server" not in request.query_params:  # point the simulator at this server
            scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
            return RedirectResponse(f"/sim?server={scheme}://{request.headers.get('host', request.url.netloc)}/mcp")
        return static_file(ROOT / "echo-show-mcp-sim" / "index.html", "text/html")

    return api


def create_app():
    logging.basicConfig(level=logging.INFO)
    store = Store()
    ensure_demo(store, engine)
    cors = Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                      allow_headers=["*"], expose_headers=["Mcp-Session-Id"])
    web = build_mcp(store, engine).http_app(path="/mcp", stateless_http=True, middleware=[cors])
    web.router.routes.append(Mount("/", app=build_api(store)))  # lowest precedence, after /mcp
    web.state.store = store
    log.info("chalk-talk app: engine=%s state=%s llm=%s", ENGINE_NAME, store.backend, llm.base_url())
    return web


app = create_app()
