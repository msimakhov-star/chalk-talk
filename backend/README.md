# backend

FastAPI JSON API (CONTRACTS.md section 5) + fastmcp MCP server at `/mcp` (section 6) + static pages,
one Modal app. The engine is imported from `../engine/chalk_engine`; until it imports cleanly the
backend logs a warning and uses `backend/_stub_engine.py` (same API, one shared motion).

## Run locally

```
python3 -m pip install --user --break-system-packages fastmcp==4.1.3 mcp==2.3.0 fastapi uvicorn httpx pytest
cd <repo>
uvicorn backend.app:app --port 8000          # http://localhost:8000  (/, /phone, /sim, /docs, /mcp)
LLM_DISABLED=1 CHALK_ENGINE=stub python3 -m pytest backend/tests -q   # backend alone (stub engine)
LLM_DISABLED=1 python3 -m pytest backend/tests -q                     # same tests through the real engine
```

Env: `LLM_BASE_URL` (default `http://localhost:11434/v1`, local Ollama), `LLM_MODEL` (default `llama3.2:3b`),
`LLM_DISABLED=1` to use the keyword rules parser only, `CHALK_STATE=memory|modal|auto` (auto: modal.Dict
only inside a Modal container), `CHALK_ENGINE=stub` to force the stub engine.

## Files

| file | what |
|---|---|
| `app.py` | app factory: fastmcp Starlette app (CORS `*`, `/mcp` stateless) with the FastAPI API mounted at `/` |
| `mcp_server.py` | the 6 tools and 5 `ui://chalk-talk/*` views; inlines `renderer/court.js` at `<!-- INLINE:court.js -->` |
| `plays.py` | create a play from text (LLM, then rules) or sketch; counters |
| `playbook.py` | PlaySummary, ranking, practice plan builder |
| `tv.py` | pairing codes, long-poll state with cursor, commands |
| `state.py` | `modal.Dict` "chalk-talk-state" with in-memory fallback; demo team seeding |
| `llm.py` | `parse_play_text` with a JSON-schema-constrained chat completion (6 s budget, falls back to rules) |
| `engine_loader.py` / `_stub_engine.py` | real engine import with stub fallback |
| `modal_app.py` | Modal app `chalk-talk`, function `web` |
| `llm_modal_app.py` | Modal app `chalk-talk-llm`, llama.cpp server |
| `views/*.html` | MCP Apps views (written by the simulator component) |
| `tests/test_api.py` | the runnable check (10 tests, HTTP + MCP smoke) |

Mounting note: `FastAPI.mount("/mcp", mcp.http_app(path="/"))` answers `POST /mcp` with a 307 to `/mcp/`,
so the fastmcp app is the outer app (`http_app(path="/mcp", stateless_http=True, middleware=[cors])`)
and the FastAPI routes are appended as `Mount("/", api)` with lowest precedence. Verified: `POST /mcp`
initialize returns 200, one CORS header set, `/docs` still works.

## Deployed

| app | URL |
|---|---|
| `chalk-talk` (web) | https://m-simakhov--chalk-talk-web.us-east.modal.run |
| `chalk-talk-llm` (llama.cpp, OpenAI-compatible) | https://m-simakhov--chalk-talk-llm.us-east.modal.run (`/v1/chat/completions`, `/health`) |

```
modal run backend/llm_modal_app.py::download_model      # once, 2.1 GB into Volume chalk-talk-models
CHALK_LLM_GPU=none modal deploy backend/llm_modal_app.py
modal deploy backend/modal_app.py
```

### LLM: CPU vs GPU (measured 22 Oct 2026)

Qwen2.5-3B-Instruct GGUF Q4_K_M, `ghcr.io/ggml-org/llama.cpp:server`, Modal CPU container (8 vCPU, 8 GB),
`scaledown_window=900`:

| measure | result |
|---|---|
| cold start (container + model load until `/health` 200) | 12 s |
| first request after cold start | 3.0 s |
| warm p50, schema-constrained template choice (183 prompt tokens, ~23 output) | 2.06 s (max 2.6 s over 8 phrases) |
| warm, 60-token JSON response | 3.8 s |
| accuracy on 8 phrasings | 8/8 correct template and side |

p50 is under the 4 s target on CPU, so the GPU build was not needed. GPU was also unavailable: Modal
refused `T4` with "Please add a payment method to use T4 GPU functions." (account has no card on file).
`CHALK_LLM_GPU=T4 modal deploy backend/llm_modal_app.py` switches to `server-cuda` + `-ngl 99` once a card exists.

Local Ollama `llama3.2:3b` on the same prompt: 3.7 to 4.1 s, correct template, but `confidence` is unreliable
(it answered 8 and 0; values above 1 are divided by 10, then clamped).

## Contract notes

- `GET /api/tv/{code}/state` also returns `playing` (bool) next to the contract fields.
- `POST /api/plays` with only a sketch: the side comes from the mean x of the strokes, the template from the
  stroke count (1 backdoor cut, 2 pick and roll, else give and go), `confidence` 0.3. A real sketch matcher is
  the engine's job if one is wanted.
- The LLM picks `template` and `side` only; role params use the engine's template defaults.
- `/sim` without `?server=` redirects to `/sim?server=<this origin>/mcp`.
- `/sim-intents.json` serves `backend/views/sim-intents.json` (the simulator's intent table, written by the simulator component).
