// Client-side crew simulation for one shift — a module-level singleton, NOT
// Zustand: positions churn at 60Hz and must never trigger React re-renders on
// their own. MapScene's rAF loop calls step(); NpcLayer reads positions().
//
// The backend owns truth (which encounters exist, what was said, clue grants);
// this module only animates the plan it was given. The shift clock starts at
// load() and pauses while the tab is hidden (rAF stops).
import type { NpcId, RoomId, ShiftPlan } from '../../types'
import { CREW_IDS } from '../../data/npcs'
import { meetingPoints, ROOM_CENTERS, roomSlot, routeBetween } from './stationLayout'

export type Facing = 'down' | 'up' | 'side'

export interface NpcSimState {
  x: number
  y: number
  room: RoomId
  facing: Facing
  dir: 1 | -1
  walking: boolean
  talking: boolean
  encounterId: string | null
  engaged: boolean // frozen because the player is talking to them
}

const NPC_SPEED = 190 // px/s — slower than the player (280), chases are winnable

interface Walker extends NpcSimState {
  path: Array<{ x: number; y: number }>
  pendingMoves: Array<{ atSec: number; toRoom: RoomId }>
}

let walkers = new Map<NpcId, Walker>()
let plan: ShiftPlan | null = null
let clockSec = 0

function slotFor(npc: NpcId, room: RoomId) {
  return roomSlot(room, CREW_IDS.indexOf(npc))
}

export const npcSim = {
  load(next: ShiftPlan) {
    plan = next
    clockSec = 0
    walkers = new Map()
    for (const npc of CREW_IDS) {
      const room = next.positions[npc]
      const p = slotFor(npc, room)
      walkers.set(npc, {
        x: p.x, y: p.y, room,
        facing: 'down', dir: 1, walking: false, talking: false,
        encounterId: null, engaged: false,
        path: [],
        pendingMoves: next.moves
          .filter((m) => m.npcId === npc)
          .map((m) => ({ atSec: m.atSec, toRoom: m.toRoom }))
          .sort((a, b) => a.atSec - b.atSec),
      })
    }
  },

  step(dt: number) {
    if (!plan) return
    clockSec += dt

    for (const [npc, w] of walkers) {
      // engaged = the player is talking to them: freeze in place and hold any
      // queued moves until released, so they visibly walk off afterwards
      if (w.engaged) {
        w.path = []
        w.walking = false
        continue
      }

      // due moves become paths
      while (w.pendingMoves.length && w.pendingMoves[0].atSec <= clockSec) {
        const move = w.pendingMoves.shift()!
        if (move.toRoom !== w.room) {
          const dest = slotFor(npc, move.toRoom)
          w.path = [...routeBetween(w.room, move.toRoom).slice(0, -1), dest]
          w.room = move.toRoom
        }
      }

      // encounter windows: mark talking + settle face-to-face
      w.talking = false
      w.encounterId = null
      for (const e of plan.encounters) {
        const i = e.npcs.indexOf(npc)
        if (i === -1) continue
        if (clockSec >= e.startSec && clockSec <= e.endSec) {
          w.encounterId = e.id
          if (w.path.length === 0 && w.room === e.room) {
            const pts = meetingPoints(e.room)
            const target = pts[i]
            if (Math.hypot(w.x - target.x, w.y - target.y) > 4) {
              w.path = [target]
            } else {
              w.talking = true
              w.facing = 'side'
              w.dir = i === 0 ? 1 : -1
            }
          }
        }
      }

      // walk the path
      if (w.path.length) {
        const t = w.path[0]
        const dx = t.x - w.x
        const dy = t.y - w.y
        const d = Math.hypot(dx, dy)
        const step = NPC_SPEED * dt
        if (d <= step) {
          w.x = t.x
          w.y = t.y
          w.path.shift()
        } else {
          w.x += (dx / d) * step
          w.y += (dy / d) * step
          if (Math.abs(dx) >= Math.abs(dy)) {
            w.facing = 'side'
            w.dir = dx > 0 ? 1 : -1
          } else {
            w.facing = dy > 0 ? 'down' : 'up'
          }
        }
        w.walking = w.path.length > 0
        if (!w.walking) w.facing = 'down'
      } else {
        w.walking = false
      }
    }
  },

  nowSec(): number {
    return clockSec
  },

  // Reactive encounters spawn mid-shift (a crewmate walking off to discuss
  // what the investigator just said). The backend marks them always-active;
  // we re-time them locally from the moment we learn about them and queue the
  // walk for both participants.
  syncEncounters(next: ShiftPlan) {
    if (!plan || next.shift !== plan.shift) return
    const known = new Set(plan.encounters.map((e) => e.id))
    for (const e of next.encounters) {
      if (known.has(e.id)) continue
      const start = Math.ceil(clockSec) + 6
      const timed = { ...e, startSec: start, endSec: start + 55 }
      plan.encounters.push(timed)
      for (const npc of e.npcs) {
        const w = walkers.get(npc)
        if (!w) continue
        w.pendingMoves.push({ atSec: clockSec, toRoom: e.room })
        w.pendingMoves.push({ atSec: timed.endSec, toRoom: next.positions[npc] })
        w.pendingMoves.sort((a, b) => a.atSec - b.atSec)
      }
    }
  },

  positions(): ReadonlyMap<NpcId, NpcSimState> {
    return walkers
  },

  get(npc: NpcId): NpcSimState | undefined {
    return walkers.get(npc)
  },

  // Active (window-open) encounters right now, with their meeting midpoint.
  activeEncounters(): Array<{ id: string; room: RoomId; npcs: [NpcId, NpcId]; x: number; y: number }> {
    if (!plan) return []
    return plan.encounters
      .filter((e) => clockSec >= e.startSec && clockSec <= e.endSec)
      .map((e) => {
        const c = ROOM_CENTERS[e.room]
        return { id: e.id, room: e.room, npcs: e.npcs, x: c.x, y: c.y }
      })
  },

  // Encounters whose window has closed (for "you missed it" notes).
  expiredEncounters(): string[] {
    if (!plan) return []
    return plan.encounters.filter((e) => clockSec > e.endSec).map((e) => e.id)
  },

  engage(npc: NpcId) {
    const w = walkers.get(npc)
    if (w) {
      w.engaged = true
      w.walking = false
      w.facing = 'down'
    }
  },

  release(npc: NpcId) {
    const w = walkers.get(npc)
    if (w) w.engaged = false
  },
}
