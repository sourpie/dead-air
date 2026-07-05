import { useEffect, useState } from 'react'
import { useGame } from '../state/gameStore'
import { CREW_IDS, NPCS } from '../data/npcs'
import { api } from '../api/client'
import type { MemoryEvent, NpcId } from '../types'

const TYPE_COLOR: Record<string, string> = {
  npc_gossip: '#e85fc0',
  claim: '#b06bff',
  confrontation: '#ff5a72',
  clue: '#36c5e0',
}

type Features = Awaited<ReturnType<typeof api.debugDatasets>>['features']

export function MemoryDebugger() {
  const { debug, toggleDebugger } = useGame()
  const [features, setFeatures] = useState<Features | null>(null)

  useEffect(() => {
    api.debugDatasets().then((d) => setFeatures(d.features)).catch(() => {})
  }, [])

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
        <p className="mb-3 max-w-3xl font-body text-lg leading-tight text-dim">
          The secret sauce: each crewmate recalls only their <b className="text-text">own</b> Cognee
          dataset (plus shared rumours). Gossip between crew writes real memories — watch information
          travel the station whether or not you overheard it.
        </p>

        <FeatureStrip features={features} />

        <AskGraph />

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {CREW_IDS.map((id) => (
            <Column key={id} npcId={id} memories={debug[id] ?? []} />
          ))}
        </div>
      </section>
    </div>
  )
}

// The cognee capabilities live this run — a judge-facing "how we use Cognee" strip.
function FeatureStrip({ features }: { features: Features | null }) {
  if (!features) return null
  const chips: Array<[string, boolean | string]> = [
    ['graph pipeline', features.granular],
    ['node_set metadata', features.granular],
    ['temporal graph', features.temporal],
    ['ontology grounding', features.ontology],
    ['memify enrichment', features.memify],
    [`feedback ranking ${features.feedbackInfluence}`, features.feedbackInfluence > 0],
  ]
  return (
    <div className="mb-5 flex flex-wrap items-center gap-2">
      <span className="chip bg-white/10 px-2 py-0.5 text-dim">POWERED BY COGNEE</span>
      {chips.map(([label, on]) => (
        <span
          key={label}
          className="chip px-2 py-0.5 font-mono text-[10px]"
          style={{ background: on ? 'rgba(54,197,224,0.18)' : 'rgba(255,255,255,0.05)',
                   color: on ? '#36c5e0' : '#6b7394' }}
        >
          {on ? '✓' : '·'} {label}
        </span>
      ))}
      <span className="chip px-2 py-0.5 font-mono text-[10px] text-dim">
        recall: whereabouts→TEMPORAL · confront→COT · free-text→HYBRID
      </span>
    </div>
  )
}

// Investigator console — ask the station's whole memory graph in natural
// language (cognee NL -> Cypher). A judge-facing "query the memory" demo.
function AskGraph() {
  const [q, setQ] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const ask = async () => {
    if (!q.trim() || busy) return
    setBusy(true)
    setAnswer(null)
    try {
      const r = await api.askGraph(q.trim())
      setAnswer(r.answer)
    } catch {
      setAnswer('(query failed)')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mb-5 flex flex-col gap-2 border border-line bg-grape-2/40 p-3">
      <div className="flex items-center gap-2">
        <span className="chip bg-white/10 px-2 py-0.5 text-teal">◈ ASK THE MEMORY GRAPH</span>
        <a
          href={api.provenanceUrl()}
          target="_blank"
          rel="noreferrer"
          className="btn btn-soft ml-auto px-2 py-1 text-[9px]"
        >
          ◇ PROVENANCE GRAPH
        </a>
      </div>
      <div className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && ask()}
          placeholder="e.g. Who was seen near the engine room that night?"
          className="flex-1 bg-grape px-3 py-1.5 font-body text-lg text-ink outline-none"
        />
        <button onClick={ask} disabled={busy} className="btn btn-soft px-3 py-1.5 text-[9px]">
          {busy ? '…' : 'ASK'}
        </button>
      </div>
      {answer && (
        <p className="font-body text-lg leading-tight text-ink">
          <span className="text-teal">→ </span>
          {answer}
        </p>
      )}
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
      <a
        href={api.graphUrl(npcId)}
        target="_blank"
        rel="noreferrer"
        className="btn btn-soft px-2 py-1 text-center text-[9px]"
        title="Open cognee's knowledge-graph render of this crewmate's memory"
      >
        ◈ VIEW KNOWLEDGE GRAPH
      </a>
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
      {m.nodeSet && m.nodeSet.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {m.nodeSet.map((tag) => (
            <span key={tag} className="rounded bg-teal/15 px-1.5 py-0.5 font-mono text-[9px] text-teal">
              {tag}
            </span>
          ))}
        </div>
      )}
      <p className="mt-1 font-body text-sm leading-tight text-ink-dim">
        → {m.datasets.length ? m.datasets.join(', ') : 'ledger only (no cognee write)'}
        {m.writtenOk === false && <span className="text-bad"> · write failed (ledger kept)</span>}
        {m.writtenOk === null && <span className="text-gold"> · writing…</span>}
      </p>
    </div>
  )
}
