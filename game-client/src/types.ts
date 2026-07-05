// Shared types mirroring the DEAD AIR FastAPI backend JSON.

export type NpcId = 'oda' | 'vega' | 'lin' | 'rio' | 'nova'
export type RoomId = 'cafeteria' | 'medbay' | 'engine' | 'storage' | 'comms' | 'quarters'

export interface Relationship {
  trust: number
  suspicion: number
}

// One button in the question menu (built server-side from the case).
export interface Verb {
  id: string
  verb: 'ask_whereabouts' | 'ask_sabotage' | 'ask_about' | 'present_clue' | 'confront'
  arg: string | null
  label: string
}

export interface Move {
  npcId: NpcId
  atSec: number
  toRoom: RoomId
}

export interface EncounterPlan {
  id: string
  room: RoomId
  npcs: [NpcId, NpcId]
  startSec: number
  endSec: number
}

export interface ShiftPlan {
  shift: number
  shiftName: string
  shiftSeconds: number
  positions: Record<NpcId, RoomId>
  moves: Move[]
  encounters: EncounterPlan[]
}

export interface ClueCatalogEntry {
  id: string
  title: string
  icon: string
  hint: string
  found?: string // present once collected
}

export interface GameState {
  runId: string
  seeding: string
  shift: number
  maxShifts: number
  shiftName: string
  shiftPlan: ShiftPlan
  playerRoom: RoomId
  sabotage: { name: string; room: RoomId; time: string }
  relationships: Record<NpcId, Relationship>
  flustered: Record<NpcId, number>
  statements: Partial<Record<NpcId, string>>
  notebook: string[]
  cluesFound: string[]
  clueCatalog: ClueCatalogEntry[]
  examined: string[]
  overheard: string[]
  ledger: MemoryEvent[]
  solved: boolean | null
  result: Result | null
}

export interface Result {
  accused: NpcId
  accusedName: string
  saboteur: NpcId
  saboteurName: string
  wasSaboteur: boolean
  solvedCorrectly: boolean
  score: number
  stars: number
  maxStars: number
  cluesFound: number
  totalClues: number
  flustered: number
  rank: { title: string; icon: string; blurb: string }
  narrative: { id: string; headline: string; body: string }
}

export type LineSource = 'cognee' | 'bedrock' | 'fallback' | 'script'

export interface TalkResponse {
  npcId: NpcId
  name: string
  npcLine: string
  emotion: string
  source: LineSource
  verbs: Verb[]
  relationship: Relationship
  shift: number
}

export interface AskResponse {
  npcId: NpcId
  name: string
  npcLine: string
  emotion: string
  source: LineSource
  verbs: Verb[]
  relationship: Relationship
  newClues: string[]
  newStatements: NpcId[]
  state: GameState
}

export interface SayResponse {
  npcId: NpcId
  name: string
  npcLine: string
  emotion: string
  source: LineSource
  relationship: Relationship
  state: GameState
}

export interface OverhearResponse {
  encounterId: string
  lines: Array<{ speaker: NpcId; text: string }>
  source: LineSource
  newClues: string[]
  state: GameState
}

export interface ExamineResponse {
  state: GameState
  newClues: string[]
  title: string
  text: string
  doorLog?: Array<{ time: string; npc: string; kind: string; room: string; corrupted: boolean }>
}

export interface Catalog {
  crew: Array<{ id: NpcId; name: string; post: RoomId }>
  rooms: Record<RoomId, string>
  adjacency: Record<RoomId, RoomId[]>
}

// A structured memory event as surfaced in state.ledger / /debug/memories.
export interface MemoryEvent {
  id: string
  type: 'npc_gossip' | 'claim' | 'confrontation' | 'clue'
  ownerNpc: NpcId | 'shared'
  canonicalText: string
  source: string
  shift: number
  importance: number
  privacy: string
  truthStatus: string
  relatedQuest: string
  datasets: string[]
  nodeSet?: string[] // cognee node_set tags this memory was written with
  writtenOk?: boolean | null
}
