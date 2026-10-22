"""Playbook entries (PlaySummary) and the practice plan builder."""

from backend.state import now_iso

PRACTICE_NOTE = "Walk it through beat by beat on the TV; ask the kids to say the read before each step."


def play_summary(play, tags=None, saved_at=None):
    return {"id": play["id"], "name": play["name"], "template": play["template"],
            "defence": play.get("defence", "man"), "tags": list(tags or []),
            "beats": len(play["beats"]), "saved_at": saved_at or now_iso()}


def save_to_playbook(store, team_id, play, tags):
    entries = [e for e in store.get_playbook(team_id) if e["id"] != play["id"]]
    entry = play_summary(play, tags)
    entries.append(entry)
    store.put_playbook(team_id, entries)
    return {"count": len(entries), "play": entry}


def _score(entry, words):
    text = " ".join([entry["name"], entry["template"].replace("_", " "), *entry["tags"]]).lower()
    return sum(1 for w in words if w in text)


def rank_plays(entries, filter_text="", limit=5):
    """Strongest first: matches the filter, then more tags, then most recent. 3 to 5 results."""
    words = [w for w in filter_text.lower().split() if len(w) > 2]
    ranked = sorted(entries, key=lambda e: (_score(e, words), len(e["tags"]), e["saved_at"]), reverse=True)
    if words:
        matched = [e for e in ranked if _score(e, words) > 0]
        ranked = matched + [e for e in ranked if e not in matched]
    return ranked[:max(3, min(limit, 5))]


def build_practice_plan(team, entries, minutes, focus=""):
    """Blocks: warm-up, 2 to 3 plays matching the focus, scrimmage, cool-down."""
    minutes = max(20, int(minutes))
    warm = max(5, round(minutes * 0.15))
    cool = max(5, round(minutes * 0.10))
    scrim = max(10, round(minutes * 0.25))
    chosen = rank_plays(entries, focus, limit=3)[:3] if entries else []
    chosen = chosen[:3 if minutes >= 60 else 2]
    play_total = minutes - warm - cool - scrim
    per_play = play_total // len(chosen) if chosen else 0
    scrim += play_total - per_play * len(chosen)  # leftover minutes go to the scrimmage

    blocks, start = [], 0

    def add(title, mins, notes, play_id=None):
        nonlocal start
        block = {"start_min": start, "minutes": mins, "title": title, "notes": notes}
        if play_id:
            block["play_id"] = play_id
        blocks.append(block)
        start += mins

    add("Warm-up", warm, "Dynamic stretch, two lines of layups, form shooting.")
    for entry in chosen:
        add(entry["name"], per_play, PRACTICE_NOTE, entry["id"])
    add("Scrimmage", scrim, f"Run {', '.join(e['name'] for e in chosen) or 'the plays'} live; stop and fix the read.")
    add("Cool-down", cool, "Free throws, stretch, one thing each player did well.")

    short = [e["name"].split(",")[0] for e in chosen]  # "Pick and roll, right wing" -> "Pick and roll"
    names = (", ".join(short[:-1]) + " and " + short[-1]) if len(short) > 1 else (short[0] if short else "no saved plays yet")
    topic = f" on {focus}" if focus else ""
    summary = f"{minutes} minutes{topic} for {team['name']}: warm-up, {names}, then scrimmage and cool-down."
    return {"minutes": minutes, "focus": focus, "blocks": blocks, "summary": summary}
