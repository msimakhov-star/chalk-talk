"""narrate(play): make every read something a 10-year-old follows.

Templates write reads in plain words. This pass adds a one-time gloss the first time a
basketball word appears in a play, and enforces the contract limits (read under 140
characters, title under 24).
"""

import re

READ_LIMIT = 140
TITLE_LIMIT = 24

# word -> gloss, added in brackets the first time the word shows up in a play.
GLOSSARY = {
    "screen": "stand still so the defender bumps into you",
    "backdoor": "cut behind your defender to the basket",
    "handoff": "hand the ball to a teammate running past",
    "flare": "a screen that sends the shooter away from the ball",
    "switch": "the defenders swap who they guard",
    "hedge": "the screener's defender jumps out, then runs back",
    "drop": "the screener's defender backs up toward the basket",
    "zone": "each defender guards an area, not a player",
    "paint": "the box under the basket",
    "pop": "step out for a shot",
}


def narrate(play):
    seen = set()
    for b in play["beats"]:
        read = b["read"]
        inserts = []  # (position, gloss) found on the original text, applied back to front
        for word, gloss in GLOSSARY.items():
            if word in seen or f"({gloss})" in read:
                seen.add(word)
                continue
            m = re.search(rf"\b{word}(?:s|es)?\b", read, flags=re.IGNORECASE)
            if m:
                seen.add(word)
                inserts.append((m.end(), gloss))
        for pos, gloss in sorted(inserts, reverse=True):
            read = read[:pos] + f" ({gloss})" + read[pos:]
        b["read"] = read
        if len(read) > READ_LIMIT:
            raise ValueError(f"{play['template']} beat {b['index']}: read is {len(read)} chars: {read!r}")
        if len(b["title"]) > TITLE_LIMIT:
            raise ValueError(f"{play['template']} beat {b['index']}: title too long: {b['title']!r}")
    return play
