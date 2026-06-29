import { useGame } from '../state/gameStore'
import { LOCATIONS } from '../data/locations'
import { LocationCard } from './LocationCard'

export function MapView() {
  const { selectNpc, visited } = useGame()
  return (
    <div className="animate-rise">
      <h2 className="font-display text-2xl font-bold text-text">🏘️ Maple Street</h2>
      <p className="mb-5 font-body text-dim">Knock on a door — every conversation can turn up a clue.</p>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {LOCATIONS.map((loc) => (
          <LocationCard
            key={loc.id}
            loc={loc}
            visited={visited.includes(loc.npc)}
            onClick={() => selectNpc(loc.npc)}
          />
        ))}
      </div>
    </div>
  )
}
