import { useGame } from '../state/gameStore'
import { CREW_IDS, NPCS } from '../data/npcs'
import type { MemoryEvent, NpcId } from '../types'

const TYPE_COLOR: Record<string, string> = {
  npc_gossip: '#e85fc0',
  claim: '#b06bff',
  confrontation: '#ff5a72',
  clue: '#36c5e0',
}

export function MemoryDebugger() {
  const { debug, toggleDebugger } = useGame()

  return (
    <div className="fixed inset-0 z-40 flex items-end bg-grape-2/75 backdrop-blur-sm" onClick={toggleDebugger}>
      <section
        className="animate-rise max-h-[84vh] w-full overflow-y-auto border-t border-line bg-grape p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-1 flex items-center justify-between">
          <h2 className="font-display text-sm text-text">
            ◉ MEMORY.LOG <span className="text-teal">// who knows what</span>
          </h2>
          <button onClick={toggleDebugger} className="btn btn-soft px-3 py-1.5 text-[9px]">
            ✕
          </button>
        </div>
        <p className="mb-5 max-w-3xl font-body text-lg leading-tight text-dim">
          The secret sauce: each crewmate recalls only their <b className="text-text">own</b> Cognee
          dataset (plus shared rumours). Gossip between crew writes real memories — watch information
          travel the station whether or not you overheard it.
        </p>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {CREW_IDS.map((id) => (
            <Column key={id} npcId={id} memories={debug[id] ?? []} />
          ))}
        </div>
      </section>
    </div>
  )
}

function Column({ npcId, memories }: { npcId: NpcId; memories: MemoryEvent[] }) {
  const npc = NPCS[npcId]
  return (
    <div className="gpanel flex flex-col gap-3 p-4">
      <div className="flex items-center gap-2 border-b-2 border-line pb-2">
        <span className="text-2xl">{npc.emoji}</span>
        <h3 className="chip" style={{ color: npc.colorVar }}>
          {npc.name.split(' ').pop()!.toUpperCase()}
        </h3>
        <span className="chip ml-auto bg-white/10 px-2 py-0.5 text-dim">
          ×{memories.length}
        </span>
      </div>
      {memories.length === 0 ? (
        <p className="py-6 text-center font-mono text-xs text-dim">no memories yet</p>
      ) : (
        memories.map((m, i) => <MemoryCard key={m.id + i} m={m} />)
      )}
    </div>
  )
}

function MemoryCard({ m }: { m: MemoryEvent }) {
  return (
    <div className="gcard animate-pop px-3 py-2.5">
      <div className="mb-1 flex items-center gap-2">
        <span
          className="px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-white"
          style={{ background: TYPE_COLOR[m.type] ?? '#4c5876' }}
        >
          {m.type}
        </span>
        <span className="ml-auto font-mono text-[10px] text-ink-dim">
          shift {m.shift + 1} · imp {m.importance}
        </span>
      </div>
      <p className="font-body text-lg leading-tight text-ink">{m.canonicalText}</p>
      <p className="mt-1 font-body text-sm leading-tight text-ink-dim">
        → {m.datasets.length ? m.datasets.join(', ') : 'ledger only (no cognee write)'}
        {m.writtenOk === false && <span className="text-bad"> · write failed (ledger kept)</span>}
        {m.writtenOk === null && <span className="text-gold"> · writing…</span>}
      </p>
    </div>
  )
}
