// Smart display simulator: a generic MCP Apps host in a 1280x800 frame.
// Talks Streamable HTTP (JSON-RPC over POST, SSE replies) to any MCP server
// and hosts the server's MCP App views in a sandboxed iframe. No build step.
//
// Query parameters: ?server=<mcp url> ?intents=<json url> ?theme=dark|light
// Globals honoured: window.SIM_INTENTS (an intents object, same shape as the JSON).

const MCP_PROTOCOL = "2025-11-25";      // host <-> server (Streamable HTTP)
const APPS_PROTOCOL = "2026-01-26";     // host <-> view (MCP Apps, postMessage)
const HOST_INFO = { name: "smart-display-sim", version: "0.1.0" };
const LINT = { minFontPx: 24, maxActions: 2, maxCarouselItems: 5, maxSummaryChars: 200 };
const STOPWORDS = new Set("a an the to of for on in at it that this my our me please can you show tell what is are do we with and or".split(" "));

const qs = new URLSearchParams(location.search);
const settings = {
  server: qs.get("server") || new URL("/mcp", location.href).href,
  intents: qs.get("intents") || "",
  theme: qs.get("theme") || "dark",
  mute: localStorage.getItem("sim.mute") === "1",
};

// ---------- DOM ----------
const $ = (id) => document.getElementById(id);
const el = {
  device: $("device"), screen: $("screen"), clock: $("clock"), date: $("date"),
  transcript: $("transcript"), assistant: $("assistant"), view: $("view"), lightbar: $("lightbar"),
  form: $("ask"), input: $("utterance"), mic: $("mic"), drawer: $("drawer"),
  traffic: $("traffic"), lint: $("lint"), tools: $("tools"), memory: $("memory"),
};

// ---------- state ----------
let sessionId = null;
let nextId = 0;
let tools = [];
let intents = { defaults: {}, memory: {}, speak: ["summary"], intents: [] };
let memory = {};                 // argument values remembered from earlier results
const resourceCache = new Map(); // uri -> html text
let frame = null;                // the live view iframe
let retiring = null;             // the previous iframe while it answers ui/resource-teardown
let frameReady = false;
let pendingForView = null;       // {args, result} to deliver after ui/notifications/initialized
let lastSummary = "";
const hostRequests = new Map();  // id -> resolve, for host -> view requests (teardown)

// ---------- traffic log (debug drawer) ----------
const trafficLog = [];
function log(dir, msg) {
  trafficLog.push({ dir, msg, at: Date.now() });
  if (trafficLog.length > 400) trafficLog.shift();
  const li = document.createElement("li");
  const cls = { "→ server": "to-server", "← server": "from-server", "→ view": "to-view", "← view": "from-view" }[dir] || "note";
  li.innerHTML = `<span class="dir ${cls}">${dir}</span>`;
  li.append(typeof msg === "string" ? msg : JSON.stringify(msg));
  el.traffic.append(li);
  el.traffic.lastElementChild?.scrollIntoView({ block: "end" });
}

// ---------- JSON-RPC over Streamable HTTP ----------
async function rpc(method, params, notify = false) {
  const body = { jsonrpc: "2.0", method, params };
  if (!notify) body.id = ++nextId;
  const headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": MCP_PROTOCOL,
  };
  if (sessionId) headers["Mcp-Session-Id"] = sessionId;
  log("→ server", body);
  const response = await fetch(settings.server, { method: "POST", headers, body: JSON.stringify(body) });
  sessionId = response.headers.get("Mcp-Session-Id") || sessionId;
  if (notify) { log("← server", `HTTP ${response.status} (notification, no body)`); return; }
  if (!response.ok) throw new Error(`HTTP ${response.status} ${await response.text()}`);
  const text = await response.text();
  const contentType = response.headers.get("content-type") || "";
  let message;
  if (contentType.includes("text/event-stream")) {
    // One or more SSE events; take the JSON-RPC message whose id matches ours.
    for (const event of text.split(/\r?\n\r?\n/)) {
      const data = event.split(/\r?\n/).filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trimStart()).join("\n");
      if (!data) continue;
      const parsed = JSON.parse(data);
      if (parsed.id === body.id) { message = parsed; break; }
    }
  } else {
    message = JSON.parse(text);
  }
  if (!message) throw new Error("no JSON-RPC reply with id " + body.id);
  log("← server", message);
  if (message.error) throw new Error(message.error.message || JSON.stringify(message.error));
  return message.result;
}

async function connect() {
  sessionId = null;
  const init = await rpc("initialize", {
    protocolVersion: MCP_PROTOCOL,
    capabilities: { extensions: { "io.modelcontextprotocol/ui": { mimeTypes: ["text/html;profile=mcp-app"] } } },
    clientInfo: HOST_INFO,
  });
  await rpc("notifications/initialized", {}, true);
  tools = (await rpc("tools/list", {})).tools || [];
  renderToolList();
  setAssistant(`Connected to ${init.serverInfo?.name || "server"}: ${tools.length} tools.`);
  await loadIntents();
}

async function loadIntents() {
  let source = settings.intents ? "url" : window.SIM_INTENTS ? "window.SIM_INTENTS" : "server";
  let url = settings.intents || new URL("/sim-intents.json", settings.server).href;
  try {
    const data = source === "window.SIM_INTENTS" ? window.SIM_INTENTS : await (await fetch(url)).json();
    intents = { defaults: {}, memory: {}, speak: ["summary"], intents: [], ...data };
    log("note", `intents loaded from ${source === "url" ? url : source}: ${intents.intents.length} patterns`);
  } catch (err) {
    intents = { defaults: {}, memory: {}, speak: ["summary"], intents: [] };
    log("note", `no intents JSON (${source === "window.SIM_INTENTS" ? source : url}); keyword routing only`);
  }
}

// ---------- router: utterance -> {tool, args} without an LLM ----------
function tokens(text) {
  return text.toLowerCase().replace(/[^a-z0-9_ ]+/g, " ").split(/\s+/).filter((w) => w && !STOPWORDS.has(w));
}

function stripWakeWord(text) {
  return text.trim().replace(/^(alexa|echo|computer|hey|ok)[,!]?\s+/i, "").replace(/[?.!]+$/, "").trim();
}

function findTool(name) { return tools.find((t) => t.name === name); }

// 1. intents table: first regex that matches wins; named groups become arguments.
function routeByIntent(text) {
  for (const intent of intents.intents) {
    const re = new RegExp(intent.match, "i");
    const m = re.exec(text);
    if (!m) continue;
    const tool = findTool(intent.tool);
    if (!tool) continue;
    const args = { ...(intent.args || {}) };
    for (const [k, v] of Object.entries(m.groups || {})) if (v !== undefined) args[k] = v.trim();
    return { tool, args, via: `intent /${intent.match}/` };
  }
  return null;
}

// 2. keyword overlap between the utterance and each tool's name + description.
function routeByKeywords(text) {
  const words = new Set(tokens(text));
  let best = null;
  for (const tool of tools) {
    const toolWords = new Set(tokens(tool.name.replace(/_/g, " ") + " " + (tool.title || "") + " " + (tool.description || "")));
    let score = 0;
    for (const w of words) if (toolWords.has(w)) score += tool.name.includes(w) ? 2 : 1;
    if (score > 0 && (!best || score > best.score)) best = { tool, score };
  }
  if (!best) return null;
  return { tool: best.tool, args: argsFromEntities(text, best.tool), via: `keywords (score ${best.score})` };
}

// Named-entity regexes for the keyword route: codes, ids, numbers, enums, "<name> <value>".
function argsFromEntities(text, tool) {
  const props = tool.inputSchema?.properties || {};
  const required = tool.inputSchema?.required || [];
  const args = {};
  for (const [name, schema] of Object.entries(props)) {
    let m;
    if (schema.enum) {
      const hit = schema.enum.find((v) => new RegExp(`\\b${String(v)}\\b`, "i").test(text));
      if (hit !== undefined) args[name] = hit;
    } else if (schema.type === "integer" || schema.type === "number") {
      if ((m = /\b(\d+(?:\.\d+)?)\b/.exec(text))) args[name] = Number(m[1]);
    } else if (/(^|_)code$/.test(name)) {
      if ((m = /\b([A-Z]{4,8})\b/i.exec(text))) args[name] = m[1].toUpperCase();
    } else if (/_id$/.test(name)) {
      if ((m = /\b([a-z]+_[0-9a-f]{4,})\b/i.exec(text))) args[name] = m[1];
    } else if ((m = new RegExp(`\\b${name.replace(/_/g, "[ _]")}\\s*(?:is|=|:)?\\s*([\\w-]+)`, "i").exec(text))) {
      args[name] = m[1];
    }
  }
  // The first still-missing string argument (required ones first) gets "the rest":
  // "weather in London" -> city: London; "lights in the kitchen" -> room: kitchen.
  const stringArgs = [...required, ...Object.keys(props).filter((n) => !required.includes(n))];
  for (const name of stringArgs) {
    if (args[name] !== undefined || props[name]?.type !== "string") continue;
    const m = /\b(?:in|for|at|to|of|about|called|named)\s+(?:the\s+)?(.+)$/i.exec(text);
    if (m) { args[name] = m[1].trim(); break; }
  }
  return args;
}

// Fill missing arguments from memory and defaults, keep only schema properties, coerce types.
function finishArgs(tool, args) {
  const props = tool.inputSchema?.properties || {};
  const out = {};
  for (const name of Object.keys(props)) {
    let v = args[name];
    if (v === undefined || v === "") v = memory[name];
    if (v === undefined || v === "") v = intents.defaults[name];
    if (v === undefined || v === "") continue;
    out[name] = coerce(v, props[name]);
  }
  for (const [k, v] of Object.entries(args)) if (!(k in props) && Object.keys(props).length === 0) out[k] = v;
  return out;
}

function coerce(value, schema = {}) {
  const type = schema.type || (Array.isArray(schema.anyOf) ? schema.anyOf.map((s) => s.type).find((t) => t && t !== "null") : undefined);
  if (type === "integer") return parseInt(value, 10);
  if (type === "number") return Number(value);
  if (type === "boolean") return /^(true|yes|on|1)$/i.test(String(value));
  if (type === "array") return Array.isArray(value) ? value : String(value).split(/\s*(?:,|\band\b)\s*/).filter(Boolean);
  return value;
}

export function route(text) {
  const plan = routeByIntent(text) || routeByKeywords(text);
  if (!plan) return null;
  plan.args = finishArgs(plan.tool, plan.args);
  return plan;
}

function remember(structured) {
  if (!structured || typeof structured !== "object") return;
  for (const [argName, paths] of Object.entries(intents.memory || {})) {
    for (const path of [].concat(paths)) {
      const v = path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), structured);
      if (v !== undefined && v !== null && typeof v !== "object") { memory[argName] = v; break; }
    }
  }
  el.memory.textContent = JSON.stringify(memory, null, 1);
}

// ---------- speaking ----------
function summaryOf(result, tool) {
  const sc = result.structuredContent;
  for (const path of intents.speak || ["summary"]) {
    const v = path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), sc);
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  if (result.isError) return (result.content || []).map((c) => c.text).filter(Boolean).join(" ") || "That did not work.";
  if (sc && typeof sc === "object") {
    const scalars = Object.entries(sc).filter(([, v]) => v !== null && typeof v !== "object").slice(0, 4);
    if (scalars.length) return `${humanize(tool.name)}: ` + scalars.map(([k, v]) => `${humanize(k)} ${v}`).join(", ") + ".";
  }
  const text = (result.content || []).find((c) => c.type === "text")?.text;
  if (text && !text.trim().startsWith("{")) return text.split(/(?<=[.!?])\s/)[0];
  return `${humanize(tool.name)} done.`;
}

function humanize(s) { return s.replace(/[_-]+/g, " "); }

function say(text) {
  lastSummary = text;
  setAssistant(text);
  if (settings.mute || !("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}

function setAssistant(text) {
  el.assistant.textContent = text;
  el.assistant.classList.toggle("show", !!text);
}

// ---------- the main flow: utterance -> tool -> view ----------
async function ask(raw) {
  const text = stripWakeWord(raw);
  if (!text) return;
  el.transcript.textContent = `“${text}”`;
  el.transcript.classList.add("show");
  el.lightbar.className = "lightbar thinking";
  try {
    if (!tools.length) await connect();
    const plan = route(text);
    log("note", plan ? `route: ${plan.tool.name} ${JSON.stringify(plan.args)} via ${plan.via}` : "route: no tool matched");
    if (!plan) { say("I do not have a tool for that."); showCard("No tool matched", { utterance: text }, true); return; }
    const result = await rpc("tools/call", { name: plan.tool.name, arguments: plan.args });
    remember(result.structuredContent);
    if (result.isError) { say(summaryOf(result, plan.tool)); showCard(humanize(plan.tool.name), { error: lastSummary }, true); return; }
    await showView(plan.tool, plan.args, result);
    say(summaryOf(result, plan.tool));
  } catch (err) {
    log("note", "error: " + err.message);
    say("Something went wrong: " + err.message);
    showCard("Error", { message: err.message }, true);
  } finally {
    el.lightbar.className = "lightbar";
  }
}

async function showView(tool, args, result) {
  const uri = tool._meta?.ui?.resourceUri || tool._meta?.["ui/resourceUri"];
  if (!uri) { showCard(tool.title || humanize(tool.name), result.structuredContent || { text: (result.content || []).map((c) => c.text).join("\n") }); return; }
  if (!resourceCache.has(uri)) {
    const contents = (await rpc("resources/read", { uri })).contents || [];
    const html = contents.find((c) => typeof c.text === "string");
    if (!html) throw new Error("resource has no text content: " + uri);
    resourceCache.set(uri, html.text);
  }
  await teardownView();
  frame = document.createElement("iframe");
  frame.sandbox = "allow-scripts";          // no same-origin: the view only sees postMessage
  frame.title = tool.name + " view";
  frameReady = false;
  pendingForView = { args, result };
  frame.srcdoc = resourceCache.get(uri) + LINT_PROBE;
  el.view.replaceChildren(frame);
  el.screen.dataset.mode = "view";
  lintReset();
}

function showCard(title, data, isError = false) {
  frame = null;
  const card = document.createElement("div");
  card.className = "card" + (isError ? " error" : "");
  const h1 = document.createElement("h1"); h1.textContent = title; card.append(h1);
  const dl = document.createElement("dl");
  for (const [k, v] of Object.entries(data || {})) {
    const dt = document.createElement("dt"); dt.textContent = humanize(k);
    const dd = document.createElement("dd"); dd.textContent = typeof v === "object" ? JSON.stringify(v) : String(v);
    dl.append(dt, dd);
  }
  card.append(dl);
  el.view.replaceChildren(card);
  el.screen.dataset.mode = "view";
}

// Ask the old view to tear down (it answers the request), then drop it.
async function teardownView() {
  if (!frame || !frameReady) { frame = null; return; }
  retiring = frame; frame = null;
  const id = ++nextId;
  const done = new Promise((resolve) => hostRequests.set(id, resolve));
  postToView(retiring, { jsonrpc: "2.0", id, method: "ui/resource-teardown", params: { reason: "new tool result" } });
  await Promise.race([done, new Promise((r) => setTimeout(r, 500))]);   // the view may answer or vanish
  hostRequests.delete(id);
  retiring.remove();
  retiring = null;
}

function hostContext() {
  return {
    platform: "web",
    theme: settings.theme,
    displayMode: "inline",
    availableDisplayModes: ["inline"],
    deviceCapabilities: { touch: true, hover: false },
    locale: navigator.language,
    containerDimensions: { width: el.view.clientWidth, maxHeight: el.view.clientHeight },
  };
}

function postToView(target, message) {
  log("→ view", message);
  target.contentWindow.postMessage(message, "*");
}

// ---------- host side of the MCP Apps protocol (postMessage) ----------
window.addEventListener("message", async (event) => {
  const m = event.data;
  if (!m || m.jsonrpc !== "2.0") return;
  const fromLive = frame && event.source === frame.contentWindow;
  const fromRetiring = retiring && event.source === retiring.contentWindow;
  if (!fromLive && !fromRetiring) return;
  if (m.method !== "sim/lint") log("← view", m);
  if (m.id !== undefined && m.method === undefined) {           // reply to a host request (teardown)
    hostRequests.get(m.id)?.(m);
    return;
  }
  if (!fromLive) return;                                        // a retiring view gets no further service
  const reply = (payload) => postToView(frame, { jsonrpc: "2.0", id: m.id, ...payload });
  switch (m.method) {
    case "ui/initialize":
      reply({ result: { protocolVersion: APPS_PROTOCOL, hostInfo: HOST_INFO,
        hostCapabilities: { serverTools: {}, serverResources: {}, openLinks: {} }, hostContext: hostContext() } });
      break;
    case "ui/notifications/initialized":                          // only now send tool data
      frameReady = true;
      if (pendingForView) {
        postToView(frame, { jsonrpc: "2.0", method: "ui/notifications/tool-input", params: { arguments: pendingForView.args } });
        postToView(frame, { jsonrpc: "2.0", method: "ui/notifications/tool-result", params: pendingForView.result });
        pendingForView = null;
      }
      break;
    case "ui/notifications/size-changed": {
      const max = el.view.clientHeight;
      frame.style.height = Math.min(m.params?.height || max, max) + "px";
      break;
    }
    case "tools/call":
      try {
        const result = await rpc("tools/call", m.params);
        remember(result.structuredContent);
        const spoken = summaryOf(result, findTool(m.params?.name) || { name: m.params?.name || "tool" });
        if (result.structuredContent && spoken !== lastSummary) say(spoken);
        reply({ result });
      } catch (err) { reply({ error: { code: -32000, message: String(err.message || err) } }); }
      break;
    case "resources/read":
      try { reply({ result: await rpc("resources/read", m.params) }); }
      catch (err) { reply({ error: { code: -32000, message: String(err.message || err) } }); }
      break;
    case "ui/open-link":
      window.open(m.params?.url, "_blank", "noopener");
      reply({ result: {} });
      break;
    case "ui/message":                                            // the view wants to say something
      say((m.params?.content || []).map((c) => c.text).filter(Boolean).join(" ") || "");
      reply({ result: {} });
      break;
    case "ping":
      reply({ result: {} });
      break;
    case "sim/lint":                                              // from the probe we appended
      lintRender(m.params);
      break;
    default:
      if (m.id !== undefined) reply({ error: { code: -32601, message: "unsupported: " + m.method } });
  }
});

// ---------- far-field lint ----------
// Appended to every view HTML. Sandboxed iframes have no DOM access from the host,
// so the probe measures from inside and posts a sim/lint notification.
const LINT_PROBE = `
<script>(function () {
  var visible = function (e) { var r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== "hidden"; };
  function run() {
    var small = [], seen = new Set(), walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), n;
    while ((n = walker.nextNode())) {
      var t = n.textContent.trim(), e = n.parentElement;
      if (!t || !e || seen.has(e) || !visible(e)) continue;
      seen.add(e);
      var px = parseFloat(getComputedStyle(e).fontSize);
      if (px < ${LINT.minFontPx}) small.push({ text: t.slice(0, 40), px: Math.round(px) });
    }
    var toolbars = Array.prototype.filter.call(document.querySelectorAll("[role=toolbar]"), visible);
    var actions = Array.prototype.filter.call(document.querySelectorAll("button,[role=button],a[href],input[type=submit]"), function (b) { return visible(b) && !b.closest("[role=toolbar]"); });
    var items = Math.max.apply(null, [0].concat(Array.prototype.map.call(document.querySelectorAll("[data-carousel],[role=list]"), function (c) { return c.children.length; })));
    parent.postMessage({ jsonrpc: "2.0", method: "sim/lint", params: { smallText: small, actions: actions.length + toolbars.length, carouselItems: items } }, "*");
  }
  var timer; var schedule = function () { clearTimeout(timer); timer = setTimeout(run, 400); };
  new MutationObserver(schedule).observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true });
  addEventListener("load", schedule); schedule();
})();<\/script>`;

function lintReset() { el.lint.innerHTML = '<li class="muted">Waiting for the view to render.</li>'; }

function lintRender(r) {
  const summary = lastSummaryForLint();
  const rows = [
    { ok: r.smallText.length === 0, text: `Text under ${LINT.minFontPx} px: ${r.smallText.length}`,
      detail: r.smallText.slice(0, 6).map((s) => `${s.px}px “${s.text}”`).join("; ") },
    { ok: r.actions <= LINT.maxActions, text: `Actions: ${r.actions} (max ${LINT.maxActions}; a toolbar group counts as one)` },
    { ok: r.carouselItems <= LINT.maxCarouselItems, text: `Carousel items: ${r.carouselItems} (max ${LINT.maxCarouselItems})` },
    { ok: summary.length <= LINT.maxSummaryChars, text: `Spoken summary: ${summary.length} characters (max ${LINT.maxSummaryChars})`, detail: summary },
  ];
  el.lint.innerHTML = "";
  for (const row of rows) {
    const li = document.createElement("li");
    li.className = row.ok ? "" : "warn";
    li.textContent = (row.ok ? "pass  " : "WARN  ") + row.text;
    if (row.detail) { const s = document.createElement("small"); s.textContent = row.detail; li.append(s); }
    el.lint.append(li);
  }
}
function lastSummaryForLint() { return lastSummary || ""; }

// ---------- UI wiring ----------
function renderToolList() {
  el.tools.innerHTML = "";
  for (const t of tools) {
    const li = document.createElement("li");
    const uri = t._meta?.ui?.resourceUri || t._meta?.["ui/resourceUri"];
    li.innerHTML = `<b></b> <small></small><small></small>`;
    li.children[0].textContent = t.name;
    li.children[1].textContent = t.description || "";
    li.children[2].textContent = (uri ? "view " + uri + " · " : "") + "args " + Object.keys(t.inputSchema?.properties || {}).join(", ");
    el.tools.append(li);
  }
}

function tickClock() {
  const now = new Date();
  el.clock.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  el.date.textContent = now.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" });
}

function fitDevice() {
  const w = 1280 + 56, h = 800 + 56;          // screen plus bezel
  const drawerW = el.drawer.hidden ? 0 : el.drawer.offsetWidth;
  const scale = Math.min(1, (innerWidth - drawerW - 32) / w, (innerHeight - 110) / h);
  el.device.style.transform = `scale(${scale})`;
  el.device.style.marginBottom = (scale - 1) * h + "px";
  el.device.style.marginRight = (scale - 1) * w + "px";
}

function wireUi() {
  el.form.addEventListener("submit", (e) => { e.preventDefault(); ask(el.input.value); el.input.select(); });
  $("toggle-drawer").onclick = () => { el.drawer.hidden = !el.drawer.hidden; fitDevice(); };
  for (const b of document.querySelectorAll(".tabs button")) b.onclick = () => {
    document.querySelectorAll(".tabs button, .panel").forEach((x) => x.classList.remove("active"));
    b.classList.add("active"); document.querySelector(`[data-panel="${b.dataset.tab}"]`).classList.add("active");
  };
  $("clear-traffic").onclick = () => { trafficLog.length = 0; el.traffic.innerHTML = ""; };
  $("copy-traffic").onclick = () => navigator.clipboard?.writeText(trafficLog.map((e) => `${e.dir} ${typeof e.msg === "string" ? e.msg : JSON.stringify(e.msg)}`).join("\n"));
  $("server-url").value = settings.server;
  $("intents-url").value = settings.intents;
  $("theme").value = settings.theme;
  $("mute").checked = settings.mute;
  $("mute").onchange = (e) => { settings.mute = e.target.checked; localStorage.setItem("sim.mute", settings.mute ? "1" : "0"); };
  $("theme").onchange = (e) => {
    settings.theme = e.target.value;
    if (frame && frameReady) postToView(frame, { jsonrpc: "2.0", method: "ui/notifications/host-context-changed", params: { theme: settings.theme } });
  };
  $("reconnect").onclick = async () => {
    settings.server = $("server-url").value.trim(); settings.intents = $("intents-url").value.trim();
    tools = []; memory = {}; resourceCache.clear();
    try { await connect(); } catch (err) { say("Cannot connect: " + err.message); }
  };
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR) {
    el.mic.hidden = false;
    el.mic.onclick = () => {
      const rec = new SR(); rec.lang = navigator.language; rec.interimResults = false;
      el.mic.classList.add("listening"); el.lightbar.className = "lightbar listening";
      rec.onresult = (e) => { el.input.value = e.results[0][0].transcript; ask(el.input.value); };
      rec.onend = () => { el.mic.classList.remove("listening"); if (el.lightbar.className.includes("listening")) el.lightbar.className = "lightbar"; };
      rec.onerror = (e) => log("note", "speech recognition error: " + e.error);
      rec.start();
    };
  }
  addEventListener("resize", fitDevice);
  fitDevice();
  tickClock(); setInterval(tickClock, 10_000);
}

if (typeof document !== "undefined") {
  wireUi();
  connect().catch((err) => { log("note", "connect failed: " + err.message); say("Cannot reach the MCP server at " + settings.server); });
  // Exposed for the end-to-end check (dev/check.py) and for poking at the host from the console.
  window.SIM = { ask, route, rpc, get tools() { return tools; }, get memory() { return memory; }, trafficLog, settings, get lastSummary() { return lastSummary; } };
}
