"""TV pairing codes, state with a change cursor, and commands from the phone / MCP."""

import asyncio
import datetime as dt
import secrets

from backend.state import new_id, now_iso

CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # no I or O
LONG_POLL_SECONDS = 10
POLL_INTERVAL = 0.3
TV_NAME = "Living room TV"


def new_code():
    return "".join(secrets.choice(CODE_LETTERS) for _ in range(4))


def pair(store):
    code = new_code()
    while store.get_tv(code):
        code = new_code()
    expires = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24)).replace(microsecond=0)
    state = {"code": code, "tv_id": new_id("tv"), "play_id": None, "beat_index": 0, "defence": "man",
             "playing": False, "cursor": 0, "updated_at": now_iso(),
             "expires_at": expires.isoformat().replace("+00:00", "Z")}
    store.put_tv(state)
    return {"code": code, "tv_id": state["tv_id"], "expires_at": state["expires_at"]}


def public_state(store, state):
    play = store.get_play(state["play_id"]) if state["play_id"] else None
    return {"cursor": state["cursor"], "play": play, "beat_index": state["beat_index"],
            "defence": state["defence"], "playing": state["playing"], "updated_at": state["updated_at"]}


async def wait_state(store, code, cursor, wait):
    """Return the TV state; with wait, block up to 10 s for the cursor to move past `cursor`."""
    deadline = asyncio.get_event_loop().time() + LONG_POLL_SECONDS
    while True:
        state = store.get_tv(code)
        if state is None:
            return None
        if not wait or state["cursor"] != cursor or asyncio.get_event_loop().time() >= deadline:
            return public_state(store, state)
        await asyncio.sleep(POLL_INTERVAL)


def apply_command(store, engine, code, command):
    """Mutate the TV state for one command and bump the cursor. Raises ValueError on bad input."""
    state = store.get_tv(code)
    if state is None:
        raise KeyError(code)
    kind = command.get("type")
    if kind == "show_play":
        play = store.get_play(command.get("play_id"))
        if play is None:
            raise ValueError(f"unknown play {command.get('play_id')!r}")
        state.update(play_id=play["id"], beat_index=0, defence=play.get("defence", "man"), playing=False)
    elif kind == "set_beat":
        play = store.get_play(state["play_id"]) if state["play_id"] else None
        last = len(play["beats"]) - 1 if play else 0
        state["beat_index"] = min(max(int(command.get("index", 0)), 0), last)
    elif kind == "counter":
        if not state["play_id"]:
            raise ValueError("no play on the TV yet")
        base = store.get_play(state["play_id"].split("-")[0])
        defence = command.get("defence", "man")
        if defence == "man":
            shown = base
        else:
            shown = engine.counter_play(base, defence)
            store.put_play(shown)
        state.update(play_id=shown["id"], defence=defence)
    elif kind in ("play", "pause"):
        state["playing"] = kind == "play"
    else:
        raise ValueError(f"unknown command type {kind!r}")
    state["cursor"] += 1
    state["updated_at"] = now_iso()
    store.put_tv(state)
    return {"ok": True, "cursor": state["cursor"]}
