# For judges

## 60-second path (browser only)

1. Open https://m-simakhov--chalk-talk-web.us-east.modal.run/sim
2. Type `draw a pick and roll on the right`. A court view animates the play; use Step, Back, Auto.
3. Type `what if they switch?` The defence re-plans and the read changes.
4. Type `show me the playbook`. A carousel of saved plays appears (the demo team is seeded).
5. Type `send it to the TV`. A confirmation card shows the play going to TV `KQZT`.

Also try `what are we practising on Thursday?` for a practice plan built from the playbook. The simulator speaks a one-line summary if your browser allows speech. The first call after idle can be slow while Modal containers start (the LLM container took about 12 s to start in our tests).

Demo TV code: `KQZT`.

## The six MCP tools

| Tool | What it does | View |
|---|---|---|
| draw_play | Turns a description ("backdoor cut from the left wing") into a validated play | court |
| counter_play | Re-plans the defence of a play (switch, hedge, drop, zone) and says what changed | court |
| save_to_playbook | Saves a play to a team playbook with tags | saved |
| list_playbook | Lists 3 to 5 saved plays, strongest first | playbook carousel |
| practice_plan | Builds a practice plan (warm-up, focus plays, scrimmage, cool-down) from the playbook | practice |
| send_to_tv | Sends a play to a paired TV by its 4-letter code | sent |

Unknown team ids fall back to the demo team `team_demo00`.

## Call the MCP server from any client

Endpoint: `https://m-simakhov--chalk-talk-web.us-east.modal.run/mcp` (Streamable HTTP, spec 2025-11-25, stateless). Replies come as `text/event-stream`, so send both Accept types.

```sh
curl -sS https://m-simakhov--chalk-talk-web.us-east.modal.run/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'

curl -sS https://m-simakhov--chalk-talk-web.us-east.modal.run/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

Tool calls use `tools/call` with `{"name":"draw_play","arguments":{"description":"pick and roll on the right"}}`. Each tool returns `structuredContent` and advertises its view through `_meta.ui.resourceUri` (`ui://chalk-talk/...`). CORS allows all origins and exposes `Mcp-Session-Id`. A GET on `/mcp` returns 404 because the server is stateless.

## Phone flow

Open https://m-simakhov--chalk-talk-web.us-east.modal.run/phone. Enter the TV code (`KQZT`), then either type or tap Say it (Web Speech API, where the browser supports it), or sketch on the court. Choose players per side and age group, tap Draw the play, step through the preview, tap Send to TV, or use the switch / hedge / drop / zone buttons to send a counter. The "understood as" line shows whether the language model or the rules parser read your text.

## TV app

Source is in `tv/` (react-native-tvos, Android TV target). `tv/release/chalk-talk.apk` does not exist yet, so there is nothing to sideload. To build and run on an Android TV emulator or a Fire TV in developer mode, follow tv/TOOLCHAIN.md, then:

```sh
tv/scripts/emulator.sh
cd tv/app && npm install && npx react-native run-android
```

On a Fire TV, enable ADB debugging and `adb connect <ip>` first. See docs/STATUS.md for exactly what was and was not verified on a device.

## Tests

- `engine/tests/test_engine.py`: every template x side x players per side x age group builds a valid play, every counter is valid, 40 phrasings parse correctly.
- `backend/tests/test_api.py`: API, TV pairing, playbook, MCP initialize, tools and resources.
- `renderer/test.mjs`: renderer maths.
- `echo-show-mcp-sim/dev/check.py`: end-to-end browser check of the simulator (needs playwright-cli).
- `phone/check.js`: phone page flows (needs playwright-cli).

## Evaluation

`eval/` holds the harness (`run_eval.py`), the 40 phrasings (`phrasings.json`), raw results (`eval/results/*.jsonl`, `summary.json`) and the table (`eval/results/table.md`). Headline: template arm 100% legal plays and 92.5% template accuracy; freehand 2.5% legal; n=40.

## Source

https://github.com/msimakhov-star/chalk-talk. The simulator is also at https://github.com/msimakhov-star/echo-show-mcp-sim.
