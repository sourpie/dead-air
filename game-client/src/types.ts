// Shared types mirroring the FastAPI backend JSON (plan §6/§7/§8).

export type NpcId = 'maya' | 'sam' | 'jules'
export type LocationId = 'bakery' | 'garden' | 'teastall'

export interface Relationship {
  trust: number
  suspicion: number
}

export interface GameState {
  day: number
  location: LocationId
  relationships: Record<NpcId, Relationship>
  flags: Record<string, boolean>
  notebook: string[]
  cluesFound: string[]
  ledger: MemoryEvent[]
  convo: Record<NpcId, string>
  solved: boolean | null
  result: Result | null
}

export interface Clue {
  id: string
  title: string
  icon: string
  hint: string
}

export interface Theory {
  id: string
  text: string
}

export interface Catalog {
  clues: Clue[]
  theories: Theory[]
}

export interface Result {
  solvedCorrectly: boolean
  chosenTheory: string
  correctTheory: string
  correctText: string
  score: number
  stars: number
  maxStars: number
  cluesFound: number
  totalClues: number
  betrayed: boolean
  rank: { title: string; icon: string; blurb: string }
  narrative: Ending
}

export interface Choice {
  id: string
  text: string
}

export interface TalkResponse {
  npcId: NpcId
  name: string
  nodeId: string
  npcLine: string
  emotion: string
  source: 'cognee' | 'fallback'
  choices: Choice[]
  relationship: Relationship
  day: number
}

// A structured memory event (plan §6) as surfaced by /debug/memories/{npcId}.
export interface MemoryEvent {
  id: string
  type: 'promise' | 'secret' | 'gossip' | 'betrayal' | 'clue' | 'claim'
  ownerNpc: NpcId | 'shared'
  canonicalText: string
  source: string
  day: number
  importance: number
  privacy: string
  truthStatus: string
  relatedQuest: string
  datasets: string[]
  writtenOk?: boolean
}

export interface Ending {
  id: string
  title: string
  mystery: string
  relationship: string
  memory: string
}

export interface LocationInfo {
  id: LocationId
  name: string
  blurb: string
  npc: NpcId
}
