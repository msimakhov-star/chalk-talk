"""Backdoor cut: x2 denies the pass to the wing, so 2 cuts behind him to the basket."""

from ..court import LEFT_BLOCK, LEFT_CORNER, LEFT_WING, RIGHT_WING, RIM, TOP
from ..template import Template, beat


def build(c):
    pa, cu = c.role("passer"), c.role("cutter")
    xcu = c.d(cu)
    p, k, xk = c.lab(pa), c.lab(cu), c.lab(xcu)
    spare = c.fill([LEFT_WING, LEFT_CORNER, LEFT_BLOCK])
    return [
        beat("Setup", f"{p} has the ball at the top. {xk} is denying the pass to {k} on the right wing: a hand in the way.", 0,
             {pa: TOP, cu: RIGHT_WING, **spare}, pa,
             defence={xcu: (37, 23)}),
        beat("Fake", f"{p} dribbles toward {k}. {k} walks up to the ball as if to catch it. {xk} is still reaching for the pass.", 1.8,
             {pa: (28, 29), cu: (37, 25), **spare}, pa,
             defence={xcu: (34, 26.5)}),
        beat("Backdoor", f"{k} plants and cuts backdoor. {p} throws a bounce pass to the hand away from {xk}.", 1.8,
             {pa: (29, 28), cu: (33, 12), **spare}, (pa, cu),
             via={cu: [(39, 22)]},
             defence={xcu: (35, 23)}),
        beat("Layup", f"{k} lays it in with the inside hand. If a helper steps in, look for the open teammate.", 1.8,
             {pa: (29, 28), cu: RIM, **spare}, cu,
             defence={xcu: (31.5, 14.5)}),
    ]


def counter(c, defence):
    pa, cu = c.role("passer"), c.role("cutter")
    xpa, xcu = c.d(pa), c.d(cu)
    p, k, xp, xk = c.lab(pa), c.lab(cu), c.lab(xpa), c.lab(xcu)
    if defence == "switch":
        return {
            2: {"assign": {xpa: cu, xcu: pa}, "defence": {xpa: (30.5, 9.5), xcu: (31.5, 24)},
                "read": f"{xp} sees the cut and runs back to take {k}. {xk} switches onto {p}. The lane is closed: hold the pass."},
            3: {"defence": {xpa: (28.5, 11.5), xcu: None},
                "read": f"When they switch, {p} is open at the top for a moment. Next time, {k} kicks it back out."},
        }
    if defence == "zone":
        return {i: {"read": t} for i, t in enumerate([
            f"They are in a zone, so nobody denies {k}. Cut through the gaps instead.",
            f"{p} dribbles at the front defender on the right to pull him out.",
            f"{k} cuts to the basket through the gap behind the front defenders. {p} passes if the middle is open.",
            "Finish quickly: the back defenders are close.",
        ])}
    raise ValueError(f"no counter {defence!r}")


TEMPLATE = Template(
    id="backdoor_cut",
    name="Backdoor cut, right wing",
    summary="x2 overplays 2 on the right wing; 2 cuts behind him to the basket for a bounce pass from 1.",
    roles={"passer": "P1", "cutter": "P2"},
    counters=["switch", "zone"],
    build=build,
    counter=counter,
)
