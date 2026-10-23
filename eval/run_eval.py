"""Freehand LLM vs template engine, over the same coach phrasings (eval/phrasings.json).

Arms
  rules             parse_rules(text) only, no LLM -> build_play -> validate
  template          backend/llm.py prompt+schema on the hosted LLM (fallback parse_rules, as in
                    backend/plays.py) -> build_play -> validate
  freehand_hosted   hosted LLM writes every player's position for 4 to 5 beats as JSON -> validate
  freehand_gemma    same prompt and schema on local Ollama gemma4:12b-nvfp4 -> validate

    python3 eval/run_eval.py --limit 20                 # quick check
    python3 eval/run_eval.py --gemma-limit 100          # full run (gemma arm on the first 100)

Every LLM reply is cached in eval/.cache, so a re-run (or a resumed run) costs nothing.
Writes eval/results/<arm>.jsonl, eval/results/summary.json and eval/results/table.md.
"""

import argparse
import json
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "engine"), str(ROOT)]

from chalk_engine import build_play, parse_rules, template_catalog, validate  # noqa: E402
import httpx  # noqa: E402
from llmcall import HOSTED_MODEL, HOSTED_URL, OLLAMA_URL, chat  # noqa: E402
from backend import llm as backend_llm  # noqa: E402  (same SYSTEM_PROMPT and RESPONSE_SCHEMA as production)

GEMMA = "gemma4:12b-nvfp4"
CODES = ["out_of_bounds", "overlap", "too_fast", "ball_orphan", "missing_player"]
SPEED = {"u8": 12, "u10": 14, "u12": 16, "u14": 18, "u16": 20}  # CONTRACTS.md section 3
TEMPLATE_IDS = [t["id"] for t in template_catalog()]
PROD_TIMEOUT = backend_llm.TIMEOUT_SECONDS


def context(ph):
    return {"players_per_side": ph["players_per_side"], "age_group": ph["age_group"]}


# ---------- template arms ----------

def run_rules(ph):
    t0 = time.monotonic()
    choice = parse_rules(ph["text"])
    return finish_template(ph, choice, "rules" if choice else None, time.monotonic() - t0, None)


def run_template(ph):
    r = chat("template", HOSTED_URL, HOSTED_MODEL,
             [{"role": "system", "content": backend_llm.SYSTEM_PROMPT}, {"role": "user", "content": ph["text"][:500]}],
             backend_llm.RESPONSE_SCHEMA, max_tokens=80)
    llm_choice = None
    try:  # same post-processing as backend.llm.parse_play_text
        c = json.loads(r["content"])
        if c["template"] in backend_llm.TEMPLATE_IDS:
            llm_choice = {"template": c["template"], "params": {"side": c.get("side", "right")}}
    except Exception:
        pass
    # production falls back to rules on failure or on a reply slower than 6 s
    in_time = r["latency"] is not None and r["latency"] <= PROD_TIMEOUT
    choice, method = (llm_choice, "llm") if (llm_choice and in_time) else (parse_rules(ph["text"]), "rules")
    if choice is None:
        method = None
    row = finish_template(ph, choice, method, r["latency"], r["error"])
    row["llm_template"] = llm_choice and llm_choice["template"]
    row["llm_side"] = llm_choice and llm_choice["params"]["side"]
    row["llm_parse_failed"] = llm_choice is None
    row["llm_over_6s"] = not in_time
    row["raw"] = r["content"]
    return row


def finish_template(ph, choice, method, latency, error):
    row = {"id": ph["id"], "text": ph["text"], "label_template": ph["template"], "label_side": ph["side"],
           "method": method, "latency": latency, "transport_error": error}
    if choice is None:
        return {**row, "parse_failed": True}
    t1 = time.monotonic()
    play = build_play(choice["template"], {**context(ph), **choice.get("params", {})})
    v = validate(play)
    return {**row, "parse_failed": False, "template": choice["template"],
            "side": choice.get("params", {}).get("side", "right"), "issues": v["issues"],
            "latency": (latency or 0) + time.monotonic() - t1}


# ---------- freehand arms ----------

def freehand_schema(ids, offense):
    pos = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
    beat = {"type": "object", "properties": {
        "t": {"type": "number"},
        "positions": {"type": "object", "properties": {i: pos for i in ids}, "required": ids, "additionalProperties": False},
        "ball": {"type": "string", "enum": offense}},
        "required": ["t", "positions", "ball"], "additionalProperties": False}
    return {"type": "object", "properties": {
        "template": {"type": "string", "enum": TEMPLATE_IDS},
        "side": {"type": "string", "enum": ["left", "right"]},
        "beats": {"type": "array", "items": beat, "minItems": 4, "maxItems": 5}},
        "required": ["template", "side", "beats"], "additionalProperties": False}


EXAMPLE = {"template": "give_and_go", "side": "right", "beats": [  # validate()-clean, checked by hand
    {"t": 0, "positions": {"P1": [25, 32], "P2": [38, 22], "D1": [25, 28], "D2": [35, 19]}, "ball": "P1"},
    {"t": 2, "positions": {"P1": [27, 30], "P2": [40, 24], "D1": [26, 27], "D2": [37, 21]}, "ball": "P2"},
    {"t": 4, "positions": {"P1": [29, 16], "P2": [41, 22], "D1": [27, 19], "D2": [38, 20]}, "ball": "P2"},
    {"t": 6, "positions": {"P1": [27, 8], "P2": [41, 21], "D1": [24, 13], "D2": [37, 19]}, "ball": "P1"}]}
FREEHAND_SYSTEM = (
    "You draw youth basketball plays as coordinates for an animated whiteboard. Half court in feet: x runs 0 to 50 "
    "left to right, y runs 0 (baseline) to 47 (half-court line). The basket is at (25, 5.25); the free-throw line is "
    "y=19; the lane is x 17 to 33. 'Right side' means x > 25. Offense players P1 (point guard) to Pn, defenders D1 to "
    "Dn; Dk guards Pk. Output 4 or 5 beats. Each beat gives t (seconds, first beat t=0, strictly increasing), the "
    "position [x, y] of EVERY player, and which offense player holds the ball. Rules every beat must obey: every "
    "player stays inside the court (0<=x<=50, 0<=y<=47); no two players closer than 3 ft; nobody moves faster than "
    "{speed} ft/s between beats (distance / time difference); the ball holder is an offense player. Also say which of "
    "these templates the play is and the side: " + ", ".join(TEMPLATE_IDS) + ". Reply with compact JSON only.\n"
    "Example of the format and of legal spacing and speed (a 2 on 2 give and go, u12, not one of your plays): "
    + json.dumps(EXAMPLE, separators=(",", ":"))
)


def run_freehand(ph, arm, base, model, native=False):
    n = ph["players_per_side"]
    offense = [f"P{i}" for i in range(1, n + 1)]
    ids = offense + [f"D{i}" for i in range(1, n + 1)]
    user = (f"Coach says: \"{ph['text']}\"\nTeam: {n} on {n}, age group {ph['age_group']} "
            f"(max speed {SPEED[ph['age_group']]} ft/s). Players: {', '.join(ids)}.")
    r = chat(arm, base, model,
             [{"role": "system", "content": FREEHAND_SYSTEM.replace("{speed}", str(SPEED[ph["age_group"]]))}, {"role": "user", "content": user}],
             None if native else freehand_schema(ids, offense), max_tokens=1400, timeout=1200, native=native)
    row = {"id": ph["id"], "text": ph["text"], "label_template": ph["template"], "label_side": ph["side"],
           "latency": r["latency"], "transport_error": r["error"], "raw": r["content"], "finish_reason": r.get("finish_reason")}
    try:
        out = json.loads(r["content"])
        beats = [{"index": i, "t": float(b["t"]), "positions": {k: [float(v[0]), float(v[1])] for k, v in b["positions"].items()},
                  "ball": b["ball"], "paths": {}} for i, b in enumerate(out["beats"])]
    except Exception as exc:
        return {**row, "parse_failed": True, "parse_error": f"{type(exc).__name__}: {str(exc)[:120]}"}
    play = {"template": out.get("template"), "params": {"side": out.get("side"), **context(ph)},
            "players": [{"id": i, "team": "offense" if i[0] == "P" else "defense", "label": i} for i in ids], "beats": beats}
    v = validate(play)
    return {**row, "parse_failed": False, "template": out.get("template"), "side": out.get("side"),
            "issues": v["issues"], "play": play}


ARMS = {
    "rules": run_rules,
    "template": run_template,
    "freehand_hosted": lambda ph: run_freehand(ph, "freehand_hosted", HOSTED_URL, HOSTED_MODEL),
    "freehand_gemma": lambda ph: run_freehand(ph, "freehand_gemma", OLLAMA_URL, GEMMA, native=True),
}
MODELS = {"rules": "none (keyword rules)", "template": f"{HOSTED_MODEL} (Modal, llama.cpp) + rules fallback",
          "freehand_hosted": f"{HOSTED_MODEL} (Modal, llama.cpp)", "freehand_gemma": f"{GEMMA} (local Ollama, JSON mode, no schema)"}


def run_arm(arm, phrasings, workers):
    rows, lock, done = [None] * len(phrasings), threading.Lock(), [0]
    t0 = time.monotonic()

    def one(i):
        try:
            rows[i] = ARMS[arm](phrasings[i])
        except Exception as exc:  # an arm bug must not kill the run; it shows up as a failure row
            rows[i] = {"id": phrasings[i]["id"], "parse_failed": True, "parse_error": f"crash {type(exc).__name__}: {exc}",
                       "label_template": phrasings[i]["template"], "label_side": phrasings[i]["side"], "latency": None}
        with lock:
            done[0] += 1
            if done[0] % 10 == 0 or done[0] == len(phrasings):
                print(f"[{arm}] {done[0]}/{len(phrasings)}  {time.monotonic() - t0:.0f}s", flush=True)

    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, range(len(phrasings))))
    out = HERE / "results" / f"{arm}.jsonl"
    out.parent.mkdir(exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return rows


def warm_up():
    """Wake the Modal container (503 'Loading model' while cold) before anything is timed."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < 900:
        try:
            r = httpx.post(f"{HOSTED_URL}/chat/completions", timeout=120, json={
                "model": HOSTED_MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1})
            if r.status_code == 200:
                print(f"hosted LLM warm after {time.monotonic() - t0:.0f}s", flush=True)
                return
            print(f"  warm-up: HTTP {r.status_code} {r.text[:80]}", flush=True)
        except httpx.TransportError as exc:
            print(f"  warm-up: {type(exc).__name__}", flush=True)
        time.sleep(10)


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def quantile(xs, q):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(q * len(xs)))], 2) if xs else None


def summarize(arm, rows):
    n = len(rows)
    ok = [r for r in rows if not r.get("parse_failed")]
    played = len(ok)
    bad = [r for r in ok if r["issues"]]
    by_code = {c: sum(any(i["code"] == c for i in r["issues"]) for r in ok) for c in CODES}
    lat = [r["latency"] for r in rows if r.get("latency") is not None]
    s = {
        "arm": arm, "model": MODELS[arm], "n": n,
        "parse_fail_pct": pct(n - played, n),
        "template_acc_pct": pct(sum(r.get("template") == r["label_template"] for r in rows), n),
        "side_acc_pct": pct(sum(r.get("side") == r["label_side"] for r in rows), n),
        "plays_with_issue_pct": pct(len(bad), played),
        "legal_play_pct": pct(played - len(bad), n),
        "mean_issues_per_play": round(sum(len(r["issues"]) for r in ok) / played, 2) if played else None,
        "issue_code_pct": {c: pct(by_code[c], played) for c in CODES},
        "latency_p50_s": quantile(lat, 0.5), "latency_p95_s": quantile(lat, 0.95),
        "transport_errors": sum(bool(r.get("transport_error")) for r in rows),
    }
    if arm == "template":
        s["llm_json_fail_pct"] = pct(sum(r["llm_parse_failed"] for r in rows), n)
        s["llm_only_template_acc_pct"] = pct(sum(r["llm_template"] == r["label_template"] for r in rows), n)
        s["llm_only_side_acc_pct"] = pct(sum(r["llm_side"] == r["label_side"] for r in rows), n)
        s["fell_back_to_rules_pct"] = pct(sum(r["method"] == "rules" for r in rows), n)
        s["llm_over_6s_pct"] = pct(sum(r["llm_over_6s"] for r in rows), n)
    if arm.startswith("freehand"):
        s["truncated"] = sum(r.get("finish_reason") == "length" for r in rows)
    return s


def table(summaries):
    cols = [("arm", "Arm"), ("model", "Model"), ("n", "n"), ("parse_fail_pct", "Parse/JSON fail %"),
            ("template_acc_pct", "Template acc %"), ("side_acc_pct", "Side acc %"),
            ("plays_with_issue_pct", "Plays with any issue %"), ("legal_play_pct", "Legal play from phrasing %"),
            ("mean_issues_per_play", "Mean issues/play")] + [(c, c + " %") for c in CODES] + \
           [("latency_p50_s", "p50 s"), ("latency_p95_s", "p95 s")]
    lines = ["| " + " | ".join(h for _, h in cols) + " |", "|" + "---|" * len(cols)]
    for s in summaries:
        vals = [s["issue_code_pct"][k] if k in CODES else s[k] for k, _ in cols]
        lines.append("| " + " | ".join("n/a" if v is None else str(v) for v in vals) + " |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="first N phrasings (file is pre-shuffled)")
    ap.add_argument("--gemma-limit", type=int, default=100, help="freehand_gemma runs on the first N only")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--file", default=str(HERE / "phrasings.json"))
    ap.add_argument("--workers", type=int, default=4, help="parallel calls for hosted arms (Ollama always 1)")
    args = ap.parse_args()
    phrasings = json.loads(Path(args.file).read_text())[: args.limit]
    for i, ph in enumerate(phrasings):
        ph.setdefault("id", f"row{i:03d}")
    arms = args.arms.split(",")
    t0 = time.monotonic()
    results = {}
    if any(a in arms for a in ("template", "freehand_hosted")):
        warm_up()

    def go(arm):
        subset = phrasings[: args.gemma_limit] if arm == "freehand_gemma" else phrasings
        # template: 2 at a time (llama.cpp --parallel 2) so latency is what one coach would see
        workers = {"freehand_gemma": 1, "rules": 1, "template": min(2, args.workers)}.get(arm, args.workers)
        results[arm] = run_arm(arm, subset, workers)

    hosted = [a for a in arms if a in ("template", "freehand_hosted")]
    # hosted arms share one llama.cpp server: run them one after the other so one arm's load
    # does not inflate the other's latency (and push the template arm past the 6 s fallback)
    threads = [threading.Thread(target=lambda: [go(a) for a in hosted])] + \
              [threading.Thread(target=go, args=(a,)) for a in arms if a not in hosted]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    summaries = [summarize(a, results[a]) for a in arms]
    wall = round(time.monotonic() - t0, 1)
    (HERE / "results" / "summary.json").write_text(json.dumps({"wall_s": wall, "arms": summaries}, indent=1))
    md = table(summaries)
    (HERE / "results" / "table.md").write_text(md + "\n")
    print(md)
    for s in summaries:
        extra = {k: v for k, v in s.items() if k.startswith(("llm_", "fell", "transport", "truncated"))}
        print(s["arm"], extra)
    print(f"wall time {wall}s")


if __name__ == "__main__":
    main()
