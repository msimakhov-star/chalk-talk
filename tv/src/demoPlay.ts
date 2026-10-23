// A complete, valid Play (CONTRACTS.md section 2) shown when the backend is
// unreachable or has not sent a play yet. Pick and roll, right wing, 5 beats.
// Only a type import, so tv/scripts/check_demo_play.mjs can load this file
// with plain Node (type stripping) and check it against the contract's rules.
import type {Play} from './types';

export const DEMO_PLAY: Play = {
  id: 'ply_0de3a1',
  sport: 'basketball',
  template: 'pick_and_roll',
  name: 'Pick and roll, right wing',
  description: '1 uses 5\'s screen on the right wing; 5 rolls to the rim.',
  params: {
    side: 'right',
    ball_handler: 'P1',
    screener: 'P5',
    players_per_side: 5,
    age_group: 'u12',
  },
  defence: 'man',
  court: {width: 50, length: 47, units: 'ft'},
  players: [
    {id: 'P1', team: 'offense', label: '1'},
    {id: 'P2', team: 'offense', label: '2'},
    {id: 'P3', team: 'offense', label: '3'},
    {id: 'P4', team: 'offense', label: '4'},
    {id: 'P5', team: 'offense', label: '5'},
    {id: 'D1', team: 'defense', label: 'x1'},
    {id: 'D2', team: 'defense', label: 'x2'},
    {id: 'D3', team: 'defense', label: 'x3'},
    {id: 'D4', team: 'defense', label: 'x4'},
    {id: 'D5', team: 'defense', label: 'x5'},
  ],
  beats: [
    {
      index: 0,
      t: 0.0,
      title: 'Setup',
      read: '1 has the ball on the right wing. 5 jogs up from the block to set a screen on x1.',
      positions: {
        P1: [40, 30], P2: [25, 40], P3: [10, 30], P4: [5, 7], P5: [33, 12],
        D1: [37, 27], D2: [25, 35], D3: [13, 27], D4: [9, 9], D5: [30, 10],
      },
      ball: 'P1',
      paths: {},
      pass: null,
    },
    {
      index: 1,
      t: 2.0,
      title: 'Screen',
      read: '5 plants both feet on x1\'s top shoulder. 1 waits for the screen to be set before moving.',
      positions: {
        P1: [40, 30], P2: [22, 41], P3: [8, 30], P4: [5, 7], P5: [37, 31],
        D1: [38, 27], D2: [23, 36], D3: [11, 27], D4: [9, 9], D5: [35, 28],
      },
      ball: 'P1',
      paths: {P5: [[33, 12], [36, 22], [37, 31]]},
      pass: null,
    },
    {
      index: 2,
      t: 4.0,
      title: 'Use the screen',
      read: '1 dribbles shoulder to shoulder off the screen toward the middle. x1 is stuck behind 5.',
      positions: {
        P1: [33, 35], P2: [20, 41], P3: [8, 30], P4: [5, 7], P5: [37, 31],
        D1: [39, 28], D2: [21, 37], D3: [11, 27], D4: [9, 9], D5: [34, 32],
      },
      ball: 'P1',
      paths: {P1: [[40, 30], [38, 33], [33, 35]]},
      pass: null,
    },
    {
      index: 3,
      t: 6.0,
      title: 'Roll',
      read: '5 turns and rolls to the rim. 1 keeps the dribble and watches x5: who is x5 guarding?',
      positions: {
        P1: [30, 30], P2: [18, 41], P3: [8, 30], P4: [5, 7], P5: [31, 18],
        D1: [35, 32], D2: [20, 37], D3: [12, 26], D4: [9, 9], D5: [33, 29],
      },
      ball: 'P1',
      paths: {P5: [[37, 31], [35, 25], [31, 18]]},
      pass: null,
    },
    {
      index: 4,
      t: 8.0,
      title: 'Pocket pass',
      read: 'x5 stayed with 1, so 5 is open. 1 slips a bounce pass to 5 for the layup.',
      positions: {
        P1: [30, 30], P2: [18, 41], P3: [8, 30], P4: [5, 7], P5: [27, 9],
        D1: [33, 31], D2: [20, 37], D3: [12, 26], D4: [12, 10], D5: [30, 14],
      },
      ball: {from: 'P1', to: 'P5'},
      paths: {P5: [[31, 18], [29, 13], [27, 9]]},
      pass: {from: 'P1', to: 'P5'},
    },
  ],
  validity: {ok: true, issues: []},
  counters: ['switch', 'hedge', 'drop', 'zone'],
  parse: {method: 'rules', confidence: 1.0, input: 'pick and roll on the right wing'},
  created_at: '2026-10-22T12:00:00Z',
};
