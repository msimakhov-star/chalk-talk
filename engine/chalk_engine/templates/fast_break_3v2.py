"""Fast break 3 on 2: 1 dribbles down the middle, 2 and 3 run the lanes, two defenders are
back in a tandem (one up, one back). Everyone else is still running back."""

from ..template import Template, beat


def build(c):
    bh = c.role("ball_handler")
    b = c.lab(bh)
    # spare players in id order: left lane, right lane, then two trailers
    lane_ids = c.others[:2]
    left, right = (c.lab(p) for p in lane_ids)
    # The first two defenders got back (one up, one deep); the third chases.
    # Any fourth and fifth defender are auto-placed trailing their own man.
    dids = [c.d(p) for p in c.offense]

    def lanes(l_xy, r_xy, t1_xy, t2_xy):
        return c.fill([l_xy, r_xy, t1_xy, t2_xy])

    def defence(front, deep, chaser):
        return dict(zip(dids[:3], [front, deep, chaser]))

    return [
        beat("Fill the lanes", f"Fast break! {b} dribbles down the middle, {left} and {right} run wide. Only two defenders are back.", 0,
             {bh: (25, 41), **lanes((7, 43), (43, 43), (16, 46.5), (34, 46.5))}, bh,
             defence=defence((25, 17), (25, 9), (25, 46.5))),
        beat("Attack", f"{b} dribbles hard to the free-throw line. {left} and {right} run to the wings, staying wide.", 2.2,
             {bh: (25, 25), **lanes((8, 27), (42, 27), (14, 36), (36, 36))}, bh,
             defence=defence((25, 21), (25, 9), (25, 33))),
        beat("Pass", f"{b} stops at the free-throw line and passes to {right}. The back defender has to come out to {right}.", 1.8,
             {bh: (25, 22), **lanes((10, 14), (40, 14), (14, 30), (36, 30))}, (bh, lane_ids[1]),
             defence=defence((25, 18), (36.1, 11.7), (25, 28))),
        beat("Read", f"The back defender came out, so {left} is open under the basket. {right} passes to {left}.", 1.8,
             {bh: (25, 22), **lanes((21, 8), (40, 14), (16, 27), (34, 27))}, (lane_ids[1], lane_ids[0]),
             defence=defence((29, 14), (36.1, 11.7), (26, 26.5))),
        beat("Layup", f"{left} catches and lays it in. Three attackers beat two defenders when the ball moves fast.", 1.8,
             {bh: (25, 19), **lanes((23.5, 7), (37, 9.5), (16, 24), (34, 24))}, lane_ids[0],
             defence=defence((27, 11), (34, 12), (26, 24))),
    ]


def counter(c, defence):
    raise ValueError("fast_break_3v2 has no counters: the defence is already two players back")


TEMPLATE = Template(
    id="fast_break_3v2",
    name="Fast break 3 on 2",
    summary="1 pushes the ball down the middle with 2 and 3 wide; two defenders are back, so the ball moves until someone is open.",
    roles={"ball_handler": "P1"},
    counters=[],
    build=build,
    counter=counter,
)
