import { useEffect, useState } from 'react'
import { useGame } from '../state/gameStore'
import { MapScene } from '../components/map/MapScene'
import { EvidenceBoard } from '../components/EvidenceBoard'
import { MemoryDebugger } from '../components/MemoryDebugger'
import { HowItWorks } from '../components/HowItWorks'
import { ClueToasts } from '../components/ClueToast'
import { OverhearCaptions } from '../components/OverhearCaptions'
import { ShiftBeat } from '../components/ShiftBeat'
import { NPCS } from '../data/npcs'
import { ROOM_INFO } from '../data/rooms'
import { npcSim } from '../components/map/npcSim'

export function GamePage() {
  const g = useGame()
  const { state } = g
  if (!state) return null

  return (
    <div className="fixed inset-0 overflow-hidden bg-grape-2">
      <MapScene />
      <HUD />
      <BottomBar />

      {g.error && (
        <div className="gcard fixed bottom-20 left-1/2 z-50 -translate-x-1/2 px-4 py-2 font-body text-lg text-bad">
          {g.error} <button onClick={g.clearError} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {g.missedNote && (
        <div className="pointer-events-auto fixed bottom-20 right-5 z-40 max-w-xs bg-grape-2/90 px-3 py-2"
          style={{ border: '2px solid var(--color-line)' }} onClick={g.dismissMissed}>
          <p className="font-body text-base leading-tight text-dim">{g.missedNote}</p>
        </div>
      )}

      <ClueToasts />
      <OverhearCaptions />
      {g.showNotebook && <EvidenceBoard />}
      {g.showDebugger && <MemoryDebugger />}
      {g.showHowItWorks && <HowItWorks />}
      {g.showShiftBeat && <ShiftBeat />}
    </div>
  )
}

function HUD() {
  const { state, goToMeeting, toggleHowItWorks, startGame } = useGame()
  if (!state) return null
  const found = state.cluesFound.length
  const total = state.clueCatalog.length || 7
  const activeEnc = state.shiftPlan.encounters[0]

  return (
    <header className="absolute inset-x-0 top-0 z-30">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b-3 border-grape-2 bg-grape/90 px-4 py-2.5 sm:px-6" style={{ borderBottomWidth: 3 }}>
        <span className="font-display text-[11px] text-text">
          DEAD<span className="text-coral">//</span><span className="text-gold">AIR</span>
        </span>

        <span className="chip bg-violet px-2 py-1 text-grape-2">
          SHIFT {state.shift + 1}/{state.maxShifts} · {state.shiftName}
        </span>
        <div className="flex gap-1">
          {Array.from({ length: state.maxShifts }).map((_, i) => (
            <span key={i} className="h-3 w-3 border border-grape-2"
              style={{ background: i <= state.shift ? 'var(--color-violet)' : '#2b3350' }} />
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="chip text-gold">CLUES {found}/{total}</span>
          <div className="flex gap-1">
            {Array.from({ length: total }).map((_, i) => (
              <span
                key={i}
                className="h-3 w-3 border border-grape-2"
                style={{ background: i < found ? 'var(--color-gold)' : '#2b3350' }}
              />
            ))}
          </div>
        </div>

        {activeEnc && <ChatterChip />}
        {state.seeding === 'in_progress' && (
          <span className="chip text-teal">◌ MEMORY SYNC<span className="blink">…</span></span>
        )}

        <div className="ml-auto flex items-center gap-2">
          <button onClick={goToMeeting} className="btn btn-pop px-3 py-2 text-[9px]">
            ⚠ EMERGENCY
          </button>
          <button onClick={() => toggleHowItWorks(true)} className="btn btn-soft px-3 py-2 text-[9px]">
            ?
          </button>
          <button onClick={() => startGame()} className="btn btn-soft px-3 py-2 text-[9px]" title="New run (new mystery)">
            ↺
          </button>
        </div>
      </div>
    </header>
  )
}

// Live "someone is talking somewhere" signpost. The sim clock isn't reactive,
// so poll it once a second — otherwise this chip would never notice a window
// opening between store updates.
function ChatterChip() {
  const [, setTick] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1000)
    return () => window.clearInterval(id)
  }, [])
  const active = npcSim.activeEncounters()
  const state = useGame((s) => s.state)
  if (!active.length || !state) return null
  const e = active[0]
  const heard = state.overheard.includes(e.id)
  return (
    <span className="chip" style={{ color: heard ? 'var(--color-dim)' : 'var(--color-teal)' }}>
      {heard ? '✓' : '◉'} CHATTER: {ROOM_INFO[e.room].name.toUpperCase()} — {e.npcs.map((n) => NPCS[n].name.split(' ').pop()!.toUpperCase()).join(' + ')}
    </span>
  )
}

function BottomBar() {
  const { state, toggleNotebook, toggleDebugger, advanceShift, goToMeeting, loading } = useGame()
  if (!state) return null
  const clues = state.cluesFound.length
  const lastShift = state.shift >= state.maxShifts - 1

  return (
    <footer className="absolute inset-x-0 bottom-0 z-30">
      <div className="flex items-center gap-2 border-t-3 border-grape-2 bg-grape/90 px-4 py-2 sm:px-6" style={{ borderTopWidth: 3 }}>
        <button onClick={toggleNotebook} className="btn btn-soft px-3 py-2 text-[9px]">
          ▤ EVIDENCE{clues ? ` ×${clues}` : ''}
        </button>
        <button onClick={toggleDebugger} className="btn btn-soft px-3 py-2 text-[9px]">
          ◉ MEMORY.LOG
        </button>
        <span className="hidden font-body text-lg text-dim md:inline">
          ⌨ WASD walk · [E] interact · walk close to chatter to overhear
        </span>

        {lastShift ? (
          <button onClick={goToMeeting} disabled={loading} className="btn btn-pop ml-auto px-4 py-2 text-[9px] disabled:opacity-60">
            ⚠ CALL MEETING
          </button>
        ) : (
          <button onClick={() => advanceShift(state.playerRoom)} disabled={loading} className="btn btn-gold ml-auto px-4 py-2 text-[9px] disabled:opacity-60">
            NEXT SHIFT ▸
          </button>
        )}
      </div>
    </footer>
  )
}
