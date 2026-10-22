# Protocol: the exact message sequence

Captured from the simulator's debug drawer against fastmcp 4.1.3 (`stateless_http=True`,
`json_response=False`) on 22 October 2026. Payloads are the real ones, trimmed with `...`.

Two channels:

- **host <-> server**: JSON-RPC 2.0 over Streamable HTTP. Every message is a `POST` to the MCP URL with
  `Content-Type: application/json`, `Accept: application/json, text/event-stream`,
  `MCP-Protocol-Version: 2025-11-25` and, once the server has issued one, `Mcp-Session-Id`.
  Replies come back as `text/event-stream`; the host splits events on blank lines, joins the `data:`
  lines, and takes the JSON-RPC message whose `id` matches the request. Notifications get `202` and no
  body. A plain `application/json` reply is accepted too.
- **host <-> view**: JSON-RPC 2.0 over `postMessage` between the page and a
  `<iframe sandbox="allow-scripts" srcdoc="...">`. The view posts to `parent` with target origin `*`;
  the host only listens to messages whose `source` is the live iframe (or the one it is tearing down).

## 1. Connect (page load)

```
→ server  id=1  initialize
   {"protocolVersion":"2025-11-25",
    "capabilities":{"extensions":{"io.modelcontextprotocol/ui":{"mimeTypes":["text/html;profile=mcp-app"]}}},
    "clientInfo":{"name":"smart-display-sim","version":"0.1.0"}}
← server  id=1  result
   {"protocolVersion":"2025-11-25","capabilities":{"logging":{},"prompts":{...},"resources":{...},"tools":{...}},
    "serverInfo":{"name":"chalk-talk-fake",...}}
→ server       notifications/initialized   {}
← server       HTTP 202, no body
→ server  id=2  tools/list   {}
← server  id=2  result
   {"tools":[{"name":"draw_play","description":"Draw a basketball play from a description...",
              "inputSchema":{"properties":{"description":{"type":"string"},"team_id":{...},"defence":{...}},"required":["description"]},
              "_meta":{"ui":{"resourceUri":"ui://chalk-talk/court"},"fastmcp":{"tags":[]}}}, ...]}
→ GET /sim-intents.json (same origin as the server) unless ?intents= or window.SIM_INTENTS is set
```

The host reads the view URI from `_meta.ui.resourceUri` (and accepts the older `_meta["ui/resourceUri"]`).

## 2. "draw a pick and roll on the right": tool call and view handshake

```
→ server  id=3  tools/call
   {"name":"draw_play","arguments":{"description":"pick and roll on the right","team_id":"team_demo00"}}
← server  id=3  result
   {"content":[{"type":"text","text":"{\"id\":\"ply_7f3a9c\",...}"}],
    "structuredContent":{"id":"ply_7f3a9c","name":"Pick and roll on the right","beats":[...],"summary":"Here is ..."},
    "isError":false}
→ server  id=4  resources/read   {"uri":"ui://chalk-talk/court"}
← server  id=4  result
   {"contents":[{"uri":"ui://chalk-talk/court","mimeType":"text/html;profile=mcp-app",
                 "_meta":{"ui":{"csp":{"connectDomains":[],"resourceDomains":[]},"prefersBorder":false}},
                 "text":"<!doctype html>..."}]}
```

The host appends its lint probe to `text` and sets it as the iframe `srcdoc`. The view starts the
handshake:

```
← view    id=1  ui/initialize
   {"protocolVersion":"2026-01-26","appInfo":{"name":"chalk-talk-court","version":"1.0.0"},"appCapabilities":{}}
→ view    id=1  result
   {"protocolVersion":"2026-01-26","hostInfo":{"name":"smart-display-sim","version":"0.1.0"},
    "hostCapabilities":{"serverTools":{},"serverResources":{},"openLinks":{}},
    "hostContext":{"platform":"web","theme":"dark","displayMode":"inline","availableDisplayModes":["inline"],
                   "deviceCapabilities":{"touch":true,"hover":false},"locale":"en-GB",
                   "containerDimensions":{"width":1280,"maxHeight":728}}}
← view         ui/notifications/initialized   {}
→ view         ui/notifications/tool-input
   {"arguments":{"description":"pick and roll on the right","team_id":"team_demo00"}}
→ view         ui/notifications/tool-result
   {"content":[...],"structuredContent":{"id":"ply_7f3a9c",...},"isError":false}      (the CallToolResult, verbatim)
← view         ui/notifications/size-changed   {"height":728}
```

Order matters: `tool-input` and `tool-result` are sent only after `ui/notifications/initialized`.
A view that renders on `ui/initialize`'s reply alone will miss the data. The host clamps the reported
height to the screen area (800 minus the 72 px transcript bar).

Then the host speaks `structuredContent.summary`.

## 3. The view calls a tool through the host ("What if they switch?")

```
← view    id=2  tools/call   {"name":"counter_play","arguments":{"play_id":"ply_7f3a9c","defence":"switch"}}
→ server  id=5  tools/call   {"name":"counter_play","arguments":{"play_id":"ply_7f3a9c","defence":"switch"}}
← server  id=5  result       {"content":[...],"structuredContent":{"id":"ply_7f3a9c-switch","what_changed":"Against a switch: ..."},"isError":false}
→ view    id=2  result       (the same CallToolResult)
```

The view's request id and the server's request id are independent. A failed server call is returned
to the view as `{"error":{"code":-32000,"message":"..."}}`. A tool result with `isError: true` is
returned as a normal result (the view decides what to show). Memory is updated from the result, and
the summary is spoken when it differs from the last one.

`resources/read` from a view is proxied the same way.

## 4. A new result replaces the view ("save it as go-to")

```
→ server  id=6  tools/call       {"name":"save_to_playbook","arguments":{"play_id":"ply_7f3a9c","team_id":"team_demo00","tags":["go-to"]}}
← server  id=6  result           {...,"structuredContent":{"play":{...},"playbook_count":5,"team_name":"Cambridge Comets U12","summary":"Saved ..."}}
→ server  id=7  resources/read   {"uri":"ui://chalk-talk/saved"}     (skipped when the URI is cached)
← server  id=7  result
→ view    id=8  ui/resource-teardown   {"reason":"new tool result"}   (to the old court view)
← view    id=8  result                 {}
← view    id=1  ui/initialize          (from the new saved view; the sequence of section 2 repeats)
→ view    id=1  result
← view         ui/notifications/initialized
→ view         ui/notifications/tool-input
→ view         ui/notifications/tool-result
← view         ui/notifications/size-changed   {"height":728}
```

The host waits up to 500 ms for the teardown reply, then removes the old iframe either way.

## 5. Other messages the host handles

| from the view | host behaviour |
|---|---|
| `ping` (request) | replies `{}` |
| `ui/open-link` `{url}` | `window.open(url, "_blank")`, replies `{}` |
| `ui/message` `{content:[{type:"text",text}]}` | speaks and shows the text, replies `{}` |
| `sim/lint` (notification, from the appended probe) | updates the lint panel |
| any other request | `{"error":{"code":-32601,"message":"unsupported: <method>"}}` |

| from the host | when |
|---|---|
| `ui/notifications/host-context-changed` `{theme}` | the theme is changed in Settings |
| `ui/resource-teardown` `{reason}` | before the iframe is replaced |

## 6. Minimal view

The five Chalk Talk views share this bridge (also the shape the lights demo uses):

```js
const host = (() => {
  let nextId = 0; const pending = new Map(); const handlers = {};
  const send = (m) => parent.postMessage({ jsonrpc: "2.0", ...m }, "*");
  const request = (method, params) => new Promise((resolve, reject) => {
    const id = ++nextId; pending.set(id, { resolve, reject }); send({ id, method, params }); });
  addEventListener("message", (e) => {
    if (e.source !== parent) return; const m = e.data; if (!m || m.jsonrpc !== "2.0") return;
    if (m.id !== undefined && m.method === undefined) { const p = pending.get(m.id); pending.delete(m.id);
      if (p) m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result); return; }
    if (m.method === "ui/resource-teardown" || m.method === "ping") { send({ id: m.id, result: {} }); return; }
    (handlers[m.method] || (() => {}))(m.params || {});
  });
  async function start(appInfo) {
    const init = await request("ui/initialize", { protocolVersion: "2026-01-26", appInfo, appCapabilities: {} });
    document.documentElement.dataset.theme = init.hostContext?.theme === "light" ? "light" : "dark";
    send({ method: "ui/notifications/initialized", params: {} });
    new ResizeObserver(() => send({ method: "ui/notifications/size-changed",
      params: { height: document.documentElement.scrollHeight } })).observe(document.body);
    return init.hostContext || {};
  }
  return { start, on: (method, fn) => handlers[method] = fn,
           callTool: (name, args) => request("tools/call", { name, arguments: args }) };
})();

host.on("ui/notifications/tool-result", (params) => render(params.structuredContent));
host.start({ name: "my-view", version: "1.0.0" });
```
