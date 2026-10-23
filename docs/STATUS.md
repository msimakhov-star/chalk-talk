# Status

Only facts from the build reports. "Verified live" means checked against the deployed Modal app in a browser.

| Feature | Status |
|---|---|
| 8 templates + validator | Built and tested locally: 870 plays (8 templates x 2 sides x 3 sizes x 5 age groups, man plus every counter) validate with zero issues; 16 engine tests pass. Used live. |
| Rules parser | Built and tested locally: all 40 fixture phrasings map to the right template. Scores 75% template accuracy and 85% legal plays on the eval phrasings. |
| LLM text-to-template on Modal | Built and verified live: Qwen2.5-3B-Instruct Q4_K_M on llama.cpp, CPU, JSON-schema constrained, rules fallback after 6 s. Cold start about 12 s, warm p50 about 2 s. No GPU (no payment method on the Modal account). |
| MCP server, 6 tools | Built and verified live: initialize, tools/list, tools/call for all six, in the browser trace on 22 Oct. 10 backend tests pass locally. |
| 5 MCP App views | Built and verified live in the simulator (court, playbook, practice, saved, sent). |
| Smart display simulator | Built and verified live; 35/35 end-to-end assertions pass locally. Microphone input and spoken audio not exercised in a headless browser. Not run on a real Alexa+ device: the Alexa+ toolkit was not available to us. |
| Phone page: sketch + voice | Sketch, text, send and counters built and tested locally in headless Chromium. Voice (Web Speech) only tested on the unsupported fallback branch, not on a real phone. |
| TV app: Pair and Court screens | Built and verified on the Android TV emulator on 23 Oct: the app installs, pairs with the live backend (code shown on screen), receives a play sent through the API and renders the court with all ten players and the first beat caption (tv/screenshots/pair.png, court.png). D-pad stepping between beats did not advance on the emulator (court-beat3.png is identical to court.png); not diagnosed. The debug APK needs Metro running (no bundled JS). |
| TV release APK | Not done. A debug APK is at tv/release/chalk-talk-debug.apk; it needs a Metro server (see tv/TOOLCHAIN.md). |
| Vega OS build | Not done (SDK disk and GUI requirements, see FRICTION_LOG). |
| Evaluation | Done, n=40 phrasings, three arms; see eval/results/table.md. |
| Ring track | Not entered (Developer Playground sign-in was not available). |
| Elicitation (asking for a missing team id) | Not done; unknown teams fall back to the demo team. |
| Known gap: `enrich_reads` | Not done: it is a no-op; the model chooses template and side only. |
