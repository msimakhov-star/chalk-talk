"""Defensive placement: man-to-man from assignments, 2-3 zone from areas, plus a nudge
that keeps auto-placed defenders the legal 3 ft away from everyone."""

from .court import BASKET, MIN_GAP, away, clamp_to_court, dist, guard, toward

# Zone formations by defender count: 5 = 2-3 zone, 4 = box, 3 = triangle (one up, two low).
ZONE_SPOTS = {
    5: [(18.0, 20.0), (32.0, 20.0), (13.0, 8.0), (25.0, 11.0), (37.0, 8.0)],
    4: [(19.0, 20.0), (31.0, 20.0), (19.0, 8.0), (31.0, 8.0)],
    3: [(25.0, 21.0), (19.0, 8.0), (31.0, 8.0)],
}


def man_positions(offense, ball_xy, ball_holder, assign, overrides):
    """Place every defender: hand overrides win, the rest guard their assigned man."""
    placed = dict(overrides)
    taken = list(offense.values()) + list(placed.values())
    for did in sorted(d for d in assign if d not in placed):
        man = offense[assign[did]]
        spot = guard(man, ball_xy, on_ball=(assign[did] == ball_holder))
        spot = settle(spot, taken)
        placed[did] = spot
        taken.append(spot)
    return placed


def zone_positions(defenders, offense, ball_xy):
    """Area defence: the formation slides toward the ball and the nearest defender steps up."""
    spots = ZONE_SPOTS[len(defenders)]
    shift = max(-6.0, min(6.0, 0.3 * (ball_xy[0] - 25.0)))
    spots = [(x + shift, y) for x, y in spots]
    nearest = min(range(len(spots)), key=lambda i: dist(spots[i], ball_xy))
    step_up = toward(ball_xy, BASKET, 4.5)
    if all(dist(step_up, p) >= MIN_GAP for p in offense.values()):
        spots[nearest] = step_up
    placed = {}
    taken = list(offense.values())
    for did, spot in zip(sorted(defenders), spots):
        spot = settle(spot, taken)
        placed[did] = spot
        taken.append(spot)
    return placed


def settle(spot, taken):
    """Nudge `spot` straight away from anyone closer than MIN_GAP, a few rounds at most."""
    # ponytail: 6 rounds of straight-line nudging is plenty for 10 points on a half court.
    for _ in range(6):
        crowd = [p for p in taken if dist(spot, p) < MIN_GAP]
        if not crowd:
            break
        spot = clamp_to_court(away(min(crowd, key=lambda q: dist(spot, q)), spot, MIN_GAP + 0.5))
    return spot
