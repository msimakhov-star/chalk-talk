"""Key-value state: a modal.Dict inside a Modal container, a plain dict elsewhere.

Keys (CONTRACTS.md section 5): play:{id}, team:{id}, playbook:{team_id} (list of
PlaySummary), tv:{code}. The demo team team_demo00 is seeded on first use.
"""

import datetime as dt
import logging
import os
import secrets

log = logging.getLogger("chalk.state")

DEMO_TEAM_ID = "team_demo00"
DEMO_PLAYS = [  # (template, params, tags) saved into the demo playbook
    ("pick_and_roll", {"side": "right"}, ["screens", "half court"]),
    ("backdoor_cut", {"side": "left"}, ["cuts", "passing"]),
    ("give_and_go", {"side": "right"}, ["passing", "cuts"]),
    ("horns", {"side": "right"}, ["screens", "set play"]),
]


def now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix):
    return f"{prefix}_{secrets.token_hex(3)}"


def _open_modal_dict():
    """A modal.Dict only when this process runs inside Modal; local dev stays in memory."""
    if os.environ.get("CHALK_STATE", "auto") == "memory":
        return None
    try:
        import modal
        if modal.is_local() and os.environ.get("CHALK_STATE") != "modal":
            return None
        return modal.Dict.from_name("chalk-talk-state", create_if_missing=True)
    except Exception as exc:  # no modal, no token, no network
        log.warning("modal.Dict unavailable (%s); using in-memory state", exc)
        return None


class Store:
    def __init__(self):
        self._dict = _open_modal_dict()
        self.backend = "modal" if self._dict is not None else "memory"
        if self._dict is None:
            self._dict = {}

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def put(self, key, value):
        if self.backend == "modal":
            self._dict.put(key, value)
        else:
            self._dict[key] = value

    def contains(self, key):
        return key in self._dict if self.backend == "memory" else self._dict.contains(key)

    # Typed helpers so callers do not spell keys.
    def get_play(self, play_id):
        return self.get(f"play:{play_id}")

    def put_play(self, play):
        self.put(f"play:{play['id']}", play)
        return play

    def get_team(self, team_id):
        return self.get(f"team:{team_id}")

    def put_team(self, team):
        self.put(f"team:{team['id']}", team)
        return team

    def get_playbook(self, team_id):
        return self.get(f"playbook:{team_id}", [])

    def put_playbook(self, team_id, entries):
        self.put(f"playbook:{team_id}", entries)

    def get_tv(self, code):
        return self.get(f"tv:{code}")

    def put_tv(self, state):
        self.put(f"tv:{state['code']}", state)
        return state


def ensure_demo(store, engine):
    """Seed 'Cambridge Comets U12' with 4 saved plays so every judge sees a filled playbook."""
    ensure_demo_tv(store)
    if store.get_team(DEMO_TEAM_ID):
        return
    from backend.playbook import play_summary

    store.put_team({"id": DEMO_TEAM_ID, "name": "Cambridge Comets U12", "sport": "basketball",
                    "age_group": "u12", "players_per_side": 5, "created_at": now_iso()})
    entries = []
    for template, params, tags in DEMO_PLAYS:
        play = engine.build_play(template, {**params, "players_per_side": 5, "age_group": "u12"})
        play["parse"] = {"method": "rules", "confidence": 1.0, "input": f"demo: {template}"}
        store.put_play(play)
        entries.append(play_summary(play, tags))
    store.put_playbook(DEMO_TEAM_ID, entries)
    log.info("seeded demo team with %d plays", len(entries))


DEMO_TV_CODE = "KQZT"  # a TV that is always paired, so judges can say "send it to the TV" without pairing


def ensure_demo_tv(store):
    if store.get_tv(DEMO_TV_CODE):
        return
    store.put_tv({"code": DEMO_TV_CODE, "tv_id": "tv_demo00", "play_id": None, "beat_index": 0,
                  "defence": "man", "playing": False, "cursor": 0, "updated_at": now_iso(),
                  "expires_at": "2027-01-01T00:00:00Z"})
    log.info("seeded demo TV %s", DEMO_TV_CODE)
