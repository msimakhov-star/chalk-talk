"""validate(play): is this play physically legal? Codes are fixed by CONTRACTS.md section 2."""

from .court import LENGTH, MIN_GAP, SPEED_LIMIT, WIDTH, dist, path_length


def validate(play):
    issues = []
    ids = [p["id"] for p in play.get("players", [])]
    limit = SPEED_LIMIT.get(play.get("params", {}).get("age_group", "u16"), SPEED_LIMIT["u16"])
    prev = None
    for b in play.get("beats", []):
        i = b["index"]
        pos = b.get("positions", {})
        for pid in ids:
            if pid not in pos:
                issues.append(_issue(i, pid, "missing_player", "no position at this beat"))
                continue
            x, y = pos[pid]
            if not (0 <= x <= WIDTH and 0 <= y <= LENGTH):
                issues.append(_issue(i, pid, "out_of_bounds", f"({x}, {y}) is off the court"))
        present = [pid for pid in ids if pid in pos]
        for a_i, a in enumerate(present):
            for b_id in present[a_i + 1:]:
                gap = dist(pos[a], pos[b_id])
                if gap < MIN_GAP:
                    issues.append(_issue(i, a, "overlap", f"{a} and {b_id} are {gap:.1f} ft apart"))
        if prev is not None:
            dt = b["t"] - prev["t"]
            for pid in present:
                if pid not in prev["positions"]:
                    continue
                path = b.get("paths", {}).get(pid) or [prev["positions"][pid], pos[pid]]
                run = path_length(path)
                if dt <= 0:
                    issues.append(_issue(i, pid, "too_fast", f"beat time must increase (dt={dt})"))
                    break
                if run / dt > limit:
                    issues.append(_issue(i, pid, "too_fast", f"{run / dt:.1f} ft/s over {limit} ft/s"))
        ball = b.get("ball")
        if isinstance(ball, dict):
            for end in ("from", "to"):
                if ball.get(end) not in present:
                    issues.append(_issue(i, ball.get(end), "ball_orphan", f"pass {end} a missing player"))
        elif ball not in present:
            issues.append(_issue(i, ball, "ball_orphan", "ball holder is not on the court"))
        prev = b
    return {"ok": not issues, "issues": issues}


def _issue(beat, player, code, detail):
    return {"beat": beat, "player": player, "code": code, "detail": detail}
