// Display-only NPC metadata (canonical data lives in the backend).
import type { LocationId, NpcId } from '../types'

export interface NpcDisplay {
  id: NpcId
  name: string
  role: string
  emoji: string
  location: LocationId
  colorVar: string // CSS var name from the theme
  accent: string // tailwind-ish text color class via inline style
}

export const NPCS: Record<NpcId, NpcDisplay> = {
  maya: {
    id: 'maya',
    name: "Maya D'Souza",
    role: 'Bakery owner · warm, protective, anxious',
    emoji: '🧁',
    location: 'bakery',
    colorVar: 'var(--color-maya)',
    accent: '#ff8a4c',
  },
  sam: {
    id: 'sam',
    name: "Sam D'Souza",
    role: "Maya's brother · nervous, defensive, misunderstood",
    emoji: '🌱',
    location: 'garden',
    colorVar: 'var(--color-sam)',
    accent: '#36c5e0',
  },
  jules: {
    id: 'jules',
    name: 'Jules',
    role: 'Tea-stall regular · curious, charming, exaggerates',
    emoji: '🍵',
    location: 'teastall',
    colorVar: 'var(--color-jules)',
    accent: '#e85fc0',
  },
}

export const EMOTION_LABEL: Record<string, string> = {
  neutral: '😐 neutral',
  warm: '😊 warm',
  anxious: '😟 anxious',
  defensive: '😠 defensive',
  hurt: '💔 hurt',
  angry: '😡 angry',
  relieved: '😌 relieved',
  excited: '🤩 excited',
  smug: '😏 smug',
  guarded: '🙅 guarded',
  sad: '😢 sad',
}
