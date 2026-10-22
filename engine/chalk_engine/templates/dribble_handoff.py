"""Dribble handoff: 1 dribbles at 2 on the wing and hands the ball off as 2 runs past."""

from ..court import LEFT_BLOCK, LEFT_CORNER, LEFT_WING, RIGHT_WING, TOP
from ..template import Template, beat


def build(c):
    ha, re = c.role("handler"), c.role("receiver")
    xha, xre = c.d(ha), c.d(re)
    h, r, xh, xr = c.lab(ha), c.lab(re), c.lab(xha), c.lab(xre)
    spare = c.fill([LEFT_WING, LEFT_CORNER, LEFT_BLOCK])
    return [
        beat("Setup", f"{h} has the ball at the top. {r} waits on the right wing.", 0,
             {ha: TOP, re: RIGHT_WING, **spare}, ha),
        beat("Dribble at", f"{h} dribbles toward {r}. {r} waits until {h} is close, then runs at him.", 2.0,
             {ha: (34, 26), re: (39.5, 22.5), **spare}, ha),
        beat("Handoff", f"{h} gives {r} the handoff and stands still. {xr} is stuck behind {h}.", 1.8,
             {ha: (36.5, 24.5), re: (33, 27.5), **spare}, re,
             via={re: [(38.5, 26.5)]},
             defence={xha: (34, 21.5), xre: (37.5, 21)}),
        beat("Attack", f"{r} turns the corner and pulls up at the free-throw line. If {xh} steps up, pass to {h} rolling.", 2.0,
             {ha: (34, 12), re: (31, 19), **spare}, re,
             defence={xha: (29.5, 15), xre: (34.5, 23)}),
    ]


def counter(c, defence):
    ha, re = c.role("handler"), c.role("receiver")
    xha, xre = c.d(ha), c.d(re)
    h, r, xh, xr = c.lab(ha), c.lab(re), c.lab(xha), c.lab(xre)
    if defence == "switch":
        return {
            2: {"assign": {xha: re, xre: ha}, "defence": {xha: (33.5, 23.5), xre: (36.5, 20.5)},
                "read": f"They switch: {xh} jumps to {r}, and {xr} stays with {h}."},
            3: {"defence": {xha: (29.5, 15.5), xre: (33, 15.5)},
                "read": f"{r} now has {xh} on him. Drive at him, or throw it in to {h}, who has {xr} behind him."},
        }
    if defence == "hedge":
        return {
            2: {"defence": {xha: (36, 29)}, "read": f"{xh} hedges: jumps out above {h} to slow {r} down. {h} is open for a second."},
            3: {"defence": {xha: (32.5, 15.5)}, "read": f"{xh} runs back to {h}. {r} keeps the dribble and pulls up, or hits {h} if {xh} is late."},
        }
    if defence == "zone":
        return {i: {"read": t} for i, t in enumerate([
            f"They are in a zone. {h} and {r} will crowd one side to pull the zone over.",
            f"{h} dribbles at the front defender on the right and {r} comes to meet him.",
            f"{r} takes the handoff. Both front defenders are on the right side now.",
            f"{r} attacks the gap in the middle, where the zone is thin.",
        ])}
    raise ValueError(f"no counter {defence!r}")


TEMPLATE = Template(
    id="dribble_handoff",
    name="Dribble handoff, right wing",
    summary="1 dribbles at 2 on the right wing and hands the ball off; 2 attacks the middle while 1 rolls.",
    roles={"handler": "P1", "receiver": "P2"},
    counters=["switch", "hedge", "zone"],
    build=build,
    counter=counter,
)
