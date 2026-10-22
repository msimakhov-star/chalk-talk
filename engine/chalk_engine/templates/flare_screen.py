"""Flare screen: 4 screens for 2 at the top, 2 fades away from the ball to the right wing,
and 1 throws the long pass for the shot."""

from ..court import LEFT_BLOCK, LEFT_CORNER
from ..template import Template, beat

PASSER_SPOT = (18.0, 30.0)
SHOOTER_START = (30.0, 30.0)
SCREENER_START = (36.0, 18.0)
FLARE_SPOT = (30.5, 26.0)
SHOT_SPOT = (41.0, 22.0)


def build(c):
    sh, sc, pa = c.role("shooter"), c.role("screener"), c.role("passer")
    xsh, xsc = c.d(sh), c.d(sc)
    s, k, p, xs = c.lab(sh), c.lab(sc), c.lab(pa), c.lab(xsh)
    spare = c.fill([LEFT_CORNER, LEFT_BLOCK])
    return [
        beat("Setup", f"{p} has the ball on the left. {s} is at the top, and {k} is near the free-throw line on the right.", 0,
             {pa: PASSER_SPOT, sh: SHOOTER_START, sc: SCREENER_START, **spare}, pa,
             defence={xsh: (27.5, 25)}),
        beat("Set it up", f"{k} comes up and stands still behind {xs}. {s} takes one step toward the ball, as if coming to catch.", 1.8,
             {pa: PASSER_SPOT, sh: (28, 30), sc: FLARE_SPOT, **spare}, pa,
             defence={xsh: (27.5, 25), xsc: (33, 22.5)}),
        beat("Flare", f"{s} runs off the flare to the right wing. {xs} is stuck behind {k}.", 2.0,
             {pa: PASSER_SPOT, sh: SHOT_SPOT, sc: FLARE_SPOT, **spare}, pa,
             via={sh: [(33, 30), (38, 26)]},
             defence={xsh: (29.5, 22.5), xsc: (33, 22.5)}),
        beat("Long pass", f"{p} throws a long pass over the top to {s}. {xs} is a step late.", 1.8,
             {pa: PASSER_SPOT, sh: SHOT_SPOT, sc: FLARE_SPOT, **spare}, (pa, sh),
             defence={xsh: (35, 23.5), xsc: (32, 20)}),
        beat("Shoot", f"{s} catches with feet set and shoots. {k} slips to the basket for the rebound.", 1.8,
             {pa: PASSER_SPOT, sh: SHOT_SPOT, sc: (31, 12), **spare}, sh,
             defence={xsh: (38, 23), xsc: (30, 16)}),
    ]


def counter(c, defence):
    sh, sc, pa = c.role("shooter"), c.role("screener"), c.role("passer")
    xsh, xsc = c.d(sh), c.d(sc)
    s, k, p, xs, xk = c.lab(sh), c.lab(sc), c.lab(pa), c.lab(xsh), c.lab(xsc)
    if defence == "switch":
        return {
            2: {"assign": {xsc: sh, xsh: sc}, "defence": {xsc: (37, 25)},
                "read": f"They switch: {xk} runs out to {s}. {k} now has {xs} behind him: slip to the basket."},
            3: {"defence": {xsc: (38, 24), xsh: (29.5, 22.5)},
                "read": f"The switch took away the shot. {p} should look for {k} slipping inside instead."},
            4: {"defence": {xsc: (38.5, 24.5), xsh: (29.5, 16)},
                "read": f"{s} shoots over {xk} anyway. Next time, hit {k} on the slip."},
        }
    if defence == "zone":
        return {i: {"read": t} for i, t in enumerate([
            f"They are in a zone. {p} holds the ball on the left to pull the zone over.",
            f"{k} screens the defender nearest the right wing.",
            f"{s} fades to the right wing, where the zone is thin.",
            f"{p} throws the long pass before the zone shifts over.",
            f"{s} shoots before the defender can run out to him.",
        ])}
    raise ValueError(f"no counter {defence!r}")


TEMPLATE = Template(
    id="flare_screen",
    name="Flare screen, right wing",
    summary="4 flare-screens for 2 at the top; 2 fades to the right wing for a long pass from 1 and a shot.",
    roles={"shooter": "P2", "screener": "P4", "passer": "P1"},
    counters=["switch", "zone"],
    build=build,
    counter=counter,
)
