"""Grow 40 hand-written seeds (seeds.json) to 300 labelled coach phrasings (phrasings.json).

A local Ollama model writes candidate phrasings for a requested (template, side, size, age);
the label is the request. Filters: the side word must be present (or absent for "unspecified",
labelled "right", the engine's default), no near-duplicates (difflib ratio >= 0.85), length 3..30
words. The final file is shuffled with a fixed seed so any prefix (--limit) is a mixed sample.

    python3 eval/gen_phrasings.py [--model gemma4:12b-nvfp4] [--per-call 14]
"""

import argparse
import difflib
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llmcall import OLLAMA_URL, chat  # noqa: E402

HERE = Path(__file__).resolve().parent
TOTAL = 300
DESCRIPTIONS = {
    "pick_and_roll": "a ball screen: a teammate screens the dribbler's defender, then rolls to the basket",
    "pick_and_pop": "a ball screen where the screener steps out (pops) to the perimeter for a jump shot instead of rolling",
    "backdoor_cut": "a wing player who is being overplayed fakes toward the ball, then cuts behind the defender to the basket for a pass",
    "give_and_go": "a player passes to a teammate, cuts to the basket, and gets the ball straight back",
    "dribble_handoff": "the ball handler dribbles toward a teammate and hands the ball off to him as he runs past",
    "flare_screen": "an off-ball screen where the shooter drifts away from the ball to the wing or corner for a shot",
    "horns": "a set with two bigs at the elbows; the guard uses a screen from one of them",
    "fast_break_3v2": "transition after a rebound or steal: three attackers run against two defenders",
}
SIDE_RULE = {
    "left": "Every phrasing must say the play is on the LEFT side (use the word 'left'). Never use the word 'right'.",
    "right": "Every phrasing must say the play is on the RIGHT side (use the word 'right'). Never use the word 'left'.",
    "unspecified": "Do NOT mention a side: never use the words 'left', 'right', 'strong side' or 'weak side'.",
}


def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def side_ok(text, side):
    has_l = re.search(r"\bleft\b|\bweak[ -]side\b", text, re.I)
    has_r = re.search(r"\bright\b|\bstrong[ -]side\b", text, re.I)
    if side == "unspecified":
        return not has_l and not has_r
    return bool(has_l if side == "left" else has_r) and not (has_r if side == "left" else has_l)


def generate(model, per_call, rng):
    seeds = json.loads((HERE / "seeds.json").read_text())
    out = []
    for template, desc in DESCRIPTIONS.items():
        examples = [s["text"] for s in seeds if s["template"] == template]
        for side in ("left", "right", "unspecified"):
            n = rng.choice([3, 4, 5])
            age = rng.choice(["u8", "u10", "u12", "u14", "u16"])
            prompt = (
                f"You write test data. A volunteer youth basketball coach ({age}, {n} on {n}) is asking an app to draw a play: "
                f"{desc}.\nWrite {per_call} different things the coach might type or say, 4 to 25 words each. "
                "Vary them a lot: some use the play's usual name or slang, some only describe the action, some casual, "
                "some mention the age group or team size, some give a reason. "
                f"{SIDE_RULE[side]}\nStyle examples (do not copy): " + " | ".join(examples)
            )
            prompt += '\nReply with JSON only: {"phrasings": ["...", "..."]}'
            # JSON mode, not a schema: Ollama's schema-constrained decoding ran at ~1 token/s here
            r = chat("gen", OLLAMA_URL, model, [{"role": "user", "content": prompt}], None,
                     max_tokens=900, temperature=0.9, timeout=900, extra={"seed": 7}, native=True)
            try:
                texts = json.loads(r["content"])["phrasings"]
            except Exception:
                print(f"  {template}/{side}: unparseable reply ({r['error'] or (r['content'] or '')[:80]})")
                continue
            print(f"  {template}/{side}: {len(texts)} candidates ({r['latency']}s)", flush=True)
            for t in texts:
                out.append({"text": t.strip(), "template": template, "side": "right" if side == "unspecified" else side,
                            "players_per_side": n, "age_group": age, "source": f"{model}", "side_stated": side != "unspecified"})
    return seeds, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma4:12b-nvfp4")
    ap.add_argument("--per-call", type=int, default=14)
    args = ap.parse_args()
    rng = random.Random(0)
    seeds, cands = generate(args.model, args.per_call, rng)
    kept = [{**s, "source": "hand", "side_stated": bool(re.search(r"\b(left|right)\b", s["text"]))} for s in seeds]
    seen = [norm(s["text"]) for s in kept]
    dropped = {"side": 0, "length": 0, "duplicate": 0}
    pool = {t: [] for t in DESCRIPTIONS}
    for c in cands:
        words = len(c["text"].split())
        if not 3 <= words <= 30:
            dropped["length"] += 1
            continue
        if not side_ok(c["text"], "unspecified" if not c["side_stated"] else c["side"]):
            dropped["side"] += 1
            continue
        n = norm(c["text"])
        if any(difflib.SequenceMatcher(None, n, s).ratio() >= 0.85 for s in seen):
            dropped["duplicate"] += 1
            continue
        seen.append(n)
        pool[c["template"]].append(c)
    # balance: equal share per template, round-robin across sides inside each template
    need = TOTAL - len(kept)
    per_t = {t: need // len(pool) + (1 if i < need % len(pool) else 0) for i, t in enumerate(pool)}
    for t, items in pool.items():
        rng.shuffle(items)
        by_side = {}
        for c in items:
            by_side.setdefault((c["side_stated"], c["side"]), []).append(c)
        picked = []
        while len(picked) < per_t[t] and any(by_side.values()):
            for k in list(by_side):
                if by_side[k] and len(picked) < per_t[t]:
                    picked.append(by_side[k].pop())
        if len(picked) < per_t[t]:
            print(f"  WARNING {t}: only {len(picked)} of {per_t[t]} usable candidates")
        kept += picked
    rng.shuffle(kept)
    for i, k in enumerate(kept):
        k["id"] = f"ph{i:03d}"
    (HERE / "phrasings.json").write_text(json.dumps(kept, indent=1))
    by_t = {t: sum(k["template"] == t for k in kept) for t in DESCRIPTIONS}
    print(f"candidates {len(cands)}, dropped {dropped}, kept {len(kept)} -> eval/phrasings.json")
    print("per template:", by_t)


if __name__ == "__main__":
    main()
