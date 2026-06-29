import { useGame } from '../state/gameStore'
import { NPCS } from '../data/npcs'

export function DayBeat() {
  const { state, dismissDayBeat } = useGame()
  const betrayed = state?.flags?.playerToldJules

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-grape-2/80 p-4 backdrop-blur-sm">
      <div className="gcard animate-pop max-w-md p-8 text-center">
        <p className="chip font-bold text-violet">🌙 Night falls on Maple Street</p>
        <h2 className="mt-1 font-display text-4xl font-bold text-ink">Day 2</h2>

        {betrayed ? (
          <>
            <TravelThread />
            <p className="mt-4 font-body text-lg leading-relaxed text-ink">
              The secret you told <b style={{ color: NPCS.jules.accent }}>Jules</b> raced down the
              street overnight… and reached <b style={{ color: NPCS.maya.accent }}>Maya</b>.
            </p>
            <p className="mt-1 font-body text-sm font-semibold text-bad">She knows you talked.</p>
          </>
        ) : (
          <>
            <div className="my-5 text-5xl">☕️🌤️</div>
            <p className="font-body text-lg leading-relaxed text-ink">
              A quiet morning. You kept <b style={{ color: NPCS.maya.accent }}>Maya's</b> secret —
              and she hasn't forgotten that either.
            </p>
          </>
        )}

        <button onClick={dismissDayBeat} className="btn btn-pop mt-6 px-7 py-3 text-lg">
          Continue →
        </button>
      </div>
    </div>
  )
}

/* Jules → Maya, the rumour travelling along the thread */
function TravelThread() {
  return (
    <div className="relative my-5 flex items-center justify-between px-6">
      <Node emoji={NPCS.jules.emoji} color={NPCS.jules.accent} label="Jules" />
      <svg className="mx-2 h-10 flex-1" viewBox="0 0 200 40" preserveAspectRatio="none" aria-hidden>
        <path
          d="M4 20 C 60 -6, 140 46, 196 20"
          fill="none"
          stroke="var(--color-bad)"
          strokeWidth="3"
          strokeLinecap="round"
          className="thread-travel"
        />
      </svg>
      <Node emoji={NPCS.maya.emoji} color={NPCS.maya.accent} label="Maya" />
    </div>
  )
}

function Node({ emoji, color, label }: { emoji: string; color: string; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className="flex h-12 w-12 items-center justify-center rounded-full text-2xl ring-4"
        style={{ background: '#fff', ['--tw-ring-color' as string]: color }}
      >
        {emoji}
      </div>
      <span className="font-display text-xs font-bold" style={{ color }}>
        {label}
      </span>
    </div>
  )
}
