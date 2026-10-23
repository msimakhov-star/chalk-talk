"""One cached, retrying call to an OpenAI-compatible /chat/completions (llama.cpp on Modal or Ollama).

Cache: eval/.cache/<arm>/<sha256 of model+messages+schema+max_tokens>.json holding the raw reply
text and the latency of the first real call, so re-runs are free and latency numbers are stable.
Transport errors are not cached (a re-run retries them); a reply that fails to parse is cached.
"""

import hashlib
import json
import time
from pathlib import Path

import httpx

CACHE = Path(__file__).resolve().parent / ".cache"
HOSTED_URL = "https://m-simakhov--chalk-talk-llm.us-east.modal.run/v1"
HOSTED_MODEL = "qwen2.5-3b-instruct"  # backend/modal_app.py LLM_MODEL
OLLAMA_URL = "http://localhost:11434"  # native API
RETRY_STATUS = {429, 500, 502, 503, 504}


def chat(arm, base_url, model, messages, schema, max_tokens, temperature=0.0, timeout=180.0, tries=6, extra=None, native=False):
    """-> {"content": str|None, "latency": float, "error": str|None, "cached": bool}

    native=True uses Ollama's own /api/chat with think=false. schema=None there means plain JSON
    mode (format="json"): on this Mac, Ollama's grammar-constrained decoding ran ~1 token/s
    against ~6-9 unconstrained, so the gemma arm cannot afford the schema (see RESULTS.md)."""
    if native:
        body = {"model": model, "messages": messages, "stream": False, "think": False,
                "format": schema or "json", "options": {"num_predict": max_tokens, "temperature": temperature, **(extra or {})}}
        return _post(arm, f"{base_url}/api/chat", body, timeout, tries,
                     lambda j: (j["message"].get("content"), j.get("done_reason")))
    body = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_schema", "json_schema": {"name": "out", "schema": schema, "strict": True}},
        "temperature": temperature,
        "max_tokens": max_tokens,
        **(extra or {}),
    }
    return _post(arm, f"{base_url}/chat/completions", body, timeout, tries,
                 lambda j: (j["choices"][0]["message"].get("content"), j["choices"][0].get("finish_reason")))


def _post(arm, url, body, timeout, tries, extract):
    key = hashlib.sha256(json.dumps([arm, body], sort_keys=True).encode()).hexdigest()[:24]
    path = CACHE / arm / f"{key}.json"
    if path.exists():
        return {**json.loads(path.read_text()), "cached": True}
    error = None
    for attempt in range(tries):
        start = time.monotonic()
        try:
            r = httpx.post(url, json=body, timeout=timeout)
            latency = time.monotonic() - start
            if r.status_code in RETRY_STATUS:
                error = f"HTTP {r.status_code}: {r.text[:200]}"
            else:
                r.raise_for_status()
                content, finish = extract(r.json())
                out = {"content": content, "latency": round(latency, 3), "finish_reason": finish, "error": None}
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(out))
                return {**out, "cached": False}
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            error = f"{type(exc).__name__}: {str(exc)[:200]}"
        print(f"  [{arm}] attempt {attempt + 1} failed: {error}", flush=True)
        time.sleep(min(2 ** (attempt + 1), 40))
    return {"content": None, "latency": None, "error": error, "cached": False}
