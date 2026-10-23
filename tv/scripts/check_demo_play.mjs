// Self-check for the TV component. Run: node tv/scripts/check_demo_play.mjs
// Checks DEMO_PLAY against the rules in CONTRACTS.md sections 2 and 3, and
// the geometry helpers the Court screen animates with. Exit code 1 on failure.
import assert from 'node:assert/strict';
import {DEMO_PLAY} from '../src/demoPlay.ts';
import {
  ballWaypoints,
  dotsAlong,
  playerWaypoints,
  polylineLength,
  stepDurationMs,
  toScreen,
} from '../src/court.ts';

const MAX_SPEED = {u8: 12, u10: 14, u12: 16, u14: 18, u16: 20};
const play = DEMO_PLAY;
const ids = play.players.map(p => p.id);
const maxSpeed = MAX_SPEED[play.params.age_group];

assert.match(play.id, /^ply_[0-9a-f]{6}$/, 'id format');
assert.equal(play.template, 'pick_and_roll');
assert.equal(play.beats.length, 5, 'five beats');
assert.equal(play.beats[0].t, 0, 'first beat at t=0');
assert.equal(play.players.length, 10, '5v5');

for (let i = 0; i < play.beats.length; i++) {
  const beat = play.beats[i];
  const where = `beat ${i}`;
  assert.equal(beat.index, i, `${where} index`);
  assert.ok(beat.title.length < 24, `${where} title under 24 chars`);
  assert.ok(beat.read.length < 140, `${where} read under 140 chars`);
  if (i > 0) {
    assert.ok(beat.t > play.beats[i - 1].t, `${where} t increasing`);
  }
  for (const id of ids) {
    const pos = beat.positions[id];
    assert.ok(pos, `${where} missing_player ${id}`);
    assert.ok(pos[0] >= 0 && pos[0] <= 50 && pos[1] >= 0 && pos[1] <= 47, `${where} out_of_bounds ${id}`);
  }
  for (let a = 0; a < ids.length; a++) {
    for (let b = a + 1; b < ids.length; b++) {
      const [ax, ay] = beat.positions[ids[a]];
      const [bx, by] = beat.positions[ids[b]];
      const dist = Math.hypot(ax - bx, ay - by);
      assert.ok(dist >= 3, `${where} overlap ${ids[a]} ${ids[b]} (${dist.toFixed(2)} ft)`);
    }
  }
  if (typeof beat.ball === 'string') {
    assert.ok(ids.includes(beat.ball), `${where} ball_orphan ${beat.ball}`);
  } else {
    assert.ok(ids.includes(beat.ball.from) && ids.includes(beat.ball.to), `${where} ball_orphan pass`);
    assert.deepEqual(beat.pass, beat.ball, `${where} pass mirrors ball`);
  }
  if (i > 0) {
    const dt = beat.t - play.beats[i - 1].t;
    for (const id of ids) {
      const dist = polylineLength(playerWaypoints(play, id, i - 1, i));
      assert.ok(dist / dt < maxSpeed, `${where} too_fast ${id} (${(dist / dt).toFixed(1)} ft/s)`);
    }
    for (const [id, path] of Object.entries(beat.paths)) {
      assert.deepEqual(path[0], play.beats[i - 1].positions[id], `${where} path ${id} starts at previous position`);
      assert.deepEqual(path[path.length - 1], beat.positions[id], `${where} path ${id} ends at new position`);
    }
  }
}

// Geometry helpers.
assert.deepEqual(playerWaypoints(play, 'P5', 0, 1), play.beats[1].paths.P5, 'forward follows the path');
assert.deepEqual(playerWaypoints(play, 'P5', 1, 0), [...play.beats[1].paths.P5].reverse(), 'backward reverses it');
assert.deepEqual(playerWaypoints(play, 'P2', 0, 1), [[25, 40], [22, 41]], 'no path means a straight line');
assert.deepEqual(playerWaypoints(play, 'P1', 0, 4), [[40, 30], [30, 30]], 'jumps are straight');
const pass = ballWaypoints(play, 3, 4);
assert.deepEqual(pass, [[31.2, 31.2], [28.2, 10.2]], 'pass flies from passer to receiver');
assert.equal(ballWaypoints(play, 1, 2).length, 3, 'ball rides the holder path');
assert.deepEqual(toScreen([0, 0], 500, 470), [0, 470], 'baseline is at the bottom');
assert.deepEqual(toScreen([50, 47], 500, 470), [500, 0], 'half court is at the top');
assert.equal(stepDurationMs(play, 0, 1), 2000);
assert.equal(stepDurationMs(play, 1, 0), 2000);
const dots = dotsAlong([[0, 0], [10, 0]], 2.5);
assert.equal(dots.length, 5, 'dots every 2.5 ft on a 10 ft line');
assert.deepEqual(dots[4], [10, 0]);

console.log(`ok: DEMO_PLAY "${play.name}" is valid (${play.beats.length} beats, max speed ${maxSpeed} ft/s) and geometry helpers pass`);
