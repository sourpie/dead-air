import { useGame } from '../state/gameStore'

const POINTS = [
  ['🧠', 'Each neighbour has their own memory', 'Maya, Sam, and Jules each recall from a separate Cognee dataset — they do not all know the same things.'],
  ['✍️', 'Your actions are written down', 'Promises, secrets, and gossip become real memories stored against specific neighbours.'],
  ['🧵', 'Memory travels the street', 'Tell Jules a secret and it spreads through the neighbourhood — reaching Maya by the next day.'],
  ['⚖️', 'They hold you accountable', 'On Day 2 the neighbours react to what they remember. Open the Memory Debugger to see who knows what.'],
]

export function HowItWorks() {
  const { toggleHowItWorks } = useGame()
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-grape-2/80 p-4 backdrop-blur-sm"
      onClick={() => toggleHowItWorks(false)}
    >
      <div className="gcard animate-pop max-w-lg p-7" onClick={(e) => e.stopPropagation()}>
        <h2 className="font-display text-2xl font-bold text-ink">How NPC memory works 🧵</h2>
        <ol className="mt-4 flex flex-col gap-3">
          {POINTS.map(([icon, title, body], i) => (
            <li key={i} className="flex gap-3">
              <span className="text-2xl">{icon}</span>
              <p className="font-body text-[15px] leading-relaxed text-ink-dim">
                <b className="font-bold text-ink">{title}.</b> {body}
              </p>
            </li>
          ))}
        </ol>
        <button onClick={() => toggleHowItWorks(false)} className="btn btn-pop mt-6 px-5 py-2.5 text-base">
          Got it!
        </button>
      </div>
    </div>
  )
}
