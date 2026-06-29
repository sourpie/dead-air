// Central game store (Zustand). The backend is the source of truth; this store
// caches /game/state + catalog and the current conversation, and drives every call.
import { create } from 'zustand'
import { api } from '../api/client'
import { NPCS } from '../data/npcs'
import type { Catalog, Clue, GameState, MemoryEvent, NpcId, TalkResponse } from '../types'

type Screen = 'start' | 'game' | 'solve' | 'result'

interface Toast {
  id: number
  clue: Clue
}

interface Store {
  screen: Screen
  state: GameState | null
  catalog: Catalog | null
  talk: TalkResponse | null
  selectedNpc: NpcId | null
  loading: boolean
  busyChoice: string | null
  error: string | null

  toasts: Toast[]
  visited: NpcId[]
  showDayBeat: boolean
  showNotebook: boolean
  showDebugger: boolean
  showHowItWorks: boolean
  debug: Partial<Record<NpcId, MemoryEvent[]>>

  startGame: (reseed?: boolean) => Promise<void>
  selectNpc: (npcId: NpcId) => Promise<void>
  backToMap: () => void
  choose: (choiceId: string) => Promise<void>
  advanceDay: () => Promise<void>
  dismissDayBeat: () => void
  goToSolve: () => void
  backFromSolve: () => void
  solve: (theoryId: string) => Promise<void>
  removeToast: (id: number) => void
  loadDebug: (npcId: NpcId) => Promise<void>
  loadAllDebug: () => Promise<void>
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
  busyChoice: null,
  error: null,
  toasts: [],
  visited: [],
  showDayBeat: false,
  showNotebook: false,
  showDebugger: false,
  showHowItWorks: false,
  debug: {},

  startGame: async (reseed = false) => {
    set({ loading: true, error: null })
    try {
      const [state, catalog] = await Promise.all([api.start(reseed), api.catalog()])
      set({
        state,
        catalog,
        screen: 'game',
        talk: null,
        selectedNpc: null,
        debug: {},
        toasts: [],
        visited: [],
        showDayBeat: false,
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
    set((s) => ({
      selectedNpc: npcId,
      loading: true,
      error: null,
      talk: null,
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

  backToMap: () => set({ selectedNpc: null, talk: null }),

  choose: async (choiceId) => {
    const npcId = get().selectedNpc
    if (!npcId) return
    set({ busyChoice: choiceId, error: null })
    try {
      const { state, newClues } = await api.choose(npcId, choiceId)
      set({ state })
      pushClueToasts(set, get, newClues)
      const talk = await api.talk(npcId)
      set({ talk })
      void get().loadDebug(npcId)
    } catch (e) {
      set({ error: errMsg(e) })
    } finally {
      set({ busyChoice: null })
    }
  },

  advanceDay: async () => {
    set({ loading: true, error: null })
    try {
      const state = await api.advanceDay()
      set({ state, selectedNpc: null, talk: null, visited: [], showDayBeat: true })
      void get().loadAllDebug()
    } catch (e) {
      set({ error: errMsg(e) })
    } finally {
      set({ loading: false })
    }
  },

  dismissDayBeat: () => set({ showDayBeat: false }),

  goToSolve: () => set({ screen: 'solve', showNotebook: false, showDebugger: false }),
  backFromSolve: () => set({ screen: 'game' }),

  solve: async (theoryId) => {
    set({ loading: true, error: null })
    try {
      const state = await api.solve(theoryId)
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
    await Promise.all((Object.keys(NPCS) as NpcId[]).map((id) => get().loadDebug(id)))
  },

  toggleNotebook: () => set((s) => ({ showNotebook: !s.showNotebook, showDebugger: false })),
  toggleDebugger: () => {
    const next = !get().showDebugger
    set({ showDebugger: next, showNotebook: false })
    if (next) void get().loadAllDebug()
  },
  toggleHowItWorks: (v) => set((s) => ({ showHowItWorks: v ?? !s.showHowItWorks })),
  clearError: () => set({ error: null }),
}))

function pushClueToasts(
  set: (fn: (s: Store) => Partial<Store>) => void,
  get: () => Store,
  newClues: string[],
) {
  const catalog = get().catalog
  if (!catalog || newClues.length === 0) return
  const toasts = newClues
    .map((id) => catalog.clues.find((c) => c.id === id))
    .filter((c): c is Clue => Boolean(c))
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
