// Typed fetch wrapper around the DEAD AIR FastAPI backend (one function per endpoint).
import type {
  AskResponse,
  Catalog,
  ExamineResponse,
  GameState,
  MemoryEvent,
  NpcId,
  OverhearResponse,
  RoomId,
  SayResponse,
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
  health: () => req<{ status: string; crew: NpcId[] }>('/health'),

  getState: () => req<GameState>('/game/state'),

  start: (seed?: number, reseed = true) =>
    req<GameState>('/game/start', {
      method: 'POST',
      body: JSON.stringify({ seed: seed ?? null, reseed }),
    }),

  catalog: () => req<Catalog>('/game/catalog'),

  talk: (npcId: NpcId) =>
    req<TalkResponse>('/npc/talk', {
      method: 'POST',
      body: JSON.stringify({ npcId }),
    }),

  ask: (npcId: NpcId, verb: string, arg: string | null) =>
    req<AskResponse>('/npc/ask', {
      method: 'POST',
      body: JSON.stringify({ npcId, verb, arg }),
    }),

  say: (npcId: NpcId, text: string) =>
    req<SayResponse>('/npc/say', {
      method: 'POST',
      body: JSON.stringify({ npcId, text }),
    }),

  advanceShift: (playerRoom: RoomId | null) =>
    req<{ state: GameState; firedTransfers: string[] }>('/shift/advance', {
      method: 'POST',
      body: JSON.stringify({ playerRoom }),
    }),

  overhear: (encounterId: string, playerRoom: RoomId) =>
    req<OverhearResponse>('/encounter/overhear', {
      method: 'POST',
      body: JSON.stringify({ encounterId, playerRoom }),
    }),

  // Fire-and-forget: warm the two speakers' memory caches as the player nears an
  // encounter so leaning in is instant. Errors are ignored (best-effort).
  prewarmEncounter: (encounterId: string) =>
    req<{ ok: boolean }>('/encounter/prewarm', {
      method: 'POST',
      body: JSON.stringify({ encounterId }),
    }).catch(() => ({ ok: false })),

  examine: (spotId: string) =>
    req<ExamineResponse>('/world/examine', {
      method: 'POST',
      body: JSON.stringify({ spotId }),
    }),

  accuse: (npcId: NpcId) =>
    req<GameState>('/game/accuse', {
      method: 'POST',
      body: JSON.stringify({ npcId }),
    }),

  debugMemories: (npcId: NpcId) =>
    req<{ npcId: NpcId; memories: MemoryEvent[] }>(`/debug/memories/${npcId}`),

  // Which cognee capabilities are live this run (shown to judges in the debugger).
  debugDatasets: () =>
    req<{
      runId: string
      seeding: string
      datasets: string[]
      features: {
        granular: boolean
        temporal: boolean
        ontology: boolean
        memify: boolean
        feedbackInfluence: number
        feedbackLearn: boolean
        searchTypes: Record<string, string>
      }
    }>('/debug/datasets'),

  // cognee's own knowledge-graph render of one crewmate's memory dataset.
  graphUrl: (npcId: NpcId) => `${BASE_URL}/debug/graph/${npcId}`,

  // cognee's memory-provenance graph (where memories came from).
  provenanceUrl: () => `${BASE_URL}/debug/provenance`,

  // Investigator console: ask the station's memory graph in natural language.
  askGraph: (query: string) =>
    req<{ query: string; answer: string }>('/debug/ask', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),
}
