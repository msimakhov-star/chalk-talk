"""The 8 templates, one module each. Add a template: write templates/<id>.py exposing
TEMPLATE, then list it here. The ids are fixed by CONTRACTS.md section 3."""

from . import (backdoor_cut, dribble_handoff, fast_break_3v2, flare_screen, give_and_go, horns,
               pick_and_pop, pick_and_roll)

TEMPLATES = {
    m.TEMPLATE.id: m.TEMPLATE
    for m in (pick_and_roll, pick_and_pop, backdoor_cut, give_and_go, dribble_handoff,
              flare_screen, horns, fast_break_3v2)
}
