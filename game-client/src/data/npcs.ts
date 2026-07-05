// Display-only crew metadata (canonical data lives in the backend).
import type { NpcId, RoomId } from '../types'

export interface NpcDisplay {
  id: NpcId
  name: string
  role: string
  emoji: string
  room: RoomId // day post
  colorVar: string
  accent: string
}

export const NPCS: Record<NpcId, NpcDisplay> = {
  oda: {
    id: 'oda',
    name: 'Captain Oda',
    role: 'Command · by-the-book, hates speculation',
    emoji: '🎖',
    room: 'cafeteria',
    colorVar: 'var(--color-oda)',
    accent: '#d92f2f',
  },
  vega: {
    id: 'vega',
    name: 'Engineer Vega',
    role: 'Systems · blunt, paranoid, blamed for everything',
    emoji: '🔧',
    room: 'engine',
    colorVar: 'var(--color-vega)',
    accent: '#ef7d57',
  },
  lin: {
    id: 'lin',
    name: 'Medic Lin',
    role: 'MedBay · warm insomniac, notices everything',
    emoji: '💉',
    room: 'medbay',
    colorVar: 'var(--color-lin)',
    accent: '#5fd346',
  },
  rio: {
    id: 'rio',
    name: 'Comms Officer Rio',
    role: 'Comms · the rumour mill, embellishes freely',
    emoji: '📡',
    room: 'comms',
    colorVar: 'var(--color-rio)',
    accent: '#38c3e8',
  },
  nova: {
    id: 'nova',
    name: 'Science Chief Nova',
    role: 'Research · ambitious, guarded, passed over',
    emoji: '🧪',
    room: 'storage',
    colorVar: 'var(--color-nova)',
    accent: '#9a5ce0',
  },
}

export const CREW_IDS = Object.keys(NPCS) as NpcId[]

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
