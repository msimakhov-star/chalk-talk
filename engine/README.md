# chalk_engine

The play engine behind Chalk Talk. Pure Python, no dependencies, runs on 3.12 and 3.14.

```python
from chalk_engine import TEMPLATES, build_play, counter_play, validate, parse_rules, template_catalog, mirror, narrate

play = build_play("pick_and_roll", {"side": "right", "players_per_side": 5, "age_group": "u12"})
play["validity"]            # {"ok": True, "issues": []}
switch = counter_play(play, "switch")   # same offense, re-planned defence, new reads
parse_rules("backdoor cut from the left wing, u10")
# {"template": "backdoor_cut", "params": {"side": "left", "age_group": "u10"}, "confidence": 0.9}
```

Run the checks from this directory:

```
python3 -m pytest -q        # or, without pytest:
python3 -m unittest -v
```

## What a template is

A template is one basketball play written as 3 to 6 **beats**. Each beat says where every
offense player stands, who has the ball (or which pass is in the air), how long the beat lasts,
a short title, and "the read": one or two sentences a 10-year-old understands. The engine
fills in the rest:

- **Roles.** `params` name who plays each role (`ball_handler`, `screener`, ...). In 3v3 or
  4v4 a role whose default player is missing is remapped to the highest free player and the
  play's `description` says so ("3v3: 3 plays screener instead of 5").
- **Defence.** The template only hand-places the defenders who matter at that beat (the one
  stuck on the screen, the one stepping up). Every other defender is auto-placed between his
  man and the basket (`court.guard`), then nudged apart so nobody is within 3 ft
  (`defence.settle`).
- **Counters.** `switch` swaps assignments, `hedge` and `drop` move the screener's defender,
  `zone` replaces man-to-man with a 2-3 zone (box with 4 defenders, triangle with 3). A counter
  never moves the offense; it re-plans the defenders and rewrites the reads.
- **Side.** Every template is written for the right side. `side: "left"` is `mirror()`:
  x becomes 50 - x and the words "left" and "right" swap in every read. Write reads so that
  "left" and "right" only ever mean the side of the court.
- **Age.** `age_group` scales every beat duration (`court.TEMPO`) and the speed limit the
  validator enforces (`court.SPEED_LIMIT`). Beats last 1.5 to 3 s at every age.
- **Narration.** `narrate()` adds a one-time gloss the first time a basketball word appears in
  a play ("screen (stand still so the defender bumps into you)") and fails the build if a read
  is over 140 characters or a title over 24.
- **Validation.** `validate()` returns the contract's issue list: `out_of_bounds`, `overlap`
  (under 3 ft), `too_fast` (path length / dt over the age limit), `ball_orphan`,
  `missing_player`. The test suite builds every template x side x players x age x counter
  (870 plays) and asserts all of them are valid.

## Coordinate system

Half court in feet. Looking from the baseline toward half court, the origin is the left
corner of the baseline. Templates are drawn for the right side.

```
 y=47 |-------------------------------------------------| half-court line
      |                                                 |
      |                        1 (25,30) "top"          |
      |  (10,21)                                (40,21) |
      |  left wing                           right wing |
 y=19 |             +-----------------------+           | free-throw line
      |   (4,6)     |(17..33)   lane        |   (46,6)  |
      | left corner |   (19,8)     (31,8)   | right cnr |
      |             |  left blk  right blk  |           |
      |             |         O (25,5.25)   |           | basket
 y=0  +-------------+-----------------------+-----------+ baseline
     x=0                                               x=50
```

`court.py` names the spots (`TOP`, `RIGHT_WING`, `LEFT_BLOCK`, `RIM`...). Offense ids are
`P1..P5` (labels "1".."5"), defenders `D1..D5` (labels "x1".."x5"), `Dn` guards `Pn` unless a
switch says otherwise.

## How to add a template

1. Copy `chalk_engine/templates/give_and_go.py` to `templates/<id>.py`.
2. Write `build(cast)`: return 3 to 6 `beat(...)` records with every offense player placed at
   every beat (use `cast.fill([...])` to park the spare players on named spots), the ball
   holder or `(passer, receiver)` for a pass, `via=` waypoints for curved runs, and `defence=`
   for the defenders you want to place by hand. Keep players 12 to 18 ft apart in the setup,
   screeners 3 to 4 ft from the defender, beats 1.8 to 2.4 s.
3. Write `counter(cast, defence)`: for each counter return `{beat_index: {"assign": {...},
   "defence": {...}, "read": "..."}}`. Set a defender to `None` to drop the base play's hand
   placement for that beat. Zone needs reads only; positions are computed.
4. Fill in `TEMPLATE = Template(id=..., name=..., summary=..., roles=..., counters=...)` and
   add the module to `templates/__init__.py`.
5. Run `python3 -m pytest -q`. The matrix test will tell you exactly which beat, player and
   age group breaks a rule; move the point and rerun.

## Rules parser

`parse_rules(text)` is the no-LLM fallback. It matches template phrases in priority order
(specific plays like "horns" or "flare" before generic words like "screen"), then picks out
`side` ("left", "right", "strong side" = right, "weak side" = left), `players_per_side`
("3v3", "four on four"), `age_group` ("u10", "under 12", "12 and under", "9 year olds") and a
few role hints ("4 screens", "3 cuts", "1 passes"). The 40 phrasings in
`tests/phrasings.json` are the fixture the contract requires.
