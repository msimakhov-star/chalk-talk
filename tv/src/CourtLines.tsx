// Court markings drawn with plain Views (no SVG dependency). The parent box
// clips overflow, so circles that cross the baseline or half-court line
// become arcs.
import React from 'react';
import {StyleSheet, View} from 'react-native';
import {BASKET, COURT_L, COURT_W, THREE_POINT_RADIUS} from './court';
import {colors} from './theme';

type Props = {width: number; height: number};

export function CourtLines({width, height}: Props) {
  const sx = width / COURT_W;
  const sy = height / COURT_L;
  const line = 3;
  // Rectangle from court feet (x, yBottom) with the given feet size.
  const rect = (x: number, y: number, w: number, h: number) => ({
    left: x * sx,
    top: height - (y + h) * sy,
    width: w * sx,
    height: h * sy,
  });
  const circle = (cx: number, cy: number, r: number) => ({
    ...rect(cx - r, cy - r, 2 * r, 2 * r),
    borderRadius: r * Math.max(sx, sy),
  });
  return (
    <View style={[styles.floor, {width, height}]}>
      <View style={[styles.stroke, circle(BASKET[0], BASKET[1], THREE_POINT_RADIUS)]} />
      <View style={[styles.stroke, rect(17, 0, 16, 19)]} />
      <View style={[styles.stroke, circle(25, 19, 6)]} />
      <View style={[styles.stroke, circle(25, COURT_L, 6)]} />
      <View style={[styles.fill, rect(22, 4, 6, 0.4)]} />
      <View style={[styles.stroke, circle(BASKET[0], BASKET[1], 0.75), {borderColor: colors.offense}]} />
      <View style={[styles.fill, {left: 0, top: 0, width, height: line}]} />
      <View style={[styles.fill, {left: 0, top: height - line, width, height: line}]} />
      <View style={[styles.fill, {left: 0, top: 0, width: line, height}]} />
      <View style={[styles.fill, {left: width - line, top: 0, width: line, height}]} />
    </View>
  );
}

const styles = StyleSheet.create({
  floor: {
    position: 'absolute',
    left: 0,
    top: 0,
    backgroundColor: colors.floor,
    overflow: 'hidden',
  },
  stroke: {
    position: 'absolute',
    borderWidth: 3,
    borderColor: colors.lines,
  },
  fill: {
    position: 'absolute',
    backgroundColor: colors.lines,
  },
});
