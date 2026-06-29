// Display-only location metadata (canonical data lives in the backend /locations).
import type { LocationId, NpcId } from '../types'

export interface LocationDisplay {
  id: LocationId
  name: string
  blurb: string
  npc: NpcId
  emoji: string
}

export const LOCATIONS: LocationDisplay[] = [
  {
    id: 'bakery',
    name: "Maya's Bakery",
    blurb: 'The warm social heart of Maple Street. Flour in the air, tension underneath.',
    npc: 'maya',
    emoji: '🥖',
  },
  {
    id: 'garden',
    name: 'Community Garden',
    blurb: 'Vegetable plots and the broken-into shed at the far end.',
    npc: 'sam',
    emoji: '🪴',
  },
  {
    id: 'teastall',
    name: 'The Tea Stall',
    blurb: 'Where every rumour on the street is poured along with the chai.',
    npc: 'jules',
    emoji: '🫖',
  },
]
