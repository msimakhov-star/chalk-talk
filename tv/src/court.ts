// Pure geometry for the Court screen. No React Native imports so that
// tv/scripts/check_demo_play.mjs can exercise it with plain Node.

import type {Beat, Play, Point} from './types';

export const COURT_W = 50; // feet, x across the court
export const COURT_L = 47; // feet, y from the baseline (0) to half court (47)
export const BASKET: Point = [25, 5.25];
export const THREE_POINT_RADIUS = 19.75; // youth arc; nothing depends on it
export const BALL_OFFSET: Point = [1.2, 1.2]; // ball sits top-right of the holder

export function holderId(beat: Beat): string {
  return typeof beat.ball === 'string' ? beat.ball : beat.ball.to;
}

export function ballPosition(beat: Beat): Point {
  const [x, y] = beat.positions[holderId(beat)];
  return [x + BALL_OFFSET[0], y + BALL_OFFSET[1]];
}

// Waypoints a player travels when the TV moves from beat `from` to beat
// `to`. Forward steps follow beats[to].paths[id] when present (the contract
// says that polyline starts at the previous position and ends at the new
// one); backward steps replay beats[from].paths[id] reversed.
export function playerWaypoints(play: Play, id: string, from: number, to: number): Point[] {
  const start = play.beats[from].positions[id];
  const end = play.beats[to].positions[id];
  if (to === from + 1) {
    const path = play.beats[to].paths[id];
    if (path && path.length >= 2) {
      return path;
    }
  }
  if (to === from - 1) {
    const path = play.beats[from].paths[id];
    if (path && path.length >= 2) {
      return [...path].reverse();
    }
  }
  return [start, end];
}

// Where the ball goes between two beats. If the same player holds it at both
// beats the ball rides along that player's path; otherwise (a pass, or a
// change of holder) it flies straight.
export function ballWaypoints(play: Play, from: number, to: number): Point[] {
  const a = play.beats[from];
  const b = play.beats[to];
  const sameHolder = typeof a.ball === 'string' && typeof b.ball === 'string' && a.ball === b.ball;
  if (sameHolder) {
    return playerWaypoints(play, a.ball as string, from, to).map(([x, y]) => [
      x + BALL_OFFSET[0],
      y + BALL_OFFSET[1],
    ]);
  }
  return [ballPosition(a), ballPosition(b)];
}

export function segmentLength(a: Point, b: Point): number {
  return Math.hypot(b[0] - a[0], b[1] - a[1]);
}

export function polylineLength(points: Point[]): number {
  let total = 0;
  for (let i = 1; i < points.length; i++) {
    total += segmentLength(points[i - 1], points[i]);
  }
  return total;
}

// Evenly spaced points along a polyline, used to draw a dotted path.
export function dotsAlong(points: Point[], spacing: number): Point[] {
  const dots: Point[] = [];
  let carry = 0;
  for (let i = 1; i < points.length; i++) {
    const [ax, ay] = points[i - 1];
    const [bx, by] = points[i];
    const len = segmentLength(points[i - 1], points[i]);
    if (len === 0) {
      continue;
    }
    let d = carry;
    while (d <= len) {
      dots.push([ax + ((bx - ax) * d) / len, ay + ((by - ay) * d) / len]);
      d += spacing;
    }
    carry = d - len;
  }
  return dots;
}

// Scale from feet to on-screen units. y is flipped: the baseline (y=0) is at
// the BOTTOM of the court box, half court at the top.
export function toScreen(point: Point, width: number, height: number): Point {
  return [(point[0] / COURT_W) * width, height - (point[1] / COURT_L) * height];
}

// Seconds the TV takes to move from beat `from` to beat `to`.
export function stepDurationMs(play: Play, from: number, to: number): number {
  const seconds = Math.abs(play.beats[to].t - play.beats[from].t);
  return Math.min(4000, Math.max(600, seconds * 1000));
}
