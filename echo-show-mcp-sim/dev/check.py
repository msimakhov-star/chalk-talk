"""End-to-end check for the simulator: drives it in a headless browser with playwright-cli.

Asserts the MCP Apps message sequence, the intent router, the context memory, the far-field lint
and view-initiated tools/call against dev/fake_chalk_talk.py (and optionally the lights demo).

Run:   python dev/check.py --url http://127.0.0.1:8791 [--demo-url http://127.0.0.1:8792] [--screenshots screenshots]
Needs: playwright-cli on PATH (npm i -g @playwright/cli), fake_chalk_talk.py already running at --url.
Python stdlib only.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SESSION = "simcheck"
failures = []


def pw(*args, raw=True):
    cmd = ["playwright-cli", f"-s={SESSION}"] + (["--raw"] if raw else []) + list(args)
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{out.stdout}\n{out.stderr}")
    return out.stdout.strip()


def decode(out):
    """playwright-cli --raw prints the JSON-encoded result, or nothing for undefined."""
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print("  (non-JSON output from playwright-cli: %r)" % out[:200])
        return out


def js(expr):
    """Evaluate a JS expression (or arrow function) in the page and return the decoded value."""
    return decode(pw("eval", expr))


def wait_for(expr, timeout=15, what=""):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if js(expr):
            return True
        time.sleep(0.4)
    raise TimeoutError(f"timed out waiting for {what or expr}")


def in_view(code):
    """Run code against the view iframe: `f` is the frameLocator. Returns the decoded value."""
    return decode(pw("run-code", f"async page => {{ const f = page.frameLocator('#view iframe'); return {code}; }}"))


def check(condition, label):
    print(("ok   " if condition else "FAIL ") + label)
    if not condition:
        failures.append(label)


def traffic():
    return js("() => window.SIM.trafficLog.map(e => ({dir: e.dir, msg: e.msg}))")


def methods(entries):
    return [(e["dir"], e["msg"].get("method") or ("result" if "result" in e["msg"] else "error"))
            for e in entries if isinstance(e["msg"], dict)]


def ask(text, timeout=15):
    js("() => { window.SIM.trafficLog.length = 0; return 0 }")
    js(f"() => {{ window.SIM.ask({json.dumps(text)}); return 0 }}")
    # Done when the lightbar stops thinking and a view/card is on screen.
    wait_for("() => !document.getElementById('lightbar').classList.contains('thinking')", timeout, f"answer to {text!r}")
    time.sleep(1.0)  # let size-changed and the lint probe arrive
    return traffic()


def lint_rows():
    return js("() => [...document.querySelectorAll('#lint li')].map(li => li.textContent)")


def shot(shots, name):
    if shots:
        pw("screenshot", f"--filename={shots / name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8791", help="origin of a running dev/fake_chalk_talk.py")
    ap.add_argument("--demo-url", default="", help="origin of the lights demo server, if running")
    ap.add_argument("--screenshots", type=Path, default=None, help="directory for PNG screenshots")
    args = ap.parse_args()
    shots = args.screenshots
    if shots:
        shots = shots.resolve()
        shots.mkdir(parents=True, exist_ok=True)

    subprocess.run(["playwright-cli", f"-s={SESSION}", "close"], capture_output=True)
    pw("open", f"{args.url}/sim/", raw=False)
    # 1400x1000 keeps the 1336x856 device at scale 1: Playwright clicks inside an iframe under a CSS
    # transform land off target, so real mouse clicks only work unscaled.
    pw("resize", "1400", "1000")
    wait_for("() => window.SIM && window.SIM.tools.length > 0", 20, "tools/list")

    # 1. connect
    names = js("() => window.SIM.tools.map(t => t.name)")
    check(set(names) >= {"draw_play", "counter_play", "save_to_playbook", "list_playbook", "practice_plan", "send_to_tv"}, "tools/list has the six Chalk Talk tools")
    seq = methods(traffic())
    check(seq[:3] == [("→ server", "initialize"), ("← server", "result"), ("→ server", "notifications/initialized")], "initialize then notifications/initialized")
    check(any("intents loaded" in str(e["msg"]) for e in traffic()), "intents JSON loaded from the server's /sim-intents.json")
    shot(shots, "home.png")

    # 2. draw a play: full host <-> view handshake
    log = ask("draw a pick and roll on the right")
    seq = methods(log)
    expected = [("→ server", "tools/call"), ("← server", "result"), ("→ server", "resources/read"), ("← server", "result"),
                ("← view", "ui/initialize"), ("→ view", "result"), ("← view", "ui/notifications/initialized"),
                ("→ view", "ui/notifications/tool-input"), ("→ view", "ui/notifications/tool-result"), ("← view", "ui/notifications/size-changed")]
    check([m for m in seq if m in expected][:len(expected)] == expected, "message sequence: tools/call, resources/read, ui/initialize, initialized, tool-input, tool-result, size-changed")
    call = next(e["msg"] for e in log if e["dir"] == "→ server" and e["msg"].get("method") == "tools/call")
    check(call["params"] == {"name": "draw_play", "arguments": {"description": "pick and roll on the right", "team_id": "team_demo00"}}, "router: draw_play with description from the utterance and team_id from defaults")
    init_reply = next(e["msg"] for e in log if e["dir"] == "→ view" and "result" in e["msg"] and "hostContext" in e["msg"]["result"])
    hc = init_reply["result"]["hostContext"]
    check(hc["platform"] == "web" and hc["theme"] == "dark" and hc["displayMode"] == "inline" and hc["containerDimensions"]["width"] == 1280, "ui/initialize reply carries hostContext (web, dark, inline, 1280 wide)")
    check(js("() => window.SIM.memory.play_id") == "ply_7f3a9c", "memory remembers play_id from the result")
    check(js("() => window.SIM.lastSummary").startswith("Here is"), "spoken summary comes from structuredContent.summary")
    check(in_view("await f.locator('#name').textContent()") == "Pick and roll on the right", "court view shows the play name")
    check(all(r.startswith("pass") for r in lint_rows()) and len(lint_rows()) == 4, "far-field lint: court view passes all four rules")
    shot(shots, "court.png")

    # 3. view-initiated tools/call: the "What if they switch?" button
    js("() => { window.SIM.trafficLog.length = 0; return 0 }")
    in_view("await f.getByRole('button', { name: /What if they switch/ }).click({ timeout: 10000 })")
    wait_for("() => window.SIM.trafficLog.some(e => e.dir === '→ view' && e.msg.result && e.msg.result.structuredContent)", 15, "counter_play reply to the view")
    time.sleep(0.5)
    log = traffic()
    req = next(e["msg"] for e in log if e["dir"] == "← view" and e["msg"].get("method") == "tools/call")
    check(req["params"] == {"name": "counter_play", "arguments": {"play_id": "ply_7f3a9c", "defence": "switch"}}, "view asked the host to call counter_play for the base play")
    check(in_view("await f.locator('#name').textContent()").endswith("vs switch"), "court view re-rendered with the counter play")
    check(js("() => window.SIM.memory.play_id") == "ply_7f3a9c-switch", "memory updated from the view-initiated call")
    shot(shots, "court-switch.png")

    # 4. step through beats inside the view
    in_view("await f.getByRole('button', { name: 'Step' }).click({ timeout: 10000 })")
    time.sleep(2.6)
    check(in_view("await f.locator('#beat-title').textContent()").startswith("2/4"), "Step advances to beat 2")

    # 5. host-routed counter with memory
    log = ask("what if they go zone")
    call = next(e["msg"] for e in log if e["dir"] == "→ server" and e["msg"].get("method") == "tools/call")
    check(call["params"]["name"] == "counter_play" and call["params"]["arguments"]["defence"] == "zone" and call["params"]["arguments"]["play_id"].startswith("ply_7f3a9c"), "router: 'what if they go zone' -> counter_play with the remembered play_id")
    teardown = next((e["msg"] for e in log if e["dir"] == "→ view" and e["msg"].get("method") == "ui/resource-teardown"), None)
    check(teardown is not None, "old view got ui/resource-teardown before the new one")
    check(teardown and any(e["dir"] == "← view" and e["msg"].get("id") == teardown["id"] and "result" in e["msg"] for e in log), "old view answered the teardown request")

    # theme change reaches the live view as ui/notifications/host-context-changed
    pw("click", "#toggle-drawer"); pw("click", "[data-tab=settings]"); pw("select", "#theme", "light")
    time.sleep(0.5)
    check(in_view("await f.locator('html').getAttribute('data-theme')") == "light", "host-context-changed switches the view to the light theme")
    pw("select", "#theme", "dark"); pw("click", "#toggle-drawer")

    # 6. save, playbook (+ Send to TV from inside the view), practice, send, error, no match
    log = ask("save it as go-to")
    call = next(e["msg"] for e in log if e["dir"] == "→ server" and e["msg"].get("method") == "tools/call")
    check(call["params"]["name"] == "save_to_playbook" and call["params"]["arguments"]["tags"] == ["go-to"] and call["params"]["arguments"]["team_id"] == "team_demo00", "router: 'save it as go-to' -> save_to_playbook with tags array and remembered play_id")
    check("Cambridge Comets" in in_view("await f.locator('#title').textContent()"), "saved view shows the team name")
    shot(shots, "saved.png")

    log = ask("show me my playbook")
    call = next(e["msg"] for e in log if e["dir"] == "→ server" and e["msg"].get("method") == "tools/call")
    check(call["params"]["name"] == "list_playbook", "router: 'show me my playbook' -> list_playbook (not draw_play)")
    check(in_view("await f.locator('#carousel .card').count()") == 5, "playbook view shows 5 cards")
    check(any("Carousel items: 5" in r and r.startswith("pass") for r in lint_rows()), "far-field lint counts the carousel items")
    shot(shots, "playbook.png")
    js("() => { window.SIM.trafficLog.length = 0; return 0 }")
    in_view("await f.getByRole('button', { name: 'Send to TV' }).click({ timeout: 10000 })")
    wait_for("() => window.SIM.trafficLog.some(e => e.dir === '→ view' && e.msg.result)", 15, "send_to_tv reply to the view")
    req = next(e["msg"] for e in traffic() if e["dir"] == "← view" and e["msg"].get("method") == "tools/call")
    check(req["params"]["name"] == "send_to_tv" and req["params"]["arguments"]["code"] == "KQZT", "playbook view sent the selected play to the TV via the host")
    time.sleep(0.5)
    check("Living room TV" in in_view("await f.locator('#status').textContent()"), "playbook view shows the TV confirmation")

    log = ask("what are we practising on thursday")
    call = next(e["msg"] for e in log if e["dir"] == "→ server" and e["msg"].get("method") == "tools/call")
    check(call["params"] == {"name": "practice_plan", "arguments": {"team_id": "team_demo00", "minutes": 60}}, "router: practice question -> practice_plan with default minutes")
    check(in_view("await f.locator('#blocks li').count()") == 5, "practice view lists the blocks")
    shot(shots, "practice.png")

    log = ask("send it to the TV")
    call = next(e["msg"] for e in log if e["dir"] == "→ server" and e["msg"].get("method") == "tools/call")
    check(call["params"]["name"] == "send_to_tv" and call["params"]["arguments"]["code"] == "KQZT", "router: 'send it to the TV' -> send_to_tv with remembered code")
    check(in_view("await f.locator('#title').textContent()") == "Showing on Living room TV", "sent view shows the TV name")
    shot(shots, "sent.png")

    ask("send it to the TV code ABCD")
    check("no TV paired" in js("() => window.SIM.lastSummary"), "tool error (isError) is spoken and shown")

    ask("make me a sandwich")
    check(js("() => window.SIM.lastSummary") == "I do not have a tool for that.", "no matching tool -> spoken refusal")

    pw("click", "#toggle-drawer")
    pw("click", "[data-tab=lint]")
    time.sleep(0.3)
    shot(shots, "debug-drawer.png")

    # 7. any other server: keyword routing + generic card + a third-party view
    if args.demo_url:
        pw("goto", f"{args.url}/sim/?server={args.demo_url}/mcp", raw=False)
        wait_for("() => window.SIM && window.SIM.tools.length > 0", 20, "demo tools/list")
        log = ask("what's the weather in London")
        call = next(e["msg"] for e in log if e["dir"] == "→ server" and e["msg"].get("method") == "tools/call")
        check(call["params"] == {"name": "get_weather", "arguments": {"city": "London"}}, "keyword route: get_weather with city from 'in London'")
        check("temp" in js("() => window.SIM.lastSummary"), "tool without a view: generated one-liner from structuredContent")
        log = ask("show the lights in the kitchen")
        call = next(e["msg"] for e in log if e["dir"] == "→ server" and e["msg"].get("method") == "tools/call")
        check(call["params"] == {"name": "show_lights", "arguments": {"room": "kitchen"}}, "keyword route: show_lights with room from 'in the kitchen'")
        check(any(e["dir"] == "→ view" and e["msg"].get("method") == "ui/notifications/tool-result" for e in log), "lights demo view received tool-result")
        shot(shots, "lights-demo.png")

    pw("close", raw=False)
    print(f"\n{len(failures)} failures" if failures else "\nall checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
