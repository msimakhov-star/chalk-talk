"""Build Play JSON from a template: cast the roles, lay the beats, place the defence,
mirror for the left side, narrate, validate."""

import copy
import re
import secrets
import time

from .court import AGE_GROUPS, PLAYERS_PER_SIDE, SIDES, TEMPO, mirror_x
from .defence import man_positions, zone_positions
from .narration import narrate
from .template import OFFENSE_IDS, Cast
from .templates import TEMPLATES
from .validator import validate

COURT = {"width": 50, "length": 47, "units": "ft"}


def build_play(template, params):
    return _build(template, params, "man")


def counter_play(play, defence):
    base_id = play["id"].split("-")[0]
    if defence not in play["counters"]:
        raise ValueError(f"{play['template']} has no counter {defence!r}; pick one of {play['counters']}")
    new = _build(play["template"], play["params"], defence)
    new["id"] = f"{base_id}-{defence}"
    new["created_at"] = play["created_at"]
    new["parse"] = copy.deepcopy(play.get("parse"))
    return new


def template_catalog():
    return [
        {
            "id": tpl.id,
            "name": tpl.name,
            "summary": tpl.summary,
            "params_schema": _params_schema(tpl),
            "counters": list(tpl.counters),
        }
        for tpl in TEMPLATES.values()
    ]


def mirror(play):
    """Flip the play across the court's centre line (x -> 50 - x). An involution."""
    out = copy.deepcopy(play)
    for b in out["beats"]:
        b["positions"] = {pid: _flip(xy) for pid, xy in b["positions"].items()}
        b["paths"] = {pid: [_flip(xy) for xy in path] for pid, path in b["paths"].items()}
        b["read"] = _swap_sides(b["read"])
        b["title"] = _swap_sides(b["title"])
    out["name"] = _swap_sides(out["name"])
    out["description"] = _swap_sides(out["description"])
    side = out["params"].get("side")
    if side in SIDES:
        out["params"]["side"] = "left" if side == "right" else "right"
    if out["params"].get("screen_side") in SIDES:
        out["params"]["screen_side"] = out["params"]["side"]
    return out


def _flip(xy):
    x, y = mirror_x(xy)
    return [round(x, 1), round(y, 1)]  # rounding keeps mirror(mirror(p)) == p exactly


def _swap_sides(text):
    return re.sub(r"\b(left|right)\b", lambda m: "right" if m.group(1) == "left" else "left", text)


# ---------------------------------------------------------------------------------------

def _build(template, params, defence):
    if template not in TEMPLATES:
        raise ValueError(f"unknown template {template!r}; known: {sorted(TEMPLATES)}")
    tpl = TEMPLATES[template]
    params, remap_note = _normalise_params(tpl, params)
    wanted_side = params["side"]
    # Templates are authored for the right side: build that, then mirror (which flips side).
    params["side"] = "right"
    if "screen_side" in params:
        params["screen_side"] = "right"
    cast = Cast({r: params[r] for r in tpl.roles}, params["players_per_side"])
    raw = tpl.build(cast)
    changes = tpl.counter(cast, defence) if defence != "man" else {}
    beats = _finish_beats(raw, changes, cast, params["age_group"], defence)
    play = {
        "id": "ply_" + secrets.token_hex(3),
        "sport": "basketball",
        "template": tpl.id,
        "name": tpl.name + (f" vs {defence}" if defence != "man" else ""),
        "description": (tpl.summary + remap_note).strip(),
        "params": params,
        "defence": defence,
        "court": dict(COURT),
        "players": _players(cast),
        "beats": beats,
        "validity": None,
        "counters": list(tpl.counters),
        "parse": {"method": "template", "confidence": 1.0, "input": ""},
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if wanted_side == "left":
        play = mirror(play)
    narrate(play)
    play["validity"] = validate(play)
    return play


def _normalise_params(tpl, params):
    """Fill defaults, check enums, remap roles to players that exist in 3v3 / 4v4."""
    p = dict(params or {})
    if "screen_side" in tpl.extra_params and p.get("screen_side") in SIDES and "side" not in p:
        p["side"] = p["screen_side"]
    p.setdefault("side", "right")
    p.setdefault("players_per_side", 5)
    p.setdefault("age_group", "u12")
    if p["side"] not in SIDES:
        raise ValueError(f"side must be one of {SIDES}, got {p['side']!r}")
    if p["players_per_side"] not in PLAYERS_PER_SIDE:
        raise ValueError(f"players_per_side must be one of {PLAYERS_PER_SIDE}, got {p['players_per_side']!r}")
    if p["age_group"] not in AGE_GROUPS:
        raise ValueError(f"age_group must be one of {AGE_GROUPS}, got {p['age_group']!r}")
    if "screen_side" in tpl.extra_params:
        p["screen_side"] = p["side"]  # horns: the screen is always on the play's side
    n = p["players_per_side"]
    on_court = OFFENSE_IDS[:n]
    notes = []
    taken = set()
    for role, default in tpl.roles.items():
        wanted = p.get(role) or default
        pid = wanted
        if pid not in on_court or pid in taken:
            # highest-numbered free player, preferring one that is not another role's default
            free = [q for q in reversed(on_court) if q not in taken]
            pid = next((q for q in free if q not in tpl.roles.values()), free[0])
            notes.append(f"{n}v{n}: {pid[1]} plays {role.replace('_', ' ')} instead of {wanted[1]}.")
        taken.add(pid)
        p[role] = pid
    return p, (" " + " ".join(notes) if notes else "")


def _players(cast):
    players = [{"id": pid, "team": "offense", "label": Cast.lab(pid)} for pid in cast.offense]
    players += [{"id": Cast.d(pid), "team": "defense", "label": Cast.lab(Cast.d(pid))} for pid in cast.offense]
    return players


def _finish_beats(raw, changes, cast, age_group, defence):
    """Scale durations, build polylines, place the defence, and emit contract-shaped beats."""
    if not 3 <= len(raw) <= 6:
        raise ValueError(f"a template must have 3 to 6 beats, got {len(raw)}")
    defenders = [Cast.d(pid) for pid in cast.offense]
    assign = {Cast.d(pid): pid for pid in cast.offense}
    beats = []
    t = 0.0
    prev_offense = None
    for i, rb in enumerate(raw):
        change = changes.get(i, {})
        assign.update(change.get("assign", {}))
        overrides = dict(rb["defence"])
        overrides.update(change.get("defence", {}))
        overrides = {d: xy for d, xy in overrides.items() if xy is not None}
        offense = rb["offense"]
        ball = rb["ball"]
        holder = ball[1] if isinstance(ball, tuple) else ball
        ball_xy = offense[holder]
        if defence == "zone":
            dpos = zone_positions(defenders, offense, ball_xy)
        else:
            dpos = man_positions(offense, ball_xy, holder, assign, overrides)
        positions = {**offense, **dpos}
        if i > 0:
            t += round(rb["dur"] * TEMPO[age_group], 2)
        paths = {}
        for pid, via in rb["via"].items():
            paths[pid] = [prev_offense[pid], *via, offense[pid]]
        beats.append({
            "index": i,
            "t": round(t, 2),
            "title": rb["title"],
            "read": change.get("read") or rb["read"],
            "positions": {pid: [round(x, 1), round(y, 1)] for pid, (x, y) in positions.items()},
            "ball": {"from": ball[0], "to": ball[1]} if isinstance(ball, tuple) else ball,
            "paths": {pid: [[round(x, 1), round(y, 1)] for x, y in path] for pid, path in paths.items()},
            "pass": {"from": ball[0], "to": ball[1]} if isinstance(ball, tuple) else None,
        })
        prev_offense = offense
    return beats


def _params_schema(tpl):
    props = {
        "side": {"type": "string", "enum": list(SIDES), "default": "right"},
        "players_per_side": {"type": "integer", "enum": list(PLAYERS_PER_SIDE), "default": 5},
        "age_group": {"type": "string", "enum": list(AGE_GROUPS), "default": "u12"},
    }
    for role, default in tpl.roles.items():
        props[role] = {"type": "string", "enum": list(OFFENSE_IDS), "default": default}
    for key, spec in tpl.extra_params.items():
        props[key] = dict(spec)
    return {"type": "object", "properties": props, "additionalProperties": False}
