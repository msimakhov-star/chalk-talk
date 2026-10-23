// Mirrors CONTRACTS.md section 2 (Play JSON) and section 5 (TV state).

export type Point = [number, number];

export type PlayerDef = {
  id: string;
  team: 'offense' | 'defense';
  label: string;
};

export type Pass = {from: string; to: string};

export type Beat = {
  index: number;
  t: number;
  title: string;
  read: string;
  positions: Record<string, Point>;
  ball: string | Pass;
  paths: Record<string, Point[]>;
  pass?: Pass | null;
};

export type Play = {
  id: string;
  sport: string;
  template: string;
  name: string;
  description: string;
  params: Record<string, unknown>;
  defence: string;
  court: {width: number; length: number; units: string};
  players: PlayerDef[];
  beats: Beat[];
  validity: {ok: boolean; issues: unknown[]};
  counters: string[];
  parse: {method: string; confidence: number; input: string};
  created_at: string;
};

export type TvState = {
  cursor: number;
  play: Play | null;
  beat_index: number;
  defence: string;
  playing?: boolean;
  updated_at: string;
};

export type TvCommand =
  | {type: 'show_play'; play_id: string}
  | {type: 'set_beat'; index: number}
  | {type: 'counter'; defence: string}
  | {type: 'play'}
  | {type: 'pause'};
