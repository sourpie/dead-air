import { useState } from 'react'
import { useGame } from '../state/gameStore'

export function SolvePage() {
  const { state, catalog, solve, backFromSolve, loading } = useGame()
  const [picked, setPicked] = useState<string | null>(null)
  const found = state?.cluesFound.length ?? 0
  const total = catalog?.clues.length ?? 5
  const theories = catalog?.theories ?? []

  return (
    <div className="mx-auto min-h-screen max-w-3xl px-6 py-12">
      <button onClick={backFromSolve} className="chip mb-4 text-dim hover:text-text">
        ← keep investigating
      </button>

      <div className="animate-rise text-center">
        <div className="text-5xl">⚖️</div>
        <h1 className="mt-2 font-display text-4xl font-bold text-text sm:text-5xl">Solve the Case</h1>
        <p className="mt-2 font-body text-lg text-dim">
          You've gathered <b className="text-gold">{found}</b> of {total} clues. So… what really
          happened to the shed?
        </p>
      </div>

      <div className="animate-rise mt-8 flex flex-col gap-3" style={{ animationDelay: '80ms' }}>
        {theories.map((t, i) => {
          const sel = picked === t.id
          return (
            <button
              key={t.id}
              onClick={() => setPicked(t.id)}
              className={
                'flex items-start gap-4 rounded-2xl border-2 p-4 text-left transition ' +
                (sel
                  ? 'gcard scale-[1.01] border-coral'
                  : 'gpanel border-transparent hover:border-line')
              }
            >
              <span
                className={
                  'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-display text-sm font-bold ' +
                  (sel ? 'bg-coral text-white' : 'bg-white/10 text-dim')
                }
              >
                {String.fromCharCode(65 + i)}
              </span>
              <span className={'font-body text-[15px] leading-snug ' + (sel ? 'text-ink' : 'text-text')}>
                {t.text}
              </span>
            </button>
          )
        })}
      </div>

      <div className="animate-rise mt-8 flex justify-center" style={{ animationDelay: '160ms' }}>
        <button
          onClick={() => picked && solve(picked)}
          disabled={!picked || loading}
          className="btn btn-gold px-10 py-4 text-xl disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? 'Making the call…' : '🔨 Make the Accusation'}
        </button>
      </div>
    </div>
  )
}
