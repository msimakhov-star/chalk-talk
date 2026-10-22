// Run: node --test renderer/test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { interpolate, beatStart, totalDuration, playerColor, COURT } from "./court.js";

const here = dirname(fileURLToPath(import.meta.url));
const play = JSON.parse(readFileSync(join(here, "fixtures", "pick_and_roll.json"), "utf8"));

function close(a, b, eps = 1e-9) {
  assert.ok(Math.abs(a[0] - b[0]) < eps && Math.abs(a[1] - b[1]) < eps, `${a} != ${b}`);
}

test("fixture follows the contract's validator limits", () => {
  const limit = 16; // u12 max speed ft/s
  assert.equal(play.beats[0].t, 0);
  play.beats.forEach((beat, i) => {
    const ids = Object.keys(beat.positions);
    assert.equal(ids.length, play.players.length, `beat ${i} lists every player`);
    assert.ok(beat.title.length < 24 && beat.read.length < 140, `beat ${i} text lengths`);
    for (const [x, y] of Object.values(beat.positions)) {
      assert.ok(x >= 0 && x <= COURT.width && y >= 0 && y <= COURT.length, `beat ${i} in bounds`);
    }
    for (let a = 0; a < ids.length; a++) {
      for (let b = a + 1; b < ids.length; b++) {
        const d = Math.hypot(...[0, 1].map((k) => beat.positions[ids[a]][k] - beat.positions[ids[b]][k]));
        assert.ok(d >= 3, `beat ${i}: ${ids[a]} and ${ids[b]} overlap (${d.toFixed(2)} ft)`);
      }
    }
    if (i > 0) {
      const prev = play.beats[i - 1];
      assert.ok(beat.t > prev.t, "t strictly increasing");
      for (const id of ids) {
        const d = Math.hypot(beat.positions[id][0] - prev.positions[id][0], beat.positions[id][1] - prev.positions[id][1]);
        assert.ok(d / (beat.t - prev.t) <= limit, `beat ${i}: ${id} too fast`);
      }
    }
  });
});

test("beatStart and totalDuration", () => {
  assert.equal(beatStart(play, 0), 0);
  assert.equal(beatStart(play, 3), 6);
  assert.equal(beatStart(play, 99), 8); // clamped
  assert.equal(totalDuration(play), 8);
});

test("interpolate at every beat boundary returns that beat exactly", () => {
  play.beats.forEach((beat, i) => {
    const frame = interpolate(play, beat.t);
    assert.equal(frame.beatIndex, i);
    assert.equal(frame.progress, 0);
    for (const id of Object.keys(beat.positions)) close(frame.positions[id], beat.positions[id]);
  });
  // The pass completes at the last beat: the receiver holds the ball.
  assert.deepEqual(interpolate(play, 8).ball.holder, "P5");
});

test("mid-beat straight line is the midpoint", () => {
  // Beat 0 -> 1: D5 moves (30,18) -> (29,33) with no path.
  const frame = interpolate(play, 1);
  assert.equal(frame.beatIndex, 0);
  assert.equal(frame.progress, 0.5);
  close(frame.positions.D5, [29.5, 25.5]);
  close(frame.positions.P1, [25, 40]); // did not move
  assert.equal(frame.ball.holder, "P1");
  close(frame.ball.xy, [25, 40]);
});

test("mid-beat along a polyline follows arc length, not the chord", () => {
  // Beat 2 -> 3: P5 path (28.5,37) -> (27,30) -> (27,18). Total length:
  const l1 = Math.hypot(1.5, 7); // 7.159
  const l2 = 12;
  const half = (l1 + l2) / 2; // 9.579, past the first segment
  const frame = interpolate(play, 5);
  const expectedY = 30 - (half - l1); // second segment runs straight down x=27
  close(frame.positions.P5, [27, expectedY], 1e-6);
  // A quarter of the way is still on the first segment.
  const quarter = interpolate(play, 4.5);
  const f = (l1 + l2) / 4 / l1;
  close(quarter.positions.P5, [28.5 - 1.5 * f, 37 - 7 * f], 1e-6);
});

test("pass in flight reports from, to, progress and ball position", () => {
  const frame = interpolate(play, 7);
  assert.equal(frame.beatIndex, 3);
  assert.equal(frame.ball.from, "P1");
  assert.equal(frame.ball.to, "P5");
  assert.equal(frame.ball.progress, 0.5);
  // From 1's previous position (36,28) to 5's catch spot (26,9).
  close(frame.ball.xy, [31, 18.5]);
  assert.equal(frame.ball.holder, undefined);
});

test("times outside the play clamp to the ends", () => {
  close(interpolate(play, -5).positions.P1, play.beats[0].positions.P1);
  const end = interpolate(play, 1000);
  assert.equal(end.beatIndex, 4);
  close(end.positions.P5, [26, 9]);
  assert.equal(interpolate(play, NaN).beatIndex, 0);
});

test("playerColor", () => {
  assert.equal(playerColor({ id: "P1", team: "offense" }), "#f28c28");
  assert.equal(playerColor({ id: "D1", team: "defense" }), "#3b82f6");
  assert.equal(playerColor("D3"), "#3b82f6");
  assert.equal(playerColor("ball"), "#ffffff");
});
