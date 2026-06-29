// Typed fetch wrapper around the FastAPI backend (one function per endpoint).
import type {
  Catalog,
  GameState,
  MemoryEvent,
  NpcId,
  TalkResponse,
} from '../types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`${res.status} ${path}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => req<{ status: string; npcs: NpcId[] }>('/health'),

  getState: () => req<GameState>('/game/state'),

  start: (reseed = false) =>
    req<GameState>('/game/start', {
      method: 'POST',
      body: JSON.stringify({ reseed }),
    }),

  talk: (npcId: NpcId) =>
    req<TalkResponse>('/npc/talk', {
      method: 'POST',
      body: JSON.stringify({ npcId }),
    }),

  choose: (npcId: NpcId, choiceId: string) =>
    req<{ state: GameState; nextNodeId: string; newClues: string[] }>('/game/choose', {
      method: 'POST',
      body: JSON.stringify({ npcId, choiceId }),
    }),

  advanceDay: () => req<GameState>('/day/advance', { method: 'POST' }),

  catalog: () => req<Catalog>('/game/catalog'),

  solve: (theoryId: string) =>
    req<GameState>('/game/solve', {
      method: 'POST',
      body: JSON.stringify({ theoryId }),
    }),

  debugMemories: (npcId: NpcId) =>
    req<{ npcId: NpcId; memories: MemoryEvent[] }>(`/debug/memories/${npcId}`),
}
