import { useGame } from '../state/gameStore'
import { CREW_IDS, NPCS } from '../data/npcs'
import { PixelSprite } from '../components/map/PixelSprite'
import { CREW_SPRITES } from '../components/map/sprites'

export function ResultPage() {
  const { state, startGame } = useGame()
  const r = state?.result
  if (!r) return null
  const won = r.wasSaboteur

  return (
    <div className="relative mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-12">
      {won && <Confetti />}

      {/* the ejection: accused bean tumbling across the stars */}
      <div className="relative z-10 mb-5 h-28 overflow-hidden bg-grape-2" style={{ border: '3px solid var(--color-line)' }}>
        <div className="eject-drift absolute top-8">
          <svg viewBox="0 0 60 80" width="45" height="60" shapeRendering="crispEdges">
            <g transform="translate(30,76)">
              <PixelSprite sprite={CREW_SPRITES[r.accused].down[0]} px={4} />
            </g>
          </svg>
        </div>
        {Array.from({ length: 24 }).map((_, i) => (
          <span key={i} className="absolute block h-0.5 w-0.5 bg-dim"
            style={{ left: `${(i * 41) % 100}%`, top: `${(i * 53) % 100}%` }} />
        ))}
        <p className="absolute inset-x-0 bottom-1 text-center font-body text-xl text-teal">
          {r.narrative.headline}
        </p>
      </div>

      <div className="animate-pop gcard relative z-10 overflow-hidden text-center">
        <div className="px-6 pb-8 pt-7">
          <p className="chip" style={{ color: won ? 'var(--color-good)' : 'var(--color-bad)' }}>
            {won ? '** SABOTEUR EJECTED **' : '** WRONG AIRLOCK **'}
          </p>

          <div className="mt-3 flex justify-center gap-2">
            {Array.from({ length: r.maxStars }).map((_, i) => (
              <span
                key={i}
                className={'animate-star font-display text-4xl ' + (i < r.stars ? 'text-gold' : 'text-card-line')}
                style={{ animationDelay: `${200 + i * 180}ms`, textShadow: i < r.stars ? '3px 3px 0 #0b0f1c' : 'none' }}
              >
                ★
              </span>
            ))}
          </div>

          <div className="mt-4 text-5xl">{r.rank.icon}</div>
          <h1 className="mt-2 font-display text-lg text-ink sm:text-xl">{r.rank.title.toUpperCase()}</h1>
          <p className="mx-auto mt-2 max-w-md font-body text-xl leading-tight text-ink-dim">{r.rank.blurb}</p>

          <div className="mt-5 inline-flex items-center gap-3 bg-grape-2 px-5 py-2">
            <span className="chip text-gold">SCORE</span>
            <span className="font-display text-xl text-cream">{String(r.score).padStart(4, '0')}</span>
          </div>

          <div className="mt-6 grid grid-cols-3 gap-3">
            <Stat label="Clues" value={`${r.cluesFound}/${r.totalClues}`} good={r.cluesFound >= 4} />
            <Stat label="Verdict" value={won ? 'Correct' : 'Wrong'} good={won} />
            <Stat label="Cracked" value={r.flustered > 0 ? `×${r.flustered}` : 'Never'} good={r.flustered > 0} />
          </div>
        </div>
      </div>

      {/* the story */}
      <div className="animate-rise relative z-10 mt-5 gpanel p-5" style={{ animationDelay: '160ms' }}>
        <h3 className="chip mb-1 text-gold">The truth</h3>
        <p className="font-body text-xl leading-snug text-text">{r.narrative.body}</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
          {CREW_IDS.map((id) => {
            const rel = state?.relationships[id]
            return (
              <div key={id} className="bg-white/6 p-3 text-center" style={{ outline: id === r.saboteur ? '2px solid var(--color-coral)' : undefined }}>
                <div className="text-2xl">{NPCS[id].emoji}</div>
                <div className="font-display text-[10px] font-bold" style={{ color: NPCS[id].colorVar }}>
                  {NPCS[id].name.split(' ').pop()}
                </div>
                <div className="mt-1 font-mono text-[10px] text-dim">
                  ♥{rel?.trust} · ⚠{rel?.suspicion}
                </div>
                {id === r.saboteur && <div className="chip mt-1 text-coral">SABOTEUR</div>}
              </div>
            )
          })}
        </div>
      </div>

      <div className="animate-rise relative z-10 mt-6 flex justify-center" style={{ animationDelay: '240ms' }}>
        <button onClick={() => startGame()} className="btn btn-pop px-8 py-4 text-xs">
          <span className="blink">▶</span> NEW MYSTERY
        </button>
      </div>
    </div>
  )
}

function Stat({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div className="bg-grape-2 p-3">
      <div className="chip text-dim">{label}</div>
      <div className="mt-1 font-display text-xs" style={{ color: good ? 'var(--color-good)' : 'var(--color-bad)' }}>
        {value.toUpperCase()}
      </div>
    </div>
  )
}

function Confetti() {
  const bits = Array.from({ length: 28 })
  const colors = ['#d92f2f', '#5fd346', '#f5d442', '#38c3e8', '#9a5ce0', '#6ee7f0']
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {bits.map((_, i) => (
        <span
          key={i}
          className="absolute top-0 block h-2.5 w-2.5"
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
