"""parse_rules(text): a keyword parser for coach phrasings. It is the no-LLM fallback, so it
is deliberately simple: the first template whose pattern matches wins, in priority order,
then side, players per side, age group and a couple of role hints are picked out."""

import re

# (template, regex, confidence). Priority order: specific plays first, generic words last.
TEMPLATE_PATTERNS = [
    ("fast_break_3v2", r"fast[ -]?break|\b3[ -]?(?:v|vs|on)[ -]?2\b|three[ -]on[ -]two|\b3[ -]?on[ -]?two\b", 0.9),
    ("horns", r"\bhorns?\b|\bhorn set\b|\bdouble high\b|\belbow screens?\b", 0.9),
    ("flare_screen", r"\bflares?\b|\bflare[ -]screen", 0.9),
    ("dribble_handoff", r"\bdho\b|\bhand[ -]?offs?\b|\bdribble hand", 0.9),
    ("give_and_go", r"give[ -]?(?:and|n|&|'n)[ -]?go|\bpass and (?:cut|follow)\b", 0.9),
    ("backdoor_cut", r"\bback[ -]?door\b|\bback[ -]?cuts?\b", 0.9),
    ("pick_and_pop", r"pick[ -]?(?:and|n|&|'n)[ -]?pop|\bpnp\b|screen[ -]and[ -]pop", 0.9),
    ("pick_and_roll", r"pick[ -]?(?:and|n|&|'n)[ -]?roll|\bpnr\b|screen[ -]and[ -]roll", 0.9),
    ("fast_break_3v2", r"\btransition\b|\bthe break\b|\brun the break\b|\bprimary break\b", 0.7),
    ("pick_and_pop", r"\bpops?\b", 0.7),
    ("pick_and_roll", r"\brolls?\b|\bball[ -]?screen|\bon[ -]ball screen", 0.7),
    ("pick_and_roll", r"\bscreens?\b|\bpicks?\b", 0.6),
]

PLAYERS_WORDS = {"three": 3, "four": 4, "five": 5}
AGE_BUCKETS = [(8, "u8"), (10, "u10"), (12, "u12"), (14, "u14")]


def parse_rules(text):
    t = (text or "").lower()
    hit = next(((tpl, conf) for tpl, pat, conf in TEMPLATE_PATTERNS if re.search(pat, t)), None)
    if hit is None:
        return None
    template, confidence = hit
    params = {}
    side = _side(t)
    if side:
        params["side"] = side
    n = _players_per_side(t)
    if n:
        params["players_per_side"] = n
    age = _age_group(t)
    if age:
        params["age_group"] = age
    params.update(_role_hints(t, template))
    return {"template": template, "params": params, "confidence": confidence}


def _side(t):
    if re.search(r"\bleft\b|\bweak[ -]side\b", t):
        return "left"
    if re.search(r"\bright\b|\bstrong[ -]side\b", t):
        return "right"
    return None


def _players_per_side(t):
    m = re.search(r"\b([345])\s*(?:v|vs|on|x|-on-|-v-)\s*\1\b", t)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(three|four|five)[ -](?:on|v|vs)[ -](three|four|five)\b", t)
    if m and m.group(1) == m.group(2):
        return PLAYERS_WORDS[m.group(1)]
    return None


def _age_group(t):
    m = (re.search(r"\bu[ -]?(\d{1,2})s?\b", t)
         or re.search(r"\bunder[ -]?(\d{1,2})s?\b", t)
         or re.search(r"\b(\d{1,2})\s*(?:u\b|and under|& under|or under|[ -]year[ -]olds?)", t))
    if not m:
        return None
    age = int(m.group(1))
    return next((group for limit, group in AGE_BUCKETS if age <= limit), "u16")


def _role_hints(t, template):
    """'4 screens' -> screener P4, '3 cuts' -> cutter P3. Only roles the template has."""
    hints = {}
    m = re.search(r"\b([1-5])\s+(?:sets|screens|screening|setting)\b", t)
    if m and template in ("pick_and_roll", "pick_and_pop", "flare_screen"):
        hints["screener"] = "P" + m.group(1)
    m = re.search(r"\b([1-5])\s+(?:cuts|cutting)\b", t)
    if m and template == "backdoor_cut":
        hints["cutter"] = "P" + m.group(1)
    m = re.search(r"\b([1-5])\s+(?:passes|passing)\b", t)
    if m and template in ("backdoor_cut", "give_and_go", "flare_screen"):
        hints["passer"] = "P" + m.group(1)
    return hints
