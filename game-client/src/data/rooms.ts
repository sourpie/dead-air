// Display metadata for station rooms (canonical layout math lives in
// components/map/stationLayout.ts; backend truth in mystery.py).
import type { RoomId } from '../types'

export interface RoomInfo {
  id: RoomId
  name: string
  blurb: string
  emoji: string
}

export const ROOM_INFO: Record<RoomId, RoomInfo> = {
  cafeteria: { id: 'cafeteria', name: 'Cafeteria', blurb: 'The hub. The emergency button waits under glass.', emoji: '🍽' },
  medbay: { id: 'medbay', name: 'MedBay', blurb: "Lin's kingdom of scanners and sample trays.", emoji: '💉' },
  engine: { id: 'engine', name: 'Engine Room', blurb: 'Machinery, heat, and the scene of the crime.', emoji: '⚙' },
  storage: { id: 'storage', name: 'Storage', blurb: 'Crates, manifests, and places to hide things.', emoji: '📦' },
  comms: { id: 'comms', name: 'Comms', blurb: 'The station’s ears — and the door-log console.', emoji: '📡' },
  quarters: { id: 'quarters', name: 'Quarters', blurb: 'Bunks and lockers. Everyone claims they were here.', emoji: '🛏' },
}
