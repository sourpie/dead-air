import { useGame } from '../state/gameStore'
import { NPCS } from '../data/npcs'
import type { NpcId } from '../types'

export function ResultPage() {
  const { state, startGame } = useGame()
  const r = state?.result
  if (!r) return null
  const won = r.solvedCorrectly

  return (
    <div className="relative mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-12">
      {won && <Confetti />}

      <div className="animate-pop gcard relative z-10 overflow-hidden text-center">
        <div className="px-6 pb-8 pt-7">
          <p className="chip font-bold" style={{ color: won ? 'var(--color-good)' : 'var(--color-bad)' }}>
            {won ? 'Case cracked!' : 'The trail went cold'}
          </p>

          {/* Stars */}
          <div className="mt-3 flex justify-center gap-2">
            {Array.from({ length: r.maxStars }).map((_, i) => (
              <span
                key={i}
                className={'animate-star text-5xl ' + (i < r.stars ? '' : 'opacity-20 grayscale')}
                style={{ animationDelay: `${200 + i * 180}ms` }}
              >
                ⭐
              </span>
            ))}
          </div>

          <div className="mt-4 text-5xl">{r.rank.icon}</div>
          <h1 className="mt-1 font-display text-4xl font-bold text-ink">{r.rank.title}</h1>
          <p className="mx-auto mt-2 max-w-md font-body text-base text-ink-dim">{r.rank.blurb}</p>

          <div className="mt-5 inline-flex items-center gap-2 rounded-full bg-grape px-5 py-2">
            <span className="chip text-gold">Score</span>
            <span className="font-display text-2xl font-bold text-text">{r.score}</span>
          </div>

          {/* Scorecard */}
          <div className="mt-6 grid grid-cols-3 gap-3">
            <Stat label="Clues" value={`${r.cluesFound}/${r.totalClues}`} good={r.cluesFound >= 4} />
            <Stat label="Verdict" value={won ? 'Correct' : 'Wrong'} good={won} />
            <Stat label="Promise" value={r.betrayed ? 'Broken' : 'Kept'} good={!r.betrayed} />
          </div>

          {!won && (
            <p className="mt-5 rounded-2xl bg-grape px-4 py-3 font-body text-sm text-text/85">
              <b className="text-gold">The truth:</b> {r.correctText}
            </p>
          )}
        </div>
      </div>

      {/* Story outcome + final standing */}
      <div className="animate-rise relative z-10 mt-5 gpanel p-5" style={{ animationDelay: '160ms' }}>
        <Block label="The mystery" text={r.narrative.mystery} />
        <Block label="The neighbourhood" text={r.narrative.relationship} />
        <div className="mt-4 grid grid-cols-3 gap-3">
          {(Object.keys(NPCS) as NpcId[]).map((id) => {
            const rel = state?.relationships[id]
            return (
              <div key={id} className="rounded-2xl bg-white/6 p-3 text-center">
                <div className="text-2xl">{NPCS[id].emoji}</div>
                <div className="font-display text-xs font-bold" style={{ color: NPCS[id].colorVar }}>
                  {NPCS[id].name.split(' ')[0]}
                </div>
                <div className="mt-1 font-mono text-[11px] text-dim">
                  ♥{rel?.trust} · ⚠{rel?.suspicion}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="animate-rise relative z-10 mt-6 flex justify-center" style={{ animationDelay: '240ms' }}>
        <button onClick={() => startGame(false)} className="btn btn-pop px-9 py-4 text-xl">
          🔁 Play again
        </button>
      </div>
    </div>
  )
}

function Stat({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div className="rounded-2xl bg-grape p-3">
      <div className="chip text-dim">{label}</div>
      <div className="font-display text-lg font-bold" style={{ color: good ? 'var(--color-good)' : 'var(--color-bad)' }}>
        {value}
      </div>
    </div>
  )
}

function Block({ label, text }: { label: string; text: string }) {
  return (
    <div className="mb-3">
      <h3 className="chip mb-1 text-gold">{label}</h3>
      <p className="font-body text-[15px] leading-relaxed text-text">{text}</p>
    </div>
  )
}

function Confetti() {
  const bits = Array.from({ length: 28 })
  const colors = ['#ff6b5e', '#25cfb0', '#ffc94d', '#b06bff', '#e85fc0']
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {bits.map((_, i) => (
        <span
          key={i}
          className="absolute top-0 block h-2.5 w-2.5 rounded-sm"
          style={{
            left: `${(i * 37) % 100}%`,
            background: colors[i % colors.length],
            animation: `confetti-fall ${2.4 + (i % 5) * 0.4}s linear ${(i % 7) * 0.18}s infinite`,
          }}
        />
      ))}
    </div>
  )
}
