// Chalk Talk TV. Pairs with the backend, long-polls the TV state, and steps
// through the play with the D-pad. Falls back to DEMO_PLAY when offline.
import React, {useCallback, useEffect, useRef, useState} from 'react';
import {BackHandler, StatusBar, useTVEventHandler, View} from 'react-native';
import {fetchState, pairTv, sendCommand} from './api';
import {READ_PAUSE_MS, RETRY_MS} from './config';
import {CourtScreen} from './CourtScreen';
import {DEMO_PLAY} from './demoPlay';
import {PairScreen} from './PairScreen';
import type {Play, TvState} from './types';

const sleep = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms));

export default function App() {
  const [screen, setScreen] = useState<'pair' | 'court'>('pair');
  const [code, setCode] = useState<string | null>(null);
  const [online, setOnline] = useState(false);
  const [backendPlay, setBackendPlay] = useState<Play | null>(null);
  const [defence, setDefence] = useState('man');
  const [beatIndex, setBeatIndex] = useState(0);
  const [showPaths, setShowPaths] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [animating, setAnimating] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const play = backendPlay ?? DEMO_PLAY;
  const lastBeat = play.beats.length - 1;

  // Pair once, then long-poll the state forever. 404 means the backend forgot
  // the code (restart), so pair again. Any other error flips to offline and retries.
  useEffect(() => {
    let stopped = false;
    const applyState = (state: TvState) => {
      if (!state.play) {
        return;
      }
      setBackendPlay(state.play);
      setDefence(state.defence || state.play.defence);
      setBeatIndex(Math.min(Math.max(state.beat_index || 0, 0), state.play.beats.length - 1));
      setPlaying(Boolean(state.playing));
      setScreen('court');
    };
    (async () => {
      let paired: string | null = null;
      let cursor: number | null = null;
      while (!stopped) {
        if (!paired) {
          try {
            paired = (await pairTv()).code;
            cursor = null;
            setCode(paired);
            setOnline(true);
          } catch {
            setOnline(false);
            await sleep(RETRY_MS * 3);
            continue;
          }
        }
        try {
          const state = await fetchState(paired, cursor);
          if (stopped) {
            return;
          }
          setOnline(true);
          if (state.cursor !== cursor) {
            cursor = state.cursor;
            applyState(state);
          }
        } catch (error) {
          if (String(error).includes('HTTP 404')) {
            paired = null;
            setCode(null);
          } else {
            setOnline(false);
            await sleep(RETRY_MS);
          }
        }
      }
    })();
    return () => {
      stopped = true;
    };
  }, []);

  // Auto-play: after each beat settles, hold the caption for READ_PAUSE_MS, then advance.
  useEffect(() => {
    if (!playing || animating) {
      return;
    }
    if (beatIndex >= lastBeat) {
      setPlaying(false);
      return;
    }
    const timer = setTimeout(() => setBeatIndex(i => Math.min(i + 1, lastBeat)), READ_PAUSE_MS);
    return () => clearTimeout(timer);
  }, [playing, animating, beatIndex, lastBeat]);

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(timer);
  }, [toast]);

  const cycleCounter = useCallback(async () => {
    if (!code || !online || !backendPlay) {
      setToast('Counters need the backend: send a play from the phone first');
      return;
    }
    const options = ['man', ...backendPlay.counters];
    const next = options[(options.indexOf(defence) + 1) % options.length];
    setToast(next === 'man' ? 'Back to man-to-man...' : `What if they ${next}? Re-planning the defence...`);
    try {
      await sendCommand(code, {type: 'counter', defence: next});
    } catch (error) {
      setToast(`Backend refused the counter: ${String(error)}`);
    }
  }, [code, online, backendPlay, defence]);

  // Keep one stable listener; read the latest state through a ref.
  const onKey = useRef<(eventType: string) => void>(() => {});
  onKey.current = (eventType: string) => {
    if (screen === 'pair') {
      if (eventType === 'select' || eventType === 'right' || eventType === 'playPause') {
        setBeatIndex(0);
        setPlaying(false);
        setScreen('court');
      }
      return;
    }
    switch (eventType) {
      case 'right':
        setPlaying(false);
        setBeatIndex(i => Math.min(i + 1, lastBeat));
        break;
      case 'left':
        setPlaying(false);
        setBeatIndex(i => Math.max(i - 1, 0));
        break;
      case 'select':
      case 'playPause':
        if (playing) {
          setPlaying(false);
        } else {
          if (beatIndex >= lastBeat) {
            setBeatIndex(0); // play pressed on the last beat starts over
          }
          setPlaying(true);
        }
        break;
      case 'up':
        setShowPaths(s => !s);
        break;
      case 'down':
        cycleCounter();
        break;
    }
  };
  // RNTV on Android sends key up only (eventKeyAction 1); key down (0) comes too only
  // when ReactFeatureFlags.enableKeyDownEvents is on. Act on key up so a press steps once.
  // The RNTV type declares eventKeyAction as a string, the native side sends an int.
  const onTvEvent = useCallback((event: {eventType: string; eventKeyAction?: string | number}) => {
    if (event.eventKeyAction !== undefined && Number(event.eventKeyAction) === 0) {
      return;
    }
    onKey.current(event.eventType);
  }, []);
  useTVEventHandler(onTvEvent);

  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (screen === 'court') {
        setPlaying(false);
        setScreen('pair');
        return true;
      }
      return false;
    });
    return () => sub.remove();
  }, [screen]);

  const badge = !online ? 'OFFLINE DEMO' : backendPlay ? null : 'DEMO PLAY';

  return (
    <>
      <StatusBar hidden />
      {/* Android only routes D-pad keys to the React root (and so to useTVEventHandler)
          when some view inside it holds focus; the screens have none, so keep this one focused. */}
      <View focusable hasTVPreferredFocus collapsable={false} style={{position: 'absolute', width: 1, height: 1}} />
      {screen === 'pair' ? (
        <PairScreen code={code} online={online} />
      ) : (
        <CourtScreen
          play={play}
          beatIndex={beatIndex}
          defence={backendPlay ? defence : play.defence}
          showPaths={showPaths}
          playing={playing}
          badge={badge}
          code={code}
          toast={toast}
          onAnimating={setAnimating}
        />
      )}
    </>
  );
}
