import type { LocationDisplay } from '../data/locations'
import { NPCS } from '../data/npcs'

export function LocationCard({
  loc,
  visited,
  onClick,
}: {
  loc: LocationDisplay
  visited: boolean
  onClick: () => void
}) {
  const npc = NPCS[loc.npc]
  return (
    <button
      onClick={onClick}
      style={{ ['--c' as string]: npc.colorVar }}
      className="gcard group relative flex flex-col gap-3 overflow-hidden p-6 text-left transition
                 hover:-translate-y-1.5 hover:shadow-[0_24px_40px_-18px_var(--c)]"
    >
      <div className="h-2.5 w-full rounded-full" style={{ background: npc.colorVar }} />
      <div className="flex items-start justify-between">
        <span className="animate-float text-5xl">{loc.emoji}</span>
        {visited && (
          <span className="chip rounded-full bg-good/15 px-2 py-1 font-bold text-good">✓ visited</span>
        )}
      </div>
      <h3 className="font-display text-xl font-bold text-ink">{loc.name}</h3>
      <p className="font-body text-sm leading-snug text-ink-dim">{loc.blurb}</p>
      <div className="mt-1 flex items-center gap-2 font-display text-sm font-bold" style={{ color: npc.colorVar }}>
        <span className="text-lg">{npc.emoji}</span>
        <span>Talk to {npc.name.split(' ')[0]}</span>
        <span className="ml-auto translate-x-0 opacity-0 transition group-hover:translate-x-1 group-hover:opacity-100">→</span>
      </div>
    </button>
  )
}
