"""Tiny stand-in for the real `chalk_engine` package (engine/), used only when
that import fails so the backend can be developed and tested on its own.

It follows the engine API in CONTRACTS.md section 4 with the smallest possible
plays: one shared 4-beat motion for every template, a real validator, and a
keyword rules parser. Nothing here is meant to be a good basketball play.
"""

import copy
import datetime as dt
import math
import secrets

TEMPLATE_ROWS = [
    ("pick_and_roll", "Pick and roll", ["ball_handler", "screener"], ["switch", "hedge", "drop", "zone"]),
    ("pick_and_pop", "Pick and pop", ["ball_handler", "screener"], ["switch", "hedge", "drop", "zone"]),
    ("backdoor_cut", "Backdoor cut", ["passer", "cutter"], ["switch", "zone"]),
    ("give_and_go", "Give and go", ["passer", "receiver"], ["switch", "zone"]),
    ("dribble_handoff", "Dribble handoff", ["handler", "receiver"], ["switch", "hedge", "zone"]),
    ("flare_screen", "Flare screen", ["shooter", "screener", "passer"], ["switch", "zone"]),
    ("horns", "Horns set", ["ball_handler", "screen_side"], ["switch", "hedge", "drop", "zone"]),
    ("fast_break_3v2", "Fast break 3 on 2", ["ball_handler"], []),
]

TEMPLATES = {
    tid: {"id": tid, "name": name, "summary": f"{name} (stub engine)", "roles": roles, "counters": counters}
    for tid, name, roles, counters in TEMPLATE_ROWS
}

SPEED_LIMIT = {"u8": 12, "u10": 14, "u12": 16, "u14": 18, "u16": 20}

# Right-side base motion, 5v5. Each beat: (t, title, read, offense, defence, ball)
_BEATS = [
    (0.0, "Setup", "1 has the ball at the top. 5 comes up to set a screen.",
     {"P1": [25, 38], "P2": [40, 30], "P3": [10, 30], "P4": [38, 12], "P5": [33, 25]},
     {"D1": [25, 34], "D2": [37, 28], "D3": [13, 28], "D4": [35, 14], "D5": [29, 22]}, "P1"),
    (2.0, "Screen", "1 waits for the screen, then goes shoulder to shoulder off it.",
     {"P1": [30, 34], "P2": [40, 30], "P3": [10, 30], "P4": [38, 12], "P5": [27, 36]},
     {"D1": [26, 32], "D2": [37, 28], "D3": [13, 28], "D4": [35, 14], "D5": [29, 29]}, "P1"),
    (4.0, "Roll", "1 drives. 5 rolls to the rim with a hand up.",
     {"P1": [33, 30], "P2": [40, 30], "P3": [10, 30], "P4": [38, 12], "P5": [28, 14]},
     {"D1": [30, 27], "D2": [37, 28], "D3": [13, 28], "D4": [35, 14], "D5": [28, 18]}, "P1"),
    (5.5, "Finish", "If x5 is late, 1 bounces the pass to 5 for the layup.",
     {"P1": [33, 30], "P2": [40, 30], "P3": [10, 30], "P4": [38, 12], "P5": [28, 14]},
     {"D1": [30, 27], "D2": [37, 28], "D3": [13, 28], "D4": [35, 14], "D5": [28, 18]},
     {"from": "P1", "to": "P5"}),
]

# Defensive positions per counter, per beat index (beat 0 stays man-to-man unless zone).
_COUNTER_DEFENCE = {
    "switch": {1: {"D1": [29, 29], "D5": [26, 32]}, 2: {"D1": [28, 18], "D5": [30, 27]}, 3: {"D1": [28, 18], "D5": [30, 27]}},
    "hedge": {1: {"D5": [31, 38]}},
    "drop": {1: {"D5": [27, 24]}, 2: {"D5": [25, 10]}, 3: {"D5": [25, 10]}},
    "zone": {i: {"D1": [20, 24], "D2": [30, 24], "D3": [14, 12], "D4": [25, 10], "D5": [34, 9]} for i in range(4)},
}
_COUNTER_READ = {
    "switch": "They switched: x5 is on 1 now. 5 seals x1 on the roll, that is the pass.",
    "hedge": "x5 jumped out high. 1 keeps the dribble alive and hits 5 slipping to the rim.",
    "drop": "x5 dropped to the paint. 1 takes the open pull-up or hits 5 at the elbow.",
    "zone": "It is a 2-3 zone. Find the gap at the free-throw line and pass through it.",
}


def _new_id():
    return "ply_" + secrets.token_hex(3)


def _now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def template_catalog():
    return [
        {"id": t["id"], "name": t["name"], "summary": t["summary"], "counters": list(t["counters"]),
         "params_schema": {"side": ["left", "right"], "players_per_side": [3, 4, 5],
                           "age_group": list(SPEED_LIMIT), "roles": list(t["roles"])}}
        for t in TEMPLATES.values()
    ]


def build_play(template, params):
    if template not in TEMPLATES:
        raise ValueError(f"unknown template {template!r}")
    spec = TEMPLATES[template]
    params = {"side": "right", "players_per_side": 5, "age_group": "u12", **(params or {})}
    n = int(params["players_per_side"])
    keep = {f"P{i}" for i in range(1, n + 1)} | {f"D{i}" for i in range(1, n + 1)}
    # Role defaults: first role is the ball handler (P1), the others use P5 / P3 / P2.
    for role, pid in zip(spec["roles"], ["P1", "P5" if n == 5 else "P3", "P3", "P2"]):
        params.setdefault(role, pid)
    scale = {"u8": 1.6, "u10": 1.4, "u12": 1.2, "u14": 1.1, "u16": 1.0}[params["age_group"]]
    players = [{"id": f"P{i}", "team": "offense", "label": str(i)} for i in range(1, n + 1)]
    players += [{"id": f"D{i}", "team": "defense", "label": f"x{i}"} for i in range(1, n + 1)]
    beats = []
    prev = None
    for index, (t, title, read, off, dfc, ball) in enumerate(_BEATS):
        positions = {pid: list(xy) for pid, xy in {**off, **dfc}.items() if pid in keep}
        if n < 5:  # P5 is the mover in the shared motion; hand its spot to P3
            positions["P3"] = list(off["P5"])
            positions["D3"] = list(dfc["D5"])
            if isinstance(ball, dict):
                ball = {"from": "P1", "to": "P3"}
        paths = {pid: [prev[pid], xy] for pid, xy in positions.items() if prev and prev[pid] != xy}
        beat = {"index": index, "t": round(t * scale, 2), "title": title, "read": read,
                "positions": positions, "ball": ball, "paths": paths,
                "pass": ball if isinstance(ball, dict) else None}
        beats.append(beat)
        prev = positions
    play = {
        "id": _new_id(), "sport": "basketball", "template": template,
        "name": f"{spec['name']}, {params['side']} side",
        "description": f"{spec['name']} on the {params['side']} ({n}v{n}, {params['age_group']}). Stub engine.",
        "params": params, "defence": "man",
        "court": {"width": 50, "length": 47, "units": "ft"},
        "players": players, "beats": beats, "counters": list(spec["counters"]),
        "parse": {"method": "rules", "confidence": 1.0, "input": ""},
        "created_at": _now(),
    }
    if params["side"] == "left":
        play = mirror(play)
    play["validity"] = validate(play)
    return play


def counter_play(play, defence):
    if defence not in play.get("counters", []):
        raise ValueError(f"{play['template']} has no counter {defence!r}")
    new = copy.deepcopy(play)
    base_id = play["id"].split("-")[0]
    new["id"] = f"{base_id}-{defence}"
    new["defence"] = defence
    new["name"] = play["name"].split(" vs ")[0] + f" vs {defence}"
    flip = play["params"].get("side") == "left"
    for beat in new["beats"]:
        for pid, xy in _COUNTER_DEFENCE[defence].get(beat["index"], {}).items():
            if pid == "D5" and "D5" not in beat["positions"]:
                pid = "D3"  # in 3v3 / 4v4 the mover's defender is x3 (see build_play)
            if pid in beat["positions"]:
                beat["positions"][pid] = [50 - xy[0], xy[1]] if flip else list(xy)
        if beat["index"] > 0:
            beat["read"] = _COUNTER_READ[defence]
    prev = None
    for beat in new["beats"]:
        beat["paths"] = {pid: [prev[pid], xy] for pid, xy in beat["positions"].items() if prev and prev[pid] != xy}
        prev = beat["positions"]
    new["validity"] = validate(new)
    return new


def validate(play):
    issues = []
    ids = [p["id"] for p in play["players"]]
    limit = SPEED_LIMIT.get(play.get("params", {}).get("age_group", "u16"), 20)
    prev = None
    for beat in play["beats"]:
        pos = beat["positions"]
        for pid in ids:
            if pid not in pos:
                issues.append({"beat": beat["index"], "player": pid, "code": "missing_player", "detail": "no position"})
                continue
            x, y = pos[pid]
            if not (0 <= x <= 50 and 0 <= y <= 47):
                issues.append({"beat": beat["index"], "player": pid, "code": "out_of_bounds", "detail": f"{pid} at {x},{y}"})
        present = [pid for pid in ids if pid in pos]
        for i, a in enumerate(present):
            for b in present[i + 1:]:
                if math.dist(pos[a], pos[b]) < 3:
                    issues.append({"beat": beat["index"], "player": a, "code": "overlap", "detail": f"{a} and {b} under 3 ft"})
        if prev is not None:
            dt_s = beat["t"] - prev["t"]
            for pid in present:
                if pid in prev["positions"] and dt_s > 0:
                    speed = math.dist(prev["positions"][pid], pos[pid]) / dt_s
                    if speed > limit:
                        issues.append({"beat": beat["index"], "player": pid, "code": "too_fast", "detail": f"{speed:.1f} ft/s > {limit}"})
        ball = beat["ball"]
        ends = [ball["from"], ball["to"]] if isinstance(ball, dict) else [ball]
        for end in ends:
            if end not in pos:
                issues.append({"beat": beat["index"], "player": end, "code": "ball_orphan", "detail": "ball holder missing"})
        prev = beat
    return {"ok": not issues, "issues": issues}


_KEYWORDS = [
    ("pick_and_pop", ["pick and pop", "pop"]),
    ("pick_and_roll", ["pick and roll", "pick n roll", "pnr", "ball screen", "screen and roll"]),
    ("backdoor_cut", ["backdoor", "back door"]),
    ("give_and_go", ["give and go", "give-and-go"]),
    ("dribble_handoff", ["handoff", "hand off", "hand-off", "dho"]),
    ("flare_screen", ["flare"]),
    ("horns", ["horns"]),
    ("fast_break_3v2", ["fast break", "3 on 2", "three on two", "transition"]),
]


def parse_rules(text):
    low = (text or "").lower()
    for template, words in _KEYWORDS:
        if any(w in low for w in words):
            side = "left" if "left" in low else "right"
            return {"template": template, "params": {"side": side}, "confidence": 0.6}
    return None


def narrate(play):
    return play


def mirror(play):
    new = copy.deepcopy(play)
    for beat in new["beats"]:
        beat["positions"] = {pid: [50 - x, y] for pid, (x, y) in beat["positions"].items()}
        beat["paths"] = {pid: [[50 - x, y] for x, y in pts] for pid, pts in beat.get("paths", {}).items()}
    return new
