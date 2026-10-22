// Chalk Talk renderer. Draws a Play (CONTRACTS.md section 2) on a <canvas>
// and interpolates player positions between beats. ES module, no dependencies.
//
// Court coordinates are feet: x 0..50 across, y 0..47 from the baseline (y=0)
// to the half-court line. On the canvas x maps to width and y to height with
// the baseline at the BOTTOM, exactly as CONTRACTS.md section 7 says. Size the
// canvas 50:47 (for example 1000x940) if you want circles to stay circles.

export const COURT = {
  width: 50,
  length: 47,
  basket: [25, 5.25],
  freeThrowY: 19,
  laneLeft: 17,
  laneRight: 33,
  threePointRadius: 19.75,
};

const OFFENSE_COLOR = "#f28c28";
const DEFENSE_COLOR = "#3b82f6";
const BALL_COLOR = "#ffffff";

const DEFAULT_COURT_OPTS = {
  floor: "#1e2838",
  lane: "#243247",
  line: "rgba(255, 255, 255, 0.82)",
};

// ---------- small helpers ----------

function toCanvas(x, y, w, h) {
  return [(x / COURT.width) * w, h - (y / COURT.length) * h];
}

function distance(a, b) {
  return Math.hypot(b[0] - a[0], b[1] - a[1]);
}

function lerp(a, b, f) {
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
}

// Point at fraction u (0..1 by arc length) along a polyline of [x, y] points.
function pointAlongPolyline(points, u) {
  if (points.length === 1) return points[0].slice();
  const lengths = [];
  let total = 0;
  for (let i = 1; i < points.length; i++) {
    const d = distance(points[i - 1], points[i]);
    lengths.push(d);
    total += d;
  }
  if (total === 0) return points[points.length - 1].slice();
  let remaining = Math.min(Math.max(u, 0), 1) * total;
  for (let i = 0; i < lengths.length; i++) {
    const last = i === lengths.length - 1;
    if (remaining <= lengths[i] || last) {
      const f = lengths[i] === 0 ? 1 : Math.min(1, remaining / lengths[i]);
      return lerp(points[i], points[i + 1], f);
    }
    remaining -= lengths[i];
  }
  return points[points.length - 1].slice();
}

// Who holds the ball at a beat: a player id, or the receiver of a completed pass.
function holderAt(beat) {
  if (typeof beat.ball === "string") return beat.ball;
  if (beat.ball && beat.ball.to) return beat.ball.to;
  return null;
}

// Full waypoint list for a player moving from beat `from` to beat `to`.
// The contract says a path starts at the previous position and ends at the
// new one; we add both ends anyway so a sloppy path still lands correctly.
function waypoints(fromBeat, toBeat, id) {
  const start = fromBeat.positions[id];
  const end = toBeat.positions[id];
  const path = (toBeat.paths && toBeat.paths[id]) || [];
  return [start, ...path, end];
}

// ---------- public API ----------

export function playerColor(player) {
  if (player === "ball") return BALL_COLOR;
  const team = typeof player === "string" ? player : player && player.team;
  if (team === "defense" || team === "defence") return DEFENSE_COLOR;
  if (typeof team === "string" && team.startsWith("D")) return DEFENSE_COLOR;
  return OFFENSE_COLOR;
}

export function beatStart(play, i) {
  const beats = play.beats;
  const index = Math.min(Math.max(i, 0), beats.length - 1);
  return beats[index].t;
}

export function totalDuration(play) {
  return play.beats[play.beats.length - 1].t;
}

// Returns {positions: {id: [x, y]}, ball, beatIndex, progress, t}.
// ball is {holder, xy} while held, or {from, to, progress, xy} while a pass
// is in flight. beatIndex is the beat we are animating FROM; at an exact beat
// time it is that beat with progress 0.
export function interpolate(play, tSec) {
  const beats = play.beats;
  const last = beats.length - 1;
  let t = Number.isFinite(tSec) ? tSec : 0;
  t = Math.min(Math.max(t, 0), beats[last].t);

  let i = 0;
  while (i < last && beats[i + 1].t <= t) i++;

  if (i === last) {
    const beat = beats[last];
    const positions = {};
    for (const id of Object.keys(beat.positions)) positions[id] = beat.positions[id].slice();
    const holder = holderAt(beat);
    return {
      positions,
      ball: { holder, xy: holder ? positions[holder].slice() : null },
      beatIndex: last,
      progress: 0,
      t,
    };
  }

  const from = beats[i];
  const to = beats[i + 1];
  const progress = (t - from.t) / (to.t - from.t);

  const positions = {};
  for (const id of Object.keys(from.positions)) {
    if (!to.positions[id]) {
      positions[id] = from.positions[id].slice();
      continue;
    }
    positions[id] = pointAlongPolyline(waypoints(from, to, id), progress);
  }

  let ball;
  const next = to.ball;
  if (next && typeof next === "object" && next.from && next.to) {
    const start = from.positions[next.from] || positions[next.from];
    const end = to.positions[next.to] || positions[next.to];
    ball = { from: next.from, to: next.to, progress, xy: lerp(start, end, progress) };
  } else {
    const holder = holderAt(from);
    ball = { holder, xy: holder && positions[holder] ? positions[holder].slice() : null };
  }

  return { positions, ball, beatIndex: i, progress, t };
}

export function drawCourt(ctx, w, h, opts = {}) {
  const o = { ...DEFAULT_COURT_OPTS, ...opts };
  const sx = w / COURT.width;
  const sy = h / COURT.length;
  const px = (x, y) => toCanvas(x, y, w, h);
  const [bx, by] = px(...COURT.basket);

  ctx.save();
  ctx.fillStyle = o.floor;
  ctx.fillRect(0, 0, w, h);

  // The lane ("the paint").
  ctx.fillStyle = o.lane;
  const [laneX, laneTop] = px(COURT.laneLeft, COURT.freeThrowY);
  ctx.fillRect(laneX, laneTop, (COURT.laneRight - COURT.laneLeft) * sx, COURT.freeThrowY * sy);

  ctx.strokeStyle = o.line;
  ctx.lineWidth = Math.max(1.5, h * 0.006);
  ctx.lineCap = "round";

  // Boundary and half-court line.
  ctx.strokeRect(0, 0, w, h);

  // Lane outline.
  ctx.strokeRect(laneX, laneTop, (COURT.laneRight - COURT.laneLeft) * sx, COURT.freeThrowY * sy);

  // Free-throw circle: solid half toward half court, dashed half toward the basket.
  const [fx, fy] = px(25, COURT.freeThrowY);
  ctx.beginPath();
  ctx.ellipse(fx, fy, 6 * sx, 6 * sy, 0, Math.PI, 2 * Math.PI);
  ctx.stroke();
  ctx.setLineDash([6 * (h / 470), 6 * (h / 470)]);
  ctx.beginPath();
  ctx.ellipse(fx, fy, 6 * sx, 6 * sy, 0, 0, Math.PI);
  ctx.stroke();
  ctx.setLineDash([]);

  // Three-point line: straight legs from the baseline, then the arc.
  const r3 = COURT.threePointRadius;
  ctx.beginPath();
  ctx.moveTo(...px(25 - r3, 0));
  ctx.lineTo(...px(25 - r3, COURT.basket[1]));
  ctx.ellipse(bx, by, r3 * sx, r3 * sy, 0, Math.PI, 2 * Math.PI);
  ctx.lineTo(...px(25 + r3, 0));
  ctx.stroke();

  // Restricted area under the basket.
  ctx.beginPath();
  ctx.ellipse(bx, by, 4 * sx, 4 * sy, 0, Math.PI, 2 * Math.PI);
  ctx.stroke();

  // Centre circle, the half that sits in this half court.
  const [cx, cy] = px(25, COURT.length);
  ctx.beginPath();
  ctx.ellipse(cx, cy, 6 * sx, 6 * sy, 0, 0, Math.PI);
  ctx.stroke();

  // Backboard, neck and rim.
  ctx.lineWidth = Math.max(2.5, h * 0.01);
  ctx.beginPath();
  ctx.moveTo(...px(22, 4));
  ctx.lineTo(...px(28, 4));
  ctx.stroke();
  ctx.lineWidth = Math.max(1.5, h * 0.006);
  ctx.beginPath();
  ctx.moveTo(...px(25, 4));
  ctx.lineTo(...px(25, 4.5));
  ctx.stroke();
  ctx.strokeStyle = "#e8743b";
  ctx.beginPath();
  ctx.ellipse(bx, by, 0.75 * sx, 0.75 * sy, 0, 0, 2 * Math.PI);
  ctx.stroke();

  ctx.restore();
}

function drawPolyline(ctx, points, w, h) {
  ctx.beginPath();
  points.forEach(([x, y], k) => {
    const [cx, cy] = toCanvas(x, y, w, h);
    if (k === 0) ctx.moveTo(cx, cy);
    else ctx.lineTo(cx, cy);
  });
  ctx.stroke();
}

// Court + optional dotted path hints + pass line + players + ball.
// opts: showPaths (default true), plus anything drawCourt accepts.
export function drawFrame(ctx, w, h, play, tSec, opts = {}) {
  drawCourt(ctx, w, h, opts);
  const frame = interpolate(play, tSec);
  const radius = 0.035 * h; // diameter is 7% of canvas height
  const teamOf = {};
  for (const p of play.players) teamOf[p.id] = p;

  ctx.save();

  // Dotted hints for the paths of the beat we are moving into.
  const showPaths = opts.showPaths !== false;
  const nextBeat = play.beats[frame.beatIndex + 1];
  if (showPaths && nextBeat) {
    ctx.lineWidth = Math.max(1.5, h * 0.005);
    ctx.setLineDash([radius * 0.35, radius * 0.35]);
    for (const id of Object.keys(nextBeat.positions)) {
      const from = play.beats[frame.beatIndex];
      const pts = waypoints(from, nextBeat, id);
      if (distance(pts[0], pts[pts.length - 1]) < 0.5 && pts.length <= 2) continue;
      ctx.strokeStyle = playerColor(teamOf[id] || id);
      ctx.globalAlpha = 0.55;
      drawPolyline(ctx, pts, w, h);
    }
    ctx.globalAlpha = 1;
    ctx.setLineDash([]);
  }

  // Pass in flight: a dashed white line from passer to receiver.
  if (frame.ball.from) {
    const start = play.beats[frame.beatIndex].positions[frame.ball.from];
    const end = nextBeat.positions[frame.ball.to];
    ctx.strokeStyle = "rgba(255,255,255,0.7)";
    ctx.lineWidth = Math.max(1.5, h * 0.005);
    ctx.setLineDash([radius * 0.5, radius * 0.3]);
    drawPolyline(ctx, [start, end], w, h);
    ctx.setLineDash([]);
  }

  // Players: defence first so the offense draws on top when they touch.
  const ids = Object.keys(frame.positions).sort((a, b) => {
    const ta = (teamOf[a] && teamOf[a].team) || a[0];
    const tb = (teamOf[b] && teamOf[b].team) || b[0];
    return ta === tb ? 0 : ta.startsWith("d") || ta.startsWith("D") ? -1 : 1;
  });
  ctx.font = `bold ${Math.round(radius * 1.05)}px system-ui, -apple-system, Helvetica, Arial, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (const id of ids) {
    const [cx, cy] = toCanvas(...frame.positions[id], w, h);
    const player = teamOf[id] || { id, team: id.startsWith("D") ? "defense" : "offense", label: id };
    ctx.fillStyle = playerColor(player);
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
    ctx.fill();
    ctx.lineWidth = Math.max(1.5, radius * 0.08);
    ctx.strokeStyle = "rgba(0,0,0,0.45)";
    ctx.stroke();
    ctx.fillStyle = "#ffffff";
    ctx.fillText(player.label || id, cx, cy + radius * 0.04);
  }

  // Ball: small white circle; top-right of the holder, or along the pass.
  if (frame.ball.xy) {
    let [bx, by] = toCanvas(...frame.ball.xy, w, h);
    if (frame.ball.holder) {
      bx += radius * 0.8;
      by -= radius * 0.8;
    }
    ctx.fillStyle = BALL_COLOR;
    ctx.beginPath();
    ctx.arc(bx, by, radius * 0.38, 0, 2 * Math.PI);
    ctx.fill();
    ctx.lineWidth = Math.max(1, radius * 0.08);
    ctx.strokeStyle = "rgba(0,0,0,0.55)";
    ctx.stroke();
  }

  ctx.restore();
  return frame;
}
