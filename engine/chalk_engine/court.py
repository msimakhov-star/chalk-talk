"""Court geometry: constants, named spots and the small vector helpers every template uses.

Half court in feet. Origin (0, 0) is the left corner of the baseline when you stand on the
baseline and look toward half court. x runs 0..50 left to right, y runs 0..47 from the
baseline (y=0) up to the half-court line (y=47). The basket is at (25, 5.25).
All templates are authored for the RIGHT side; `mirror()` flips x across 25 for the left.
"""

import math

WIDTH = 50.0
LENGTH = 47.0
BASKET = (25.0, 5.25)
FREE_THROW_Y = 19.0
LANE_X = (17.0, 33.0)
ARC_RADIUS = 19.75  # the arc we draw (youth); nothing depends on it

MIN_GAP = 3.0  # no two players closer than this at any beat (validator "overlap")

# Max speed in ft/s per age group (validator "too_fast") and the tempo multiplier applied to
# every beat duration (younger kids move slower, so each beat lasts longer).
SPEED_LIMIT = {"u8": 12.0, "u10": 14.0, "u12": 16.0, "u14": 18.0, "u16": 20.0}
TEMPO = {"u8": 1.25, "u10": 1.12, "u12": 1.0, "u14": 0.92, "u16": 0.85}
AGE_GROUPS = list(SPEED_LIMIT)
SIDES = ("left", "right")
PLAYERS_PER_SIDE = (3, 4, 5)

# Named spots for the right-side version of every play (left is a mirror).
TOP = (25.0, 30.0)
RIGHT_SLOT = (33.0, 29.0)
LEFT_SLOT = (17.0, 29.0)
RIGHT_WING = (40.0, 21.0)
LEFT_WING = (10.0, 21.0)
RIGHT_CORNER = (46.0, 6.0)
LEFT_CORNER = (4.0, 6.0)
RIGHT_ELBOW = (33.0, 19.0)
LEFT_ELBOW = (17.0, 19.0)
RIGHT_BLOCK = (31.0, 8.0)
LEFT_BLOCK = (19.0, 8.0)
RIM = (26.5, 7.5)  # where a finisher stands for a layup


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def toward(p, target, d):
    """The point `d` feet from `p` in the direction of `target` (never past `target`)."""
    full = dist(p, target)
    if full <= d or full == 0:
        return (float(target[0]), float(target[1]))
    f = d / full
    return (p[0] + (target[0] - p[0]) * f, p[1] + (target[1] - p[1]) * f)


def away(p, spot, d):
    """The point `d` feet from `p` in the direction of `spot` (past `spot` if needed)."""
    full = dist(p, spot)
    if full == 0:
        return (p[0], p[1] + d)
    f = d / full
    return (p[0] + (spot[0] - p[0]) * f, p[1] + (spot[1] - p[1]) * f)


def guard(man, ball, on_ball):
    """A plausible man-to-man spot: between the man and the basket.

    On the ball: 4 ft off the man toward the basket. A man near the basket (post or cutter)
    is guarded from behind, 3.5 ft toward the basket. Off the ball elsewhere: 6 ft off the
    man, shaded toward the ball (the classic ball-you-man triangle).
    """
    if on_ball:
        return toward(man, BASKET, 4.0)
    if dist(man, BASKET) < 12.0:
        return toward(man, BASKET, 3.5)
    help_point = (0.6 * BASKET[0] + 0.4 * ball[0], 0.6 * BASKET[1] + 0.4 * ball[1])
    return toward(man, help_point, 6.0)


def mirror_x(p):
    return (WIDTH - p[0], p[1])


def clamp_to_court(p):
    return (min(max(p[0], 0.5), WIDTH - 0.5), min(max(p[1], 0.5), LENGTH - 0.5))


def path_length(points):
    return sum(dist(points[i], points[i + 1]) for i in range(len(points) - 1))
