"""Backend checks against the contract: run with
    cd <repo> && LLM_DISABLED=1 CHALK_ENGINE=stub python3 -m pytest backend/tests -q   # backend alone
    cd <repo> && LLM_DISABLED=1 python3 -m pytest backend/tests -q                     # with the real engine
"""

import json
import os
import re

import pytest

os.environ.setdefault("LLM_DISABLED", "1")
os.environ.setdefault("CHALK_STATE", "memory")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import create_app  # noqa: E402

MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json",
               "MCP-Protocol-Version": "2025-11-25"}


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def rpc(client, method, params, msg_id=1):
    reply = client.post("/mcp", json={"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}, headers=MCP_HEADERS)
    assert reply.status_code == 200, reply.text
    for event in reply.text.split("\n\n"):  # SSE: one event per message, pick ours by id
        data = "\n".join(line[5:].strip() for line in event.split("\n") if line.startswith("data:"))
        if data and json.loads(data).get("id") == msg_id:
            return json.loads(data)
    raise AssertionError("no reply with id %s in %r" % (msg_id, reply.text[:200]))


def test_health(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True and body["llm"] == "off" and body["version"]


def test_create_play_from_text_rules_path(client):
    play = client.post("/api/plays", json={"text": "backdoor cut from the left wing"}).json()
    assert re.fullmatch(r"ply_[0-9a-f]{6}", play["id"])
    assert play["template"] == "backdoor_cut" and play["params"]["side"] == "left"
    assert play["parse"]["method"] == "rules" and play["defence"] == "man"
    assert play["beats"][0]["t"] == 0 and play["validity"]["ok"]
    ids = {p["id"] for p in play["players"]}
    for beat in play["beats"]:
        assert set(beat["positions"]) == ids
    assert client.get(f"/api/plays/{play['id']}").json()["id"] == play["id"]


def test_create_play_errors(client):
    assert client.post("/api/plays", json={}).status_code == 422
    assert client.post("/api/plays", json={}).json()["error"]["code"]
    assert client.get("/api/plays/ply_000000").status_code == 404
    assert client.post("/api/plays", json={"text": "do a cartwheel"}).status_code == 422


def test_create_play_from_sketch(client):
    play = client.post("/api/plays", json={"sketch": {"strokes": [[[10, 30], [12, 20]], [[8, 35], [15, 25]]]}}).json()
    assert play["parse"]["method"] == "sketch" and play["params"]["side"] == "left"


def test_counter(client):
    play = client.post("/api/plays", json={"text": "pick and roll on the right"}).json()
    counter = client.post(f"/api/plays/{play['id']}/counter", json={"defence": "switch"}).json()
    assert counter["id"] == play["id"] + "-switch" and counter["defence"] == "switch"
    assert counter["name"].endswith(" vs switch") and counter["validity"]["ok"]
    assert client.get(f"/api/plays/{counter['id']}").status_code == 200
    assert client.post(f"/api/plays/{play['id']}/counter", json={"defence": "triangle"}).status_code == 422


def test_teams_playbook_and_practice_plan(client):
    demo = client.get("/api/teams/team_demo00").json()
    assert demo["name"] == "Cambridge Comets U12"
    assert client.get("/api/teams/team_demo00/playbook").json()["count"] == 4

    team = client.post("/api/teams", json={"name": "Test Tigers", "sport": "basketball", "age_group": "u10", "players_per_side": 3}).json()
    assert re.fullmatch(r"team_[0-9a-f]{6}", team["id"]) and team["created_at"]
    assert client.get(f"/api/teams/{team['id']}/playbook").json() == {"plays": [], "count": 0}

    play = client.post("/api/plays", json={"text": "give and go", "team_id": team["id"]}).json()
    assert play["params"]["players_per_side"] == 3 and play["params"]["age_group"] == "u10"
    saved = client.post(f"/api/teams/{team['id']}/playbook", json={"play_id": play["id"], "tags": ["passing"]}).json()
    assert saved["count"] == 1 and saved["play"]["id"] == play["id"] and saved["play"]["tags"] == ["passing"]
    assert set(saved["play"]) == {"id", "name", "template", "defence", "tags", "beats", "saved_at"}

    plan = client.post(f"/api/teams/{team['id']}/practice_plan", json={"minutes": 45, "focus": "passing"}).json()
    titles = [b["title"] for b in plan["blocks"]]
    assert titles[0] == "Warm-up" and titles[-2] == "Scrimmage" and titles[-1] == "Cool-down"
    assert any(b.get("play_id") == play["id"] for b in plan["blocks"])
    assert sum(b["minutes"] for b in plan["blocks"]) == 45
    assert plan["blocks"][-1]["start_min"] + plan["blocks"][-1]["minutes"] == 45
    assert plan["summary"].endswith("scrimmage and cool-down.")

    demo_plan = client.post("/api/teams/team_demo00/practice_plan", json={"minutes": 60}).json()
    assert 2 <= sum(1 for b in demo_plan["blocks"] if "play_id" in b) <= 3
    assert client.get("/api/teams/team_nope").status_code == 404


def test_tv_pair_command_state_cursor(client):
    paired = client.post("/api/tv/pair", json={}).json()
    code = paired["code"]
    assert re.fullmatch(r"[A-HJ-NP-Z]{4}", code) and paired["tv_id"].startswith("tv_") and paired["expires_at"]
    state = client.get(f"/api/tv/{code}/state").json()
    assert state["play"] is None and state["cursor"] == 0 and state["beat_index"] == 0

    play = client.post("/api/plays", json={"text": "horns"}).json()
    sent = client.post(f"/api/tv/{code}/command", json={"type": "show_play", "play_id": play["id"]}).json()
    assert sent == {"ok": True, "cursor": 1}
    state = client.get(f"/api/tv/{code}/state", params={"cursor": 0, "wait": 1}).json()
    assert state["cursor"] == 1 and state["play"]["id"] == play["id"] and state["defence"] == "man"

    assert client.post(f"/api/tv/{code}/command", json={"type": "set_beat", "index": 2}).json()["cursor"] == 2
    assert client.get(f"/api/tv/{code}/state").json()["beat_index"] == 2
    assert client.post(f"/api/tv/{code}/command", json={"type": "counter", "defence": "zone"}).json()["cursor"] == 3
    state = client.get(f"/api/tv/{code}/state").json()
    assert state["defence"] == "zone" and state["play"]["id"] == play["id"] + "-zone"
    assert client.post(f"/api/tv/{code}/command", json={"type": "play"}).json()["cursor"] == 4
    assert client.get(f"/api/tv/{code.lower()}/state").json()["playing"] is True

    assert client.get("/api/tv/ZZZZ/state").status_code == 404
    assert client.post(f"/api/tv/{code}/command", json={"type": "dance"}).status_code == 422
    assert client.post(f"/api/tv/{code}/command", json={"type": "show_play", "play_id": "ply_000000"}).status_code == 422


def test_templates_and_static(client):
    catalog = client.get("/api/templates").json()
    assert {t["id"] for t in catalog} == {"pick_and_roll", "pick_and_pop", "backdoor_cut", "give_and_go",
                                          "dribble_handoff", "flare_screen", "horns", "fast_break_3v2"}
    assert client.get("/").status_code == 200 and "/phone" in client.get("/").text
    redirect = client.get("/sim", follow_redirects=False)
    assert redirect.status_code == 307 and redirect.headers["location"].endswith("/mcp")
    assert client.get("/renderer/court.js").status_code in (200, 404)  # 404 only before the renderer lands
    assert client.get("/sim-intents.json").status_code in (200, 404)


def test_cors_headers(client):
    reply = client.get("/api/health", headers={"Origin": "http://example.com"})
    assert reply.headers.get_list("access-control-allow-origin") == ["*"]
    reply = client.options("/mcp", headers={"Origin": "http://example.com", "Access-Control-Request-Method": "POST",
                                             "Access-Control-Request-Headers": "content-type,mcp-protocol-version"})
    assert reply.status_code == 200 and reply.headers.get("access-control-allow-origin") == "*"
    reply = client.post("/mcp", json={"jsonrpc": "2.0", "id": 9, "method": "ping", "params": {}},
                        headers={**MCP_HEADERS, "Origin": "http://example.com"})
    assert "Mcp-Session-Id" in reply.headers.get("access-control-expose-headers", "")


def test_mcp_smoke(client):
    init = rpc(client, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}})
    assert init["result"]["serverInfo"]["name"] == "chalk-talk"
    tools = rpc(client, "tools/list", {})["result"]["tools"]
    assert len(tools) == 6
    views = {t["name"]: t["_meta"]["ui"]["resourceUri"] for t in tools}
    assert views == {"draw_play": "ui://chalk-talk/court", "counter_play": "ui://chalk-talk/court",
                     "save_to_playbook": "ui://chalk-talk/saved", "list_playbook": "ui://chalk-talk/playbook",
                     "practice_plan": "ui://chalk-talk/practice", "send_to_tv": "ui://chalk-talk/sent"}
    for tool in tools:
        assert len(tool["description"]) > 60, tool["name"]

    drawn = rpc(client, "tools/call", {"name": "draw_play", "arguments": {"description": "pick and pop on the left"}})["result"]
    assert not drawn.get("isError"), drawn
    play = drawn["structuredContent"]
    assert play["template"] == "pick_and_pop" and len(play["beats"]) >= 3 and play["summary"]

    countered = rpc(client, "tools/call", {"name": "counter_play", "arguments": {"play_id": play["id"], "defence": "hedge"}})["result"]["structuredContent"]
    assert countered["defence"] == "hedge" and countered["what_changed"]

    saved = rpc(client, "tools/call", {"name": "save_to_playbook", "arguments": {"play_id": play["id"], "team_id": "team_demo00", "tags": ["screens"]}})["result"]["structuredContent"]
    assert saved["team_name"] == "Cambridge Comets U12" and saved["playbook_count"] >= 5

    listed = rpc(client, "tools/call", {"name": "list_playbook", "arguments": {"team_id": "team_demo00", "filter": "screens"}})["result"]["structuredContent"]
    assert 3 <= len(listed["plays"]) <= 5 and listed["total"] >= 5

    plan = rpc(client, "tools/call", {"name": "practice_plan", "arguments": {"team_id": "team_demo00", "minutes": 60, "focus": "screens"}})["result"]["structuredContent"]
    assert plan["blocks"][0]["title"] == "Warm-up" and plan["summary"]

    code = client.post("/api/tv/pair", json={}).json()["code"]
    sent = rpc(client, "tools/call", {"name": "send_to_tv", "arguments": {"play_id": play["id"], "code": code}})["result"]["structuredContent"]
    assert sent == {"tv_name": "Living room TV", "code": code, "play_name": play["name"], "beat_index": 0, "status": "showing", "summary": sent["summary"]}
    assert client.get(f"/api/tv/{code}/state").json()["play"]["id"] == play["id"]

    failed = rpc(client, "tools/call", {"name": "send_to_tv", "arguments": {"play_id": play["id"], "code": "ZZZZ"}})["result"]
    assert failed.get("isError") is True

    resources = rpc(client, "resources/list", {})["result"]["resources"]
    assert {r["uri"] for r in resources} == set(views.values())
    for resource in resources:
        assert resource["mimeType"] == "text/html;profile=mcp-app"
        assert resource["_meta"]["ui"] == {"csp": {"connectDomains": [], "resourceDomains": []}, "prefersBorder": False}
    court = rpc(client, "resources/read", {"uri": "ui://chalk-talk/court"})["result"]["contents"][0]
    assert court["mimeType"] == "text/html;profile=mcp-app" and "ui/initialize" in court["text"]
    assert "INLINE:court.js" not in court["text"]
