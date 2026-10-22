"""Pick and pop: same screen as the pick and roll, but 5 steps out for a shot."""

from ..court import LEFT_CORNER, LEFT_WING, RIGHT_CORNER, TOP
from ..template import Template, beat
from .pick_and_roll import SCREEN_SPOT

POP_SPOT = (38.0, 27.0)  # beyond the arc on the right


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
        beat("Use it", f"{b} dribbles right off the screen. {s} holds the screen one count instead of rolling.", 2.0,
             {bh: (33, 24), sc: (29.5, 25), **spare}, bh,
             via={bh: [(28.5, 30.5), (31.5, 28)]},
             defence={xbh: (26.5, 27.5), xsc: (32, 17.5)}),
        beat("Pop", f"{xs} steps up to stop {b}, so {s} pops to the three-point line. Kick the pass out to {s}.", 2.0,
             {bh: (31.5, 18), sc: POP_SPOT, **spare}, (bh, sc),
             defence={xbh: (31, 22), xsc: (29.5, 14.5)}),
        beat("Shoot", f"{s} catches with feet set and shoots. {b} watches {xs}: whoever he leaves is open.", 1.8,
             {bh: (31.5, 18), sc: POP_SPOT, **spare}, sc,
             defence={xbh: (30.5, 21.5), xsc: (34, 22.5)}),
    ]


def counter(c, defence):
    bh, sc = c.role("ball_handler"), c.role("screener")
    xbh, xsc = c.d(bh), c.d(sc)
    b, s, xb, xs = c.lab(bh), c.lab(sc), c.lab(xbh), c.lab(xsc)
    if defence == "switch":
        return {
            2: {"assign": {xbh: sc, xsc: bh}, "defence": {xsc: (33.5, 20), xbh: (27, 22)},
                "read": f"They switch: {xs} takes {b}, and {xb} stays with {s}."},
            3: {"read": f"{xb} follows {s} outside, so the pop is covered. {b} has {xs} on him now: drive past him next time."},
            4: {"read": f"{s} has {xb} closing out. Fake the shot, then drive past him or swing the ball."},
        }
    if defence == "hedge":
        return {
            2: {"defence": {xsc: (36, 25)}, "read": f"{xs} hedges: jumps out high to slow {b}. {s} is wide open behind him for a second."},
            3: {"defence": {xsc: (34, 20)}, "read": f"{xs} runs back out to {s}. Pass quickly, before he gets there."},
            4: {"defence": {xsc: (35.5, 24)}, "read": f"{s} catches with {xs} flying at him. Fake, then drive or pass."},
        }
    if defence == "drop":
        return {
            1: {"defence": {xsc: (29, 16.5)}, "read": f"{xs} drops instead of following {s}. {b} has room to dribble."},
            2: {"defence": {xsc: (28.5, 13)}, "read": f"{xs} waits in the paint. {b} has room, and this is why {s} pops instead of rolling."},
            3: {"defence": {xsc: (28.5, 13.5)}, "read": f"{xs} stayed back, so {s} is wide open on the pop. Kick it out."},
            4: {"defence": {xsc: (34.5, 21.5)}, "read": f"{s} shoots before {xs} can get out there. Against the drop, the pop is open."},
        }
    if defence == "zone":
        return {i: {"read": t} for i, t in enumerate([
            f"They are in a zone. Nobody follows {b}: the gaps between defenders are the open spots.",
            f"{s} screens the front defender on the right. Screens work on zones too.",
            f"{b} dribbles into the gap between the front defenders.",
            f"The nearest defender steps up to {b}, so {s} is open outside. Kick it out.",
            f"Zone defenders are slow to run out. {s} shoots with feet set.",
        ])}
    raise ValueError(f"no counter {defence!r}")


TEMPLATE = Template(
    id="pick_and_pop",
    name="Pick and pop, right side",
    summary="1 dribbles off 5's screen on the right; 5 pops out to the three-point line for a shot.",
    roles={"ball_handler": "P1", "screener": "P5"},
    counters=["switch", "hedge", "drop", "zone"],
    build=build,
    counter=counter,
)
