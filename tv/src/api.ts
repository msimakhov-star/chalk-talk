// Thin wrappers over the backend HTTP API (CONTRACTS.md section 5).

import {BACKEND_URL, POLL_TIMEOUT_MS} from './config';
import type {TvCommand, TvState} from './types';

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = POLL_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(BACKEND_URL + path, {
      ...init,
      headers: {'Content-Type': 'application/json', ...(init.headers || {})},
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} for ${path}`);
    }
    return (await response.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export function pairTv(): Promise<{code: string; tv_id: string; expires_at: string}> {
  return request('/api/tv/pair', {method: 'POST', body: '{}'}, 8000);
}

// Long-polls: the server holds the request up to 10 s until `cursor` changes.
// With no cursor yet (first call) the server answers immediately.
export function fetchState(code: string, cursor: number | null): Promise<TvState> {
  const query = cursor === null ? 'wait=1' : `cursor=${cursor}&wait=1`;
  return request(`/api/tv/${code}/state?${query}`);
}

export function sendCommand(code: string, command: TvCommand): Promise<{ok: boolean; cursor: number}> {
  return request(`/api/tv/${code}/command`, {method: 'POST', body: JSON.stringify(command)}, 8000);
}
