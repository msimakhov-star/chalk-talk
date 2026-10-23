# Friction log

Entries are from the build of Chalk Talk. Error text is quoted exactly where our logs had it.

## 1. fastmcp 4.1.3: mounting the MCP app inside FastAPI

- Tool: fastmcp 4.1.3
- Task attempted: serve a FastAPI JSON API and the MCP server from one Modal web function, MCP at `/mcp`.
- Steps: `FastAPI.mount('/mcp', mcp.http_app(path='/'))`; then POST an `initialize` request to `/mcp`.
- Expected vs actual: expected 200. Got `307 Temporary Redirect` to `/mcp/` (Starlette's mount slash redirect), which MCP clients do not follow with the request body. `FastMCP.http_app()` also has no `routes=` argument, although the underlying `create_streamable_http_app` does.
- Severity: high (the server looks dead to every MCP client).
- Workaround: make the fastmcp app the outer app with `http_app(path='/mcp')` and append `Mount('/', fastapi_app)` to its router routes after creation. POST /mcp then answers 200.
- Suggestion: document the FastAPI-mounting pattern, or expose `routes=` on `http_app`.

## 2. fastmcp 4.1.3: plain exceptions flood the log

- Tool: fastmcp 4.1.3
- Task attempted: return a clean error for an expected user mistake (unknown TV code) from `send_to_tv`.
- Steps: raise `ValueError` inside the tool.
- Expected vs actual: expected a one-line error. Got a multi-screen rich traceback in the server log on every call.
- Severity: low.
- Workaround: raise `fastmcp.exceptions.ToolError`, which returns a clean `isError` result without the log spam.
- Suggestion: log expected tool errors at one line, or document `ToolError` as the way to signal user errors.

## 3. fastmcp 4.1.3: GET /mcp returns 404 in stateless mode

- Tool: fastmcp 4.1.3
- Task attempted: run the server with `stateless_http=True`.
- Steps: start the server, send `GET /mcp` as a host would to open a notification stream.
- Expected vs actual: expected 405 Method Not Allowed. Got 404; only POST and DELETE are registered. Hosts that open a GET SSE stream may log it as an error.
- Severity: low (not a blocker for our simulator).
- Workaround: none needed.
- Suggestion: return 405 with an `Allow` header, and note it in the stateless docs.

## 4. fastmcp 4.1.3: slow startup and StaticFiles index

- Tool: fastmcp 4.1.3 (with Starlette StaticFiles)
- Task attempted: run a demo server in the simulator's end-to-end check and serve the simulator from it.
- Steps: start the server, sleep a fixed time, run the check; mount `StaticFiles` at `/sim`.
- Expected vs actual: expected sub-second startup, but import and startup took over 5 s locally, so a fixed sleep was not enough. StaticFiles returned 404 for the directory index until `html=True` was passed.
- Severity: low.
- Workaround: poll the server until ready; pass `html=True`.
- Suggestion: publish expected startup time, or lazy-import heavy dependencies.

## 5. Modal: a GPU declaration blocks CPU functions in the same app

- Tool: Modal
- Task attempted: download the model weights into a Volume with a CPU-only function, in an app that also declared a T4 function.
- Steps: `modal run backend/llm_modal_app.py::download_model`.
- Expected vs actual: expected only the GPU function to be refused. Got `Please add a payment method to use T4 GPU functions.` for the CPU-only function too.
- Severity: medium (blocks any use of the app on an account without a card).
- Workaround: an environment variable (`CHALK_LLM_GPU`) read at import time switches the whole app to a CPU image. CPU p50 of about 2 s met our latency target.
- Suggestion: only check the payment method for the function being invoked or deployed, and say which function triggered the error.

## 6. Modal: web endpoint URLs carry a region segment

- Tool: Modal
- Task attempted: hard-code the deployed URL in other components.
- Steps: follow the webhook-urls guide, which documents `https://<workspace>--<label>.modal.run`.
- Expected vs actual: expected that form. The deployed URL was `https://m-simakhov--chalk-talk-llm.us-east.modal.run`, with a region segment.
- Severity: low.
- Workaround: use the `.us-east` form everywhere, copied from the deploy output.
- Suggestion: document the regional form and when it applies.

## 7. Modal + llama.cpp server: 503 while the model loads

- Tool: Modal web_server with `ghcr.io/ggml-org/llama.cpp:server`
- Task attempted: call the model right after a cold start.
- Steps: request a completion as soon as the container is routable.
- Expected vs actual: Modal routes to the container once port 8080 is open, but llama-server answers `/health` with 503 for about 9 s while loading, so first requests after a cold start got 503.
- Severity: medium (first user request silently falls back to the rules parser; `/api/health` reports `cold`).
- Workaround: treat 503 as failure and fall back to the keyword parser.
- Suggestion: let `web_server` wait on a configurable readiness path rather than just an open port.

## 8. Ollama (local dev): json_schema does not enforce numeric ranges

- Tool: Ollama with llama3.2:3b, `response_format` json_schema
- Task attempted: get a `confidence` between 0 and 1 from the model.
- Steps: request with a schema declaring a 0 to 1 number.
- Expected vs actual: the object shape was enforced but the range was not; `confidence` came back as 8 and as 0. Qwen2.5-3B on llama.cpp returned 1.0 consistently.
- Severity: low.
- Workaround: divide values above 1 by 10, then clamp to [0, 1].
- Suggestion: document which JSON-schema keywords the grammar constraint honours.

## 9. Modal Dict in local development

- Tool: Modal (`modal.Dict`)
- Task attempted: run the backend locally with the same state code as production.
- Steps: call `modal.Dict.from_name(...)` in local dev.
- Expected vs actual: `from_name` is a network call that needs a token, and our local Python 3.14 has no `modal` package at all.
- Severity: low.
- Workaround: `modal.is_local()` as the switch (True locally, False in the container), plus an ImportError fallback to an in-memory dict.
- Suggestion: a documented local stand-in for `Dict` for tests.

## 10. playwright-cli: clicks inside a scaled iframe, and slow calls

- Tool: playwright-cli
- Task attempted: test the simulator, where the device frame is scaled with `transform: scale(0.88)` and views run in an iframe.
- Steps: `getByRole(...).click()` on a button inside the iframe; time several CLI calls with a named session.
- Expected vs actual: the click reported success but no handler fired (bounding box mixes page offset with unscaled iframe coordinates). Each CLI call also took roughly 5 to 10 s, and `run-code` had no `URL` (`ReferenceError: URL is not defined`).
- Severity: medium (cost hours of confusing test output).
- Workaround: run the check at 1400x1000 so the frame is at scale 1, or dispatch `el.click()` through `locator.evaluate`; put whole flows in one `run-code` script.
- Suggestion: translate coordinates through CSS transforms, and document the sandbox globals.

## 11. MCP Apps: a sandboxed view cannot be measured by its host

- Tool: MCP Apps spec (2026-01-26 view handshake)
- Task attempted: build a far-field lint (text size, number of actions, carousel length) in the simulator.
- Steps: render the view in an iframe without `allow-same-origin`, inspect its DOM from the host.
- Expected vs actual: expected a host-side way to measure a view. The sandbox blocks DOM access.
- Severity: medium.
- Workaround: the simulator appends a probe script to the view HTML that posts a `sim/lint` message back.
- Suggestion: an optional measurement extension point in the spec for hosts.

## 12. Android TV emulator: system image fills the disk

- Tool: Android SDK / Android TV emulator (Fire OS stand-in)
- Task attempted: install the arm64 Android TV system image.
- Steps: `sdkmanager "system-images;android-34;android-tv;arm64-v8a"`.
- Expected vs actual: the image is about 8 GB unpacked and the install stopped mid-way with `No space left on device` at 33% unzip.
- Severity: medium.
- Workaround: free disk space and reinstall; one system image only.
- Suggestion: show the unpacked size before download.

## 13. Vega OS: disk and GUI requirements

- Tool: Vega SDK / Vega Virtual Device
- Task attempted: build for Vega OS.
- Steps: read the install docs.
- Expected vs actual: the SDK needs about 20 GB free and the virtual device starts from the Vega Studio GUI, so it cannot be scripted in our build setup. We did not attempt it.
- Severity: high (ruled out the Vega build).
- Workaround: react-native-tvos on the Android TV emulator, written as plain React Native so a Vega port is a build-target change.
- Suggestion: a CLI to start the virtual device headless.

## 14. Ring Developer Playground and the Alexa+ toolkit

- Tool: Ring Developer Playground; Alexa+ developer toolkit
- Task attempted: build a Ring entry; test the MCP server on an Alexa+ device.
- Steps: open the Ring Playground; look for an Alexa+ add-on simulator.
- Expected vs actual: the Playground needs an Amazon developer sign-in that was not available to us, so we dropped the Ring track. No public Alexa+ simulator was available, so we had to build a smart-display simulator ourselves (echo-show-mcp-sim).
- Severity: high.
- Workaround: the simulator speaks real MCP and the full MCP Apps host protocol, published under MIT.
- Suggestion: a public Alexa+ add-on simulator and an anonymous sandbox mode for Ring.
