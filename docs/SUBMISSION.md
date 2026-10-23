# Devpost submission text (paste into the form)

## Project name

Chalk Talk

## Elevator pitch (200 characters max)

Say or sketch a basketball play on your phone; the TV animates it beat by beat for the kids, explains the read, and re-plans when the defence switches. Alexa+ add-on via MCP.

## Tracks

Primary: Alexa+. Mini-challenge: Open Source. The Fire TV app (react-native-tvos, Android TV emulator) is included as work in progress and is not entered as a track.

## About the project

### Inspiration

Volunteer youth coaches explain plays on a whiteboard, and ten-year-olds do not read X's and O's. They watch. The living-room TV is already where the family sits, and the kitchen smart display is where the coach plans the week. Chalk Talk puts the play where the kids will actually look at it.

### What it does

- On the phone: sketch the play on a court, or say it ("backdoor cut from the left wing"). Chalk Talk maps it to one of eight basketball templates (pick and roll, pick and pop, backdoor cut, give and go, dribble handoff, flare screen, horns, fast break 3 on 2) and fills in the side, the roles, the number of players (3v3 to 5v5) and the age group, which sets the speed.
- On the TV (app in progress, see docs/STATUS.md): the play animates step by step. The D-pad steps forward and back, select plays and pauses, up shows the paths, down cycles the defensive counters. Every beat has one caption a kid can follow.
- "What if they switch?" (or hedge, drop, zone): the defence re-plans and the read changes to what the kids should look for.
- On the smart display (Alexa+ via MCP): a self-hosted MCP server with six intent-level tools and MCP Apps views: draw a play, counter it, save it to the team playbook, list the playbook as a carousel, build a practice plan from saved plays, and send a play to the TV.
- Every play passes a validator: inside the court, no two players closer than 3 ft, nobody faster than a real child, the ball always with someone. The model never draws freehand.

### How we built it

- Template engine and validator: Python, no dependencies. Eight hand-authored templates with keyframes for offence and a plausible man defence, plus counter re-plans for switch, hedge, drop and 2-3 zone.
- Backend: FastAPI on Modal, with a fastmcp server mounted at /mcp (MCP spec 2025-11-25, Streamable HTTP, stateless). State in a Modal Dict. A small open-weights model served with llama.cpp on Modal does the text-to-template parsing with a JSON schema, with a keyword parser as the fallback. The model is Qwen2.5-3B-Instruct (Q4_K_M) on CPU; warm median latency is about 2 s.
- TV app (work in progress, not entered): React Native for TV (react-native-tvos), Android TV target, written for the Android TV emulator as the organiser-accepted stand-in for Fire OS. The code is type-checked, a debug APK builds and the emulator boots; the Pair and Court screens are not yet verified on the emulator and there is no release APK. Plain React Native components so a Vega OS port is a build-target change.
- Phone page: plain HTML and canvas, Web Speech API for voice, served by the same backend.
- Smart display simulator: a generic MCP Apps host in a smart-display frame that speaks real MCP from the browser (initialize, tools/list, tools/call, resources/read) and renders MCP App views in a sandboxed iframe with the full ui/initialize handshake. Published as a separate MIT project so other developers can demo their own add-ons.
- Evaluation: 40 coach phrasings run three ways (keyword rules only, the template engine with the model, and freehand coordinates from the same model), scored by the same validator. The template engine produced 100% legal plays with 92.5% template accuracy; freehand produced 2.5% legal plays (n=40). Results in eval/results/table.md.

### Challenges we ran into

- fastmcp mounted inside FastAPI answers MCP requests with a 307 redirect that clients do not follow; we had to invert the app layout.
- Modal refuses CPU functions in an app that declares a GPU when the account has no payment method; we switched the whole app to CPU.
- No Alexa+ simulator was available, so we built a smart-display MCP Apps host; Ring's Playground and the Vega SDK were out of reach (sign-in, disk and GUI requirements).

### Accomplishments that we're proud of

- A coaching idea that only works because of the current generation of language models, built so that the model cannot produce a physically wrong play.
- One backend, three surfaces (phone, smart display, and a TV app in progress).
- A reusable open-source simulator for MCP Apps on a smart display.

### What we learned

- Constrain the model to a choice, not coordinates: freehand output from the same 3B model was legal 2.5% of the time, template choice 100%.
- A sandboxed MCP Apps view cannot be measured by its host, so far-field rules need a probe or a spec extension point.
- Toolchain weight is the real cost of a TV app: the Android TV system image is about 8 GB unpacked and filled the disk once.

### What's next for Chalk Talk

- Finish verifying the TV app on the emulator, produce a release APK, then a Vega OS build.
- Football, netball and hockey templates (the engine is sport-agnostic apart from the court drawing).
- Real voice through the Fire TV remote once the Alexa integration is open to developers.
- Shared playbooks for a club, and a kids' mode that quizzes them on the read.

### A note on the video

The narration is a generated voice: the submitter's microphone was not working on recording day. All footage is real screen capture of the live app.

### Built with

react-native-tvos, React Native, Android TV emulator, TypeScript, Python, FastAPI, fastmcp, Model Context Protocol (MCP 2025-11-25, Streamable HTTP), MCP Apps, Modal, llama.cpp, Web Speech API, HTML canvas

## What was built during the submission window

Everything. The repository was created on 22 October 2026.

## Open Source mini-challenge fields

- Contribution URL: https://github.com/msimakhov-star/echo-show-mcp-sim
- Project repository URL: https://github.com/msimakhov-star/chalk-talk
- GitHub username: msimakhov-star
- Description: A generic, dependency-free MCP Apps host that renders any MCP server's tools and MCP App views inside a smart-display frame, with voice-style input, a far-field design lint and a protocol trace. It exists because hackathon participants cannot access the Alexa+ simulator; it lets anyone demo an MCP add-on the way a customer would see it. It speaks Streamable HTTP MCP (spec 2025-11-25), runs the MCP Apps view handshake, and passes 35 end-to-end assertions against two different MCP servers (Chalk Talk and a lights demo). Microphone input is not tested in headless runs.

## Product feedback (required, one block per tool)

See docs/PRODUCT_FEEDBACK.md; paste its sections here.

## Feature requests (optional)

See docs/PRODUCT_FEEDBACK.md, section "Feature requests", each with Critical / Important / Nice-to-have.

## Friction log (optional, up to 10% bonus)

Link: https://github.com/msimakhov-star/chalk-talk/blob/master/docs/FRICTION_LOG.md

## Testing instructions for judges

See docs/FOR_JUDGES.md: 60-second path in the browser (no install, no token), how to build the TV app (no release APK yet), local run.
