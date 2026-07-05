// Station K-7 geometry: room floor plates, corridors, walkable whitelist,
// examine spots, and the waypoint routes NPCs walk between rooms.
// The collision model is INVERTED vs Maple Street: a station is mostly wall,
// so we whitelist walkable rects instead of blacklisting solid ones.
import type { NpcId, RoomId } from '../../types'

export const WORLD_W = 2560
export const WORLD_H = 1440
export const VIEW_W = 1280
export const VIEW_H = 760

export interface Rect { x: number; y: number; w: number; h: number }

/* ── rooms (floor plates) ────────────────────────────────────────────── */

export const ROOM_RECTS: Record<RoomId, Rect> = {
  cafeteria: { x: 960, y: 240, w: 640, h: 400 },
  medbay: { x: 220, y: 300, w: 420, h: 340 },
  engine: { x: 200, y: 880, w: 480, h: 380 },
  storage: { x: 1020, y: 900, w: 480, h: 360 },
  comms: { x: 1960, y: 800, w: 440, h: 340 },
  quarters: { x: 1900, y: 240, w: 460, h: 340 },
}

// Main horizontal hall + one spur per room door.
export const HALL: Rect = { x: 300, y: 690, w: 2000, h: 90 }
export const SPURS: Rect[] = [
  { x: 1240, y: 630, w: 80, h: 70 },   // cafeteria
  { x: 400, y: 630, w: 80, h: 70 },    // medbay
  { x: 400, y: 770, w: 80, h: 120 },   // engine
  { x: 1220, y: 770, w: 80, h: 140 },  // storage
  { x: 2140, y: 770, w: 80, h: 40 },   // comms
  { x: 2080, y: 570, w: 80, h: 130 },  // quarters
]

export const WALKABLE: Rect[] = [...Object.values(ROOM_RECTS), HALL, ...SPURS]

// Room centers double as NPC posts and waypoint anchors.
export const ROOM_CENTERS: Record<RoomId, { x: number; y: number }> = {
  cafeteria: { x: 1280, y: 440 },
  medbay: { x: 430, y: 470 },
  engine: { x: 440, y: 1070 },
  storage: { x: 1260, y: 1080 },
  comms: { x: 2180, y: 970 },
  quarters: { x: 2120, y: 410 },
}

// Where each room's spur meets the hall centerline (y=735).
const HALL_Y = 735
const DOOR_X: Record<RoomId, number> = {
  cafeteria: 1280,
  medbay: 440,
  engine: 440,
  storage: 1260,
  comms: 2180,
  quarters: 2120,
}

/* ── collision (feet box fully inside walkable space) ────────────────── */

function pointIn(px: number, py: number): boolean {
  for (const r of WALKABLE) {
    if (px >= r.x && px <= r.x + r.w && py >= r.y && py <= r.y + r.h) return true
  }
  return false
}

export function blocked(x: number, y: number): boolean {
  // feet box, matching the old MapScene contract
  const fx = x - 10, fy = y - 10, fw = 20, fh = 10
  return !(
    pointIn(fx, fy) && pointIn(fx + fw, fy) &&
    pointIn(fx, fy + fh) && pointIn(fx + fw, fy + fh)
  )
}

export function roomAt(x: number, y: number): RoomId | null {
  for (const [id, r] of Object.entries(ROOM_RECTS) as Array<[RoomId, Rect]>) {
    if (x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h) return id
  }
  return null
}

/* ── NPC pathing: room center → door → hall → door → room center ─────── */

export function routeBetween(from: RoomId, to: RoomId): Array<{ x: number; y: number }> {
  if (from === to) return [ROOM_CENTERS[to]]
  return [
    { x: DOOR_X[from], y: HALL_Y },
    { x: DOOR_X[to], y: HALL_Y },
    ROOM_CENTERS[to],
  ]
}

// Standing slots inside a room so crew don't stack on one point.
const SLOT_OFFSETS = [
  { x: -70, y: -20 }, { x: 70, y: -20 }, { x: 0, y: 60 },
  { x: -110, y: 60 }, { x: 110, y: 60 },
]

export function roomSlot(room: RoomId, npcIndex: number): { x: number; y: number } {
  const c = ROOM_CENTERS[room]
  const o = SLOT_OFFSETS[npcIndex % SLOT_OFFSETS.length]
  return { x: c.x + o.x, y: c.y + o.y }
}

// Face-to-face meeting points for an encounter in a room.
export function meetingPoints(room: RoomId): [{ x: number; y: number }, { x: number; y: number }] {
  const c = ROOM_CENTERS[room]
  return [{ x: c.x - 34, y: c.y + 20 }, { x: c.x + 34, y: c.y + 20 }]
}

/* ── interactable spots ──────────────────────────────────────────────── */

export type SpotKind = 'npc' | 'examine' | 'flavor'
export interface Spot {
  id: string
  x: number
  y: number
  r: number
  kind: SpotKind
  npc?: NpcId
  label: string
}

// Positions for backend examine spots (ids must match case.examineSpots),
// except the two crime-scene spots whose room varies per run — those are
// placed at runtime via sceneSpots(sabotageRoom).
export const STATIC_SPOTS: Spot[] = [
  { id: 'ops_console', x: 2320, y: 900, r: 70, kind: 'examine', label: 'DOOR LOG' },
  { id: 'med_scanner', x: 300, y: 400, r: 60, kind: 'examine', label: 'SCAN' },
  { id: 'cargo_manifest', x: 1400, y: 1000, r: 60, kind: 'examine', label: 'READ' },
  { id: 'emergency_button', x: 1280, y: 360, r: 70, kind: 'examine', label: 'EXAMINE' },
]

export function sceneSpots(sabotageRoom: RoomId): Spot[] {
  const c = ROOM_CENTERS[sabotageRoom]
  return [
    { id: 'sabotage_panel', x: c.x - 130, y: c.y - 60, r: 65, kind: 'examine', label: 'INSPECT' },
    { id: 'scene_sweep', x: c.x + 130, y: c.y - 50, r: 65, kind: 'examine', label: 'SEARCH' },
  ]
}

export const PLAYER_START = { x: 1280, y: 560 } // cafeteria, by the shuttle hatch
