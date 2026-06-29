import { useGame } from '../state/gameStore'
import { HowItWorks } from '../components/HowItWorks'
import { NPCS } from '../data/npcs'
import type { NpcId } from '../types'

const CAST: NpcId[] = ['maya', 'sam', 'jules']

const STEPS = [
  { icon: '🗣️', title: 'Talk to neighbours', body: 'Visit three doors and pick what to say. Win people over and they spill secrets.' },
  { icon: '🔍', title: 'Collect 5 clues', body: 'Every reveal drops a clue into your evidence board. Find them all to crack the case.' },
  { icon: '🤞', title: 'Keep (or break) a promise', body: 'Maya trusts you with a secret. Spill it to Jules and it spreads — and costs you points.' },
  { icon: '⚖️', title: 'Accuse & score', body: 'Say what really happened. Solve it AND keep trust to earn ⭐⭐⭐.' },
]

export function StartPage() {
  const { startGame, loading, error, toggleHowItWorks, showHowItWorks } = useGame()

  return (
    <div className="mx-auto min-h-screen max-w-5xl px-6 py-12">
      {/* Hero */}
      <div className="animate-rise text-center">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1">
          <span className="h-2 w-2 animate-pulse rounded-full bg-gold" />
          <span className="chip text-dim">A cozy whodunit · powered by NPC memory</span>
        </div>
        <h1 className="font-display text-6xl font-bold leading-[0.95] tracking-tight text-text sm:text-8xl">
          Neighbourhood
          <br />
          <span className="bg-linear-to-r from-coral via-gold to-magenta bg-clip-text text-transparent">
            Echoes
          </span>
        </h1>
        <p className="mx-auto mt-5 max-w-2xl font-body text-xl leading-relaxed text-dim sm:text-2xl">
          Someone broke into the garden shed. Talk to the neighbours, gather the clues —
          but careful: <span className="font-bold text-gold">they remember every word you say.</span>
        </p>
      </div>

      {/* Goal banner */}
      <div className="animate-rise gcard mx-auto mt-9 max-w-3xl px-6 py-5 text-center" style={{ animationDelay: '80ms' }}>
        <p className="chip text-coral">🎯 Your mission</p>
        <p className="mt-1 font-body text-lg font-semibold text-ink sm:text-xl">
          Find all <b className="text-coral">5 clues</b>, then accuse the right culprit — and keep the
          neighbourhood's trust to earn a <b className="text-coral">3‑star</b> rating.
        </p>
      </div>

      {/* How to win — 4 chunky steps */}
      <div className="animate-rise mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-4" style={{ animationDelay: '140ms' }}>
        {STEPS.map((s, i) => (
          <div key={i} className="gpanel relative p-5">
            <div className="text-3xl">{s.icon}</div>
            <div className="mt-2 flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-gold font-display text-xs font-bold text-ink">
                {i + 1}
              </span>
              <h3 className="font-display text-base font-semibold text-text">{s.title}</h3>
            </div>
            <p className="mt-1.5 font-body text-sm leading-snug text-dim">{s.body}</p>
          </div>
        ))}
      </div>

      {/* The cast */}
      <div className="animate-rise mt-10" style={{ animationDelay: '200ms' }}>
        <p className="mb-4 text-center font-display text-sm font-semibold uppercase tracking-wider text-dim">
          Meet the neighbours
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          {CAST.map((id, i) => (
            <CastCard key={id} id={id} delay={240 + i * 70} />
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="animate-rise mt-10 flex flex-col items-center gap-3" style={{ animationDelay: '320ms' }}>
        <button onClick={() => startGame(false)} disabled={loading} className="btn btn-pop px-10 py-4 text-xl disabled:opacity-60">
          {loading ? 'Opening the case…' : '🔍 Start the Investigation'}
        </button>
        <button onClick={() => toggleHowItWorks(true)} className="font-body text-sm text-dim underline-offset-4 hover:text-text hover:underline">
          How does NPC memory work?
        </button>
      </div>

      {error && (
        <p className="animate-rise mx-auto mt-6 max-w-lg rounded-2xl bg-bad/15 px-4 py-3 text-center font-mono text-sm text-bad">
          {error}
        </p>
      )}

      {showHowItWorks && <HowItWorks />}
    </div>
  )
}

function CastCard({ id, delay }: { id: NpcId; delay: number }) {
  const npc = NPCS[id]
  return (
    <div className="gcard animate-pop overflow-hidden text-center" style={{ animationDelay: `${delay}ms` }}>
      <div className="h-2" style={{ background: npc.colorVar }} />
      <div className="px-4 pb-5 pt-4">
        <div className="animate-float text-5xl" style={{ animationDelay: `${delay}ms` }}>
          {npc.emoji}
        </div>
        <div className="mt-2 font-display text-lg font-bold" style={{ color: npc.colorVar }}>
          {npc.name}
        </div>
        <div className="font-body text-sm font-semibold text-ink-dim">{roleHint(id)}</div>
      </div>
    </div>
  )
}

function roleHint(id: NpcId): string {
  return id === 'maya' ? 'has a secret to protect' : id === 'sam' ? 'the one being blamed' : 'turns secrets into gossip'
}
