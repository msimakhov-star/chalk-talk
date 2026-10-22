"""Give and go: 1 passes to 3 on the wing, cuts to the basket and gets it back."""

from ..court import LEFT_BLOCK, LEFT_CORNER, LEFT_WING, RIGHT_WING, RIM, TOP
from ..template import Template, beat


def build(c):
    pa, re = c.role("passer"), c.role("receiver")
    xpa = c.d(pa)
    p, r, xp = c.lab(pa), c.lab(re), c.lab(xpa)
    spare = c.fill([LEFT_WING, LEFT_CORNER, LEFT_BLOCK])
    return [
        beat("Setup", f"{p} has the ball at the top. {r} is on the right wing, hands ready.", 0,
             {pa: TOP, re: RIGHT_WING, **spare}, pa),
        beat("Give", f"{p} passes to {r}. {xp} turns to look at the ball. That is the moment.", 1.8,
             {pa: TOP, re: RIGHT_WING, **spare}, (pa, re)),
        beat("Go", f"{p} fakes left, then cuts hard in front of {xp} to the basket. Hand up, calling for the ball.", 2.0,
             {pa: (28, 14), re: RIGHT_WING, **spare}, re,
             via={pa: [(22.5, 27.5)]},
             defence={xpa: (25, 20)}),
        beat("Get it back", f"{r} sees {p} ahead of {xp} and throws a bounce pass to the hand that is up.", 1.8,
             {pa: (27, 9), re: RIGHT_WING, **spare}, (re, pa),
             defence={xpa: (27, 14)}),
        beat("Layup", f"{p} catches and lays it in. Give it, go, get it back.", 1.8,
             {pa: RIM, re: RIGHT_WING, **spare}, pa,
             defence={xpa: (28.5, 11.5)}),
    ]


def counter(c, defence):
    pa, re = c.role("passer"), c.role("receiver")
    xpa, xre = c.d(pa), c.d(re)
    p, r, xp, xr = c.lab(pa), c.lab(re), c.lab(xpa), c.lab(xre)
    if defence == "switch":
        return {
            3: {"assign": {xre: pa, xpa: re}, "defence": {xre: (29, 12.5), xpa: (33, 20)},
                "read": f"{xr} leaves {r} to stop {p}'s cut, and {xp} switches out to {r}. The pass is risky now."},
            4: {"defence": {xre: (28.5, 11), xpa: (36.5, 18.5)},
                "read": f"{xr} is waiting at the basket. Next time, {r} shoots as soon as {xr} leaves him."},
        }
    if defence == "zone":
        return {i: {"read": t} for i, t in enumerate([
            f"They are in a zone. {p} and {r} look for the gaps between the defenders.",
            f"{p} passes to {r}. In a zone nobody follows {p}, so the cut is open if the middle is empty.",
            f"{p} cuts through the middle of the zone, straight past the front defenders.",
            f"{r} passes inside before the middle defender slides over.",
            "Lay it in before the back defenders arrive.",
        ])}
    raise ValueError(f"no counter {defence!r}")


TEMPLATE = Template(
    id="give_and_go",
    name="Give and go, right wing",
    summary="1 passes to 3 on the right wing, cuts past his defender to the basket and gets the ball back.",
    roles={"passer": "P1", "receiver": "P3"},
    counters=["switch", "zone"],
    build=build,
    counter=counter,
)
