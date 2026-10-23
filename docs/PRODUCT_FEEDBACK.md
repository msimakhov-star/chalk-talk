# Product feedback

One block per tool. Opinions are ours; the facts are in docs/FRICTION_LOG.md.

## Alexa+ add-on docs and the MCP Apps spec

- Used for: the shape of Chalk Talk's add-on: six intent-level tools, and five MCP Apps views for a 10-inch far-field screen.
- Worked well: MCP is small enough to implement against directly (initialize, tools/list, tools/call, resources/read). The view handshake (`ui/initialize`, `ui/notifications/initialized`, tool-result, size-changed) is easy to reason about and made it possible to build a host from the spec.
- Needs work: we could not get the Alexa+ developer toolkit, so we never tested on an Alexa+ device and cannot say how the real host behaves. A sandboxed view cannot be measured by its host, so far-field rules (text size, action count) have no enforcement point.
- Onboarding: no hello world on the real platform; a working hello world with our own host was possible from the spec alone.
- Build again: yes. The protocol is open and the same server works with any MCP client.

## fastmcp

- Used for: the MCP server (six tools, five view resources), mounted in a FastAPI app on Modal.
- Worked well: tools with typed arguments and `structuredContent` need very little code; `ToolError` gives clean errors.
- Needs work: mounting beside FastAPI is undocumented and the obvious way returns a 307 (friction 1); expected errors dump long tracebacks (2); stateless GET returns 404 (3); startup took over 5 s locally (4).
- Onboarding: a first server in minutes; the production layout needed debugging (friction 1).
- Build again: yes, with the mounting pattern written down.

## Modal

- Used for: hosting the backend (FastAPI + MCP), a llama.cpp model server, a Volume for weights and a Dict for state.
- Worked well: deploy to a public HTTPS URL with one command; the Dict made state trivial; CPU inference met our latency target (warm p50 about 2 s).
- Needs work: a GPU declaration blocks CPU functions on an account without a card (5); the regional URL form is undocumented (6); the web endpoint is routable before the server is ready (7); the Dict has no local stand-in (9).
- Onboarding: zero to a deployed endpoint fast; the surprises were all at the edges above.
- Build again: yes.

## llama.cpp server

- Used for: Qwen2.5-3B-Instruct (Q4_K_M) turning coach phrasings into a template choice through a JSON schema.
- Worked well: schema-constrained output gave 0% JSON failures on 40 phrasings, with 92.5% template accuracy; a 3B model on CPU was enough.
- Needs work: `/health` returns 503 for about 9 s while the model loads. In our local Ollama comparison, numeric ranges in the schema were not enforced (8).
- Onboarding: the official server image plus a GGUF in a Volume worked on the first try.
- Build again: yes, for small constrained tasks. We would not trust it with freehand coordinates: that arm produced 2.5% legal plays.

## react-native-tvos + Android TV emulator as a Fire OS stand-in

- Used for: the TV app (Pair and Court screens, D-pad control).
- Worked well: ordinary React Native components and `Animated` cover the screens; a debug APK built and the emulator booted.
- Needs work: toolchain weight (the system image alone is about 8 GB and filled our disk, 12); we did not get to verify the Pair and Court screens on the emulator, and there is no release APK.
- Onboarding: the most expensive part of the project; tv/TOOLCHAIN.md records the exact steps for this Mac.
- Build again: yes, but with a larger disk and the emulator set up first.

## Amazon developer docs for Fire TV and Vega

- Used for: deciding between a Vega OS build and the Android TV stand-in.
- Worked well: the organisers' guidance that the Android TV emulator is an accepted stand-in saved us.
- Needs work: Vega needs about 20 GB free and the virtual device starts from a GUI, so it cannot be automated (13). We did not try it.
- Onboarding: not completed for Vega.
- Build again: not yet. We would try Vega once there is a headless way to start the virtual device.

## Ring Developer Playground

- Used for: we tried to use it for a Ring entry.
- Worked well: n/a, we could not get in.
- Needs work: it needs an Amazon developer sign-in that was not available to us, so the track was dropped (14). A Ring entry that never touched Ring's servers would have been dishonest.
- Onboarding: blocked at sign-in.
- Build again: no, not until there is an anonymous sandbox.

## Feature requests

1. A public Alexa+ add-on simulator for developers. Critical. We had to build our own host to test at all.
2. A host-side measurement hook for MCP Apps views, so far-field lint (text size, action count) works despite the sandbox. Important.
3. Documented fastmcp FastAPI mounting, or `routes=` on `http_app`. Important.
4. A Modal `web_server` readiness path, so the endpoint is not routable before the server is healthy. Important.
5. A Vega SDK CLI to start the virtual device headless. Nice-to-have.
