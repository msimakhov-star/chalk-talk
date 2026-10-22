"""Template choice by an open-weights LLM behind an OpenAI-compatible chat endpoint.

Env: LLM_BASE_URL (default local Ollama http://localhost:11434/v1), LLM_MODEL
(default llama3.2:3b), LLM_DISABLED=1 to skip. Production points at the
separate Modal app "chalk-talk-llm" (llama.cpp server, see llm_modal_app.py).
The response is constrained by a JSON schema so it is always a valid template id;
any failure or a response slower than 6 s makes the caller fall back to parse_rules.
"""

import json
import logging
import os

import httpx

log = logging.getLogger("chalk.llm")

TIMEOUT_SECONDS = 6.0
TEMPLATE_IDS = ["pick_and_roll", "pick_and_pop", "backdoor_cut", "give_and_go",
                "dribble_handoff", "flare_screen", "horns", "fast_break_3v2"]

SYSTEM_PROMPT = (
    "You help a volunteer youth basketball coach. Map the coach's words to exactly one play "
    "template id and a side. Templates: pick_and_roll (ball screen, screener rolls to rim), "
    "pick_and_pop (ball screen, screener pops out for a shot), backdoor_cut (cutter goes behind "
    "an overplaying defender), give_and_go (pass then cut to the basket for a return pass), "
    "dribble_handoff (handler dribbles at a teammate and hands the ball off), flare_screen "
    "(off-ball screen, shooter flares away from the ball), horns (two bigs at the elbows, guard "
    "picks a side), fast_break_3v2 (transition, three attackers against two). Side is left or "
    "right; default right. confidence is 0 to 1. Reply with JSON only."
)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "template": {"type": "string", "enum": TEMPLATE_IDS},
        "side": {"type": "string", "enum": ["left", "right"]},
        "confidence": {"type": "number"},
    },
    "required": ["template", "side", "confidence"],
    "additionalProperties": False,
}
# ponytail: roles (screener, cutter...) use the template defaults; add per-template role enums if coaches ask for "5 screens for 2".


def base_url():
    return os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")


def model_name():
    return os.environ.get("LLM_MODEL", "llama3.2:3b")


def disabled():
    return os.environ.get("LLM_DISABLED", "") == "1"


def parse_play_text(text, context=None):
    """-> {"template","params","confidence"} or None (caller falls back to parse_rules)."""
    if disabled() or not text:
        return None
    body = {
        "model": model_name(),
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text[:500]}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "play_choice", "schema": RESPONSE_SCHEMA, "strict": True}},
        "temperature": 0,
        "max_tokens": 80,
    }
    try:
        reply = httpx.post(f"{base_url()}/chat/completions", json=body, timeout=TIMEOUT_SECONDS)
        reply.raise_for_status()
        choice = json.loads(reply.json()["choices"][0]["message"]["content"])
        if choice["template"] not in TEMPLATE_IDS:
            return None
        confidence = float(choice.get("confidence", 0.5))
        if confidence > 1:  # small models sometimes answer on a 0..10 scale
            confidence = confidence / 10
        params = {"side": choice.get("side", "right"), **(context or {})}
        return {"template": choice["template"], "params": params, "confidence": max(0.0, min(confidence, 1.0))}
    except Exception as exc:
        log.warning("LLM parse failed (%s); falling back to rules", exc)
        return None


def enrich_reads(play):
    """Optional and skippable per the contract; the engine's reads are kept as they are."""
    return play


def status():
    """'off' | 'ready' | 'cold' for GET /api/health."""
    if disabled():
        return "off"
    try:
        reply = httpx.get(f"{base_url()}/models", timeout=2.0)
        return "ready" if reply.status_code == 200 else "cold"
    except Exception:
        return "cold"
