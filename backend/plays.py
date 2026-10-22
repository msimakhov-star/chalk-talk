"""Create a play from text or a sketch, and build counters. Shared by the HTTP API and MCP tools."""

from backend import llm
from backend.state import DEMO_TEAM_ID


def _team_context(store, team_id, players_per_side, age_group):
    team = store.get_team(team_id or DEMO_TEAM_ID) or {}
    return {"players_per_side": int(players_per_side or team.get("players_per_side", 5)),
            "age_group": age_group or team.get("age_group", "u12")}


def _parse_sketch(sketch):
    """A sketch alone only tells us the side (mean x of the strokes); the template is a guess."""
    points = [p for stroke in sketch.get("strokes", []) for p in stroke]
    if not points:
        return None
    mean_x = sum(p[0] for p in points) / len(points)
    # ponytail: template from stroke count is a placeholder; a real sketch matcher goes here.
    template = {1: "backdoor_cut", 2: "pick_and_roll"}.get(len(sketch["strokes"]), "give_and_go")
    return {"template": template, "params": {"side": "left" if mean_x < 25 else "right"}, "confidence": 0.3}


def create_play(store, engine, text=None, sketch=None, team_id=None, players_per_side=None, age_group=None, defence="man"):
    """-> Play JSON stored under its id. Raises ValueError if nothing could be parsed."""
    context = _team_context(store, team_id, players_per_side, age_group)
    choice, method = None, None
    if text:
        hints = engine.parse_rules(text)  # only what the words say: side, count, age, roles
        choice = llm.parse_play_text(text, context)
        method = "llm" if choice else None
        if choice is None:
            choice, method = hints, "rules"
        elif hints:
            # The model picks template and side; explicit words like "3 on 3" or "under 10s" beat team defaults.
            for key, value in hints.get("params", {}).items():
                if key != "side":
                    choice["params"][key] = value
    if choice is None and sketch:
        choice = _parse_sketch(sketch)
        method = "sketch"
    if choice is None:
        raise ValueError("could not recognise a play; try words like 'pick and roll on the right'")
    play = engine.build_play(choice["template"], {**context, **choice.get("params", {})})
    play["parse"] = {"method": method, "confidence": float(choice.get("confidence", 0.5)), "input": text or "sketch"}
    play = llm.enrich_reads(play)
    store.put_play(play)
    if defence and defence != "man":
        play = counter(store, engine, play["id"], defence)
    return play


def counter(store, engine, play_id, defence):
    base = store.get_play(play_id)
    if base is None:
        raise KeyError(play_id)
    if defence == "man":
        return store.get_play(play_id.split("-")[0]) or base
    play = engine.counter_play(store.get_play(play_id.split("-")[0]) or base, defence)
    store.put_play(play)
    return play


def what_changed(base, counter_play):
    moved = sorted({pid for b0, b1 in zip(base["beats"], counter_play["beats"])
                    for pid in b1["positions"] if b0["positions"].get(pid) != b1["positions"][pid]})
    who = ", ".join(moved[:3]).replace("D", "x") or "nobody"
    return f"Defence now plays {counter_play['defence']}: {who} move. {counter_play['beats'][1]['read'] if len(counter_play['beats']) > 1 else ''}".strip()
