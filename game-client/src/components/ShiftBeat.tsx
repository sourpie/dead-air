// Shift-change interstitial: announces the new shift and reminds the player
// that the crew keeps talking whether or not anyone is listening.
import { useGame } from '../state/gameStore'

const SHIFT_FLAVOR = [
  'The morning shuttle has docked. The crew scatters to their posts.',
  'Ration trays clatter. Conversations drop to whispers when you pass.',
  'The corridor lights dim to evening amber. Alliances are forming.',
  'Last shift. Whatever the crew still knows, they trade it now — press the button before the day ends.',
]

export function ShiftBeat() {
  const { state, dismissShiftBeat } = useGame()
  if (!state) return null
  const idx = Math.min(state.shift, SHIFT_FLAVOR.length - 1)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-grape-2/85 backdrop-blur-sm" onClick={dismissShiftBeat}>
      <div className="gcard animate-pop w-[min(30rem,90vw)] p-6 text-center" onClick={(e) => e.stopPropagation()}>
        <p className="chip text-violet">— SHIFT CHANGE —</p>
        <h2 className="mt-3 font-display text-lg text-ink">
          SHIFT {state.shift + 1}/{state.maxShifts}
        </h2>
        <p className="mt-1 font-display text-[10px] text-ink-dim">{state.shiftName}</p>
        <p className="mt-4 font-body text-xl leading-snug text-ink">{SHIFT_FLAVOR[idx]}</p>
        <p className="mt-2 font-body text-lg text-ink-dim">
          Watch for the <span className="text-teal">chat bubbles</span> — walk close to eavesdrop.
        </p>
        <button onClick={dismissShiftBeat} className="btn btn-gold mt-5 px-5 py-2.5 text-[10px]">
          BEGIN SHIFT ▸
        </button>
      </div>
    </div>
  )
}
