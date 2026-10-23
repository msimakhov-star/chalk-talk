# Chalk Talk

Demo video: https://youtu.be/gHFjy_-NFpE

Note on the demo video: the narration is a generated voice because the submitter's microphone was not working; the footage is real screen capture of the live app.

Chalk Talk turns a sentence or a sketch into an animated basketball play. A volunteer youth coach says "backdoor cut from the left wing" or draws it with a finger on the phone, and the living-room TV plays it beat by beat. Every beat has one short caption saying what to look for, because ten-year-olds do not read X's and O's, they watch. Asking "what if they switch?" re-plans the defence live and changes the read.

The model never draws coordinates. It chooses one of eight hand-authored templates (pick and roll, pick and pop, backdoor cut, give and go, dribble handoff, flare screen, horns, fast break 3 on 2) and fills in the side, roles, players per side (3 to 5) and age group. A validator then checks every play: inside the court, nobody closer than 3 ft, nobody faster than a real child, the ball always with someone. The same backend serves a phone page, a TV app and an MCP server for Alexa+ on a smart display. Built for the Build, Ship, Shape: Amazon Developer Hackathon. Licence: MIT.

## Try it in 60 seconds

No install, no token.

1. Open https://m-simakhov--chalk-talk-web.us-east.modal.run/sim (a smart-display simulator already pointed at the server).
2. Type `draw a pick and roll on the right`.
3. Type `what if they switch?`
4. Type `show me the playbook`.
5. Type `send it to the TV` (the demo TV code is `KQZT`).

Also: the phone page is at https://m-simakhov--chalk-talk-web.us-east.modal.run/phone, and the MCP endpoint is https://m-simakhov--chalk-talk-web.us-east.modal.run/mcp (Streamable HTTP, spec 2025-11-25, six tools). More in docs/FOR_JUDGES.md. The first request after idle can take longer while the Modal containers start.

## Architecture

```
  Phone page          TV app (React Native TV)       Smart display / Alexa+ client
  (sketch + voice)    (D-pad, long-polls state)      (MCP Apps host; /sim is our simulator)
        |                      |                               |
        |   HTTP /api/*        |   HTTP /api/tv/*              |   MCP over Streamable HTTP /mcp
        +----------------------+---------------+---------------+
                                               |
                         FastAPI + fastmcp on Modal  (app chalk-talk, function web)
                          |                |                      |
                 chalk_engine         Modal Dict             llama.cpp server on Modal
                 8 templates          (plays, teams,         Qwen2.5-3B-Instruct Q4_K_M
                 + validator          playbooks, TV          text -> template choice via
                 + counters           pairing state)         JSON schema; keyword rules
                 + rules parser                              fallback on failure or > 6 s
```

## Repo layout

```
engine/    chalk_engine: templates, keyframes, validator, counters, narration, rules parser (stdlib only)
backend/   FastAPI + fastmcp server, MCP App views, LLM client, Modal apps, tests
renderer/  court.js: dependency-free canvas renderer shared by phone page and MCP views
phone/     phone page: sketch canvas, Web Speech voice, text, TV code
tv/        react-native-tvos app for Android TV / Fire TV (see tv/TOOLCHAIN.md)
eval/      evaluation harness: freehand LLM vs template engine, results in eval/results/
echo-show-mcp-sim/   generic MCP Apps host in a smart-display frame (also its own repo, MIT)
docs/      FOR_JUDGES, STATUS, FRICTION_LOG, PRODUCT_FEEDBACK, SUBMISSION, DECISION
CONTRACTS.md   the shared contracts every component was built against
```

## Run locally

```sh
python3 -m pip install --user --break-system-packages fastmcp==4.1.3 mcp==2.3.0 fastapi uvicorn httpx pytest
uvicorn backend.app:app --port 8000        # then open http://localhost:8000/sim and /phone
```

Without Modal credentials the backend keeps state in memory. Without a model server it falls back to the keyword rules parser (set `LLM_DISABLED=1` to force that).

Tests:

```sh
cd engine && python3 -m pytest -q                          # templates, validator, counters, rules parser
LLM_DISABLED=1 python3 -m pytest backend/tests -q          # HTTP API and MCP server
node --test renderer/test.mjs                              # renderer
node --no-warnings tv/scripts/check_demo_play.mjs          # TV demo play
```

The TV app needs an Android TV emulator or a Fire TV; follow tv/TOOLCHAIN.md.

## Tracks entered

- Alexa+ (primary): a self-hosted MCP server with six intent-level tools and five MCP Apps views, demonstrated through a smart-display simulator because the Alexa+ developer toolkit was not available to us.
- Open Source mini-challenge: the simulator, published as its own MIT project at https://github.com/msimakhov-star/echo-show-mcp-sim.
- Fire TV: a react-native-tvos app is in this repo and was built for the Android TV emulator as a Fire OS stand-in. Its verification status is in docs/STATUS.md; no release APK has been produced yet, so it is not entered as a finished Fire TV submission.

## Evaluation

40 coach phrasings, each run three ways and scored by the same validator (n=40, so read the percentages as small-sample numbers). Full table: eval/results/table.md.

| Arm | Legal plays | Template accuracy |
|---|---|---|
| Template engine (Qwen2.5-3B picks a template, rules as fallback) | 100% | 92.5% |
| Keyword rules only | 85% | 75% |
| Freehand coordinates from the same model | 2.5% | 65% |

In the freehand arm 97.5% of plays had at least one validator issue (13.07 on average, almost all players overlapping) and the median latency was 41 s, against 3.3 s for the template arm.

## Licence

MIT, see LICENSE.
