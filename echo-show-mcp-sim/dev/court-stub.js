// Minimal stand-in for Chalk Talk's renderer/court.js (contract section 7), used only by
// dev/fake_chalk_talk.py to inline into backend/views/court.html while the real renderer is built.
// Same exported names and argument order as the contract; drawing is deliberately plain.

const COURT_W = 50, COURT_L = 47;

export function playerColor(player) {
  return player.team === "defense" ? "#3b82f6" : "#f28c28";
}

export function beatStart(play, i) {
  return play.beats[Math.max(0, Math.min(i, play.beats.length - 1))].t;
}

export function totalDuration(play) {
  return play.beats[play.beats.length - 1].t;
}

function lerp(a, b, k) { return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k]; }

function alongPath(path, k) {
  let total = 0;
  const segs = [];
  for (let i = 1; i < path.length; i++) {
    const d = Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]);
    segs.push(d); total += d;
  }
  if (total === 0) return path[path.length - 1];
  let dist = k * total;
  for (let i = 0; i < segs.length; i++) {
    if (dist <= segs[i]) return lerp(path[i], path[i + 1], segs[i] ? dist / segs[i] : 1);
    dist -= segs[i];
  }
  return path[path.length - 1];
}

export function interpolate(play, tSec) {
  const beats = play.beats;
  let i = 0;
  while (i + 1 < beats.length && beats[i + 1].t <= tSec) i++;
  const a = beats[i], b = beats[i + 1];
  const k = b ? Math.min(1, Math.max(0, (tSec - a.t) / (b.t - a.t))) : 1;
  const positions = {};
  for (const p of play.players) {
    const from = a.positions[p.id], to = b ? b.positions[p.id] : from;
    const path = b && b.paths && b.paths[p.id];
    positions[p.id] = path ? alongPath(path, k) : lerp(from, to, k);
  }
  let ball;
  const next = b ? b.ball : a.ball;
  if (b && next && typeof next === "object") ball = { from: next.from, to: next.to, progress: k };
  else ball = { holder: typeof a.ball === "string" ? a.ball : a.ball.to };
  return { positions, ball, beatIndex: i };
}

export function drawCourt(ctx, w, h, opts = {}) {
  const sx = w / COURT_W, sy = h / COURT_L;
  const X = (x) => x * sx, Y = (y) => h - y * sy;
  ctx.fillStyle = opts.floor || "#1d2435";
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = opts.lines || "#8fa3c8";
  ctx.lineWidth = 2;
  ctx.strokeRect(1, 1, w - 2, h - 2);
  ctx.strokeRect(X(17), Y(19), X(16), Y(0) - Y(19));          // lane
  ctx.beginPath(); ctx.arc(X(25), Y(19), 6 * sx, 0, Math.PI * 2); ctx.stroke();   // free-throw circle
  ctx.beginPath(); ctx.arc(X(25), Y(5.25), 19.75 * sx, Math.PI, 0); ctx.stroke();  // three-point arc (youth)
  ctx.beginPath(); ctx.arc(X(25), Y(5.25), 0.75 * sx, 0, Math.PI * 2); ctx.strokeStyle = "#f28c28"; ctx.stroke(); // rim
}

export function drawFrame(ctx, w, h, play, tSec, opts = {}) {
  drawCourt(ctx, w, h, opts);
  const sx = w / COURT_W, sy = h / COURT_L;
  const X = (x) => x * sx, Y = (y) => h - y * sy;
  const frame = interpolate(play, tSec);
  const r = h * 0.07 / 2;
  if (opts.paths !== false) {
    const beat = play.beats[frame.beatIndex + 1];
    ctx.setLineDash([6, 6]); ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.lineWidth = 2;
    for (const [id, path] of Object.entries((beat && beat.paths) || {})) {
      ctx.beginPath(); path.forEach(([x, y], i) => (i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y)))); ctx.stroke();
    }
    ctx.setLineDash([]);
  }
  for (const p of play.players) {
    const [x, y] = frame.positions[p.id];
    ctx.beginPath(); ctx.arc(X(x), Y(y), r, 0, Math.PI * 2);
    ctx.fillStyle = playerColor(p); ctx.fill();
    ctx.fillStyle = "#fff"; ctx.font = `bold ${Math.round(r)}px system-ui, sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(p.label, X(x), Y(y));
  }
  let bx, by;
  if (frame.ball.holder) { [bx, by] = frame.positions[frame.ball.holder]; bx = X(bx) + r * 0.8; by = Y(by) - r * 0.8; }
  else { const [a, b] = [frame.positions[frame.ball.from], frame.positions[frame.ball.to]]; const m = lerp(a, b, frame.ball.progress); bx = X(m[0]); by = Y(m[1]); }
  ctx.beginPath(); ctx.arc(bx, by, r * 0.35, 0, Math.PI * 2); ctx.fillStyle = "#fff"; ctx.fill();
}
