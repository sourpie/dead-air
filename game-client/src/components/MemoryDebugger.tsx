import { useGame } from '../state/gameStore'
import { NPCS } from '../data/npcs'
import type { MemoryEvent, NpcId } from '../types'

const TYPE_COLOR: Record<MemoryEvent['type'], string> = {
  promise: '#43d17a',
  secret: '#ffc94d',
  gossip: '#e85fc0',
  betrayal: '#ff5a72',
  clue: '#36c5e0',
  claim: '#b06bff',
}

export function MemoryDebugger() {
  const { debug, toggleDebugger } = useGame()
  const ids = Object.keys(NPCS) as NpcId[]

  return (
    <div className="fixed inset-0 z-40 flex items-end bg-grape-2/75 backdrop-blur-sm" onClick={toggleDebugger}>
      <section
        className="animate-rise max-h-[84vh] w-full overflow-y-auto rounded-t-3xl border-t border-line bg-grape p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-1 flex items-center justify-between">
          <h2 className="font-display text-2xl font-bold text-text">
            🧠 Memory Debugger
          </h2>
          <button onClick={toggleDebugger} className="btn btn-soft px-3 py-1.5 text-sm">
            ✕
          </button>
        </div>
        <p className="mb-5 max-w-3xl font-body text-[15px] text-dim">
          The secret sauce: each neighbour recalls only their <b className="text-text">own</b> Cognee
          dataset (plus shared rumours). That's why they answer differently — and how a secret only
          reaches Maya once gossip carries it there.
        </p>

        <div className="grid gap-4 lg:grid-cols-3">
          {ids.map((id) => (
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
      <div className="flex items-center gap-2 border-b border-line pb-2">
        <span className="text-2xl">{npc.emoji}</span>
        <h3 className="font-display text-base font-bold" style={{ color: npc.colorVar }}>
          {npc.name}
        </h3>
        <span className="ml-auto rounded-full bg-white/10 px-2 font-mono text-xs text-dim">
          {memories.length}
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
          className="rounded-md px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-white"
          style={{ background: TYPE_COLOR[m.type] }}
        >
          {m.type}
        </span>
        {m.ownerNpc === 'shared' && (
          <span className="rounded-md bg-violet/20 px-1.5 py-0.5 font-mono text-[10px] uppercase text-violet">
            shared
          </span>
        )}
        <span className="ml-auto font-mono text-[10px] text-ink-dim">
          day {m.day} · imp {m.importance}
        </span>
      </div>
      <p className="font-body text-[13px] font-semibold leading-snug text-ink">{m.canonicalText}</p>
      <p className="mt-1 font-mono text-[10px] text-ink-dim">
        → {m.datasets.join(', ')}
        {m.writtenOk === false && <span className="text-bad"> · write failed (ledger kept)</span>}
      </p>
    </div>
  )
}
