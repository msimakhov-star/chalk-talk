"""The Template record and the Cast (which player plays which role) handed to a template."""

from dataclasses import dataclass, field
from typing import Callable

OFFENSE_IDS = ("P1", "P2", "P3", "P4", "P5")


@dataclass
class Template:
    id: str
    name: str            # may contain "right"; mirrored to "left" for side=left
    summary: str         # one sentence for the catalog and the play description
    roles: dict          # role name -> default offense id, e.g. {"ball_handler": "P1"}
    counters: list       # defences this template can be re-planned against
    build: Callable      # build(cast) -> list of raw beats (see templates/README)
    counter: Callable    # counter(cast, defence) -> {beat_index: {"assign","defence","read"}}
    extra_params: dict = field(default_factory=dict)  # non-role params, e.g. horns screen_side


class Cast:
    """Who plays what in one build: role ids, the spare players, and label helpers."""

    def __init__(self, roles, players_per_side):
        self.roles = dict(roles)                       # role -> "P3"
        self.offense = list(OFFENSE_IDS[:players_per_side])
        used = set(self.roles.values())
        self.others = [p for p in self.offense if p not in used]

    def role(self, name):
        return self.roles[name]

    @staticmethod
    def lab(pid):
        """'P3' -> '3' and 'D3' -> 'x3': the label a coach says out loud."""
        return pid[1:] if pid.startswith("P") else "x" + pid[1:]

    @staticmethod
    def d(pid):
        """The defender who guards this offense player by default."""
        return "D" + pid[1:]

    def fill(self, spots, reverse=False):
        """Put the spare players on `spots` in id order (or highest id first)."""
        ids = list(reversed(self.others)) if reverse else self.others
        return dict(zip(ids, spots))


def beat(title, read, dur, offense, ball, via=None, defence=None, assign=None):
    """One raw beat as a template writes it.

    offense: {pid: (x, y)} for every offense player.
    ball: pid holding it, or (from_pid, to_pid) for a pass completing at this beat.
    via: {pid: [(x, y), ...]} intermediate waypoints for curved runs.
    defence: {did: (x, y)} hand-placed defenders; everyone else is auto-placed.
             A counter may set a defender to None to drop the base play's hand placement.
    assign: {did: pid} who guards whom from this beat on (switches).
    """
    return {
        "title": title,
        "read": read,
        "dur": dur,
        "offense": offense,
        "ball": ball,
        "via": via or {},
        "defence": defence or {},
        "assign": assign or {},
    }
