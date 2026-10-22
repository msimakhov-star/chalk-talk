"""Pick and roll: 1 uses 5's screen on the right, 5 rolls to the basket."""

from ..court import LEFT_CORNER, LEFT_WING, RIGHT_CORNER, RIM, TOP
from ..template import Template, beat

SCREEN_SPOT = (28.5, 27.0)   # beside x1 (who stands at (25, 26) guarding the top)


def build(c):
    bh, sc = c.role("ball_handler"), c.role("screener")
    xbh, xsc = c.d(bh), c.d(sc)
    b, s, xb, xs = c.lab(bh), c.lab(sc), c.lab(xbh), c.lab(xsc)
    spare = c.fill([LEFT_WING, LEFT_CORNER, RIGHT_CORNER])
    return [
        beat("Setup", f"{b} has the ball at the top. {s} runs up to set a screen for {b}.", 0,
             {bh: TOP, sc: (33, 14), **spare}, bh),
        beat("Screen", f"{s} stands still beside {xb}, feet wide. {b} waits until the screen is set.", 2.0,
             {bh: TOP, sc: SCREEN_SPOT, **spare}, bh,
             defence={xsc: (29.5, 22.5)}),
        beat("Use it", f"{b} dribbles right, shoulder to shoulder off {s}. {xb} is stuck behind the screen.", 2.0,
             {bh: (33, 24), sc: (30, 21.5), **spare}, bh,
             via={bh: [(28.5, 30.5), (31.5, 28)]},
             defence={xbh: (29, 27), xsc: (32, 17.5)}),
        beat("Roll", f"{xs} steps up to stop the ball, so {s} is open rolling to the basket. Bounce pass to {s}.", 2.2,
             {bh: (35, 21), sc: (28, 9), **spare}, (bh, sc),
             defence={xbh: (32, 19), xsc: (31, 15)}),
        beat("Layup", f"{s} catches and lays it in. If a helper comes, the corner is open.", 1.8,
             {bh: (36, 22), sc: RIM, **spare}, sc,
             defence={xsc: (30.5, 10.5)}),
    ]


def screen_counters(c, defence, bh, sc, reads):
    """Defensive re-plans shared by every 'screen then roll' play (pick and roll, horns).

    Beat indexes: 1 screen set, 2 handler uses it, 3 pass to the roller, 4 layup.
    """
    xbh, xsc = c.d(bh), c.d(sc)
    r = reads
    if defence == "switch":
        return {
            2: {"assign": {xbh: sc, xsc: bh}, "defence": {xsc: (33.5, 20), xbh: (27.5, 18)}, "read": r["switch"][0]},
            3: {"defence": {xbh: (30, 13.5), xsc: (33, 18.5)}, "read": r["switch"][1]},
            4: {"defence": {xbh: (28.5, 11.5), xsc: None}, "read": r["switch"][2]},
        }
    if defence == "hedge":
        return {
            2: {"defence": {xsc: (36, 25)}, "read": r["hedge"][0]},
            3: {"defence": {xsc: (33, 15)}, "read": r["hedge"][1]},
        }
    if defence == "drop":
        return {
            1: {"defence": {xsc: (29, 16.5)}, "read": r["drop"][0]},
            2: {"defence": {xsc: (28.5, 13)}, "read": r["drop"][1]},
            3: {"defence": {xsc: (27.5, 12.5)}, "read": r["drop"][2]},
            4: {"defence": {xsc: (29, 10.5)}, "read": r["drop"][3]},
        }
    if defence == "zone":
        return {i: {"read": text} for i, text in enumerate(r["zone"])}
    raise ValueError(f"no counter {defence!r}")


def counter(c, defence):
    bh, sc = c.role("ball_handler"), c.role("screener")
    b, s, xb, xs = c.lab(bh), c.lab(sc), c.lab(c.d(bh)), c.lab(c.d(sc))
    reads = {
        "switch": [
            f"They switch! {xs} jumps out on {b}, and {xb} takes {s}.",
            f"{xb} is slow getting onto {s}'s back. Pass inside to {s} before help comes.",
            f"{s} catches close to the basket with {xb} behind him. Finish strong.",
        ],
        "hedge": [
            f"{xs} hedges: jumps out high to slow {b} down. {s} is open behind him.",
            f"{xs} is caught between two players. {b} hits {s} with a bounce pass.",
        ],
        "drop": [
            f"{xs} drops instead of following {s}. {b} has room to dribble.",
            f"{xs} is waiting in the paint, so {b} has room. Pull up for a short shot, or keep going.",
            f"{xs} waits in the paint for {s}. The pass is tight. Next time {b} should take the open shot.",
            f"{s} still tries the layup, but {xs} is waiting. Against a drop, {b} shoots.",
        ],
        "zone": [
            f"They are in a zone. Nobody follows {b}: the gaps between defenders are the open spots.",
            f"{s} screens the front defender on the right. Screens work on zones too.",
            f"{b} dribbles into the gap between the front defenders and looks inside.",
            f"The nearest defender steps up to the ball, so {s} slips behind him to the basket. Bounce pass.",
            "Finish before the back defenders arrive.",
        ],
    }
    return screen_counters(c, defence, bh, sc, reads)


TEMPLATE = Template(
    id="pick_and_roll",
    name="Pick and roll, right side",
    summary="1 dribbles off 5's screen on the right; 5 rolls to the basket for a bounce pass.",
    roles={"ball_handler": "P1", "screener": "P5"},
    counters=["switch", "hedge", "drop", "zone"],
    build=build,
    counter=counter,
)
