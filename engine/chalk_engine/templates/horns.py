"""Horns: 4 and 5 at the elbows like two horns. 1 uses 5's screen; 5 rolls, 4 pops."""

from ..court import LEFT_ELBOW, RIGHT_ELBOW, RIM, TOP
from ..template import Template, beat
from .pick_and_roll import SCREEN_SPOT, screen_counters

LEFT_CORNER_H = (5.0, 7.0)
RIGHT_CORNER_H = (45.0, 7.0)


def _cast(c):
    """The highest spare player screens from the right elbow, the next one is the other horn."""
    spare = c.fill([RIGHT_ELBOW, LEFT_ELBOW, RIGHT_CORNER_H, LEFT_CORNER_H], reverse=True)
    screener, horn = list(reversed(c.others))[:2]
    return spare, screener, horn


def build(c):
    bh = c.role("ball_handler")
    spare, sc, horn = _cast(c)
    xbh, xsc = c.d(bh), c.d(sc)
    b, s, h, xb, xs = c.lab(bh), c.lab(sc), c.lab(horn), c.lab(xbh), c.lab(xsc)
    corners = {pid: xy for pid, xy in spare.items() if pid not in (sc, horn)}
    return [
        beat("Horns", f"{s} and {h} stand at the corners of the free-throw line, like two horns. {b} has the ball at the top.", 0,
             {bh: TOP, sc: RIGHT_ELBOW, horn: LEFT_ELBOW, **corners}, bh),
        beat("Screen", f"{s} comes up and sets a screen on {xb}. {h} waits at the other corner of the free-throw line.", 1.8,
             {bh: TOP, sc: SCREEN_SPOT, horn: LEFT_ELBOW, **corners}, bh,
             defence={xsc: (29.5, 22.5)}),
        beat("Use it", f"{b} dribbles right off {s}'s screen. {s} rolls to the basket and {h} pops to the top.", 2.0,
             {bh: (33, 24), sc: (30, 21.5), horn: (18, 28), **corners}, bh,
             via={bh: [(28.5, 30.5), (31.5, 28)]},
             defence={xbh: (29, 27), xsc: (32, 17.5)}),
        beat("Read", f"Two choices: {s} rolling, or {h} open at the top. {xs} stepped up, so {b} passes to {s}.", 2.0,
             {bh: (35, 21), sc: (28, 9), horn: (18, 28), **corners}, (bh, sc),
             defence={xbh: (32, 19), xsc: (31, 15)}),
        beat("Layup", f"{s} catches and lays it in. If {xs} had stayed back, {h} was open at the top.", 1.8,
             {bh: (36, 22), sc: RIM, horn: (18, 28), **corners}, sc,
             defence={xsc: (30.5, 10.5)}),
    ]


def counter(c, defence):
    bh = c.role("ball_handler")
    _, sc, horn = _cast(c)
    b, s, h, xb, xs = c.lab(bh), c.lab(sc), c.lab(horn), c.lab(c.d(bh)), c.lab(c.d(sc))
    reads = {
        "switch": [
            f"They switch! {xs} jumps out on {b}, and {xb} takes {s}.",
            f"{xb} is slow getting onto {s}'s back. Pass inside to {s}, or to {h} at the top.",
            f"{s} catches close to the basket with {xb} behind him. Finish strong.",
        ],
        "hedge": [
            f"{xs} hedges: jumps out high to slow {b}. {s} is open behind him, {h} is open at the top.",
            f"{xs} is caught between two players. {b} hits {s} with a bounce pass.",
        ],
        "drop": [
            f"{xs} drops instead of following {s}. {b} has room to dribble.",
            f"{xs} is waiting in the paint, so {b} has room. Pull up for a short shot, or swing it to {h}.",
            f"{xs} waits in the paint for {s}. The pass is tight. Next time {b} should take the open shot.",
            f"{s} still tries the layup, but {xs} is waiting. Against a drop, {b} shoots or finds {h}.",
        ],
        "zone": [
            f"They are in a zone. {s} and {h} stand at the free-throw line corners, in the middle of it.",
            f"{s} screens the front defender on the right. Screens work on zones too.",
            f"{b} dribbles into the gap between the front defenders. {h} pops to the top.",
            f"The nearest defender steps up to the ball, so {s} slips behind him to the basket. Bounce pass.",
            "Finish before the back defenders arrive.",
        ],
    }
    return screen_counters(c, defence, bh, sc, reads)


TEMPLATE = Template(
    id="horns",
    name="Horns, screen on the right",
    summary="Two players start at the elbows like horns. 1 uses the right-elbow screen; the screener rolls, the other horn pops.",
    roles={"ball_handler": "P1"},
    counters=["switch", "hedge", "drop", "zone"],
    build=build,
    counter=counter,
    extra_params={"screen_side": {"type": "string", "enum": ["left", "right"], "default": "right",
                                  "description": "Which elbow screens; same as side."}},
)
