import { useGame } from '../state/gameStore'
import { NPCS } from '../data/npcs'
import { MapView } from '../components/MapView'
import { NPCPanel } from '../components/NPCPanel'
import { DialogueBox } from '../components/DialogueBox'
import { EvidenceBoard } from '../components/EvidenceBoard'
import { MemoryDebugger } from '../components/MemoryDebugger'
import { HowItWorks } from '../components/HowItWorks'
import { ClueToasts } from '../components/ClueToast'
import { DayBeat } from '../components/DayBeat'
import type { NpcId } from '../types'

export function GamePage() {
  const g = useGame()
  const { state, selectedNpc } = g
  if (!state) return null

  return (
    <div className="min-h-screen pb-24">
      <HUD />

      <main className="mx-auto max-w-6xl px-6 py-7">
        {selectedNpc ? <Conversation npcId={selectedNpc} /> : <MapView />}
      </main>

      <BottomBar />

      {g.error && (
        <div className="fixed bottom-24 left-1/2 z-50 -translate-x-1/2 rounded-2xl bg-bad/20 px-4 py-2 font-mono text-sm text-bad shadow-xl backdrop-blur">
          {g.error} <button onClick={g.clearError} className="ml-2 underline">dismiss</button>
        </div>
      )}

      <ClueToasts />
      {g.showNotebook && <EvidenceBoard />}
      {g.showDebugger && <MemoryDebugger />}
      {g.showHowItWorks && <HowItWorks />}
      {g.showDayBeat && <DayBeat />}
    </div>
  )
}

function HUD() {
  const { state, catalog, goToSolve, toggleHowItWorks, startGame } = useGame()
  const found = state?.cluesFound.length ?? 0
  const total = catalog?.clues.length ?? 5

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-grape/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-6 py-3">
        <span className="font-display text-lg font-bold text-text">
          Neighbourhood <span className="text-gold">Echoes</span>
        </span>
        <span className="rounded-full bg-violet/20 px-3 py-0.5 font-display text-xs font-bold text-violet">
          Day {state?.day}
        </span>

        {/* clue progress */}
        <div className="flex items-center gap-2">
          <span className="font-display text-sm font-bold text-text">🔍 {found}/{total}</span>
          <div className="flex gap-1">
            {Array.from({ length: total }).map((_, i) => (
              <span
                key={i}
                className="h-2.5 w-2.5 rounded-full transition-all"
                style={{ background: i < found ? 'var(--color-gold)' : 'rgba(255,255,255,0.15)' }}
              />
            ))}
          </div>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button onClick={goToSolve} className="btn btn-gold px-4 py-1.5 text-sm">
            ⚖️ Solve the Case
          </button>
          <button onClick={() => toggleHowItWorks(true)} className="btn btn-soft px-3 py-1.5 text-xs">
            ?
          </button>
          <button onClick={() => startGame(false)} className="btn btn-soft px-3 py-1.5 text-xs">
            ↻
          </button>
        </div>
      </div>
    </header>
  )
}

function Conversation({ npcId }: { npcId: NpcId }) {
  const { backToMap, debug } = useGame()
  const hints = (debug[npcId] ?? []).slice(-4).reverse()
  const npc = NPCS[npcId]

  return (
    <div className="animate-rise">
      <button onClick={backToMap} className="chip mb-4 text-dim hover:text-text">
        ← back to Maple Street
      </button>

      <div className="grid gap-5 lg:grid-cols-[260px_1fr_240px]">
        <NPCPanel npcId={npcId} />
        <DialogueBox />
        <aside className="gpanel flex flex-col gap-3 p-4">
          <h4 className="chip text-dim">🧠 What {npc.name.split(' ')[0]} remembers</h4>
          {hints.length === 0 ? (
            <p className="font-body text-xs text-dim">Nothing notable yet.</p>
          ) : (
            hints.map((m) => (
              <div key={m.id} className="rounded-xl bg-white/6 p-2.5">
                <span className="font-mono text-[10px] font-bold uppercase" style={{ color: npc.colorVar }}>
                  {m.type}
                </span>
                <p className="font-body text-[12px] leading-snug text-text/85">{m.canonicalText}</p>
              </div>
            ))
          )}
        </aside>
      </div>
    </div>
  )
}

function BottomBar() {
  const { state, toggleNotebook, toggleDebugger, advanceDay, loading } = useGame()
  const day = state?.day ?? 1
  const clues = state?.cluesFound.length ?? 0

  return (
    <footer className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-grape/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-3">
        <button onClick={toggleNotebook} className="btn btn-soft px-4 py-2 text-sm">
          📋 Evidence{clues ? ` · ${clues}` : ''}
        </button>
        <button onClick={toggleDebugger} className="btn btn-soft px-4 py-2 text-sm">
          🧠 Memory Debugger
        </button>

        {day < 2 && (
          <button onClick={advanceDay} disabled={loading} className="btn btn-pop ml-auto px-5 py-2 text-sm disabled:opacity-60">
            🌙 End Day 1 → Day 2
          </button>
        )}
      </div>
    </footer>
  )
}
