// Central game store (Zustand). The backend is the source of truth; this store
// caches /game/state + catalog and the current conversation, and drives every
// call. High-frequency crew positions live in npcSim (not here).
import { create } from 'zustand'
import { api } from '../api/client'
import { CREW_IDS } from '../data/npcs'
import { npcSim } from '../components/map/npcSim'
import type {
  Catalog, ClueCatalogEntry, GameState, MemoryEvent, NpcId, RoomId, TalkResponse, Verb,
} from '../types'

type Screen = 'start' | 'game' | 'meeting' | 'result'

interface Toast {
  id: number
  clue: ClueCatalogEntry
}

export interface OverhearPlayback {
  encounterId: string
  room: RoomId
  lines: Array<{ speaker: NpcId; text: string }>
  source: string
}

interface Store {
  screen: Screen
  state: GameState | null
  catalog: Catalog | null
  talk: TalkResponse | null
  selectedNpc: NpcId | null
  loading: boolean
  busyVerb: string | null
  busySay: boolean
  lastPlayerLine: string | null
  error: string | null

  toasts: Toast[]
  visited: NpcId[]
  overhearPlayback: OverhearPlayback | null
  overhearPending: { encounterId: string; room: RoomId } | null
  overhearBusy: Set<string>
  missedNote: string | null
  showShiftBeat: boolean
  showNotebook: boolean
  showDebugger: boolean
  showHowItWorks: boolean
  debug: Partial<Record<NpcId, MemoryEvent[]>>

  startGame: (seed?: number) => Promise<void>
  selectNpc: (npcId: NpcId) => Promise<void>
  backToMap: () => void
  ask: (verb: Verb) => Promise<void>
  say: (text: string) => Promise<void>
  advanceShift: (playerRoom: RoomId | null) => Promise<void>
  overhearEncounter: (encounterId: string, room: RoomId, playerRoom: RoomId) => Promise<void>
  dismissOverhear: () => void
  noteMissed: (text: string) => void
  dismissMissed: () => void
  examine: (spotId: string) => Promise<{ title: string; text: string; doorLog?: unknown[] } | null>
  goToMeeting: () => void
  backFromMeeting: () => void
  accuse: (npcId: NpcId) => Promise<void>
  removeToast: (id: number) => void
  loadDebug: (npcId: NpcId) => Promise<void>
  loadAllDebug: () => Promise<void>
  dismissShiftBeat: () => void
  toggleNotebook: () => void
  toggleDebugger: () => void
  toggleHowItWorks: (v?: boolean) => void
  clearError: () => void
}

let _toastSeq = 1

export const useGame = create<Store>((set, get) => ({
  screen: 'start',
  state: null,
  catalog: null,
  talk: null,
  selectedNpc: null,
  loading: false,
  busyVerb: null,
  busySay: false,
  lastPlayerLine: null,
  error: null,
  toasts: [],
  visited: [],
  overhearPlayback: null,
  overhearPending: null,
  overhearBusy: new Set<string>(),
  missedNote: null,
  showShiftBeat: false,
  showNotebook: false,
  showDebugger: false,
  showHowItWorks: false,
  debug: {},

  startGame: async (seed) => {
    set({ loading: true, error: null })
    try {
      const [state, catalog] = await Promise.all([api.start(seed), api.catalog()])
      npcSim.load(state.shiftPlan)
      set({
        state,
        catalog,
        screen: 'game',
        talk: null,
        selectedNpc: null,
        debug: {},
        toasts: [],
        visited: [],
        overhearPlayback: null,
        overhearBusy: new Set<string>(),
        missedNote: null,
        showShiftBeat: false,
        showNotebook: false,
        showDebugger: false,
      })
    } catch (e) {
      set({ error: errMsg(e) })
    } finally {
      set({ loading: false })
    }
  },

  selectNpc: async (npcId) => {
    npcSim.engage(npcId)
    set((s) => ({
      selectedNpc: npcId,
      loading: true,
      error: null,
      talk: null,
      lastPlayerLine: null,
      visited: s.visited.includes(npcId) ? s.visited : [...s.visited, npcId],
    }))
    try {
      const talk = await api.talk(npcId)
      set({ talk })
      void get().loadDebug(npcId)
    } catch (e) {
      set({ error: errMsg(e) })
    } finally {
      set({ loading: false })
    }
  },

  backToMap: () => {
    const npc = get().selectedNpc
    if (npc) npcSim.release(npc)
    set({ selectedNpc: null, talk: null, lastPlayerLine: null })
  },

  ask: async (verb) => {
    const npcId = get().selectedNpc
    if (!npcId) return
    set({ busyVerb: verb.id, error: null, lastPlayerLine: verb.label })
    try {
      const r = await api.ask(npcId, verb.verb, verb.arg)
      npcSimSafeReload(get().state, r.state)
      set((s) => ({
        state: r.state,
        talk: s.talk && {
          ...s.talk,
          npcLine: r.npcLine,
          emotion: r.emotion,
          source: r.source,
          verbs: r.verbs,
          relationship: r.relationship,
        },
      }))
      pushClueToasts(set, get, r.newClues)
      void get().loadDebug(npcId)
    } catch (e) {
      set({ error: errMsg(e) })
    } finally {
      set({ busyVerb: null })
    }
  },

  say: async (text) => {
    const npcId = get().selectedNpc
    if (!npcId || !get().talk) return
    set({ busySay: true, error: null, lastPlayerLine: text })
    try {
      const r = await api.say(npcId, text)
      // a reactive encounter may have spawned: the crewmate will walk off to
      // discuss what you just said the moment you close the bubble
      npcSim.syncEncounters(r.state.shiftPlan)
      set((s) => ({
        state: r.state,
        talk: s.talk && {
          ...s.talk,
          npcLine: r.npcLine,
          emotion: r.emotion,
          source: r.source,
          relationship: r.relationship,
        },
      }))
      void get().loadDebug(npcId)
    } catch (e) {
      set({ error: errMsg(e) })
    } finally {
      set({ busySay: false })
    }
  },

  advanceShift: async (playerRoom) => {
    set({ loading: true, error: null })
    try {
      const { state } = await api.advanceShift(playerRoom)
      npcSim.load(state.shiftPlan)
      set({
        state,
        selectedNpc: null,
        talk: null,
        overhearPlayback: null,
        missedNote: null,
        showShiftBeat: true,
      })
      void get().loadAllDebug()
    } catch (e) {
      set({ error: errMsg(e) })
    } finally {
      set({ loading: false })
    }
  },

  overhearEncounter: async (encounterId, room, playerRoom) => {
    const s = get()
    if (s.overhearBusy.has(encounterId)) return
    if (s.state?.overheard.includes(encounterId)) return
    // Instant feedback: the "you lean in…" bar shows while the exchange is
    // being generated (live generation takes seconds).
    set((prev) => ({
      overhearBusy: new Set(prev.overhearBusy).add(encounterId),
      overhearPending: { encounterId, room },
    }))
    try {
      const r = await api.overhear(encounterId, playerRoom)
      set({
        state: r.state,
        overhearPending: null,
        overhearPlayback: { encounterId, room, lines: r.lines, source: r.source },
      })
      pushClueToasts(set, get, r.newClues)
      void get().loadAllDebug()
    } catch {
      // Out of range or raced past the window: clear the attempt so walking
      // closer can retry — a 403 must never permanently spend the encounter.
      set((prev) => {
        const busy = new Set(prev.overhearBusy)
        busy.delete(encounterId)
        return { overhearBusy: busy, overhearPending: null }
      })
    }
  },

  dismissOverhear: () => set({ overhearPlayback: null }),
  noteMissed: (text) => set((s) => (s.missedNote ? s : { missedNote: text })),
  dismissMissed: () => set({ missedNote: null }),

  examine: async (spotId) => {
    try {
      const r = await api.examine(spotId)
      set({ state: r.state })
      pushClueToasts(set, get, r.newClues)
      return { title: r.title, text: r.text, doorLog: r.doorLog }
    } catch (e) {
      set({ error: errMsg(e) })
      return null
    }
  },

  goToMeeting: () => set({ screen: 'meeting', showNotebook: false, showDebugger: false, selectedNpc: null, talk: null }),
  backFromMeeting: () => set({ screen: 'game' }),

  accuse: async (npcId) => {
    set({ loading: true, error: null })
    try {
      const state = await api.accuse(npcId)
      set({ state, screen: 'result' })
    } catch (e) {
      set({ error: errMsg(e) })
    } finally {
      set({ loading: false })
    }
  },

  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  loadDebug: async (npcId) => {
    try {
      const { memories } = await api.debugMemories(npcId)
      set((s) => ({ debug: { ...s.debug, [npcId]: memories } }))
    } catch {
      /* debugger is best-effort */
    }
  },

  loadAllDebug: async () => {
    await Promise.all(CREW_IDS.map((id) => get().loadDebug(id)))
  },

  dismissShiftBeat: () => set({ showShiftBeat: false }),
  toggleNotebook: () => set((s) => ({ showNotebook: !s.showNotebook, showDebugger: false })),
  toggleDebugger: () => {
    const next = !get().showDebugger
    set({ showDebugger: next, showNotebook: false })
    if (next) void get().loadAllDebug()
  },
  toggleHowItWorks: (v) => set((s) => ({ showHowItWorks: v ?? !s.showHowItWorks })),
  clearError: () => set({ error: null }),
}))

// A verb response returns the whole state; reload the sim only if the shift
// actually changed (it normally doesn't mid-conversation).
function npcSimSafeReload(prev: GameState | null, next: GameState) {
  if (prev && prev.shift !== next.shift) npcSim.load(next.shiftPlan)
}

function pushClueToasts(
  set: (fn: (s: Store) => Partial<Store>) => void,
  get: () => Store,
  newClues: string[],
) {
  const cat = get().state?.clueCatalog
  if (!cat || newClues.length === 0) return
  const toasts = newClues
    .map((id) => cat.find((c) => c.id === id))
    .filter((c): c is ClueCatalogEntry => Boolean(c))
    .map((clue) => ({ id: _toastSeq++, clue }))
  set((s) => ({ toasts: [...s.toasts, ...toasts] }))
}

function errMsg(e: unknown): string {
  if (e instanceof Error) {
    if (e.message.includes('Failed to fetch'))
      return 'Cannot reach the backend on :8000. Start it (uvicorn api:app --port 8000) or run devserver_stub.py.'
    return e.message
  }
  return String(e)
}
