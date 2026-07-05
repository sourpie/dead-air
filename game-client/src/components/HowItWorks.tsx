import { useGame } from '../state/gameStore'

const POINTS = [
  ['🧠', 'Each crewmate has their own memory', 'Oda, Vega, Lin, Rio and Nova each recall from a separate Cognee dataset — nobody knows everything, and the saboteur remembers only their cover story.'],
  ['🎲', 'Every run is a new case', 'A generator picks the culprit, motive, timeline and evidence per run, then seeds each crew member\'s memories accordingly.'],
  ['🧵', 'Memory travels the station', 'Crew pair up and talk between shifts. What they trade becomes real memories — overhear it, or watch it spread in the Memory Debugger.'],
  ['⚖️', 'Words are generated, truth is not', 'Cognee phrases every line from memories; the facts, clues and guardrails stay deterministic — the saboteur cannot be talked into confessing.'],
]

export function HowItWorks() {
  const { toggleHowItWorks } = useGame()
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-grape-2/80 p-4 backdrop-blur-sm"
      onClick={() => toggleHowItWorks(false)}
    >
      <div className="gcard animate-pop max-w-lg p-6" onClick={(e) => e.stopPropagation()}>
        <h2 className="font-display text-sm text-ink">HOW CREW MEMORY WORKS</h2>
        <ol className="mt-4 flex flex-col gap-3">
          {POINTS.map(([icon, title, body], i) => (
            <li key={i} className="flex gap-3">
              <span className="text-2xl">{icon}</span>
              <p className="font-body text-xl leading-tight text-ink-dim">
                <b className="text-ink">{title}.</b> {body}
              </p>
            </li>
          ))}
        </ol>
        <button onClick={() => toggleHowItWorks(false)} className="btn btn-pop mt-5 px-5 py-2.5 text-[10px]">
          GOT IT!
        </button>
      </div>
    </div>
  )
}
