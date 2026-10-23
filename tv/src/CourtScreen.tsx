// Full-screen court: absolutely positioned Animated players, a ball, an
// optional dotted "paths" overlay for the next beat, and a caption bar.
import React, {useEffect, useMemo, useRef, useState} from 'react';
import {Animated, Easing, StyleSheet, Text, View} from 'react-native';
import {
  COURT_L,
  COURT_W,
  ballPosition,
  ballWaypoints,
  dotsAlong,
  playerWaypoints,
  polylineLength,
  stepDurationMs,
  toScreen,
} from './court';
import {CourtLines} from './CourtLines';
import {BALL_SIZE, PLAYER_SIZE, colors} from './theme';
import type {Play, PlayerDef, Point} from './types';

type Props = {
  play: Play;
  beatIndex: number;
  defence: string;
  showPaths: boolean;
  playing: boolean;
  badge: string | null;
  code: string | null;
  toast: string | null;
  onAnimating: (animating: boolean) => void;
};

const TOP_BAR = 56;
const CAPTION_BAR = 150; // title line + up to three lines of read

export function CourtScreen(props: Props) {
  const {play, beatIndex, showPaths, onAnimating} = props;
  const [box, setBox] = useState({width: 0, height: 0});
  const anims = useRef<Record<string, Animated.ValueXY>>({}).current;
  const ball = useRef(new Animated.ValueXY()).current;
  const previous = useRef<{playId: string; beat: number} | null>(null);

  for (const player of play.players) {
    if (!anims[player.id]) {
      anims[player.id] = new Animated.ValueXY();
    }
  }

  useEffect(() => {
    const before = previous.current;
    previous.current = {playId: play.id, beat: beatIndex};
    const adjacent = before && before.playId === play.id && Math.abs(before.beat - beatIndex) === 1;
    if (!adjacent) {
      const beat = play.beats[beatIndex];
      for (const player of play.players) {
        const [x, y] = beat.positions[player.id];
        anims[player.id].setValue({x, y});
      }
      const [bx, by] = ballPosition(beat);
      ball.setValue({x: bx, y: by});
      return;
    }
    const from = before!.beat;
    const duration = stepDurationMs(play, from, beatIndex);
    const moves = play.players.map(player =>
      alongPolyline(anims[player.id], playerWaypoints(play, player.id, from, beatIndex), duration),
    );
    moves.push(alongPolyline(ball, ballWaypoints(play, from, beatIndex), duration));
    const running = Animated.parallel(moves);
    onAnimating(true);
    running.start(() => onAnimating(false));
    return () => running.stop();
  }, [play, beatIndex, anims, ball, onAnimating]);

  // Court box keeps the 50:47 aspect and fills the available height.
  const court = useMemo(() => {
    const height = Math.max(0, box.height - 16);
    return {width: (height * COURT_W) / COURT_L, height};
  }, [box]);

  const beat = play.beats[beatIndex];
  const last = play.beats.length - 1;

  return (
    <View style={styles.screen}>
      <View style={styles.topBar}>
        <Text style={styles.playName} numberOfLines={1}>
          {play.name}
        </Text>
        <View style={styles.badges}>
          {props.badge ? <Text style={[styles.badge, styles.demoBadge]}>{props.badge}</Text> : null}
          <Text style={[styles.badge, styles.defenceBadge]}>DEFENCE: {props.defence.toUpperCase()}</Text>
        </View>
      </View>

      <View style={styles.middle} onLayout={e => setBox(e.nativeEvent.layout)}>
        <View style={styles.side}>
          {play.beats.map(b => (
            <Text key={b.index} style={[styles.beatRow, b.index === beatIndex && styles.beatRowCurrent]}>
              {b.index + 1}. {b.title}
            </Text>
          ))}
        </View>

        <View style={[styles.courtBox, court]}>
          {court.height > 0 ? (
            <>
              <CourtLines width={court.width} height={court.height} />
              {showPaths && beatIndex < last ? (
                <PathsOverlay play={play} beatIndex={beatIndex} width={court.width} height={court.height} />
              ) : null}
              {play.players.map(player => (
                <PlayerToken key={player.id} player={player} anim={anims[player.id]} court={court} />
              ))}
              <Animated.View
                style={[styles.ball, {transform: feetToTransform(ball, court)}]}
              />
            </>
          ) : null}
        </View>

        <View style={styles.side}>
          <Legend color={colors.offense} text="Offense" />
          <Legend color={colors.defense} text="Defence" />
          <Legend color={colors.ball} text="Ball" />
          <Text style={styles.hint}>{'◀ ▶'}  beats</Text>
          <Text style={styles.hint}>OK  {props.playing ? 'pause' : 'play'}</Text>
          <Text style={styles.hint}>{'▲'}  paths {showPaths ? 'on' : 'off'}</Text>
          <Text style={styles.hint}>{'▼'}  what if they...</Text>
          {props.code ? <Text style={styles.code}>TV code {props.code}</Text> : null}
        </View>
      </View>

      <View style={styles.captionBar}>
        <View style={styles.captionText}>
          <Text style={styles.captionTitle}>{beat.title.toUpperCase()}</Text>
          <Text style={styles.captionRead} numberOfLines={3}>
            {props.toast ?? beat.read}
          </Text>
        </View>
        <Text style={styles.beatCounter}>
          {beatIndex + 1} / {play.beats.length}
        </Text>
      </View>
    </View>
  );
}

// Animated.timing segments along the waypoints, time split by segment length.
function alongPolyline(value: Animated.ValueXY, points: Point[], totalMs: number) {
  const total = polylineLength(points);
  const segments = [];
  for (let i = 1; i < points.length; i++) {
    const length = Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
    segments.push(
      Animated.timing(value, {
        toValue: {x: points[i][0], y: points[i][1]},
        duration: total === 0 ? totalMs : (totalMs * length) / total,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    );
  }
  return Animated.sequence(segments);
}

// Maps an Animated position in feet to a translate transform in screen units.
function feetToTransform(value: Animated.ValueXY, court: {width: number; height: number}) {
  return [
    {translateX: value.x.interpolate({inputRange: [0, COURT_W], outputRange: [0, court.width]})},
    {translateY: value.y.interpolate({inputRange: [0, COURT_L], outputRange: [court.height, 0]})},
  ];
}

function PlayerToken({
  player,
  anim,
  court,
}: {
  player: PlayerDef;
  anim: Animated.ValueXY;
  court: {width: number; height: number};
}) {
  const offense = player.team === 'offense';
  return (
    <Animated.View
      style={[
        styles.player,
        {backgroundColor: offense ? colors.offense : colors.defense},
        {transform: feetToTransform(anim, court)},
      ]}>
      <Text style={[styles.playerLabel, !offense && styles.defenseLabel]}>{player.label}</Text>
    </Animated.View>
  );
}

// Dotted lines showing where everyone goes at the next beat, plus the pass.
function PathsOverlay({play, beatIndex, width, height}: {play: Play; beatIndex: number; width: number; height: number}) {
  const next = beatIndex + 1;
  const dots: Array<{key: string; point: Point; color: string; end: boolean}> = [];
  for (const player of play.players) {
    const points = playerWaypoints(play, player.id, beatIndex, next);
    if (polylineLength(points) < 1) {
      continue;
    }
    const color = player.team === 'offense' ? colors.offense : colors.defense;
    dotsAlong(points, 1.5).forEach((point, i) => dots.push({key: `${player.id}-${i}`, point, color, end: false}));
    dots.push({key: `${player.id}-end`, point: points[points.length - 1], color, end: true});
  }
  const nextBeat = play.beats[next];
  if (typeof nextBeat.ball !== 'string') {
    dotsAlong(ballWaypoints(play, beatIndex, next), 1.5).forEach((point, i) =>
      dots.push({key: `ball-${i}`, point, color: colors.ball, end: false}),
    );
  }
  return (
    <>
      {dots.map(d => {
        const [x, y] = toScreen(d.point, width, height);
        const size = d.end ? 18 : 7;
        return (
          <View
            key={d.key}
            style={{
              position: 'absolute',
              left: x - size / 2,
              top: y - size / 2,
              width: size,
              height: size,
              borderRadius: size / 2,
              backgroundColor: d.end ? 'transparent' : d.color,
              borderWidth: d.end ? 3 : 0,
              borderColor: d.color,
            }}
          />
        );
      })}
    </>
  );
}

function Legend({color, text}: {color: string; text: string}) {
  return (
    <View style={styles.legendRow}>
      <View style={[styles.legendDot, {backgroundColor: color}]} />
      <Text style={styles.legendText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1, backgroundColor: colors.background},
  topBar: {
    height: TOP_BAR,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 28,
  },
  playName: {color: colors.text, fontSize: 36, fontWeight: '700', flexShrink: 1},
  badges: {flexDirection: 'row', gap: 12},
  badge: {
    fontSize: 24,
    fontWeight: '700',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
    overflow: 'hidden',
  },
  defenceBadge: {backgroundColor: colors.defense, color: colors.text},
  demoBadge: {backgroundColor: colors.warning, color: colors.background},
  middle: {flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center'},
  side: {flex: 1, paddingHorizontal: 28, justifyContent: 'center'},
  courtBox: {backgroundColor: colors.floor, borderWidth: 4, borderColor: colors.floorEdge},
  beatRow: {color: colors.muted, fontSize: 26, paddingVertical: 4},
  beatRowCurrent: {color: colors.offense, fontWeight: '700'},
  legendRow: {flexDirection: 'row', alignItems: 'center', marginBottom: 6},
  legendDot: {width: 24, height: 24, borderRadius: 12, marginRight: 12},
  legendText: {color: colors.text, fontSize: 24},
  hint: {color: colors.muted, fontSize: 24, marginTop: 6},
  code: {color: colors.text, fontSize: 24, marginTop: 18, fontWeight: '700'},
  player: {
    position: 'absolute',
    left: -PLAYER_SIZE / 2,
    top: -PLAYER_SIZE / 2,
    width: PLAYER_SIZE,
    height: PLAYER_SIZE,
    borderRadius: PLAYER_SIZE / 2,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: colors.background,
  },
  playerLabel: {color: colors.background, fontSize: 24, fontWeight: '800'},
  defenseLabel: {color: colors.text},
  ball: {
    position: 'absolute',
    left: -BALL_SIZE / 2,
    top: -BALL_SIZE / 2,
    width: BALL_SIZE,
    height: BALL_SIZE,
    borderRadius: BALL_SIZE / 2,
    backgroundColor: colors.ball,
    borderWidth: 2,
    borderColor: colors.background,
  },
  captionBar: {
    height: CAPTION_BAR,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.panel,
    paddingHorizontal: 28,
  },
  captionText: {flex: 1},
  captionTitle: {color: colors.offense, fontSize: 24, fontWeight: '800', letterSpacing: 2},
  // 32 dp is 64 physical px on a 1080p TV (xhdpi), readable from the sofa.
  captionRead: {color: colors.text, fontSize: 32, lineHeight: 38},
  beatCounter: {color: colors.muted, fontSize: 30, fontWeight: '700', marginLeft: 24},
});
