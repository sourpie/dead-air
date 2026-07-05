// Station K-7 as a top-down pixel world (2560×1440). WASD/arrows or click to
// move; the camera follows; the crew walk their shift schedule (npcSim) and
// pair up to talk — get close to overhear. Pure React/SVG/CSS — no engine.
import { useEffect, useMemo, useRef, useState } from 'react'
import { useGame } from '../../state/gameStore'
import { NPCS } from '../../data/npcs'
import { ROOM_INFO } from '../../data/rooms'
import type { NpcId, RoomId } from '../../types'
import { npcSim } from './npcSim'
import { NpcLayer } from './NpcLayer'
import { PixelSprite } from './PixelSprite'
import { SpeechBubble } from './SpeechBubble'
import { StationWorld, Prompt } from './StationWorld'
import { PLAYER_SPRITES } from './sprites'
import {
  blocked, PLAYER_START, ROOM_CENTERS, roomAt, sceneSpots, STATIC_SPOTS,
  VIEW_H, VIEW_W, WORLD_H, WORLD_W, type Spot,
} from './stationLayout'

const SPEED = 280
const EARSHOT = 240
const NPC_TALK_RADIUS = 95

type Facing = 'down' | 'up' | 'side'

interface Popup {
  title: string
  text: string
  doorLog?: Array<{ time: string; npc: string; kind: string; room: string; corrupted: boolean }>
}

function nearestRoom(x: number, y: number): RoomId {
  const inRoom = roomAt(x, y)
  if (inRoom) return inRoom
  let best: RoomId = 'cafeteria'
  let bd = Infinity
  for (const [id, c] of Object.entries(ROOM_CENTERS) as Array<[RoomId, { x: number; y: number }]>) {
    const d = Math.hypot(x - c.x, y - c.y)
    if (d < bd) { bd = d; best = id }
  }
  return best
}

export function MapScene() {
  const {
    state, selectedNpc, selectNpc, backToMap, examine, visited,
    overhearEncounter, noteMissed,
  } = useGame()

  const [pos, setPos] = useState(PLAYER_START)
  const [cam, setCam] = useState({ x: PLAYER_START.x - VIEW_W / 2, y: PLAYER_START.y - VIEW_H / 2 })
  const [facing, setFacing] = useState<Facing>('down')
  const [dir, setDir] = useState(1)
  const [walking, setWalking] = useState(false)
  const [frame, setFrame] = useState(0)
  const [, setSimTick] = useState(0) // bumped per frame so NpcLayer re-renders with the sim
  const [popup, setPopup] = useState<Popup | null>(null)

  const posRef = useRef({ ...PLAYER_START })
  const keysRef = useRef({ left: false, right: false, up: false, down: false })
  const targetRef = useRef<{ x: number; y: number; spot?: Spot; npc?: NpcId } | null>(null)
  const selectedRef = useRef<NpcId | null>(null)
  const notedMissRef = useRef<Set<string>>(new Set())
  selectedRef.current = selectedNpc

  const spots = useMemo<Spot[]>(() => {
    const scene = state ? sceneSpots(state.sabotage.room) : []
    return [...STATIC_SPOTS, ...scene]
  }, [state?.sabotage.room]) // eslint-disable-line react-hooks/exhaustive-deps

  const spotsRef = useRef(spots)
  spotsRef.current = spots

  const activateSpot = (spot: Spot) => {
    if (selectedRef.current) backToMap()
    void examine(spot.id).then((r) => r && setPopup(r as Popup))
  }

  const tryTalk = (npc: NpcId) => {
    const w = npcSim.get(npc)
    if (!w) return
    const p = posRef.current
    if (Math.hypot(p.x - w.x, p.y - w.y) <= NPC_TALK_RADIUS) {
      setPopup(null)
      void selectNpc(npc)
    } else {
      targetRef.current = { x: w.x, y: w.y + 50, npc }
      if (selectedRef.current) backToMap()
    }
  }

  const clickSpot = (spot: Spot) => {
    const p = posRef.current
    if (Math.hypot(p.x - spot.x, p.y - spot.y) <= spot.r) activateSpot(spot)
    else targetRef.current = { x: spot.x, y: spot.y + 46, spot }
  }

  // ── main loop: player + crew sim + camera + earshot ─────────────────
  useEffect(() => {
    let raf = 0
    let last = performance.now()
    const tick = (now: number) => {
      const dt = Math.min(50, now - last) / 1000
      last = now
      const p = posRef.current

      // crew simulation
      npcSim.step(dt)
      setSimTick((t) => t + 1)

      // eavesdrop check: standing in the encounter's room always counts as
      // earshot (rooms are bigger than the radius); otherwise use distance
      // to the talkers, which also covers listening from the doorway.
      const st = useGame.getState().state
      if (st) {
        const playerRoom = roomAt(p.x, p.y)
        for (const e of npcSim.activeEncounters()) {
          if (st.overheard.includes(e.id)) continue
          const inRoom = playerRoom === e.room
          if (inRoom || Math.hypot(p.x - e.x, p.y - e.y) <= EARSHOT) {
            void overhearEncounter(e.id, e.room, playerRoom ?? nearestRoom(p.x, p.y))
          }
        }
        // missed-encounter notes
        for (const id of npcSim.expiredEncounters()) {
          if (st.overheard.includes(id) || notedMissRef.current.has(id)) continue
          notedMissRef.current.add(id)
          const enc = st.shiftPlan.encounters.find((x) => x.id === id)
          if (enc) {
            const [a, b] = enc.npcs
            noteMissed(
              `${NPCS[a].name.split(' ').pop()!.toUpperCase()} and ${NPCS[b].name.split(' ').pop()!.toUpperCase()} talked in the ${ROOM_INFO[enc.room].name.toUpperCase()} — you were too far away.`,
            )
          }
        }
      }

      // player movement
      let vx = 0, vy = 0
      const k = keysRef.current
      if (k.left) vx -= 1
      if (k.right) vx += 1
      if (k.up) vy -= 1
      if (k.down) vy += 1
      if (vx || vy) targetRef.current = null
      else if (targetRef.current) {
        const t = targetRef.current
        const dx = t.x - p.x, dy = t.y - p.y
        const d = Math.hypot(dx, dy)
        if (d <= 8) {
          const { spot, npc } = t
          targetRef.current = null
          if (spot) activateSpot(spot)
          if (npc) tryTalk(npc)
        } else {
          vx = dx / d
          vy = dy / d
        }
      }
      let moving = false
      if (vx || vy) {
        const n = Math.hypot(vx, vy)
        const nx = p.x + (vx / n) * SPEED * dt
        const ny = p.y + (vy / n) * SPEED * dt
        let x = p.x, y = p.y
        if (!blocked(nx, y)) x = nx
        if (!blocked(x, ny)) y = ny
        moving = x !== p.x || y !== p.y
        if (!moving && targetRef.current) targetRef.current = null // wedged
        if (moving) {
          if (Math.abs(vx) >= Math.abs(vy)) {
            setFacing('side')
            setDir(vx > 0 ? 1 : -1)
          } else setFacing(vy > 0 ? 'down' : 'up')
          if (selectedRef.current) {
            const w = npcSim.get(selectedRef.current)
            if (w && Math.hypot(x - w.x, y - w.y) > 150) backToMap()
          }
          posRef.current = { x, y }
          setPos({ x, y })
          setCam({
            x: Math.max(0, Math.min(WORLD_W - VIEW_W, Math.round(x - VIEW_W / 2))),
            y: Math.max(0, Math.min(WORLD_H - VIEW_H, Math.round(y - VIEW_H / 2))),
          })
        }
      }
      setWalking((w) => (w === moving ? w : moving))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const id = window.setInterval(() => setFrame((f) => f ^ 1), 140)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) return
      const k = keysRef.current
      if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') k.left = true
      else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') k.right = true
      else if (e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') k.up = true
      else if (e.key === 'ArrowDown' || e.key === 's' || e.key === 'S') k.down = true
      else if (e.key === 'e' || e.key === 'E' || e.key === 'Enter') {
        const p = posRef.current
        // nearest crewmate in range beats spots
        let bestNpc: NpcId | null = null
        let bd = Infinity
        for (const [id, w] of npcSim.positions()) {
          const d = Math.hypot(p.x - w.x, p.y - w.y)
          if (d <= NPC_TALK_RADIUS && d < bd) { bd = d; bestNpc = id }
        }
        if (bestNpc) {
          setPopup(null)
          void selectNpc(bestNpc)
        } else {
          const near = nearestSpot(p, spotsRef.current)
          if (near) activateSpot(near)
        }
      } else if (e.key === 'Escape') {
        if (selectedRef.current) backToMap()
        setPopup(null)
      } else return
      e.preventDefault()
    }
    const up = (e: KeyboardEvent) => {
      const k = keysRef.current
      if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') k.left = false
      if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') k.right = false
      if (e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') k.up = false
      if (e.key === 'ArrowDown' || e.key === 's' || e.key === 'S') k.down = false
    }
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    return () => {
      window.removeEventListener('keydown', down)
      window.removeEventListener('keyup', up)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const worldRef = useRef<SVGGElement>(null)
  const groundClick = (e: React.MouseEvent) => {
    const g = worldRef.current
    if (!g) return
    const m = g.getScreenCTM()
    if (!m) return
    const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse())
    targetRef.current = { x: pt.x, y: pt.y }
    if (selectedRef.current) backToMap()
    setPopup(null)
  }

  const examinedSet = useMemo(() => new Set(state?.examined ?? []), [state?.examined])

  const world = useMemo(
    () => (
      <StationWorld
        sabotageRoom={state?.sabotage.room ?? 'engine'}
        spots={spots}
        examined={examinedSet}
        onSpot={clickSpot}
      />
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [state?.sabotage.room, spots, (state?.examined ?? []).join(',')],
  )

  const near = nearestSpot(pos, spots)
  const nearNpc = nearestCrew(pos)
  const selPos = selectedNpc ? npcSim.get(selectedNpc) : null

  return (
    <div className="absolute inset-0">
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        preserveAspectRatio="xMidYMid slice"
        className="h-full w-full"
        role="img"
        aria-label="Station K-7"
        shapeRendering="crispEdges"
      >
        {/* groundClick lives on the world group: floor tiles paint OVER the
            old transparent catch-rect, so clicks must be caught by bubbling
            (spot/NPC handlers stopPropagation to keep their own behavior). */}
        <g ref={worldRef} style={{ transform: `translate(${-cam.x}px, ${-cam.y}px)` }} onClick={groundClick}>
          {world}
          {/* NpcLayer re-renders naturally with each simTick state bump — no
              key-remount: destroying the nodes every frame kills click events
              mid-gesture and resets CSS animations. */}
          <NpcLayer
            visited={visited}
            selectedNpc={selectedNpc}
            frame={frame}
            onNpcClick={tryTalk}
          />
          <Player pos={pos} facing={facing} dir={dir} walking={walking} frame={frame} />
          {!selectedNpc && !popup && nearNpc && (
            <Prompt x={pos.x} y={pos.y} label={`TALK — ${NPCS[nearNpc].name.split(' ').pop()!.toUpperCase()}`} />
          )}
          {!selectedNpc && !popup && !nearNpc && near && (
            <Prompt x={pos.x} y={pos.y} label={near.label} />
          )}
          {selectedNpc && selPos && (
            <SpeechBubble npc={selectedNpc} pos={{ x: selPos.x, y: selPos.y }} cam={cam} />
          )}
        </g>
      </svg>

      {popup && (
        <div className="gcard animate-pop absolute bottom-16 left-1/2 z-20 w-[min(34rem,92vw)] -translate-x-1/2 p-4">
          <p className="chip font-bold text-magenta">▲ {popup.title.toUpperCase()}</p>
          <p className="mt-2 font-body text-xl leading-tight text-ink">{popup.text}</p>
          {popup.doorLog && (
            <div className="mt-2 max-h-48 overflow-y-auto border-2 border-ink bg-grape-2 p-2">
              {popup.doorLog.map((r, i) => (
                <p key={i} className={`font-body text-base leading-tight ${r.corrupted ? 'text-bad' : 'text-teal'}`}>
                  {r.time} · {r.npc} {r.kind} {r.room}
                  {r.corrupted && ' ⚠ CORRUPTED'}
                </p>
              ))}
            </div>
          )}
          <button onClick={() => setPopup(null)} className="btn btn-gold mt-3 px-3 py-1.5 text-[9px]">
            CLOSE
          </button>
        </div>
      )}
    </div>
  )
}

function nearestSpot(p: { x: number; y: number }, spots: Spot[]): Spot | null {
  let best: Spot | null = null
  let bd = Infinity
  for (const s of spots) {
    const d = Math.hypot(p.x - s.x, p.y - s.y)
    if (d <= s.r && d < bd) {
      bd = d
      best = s
    }
  }
  return best
}

function nearestCrew(p: { x: number; y: number }): NpcId | null {
  let best: NpcId | null = null
  let bd = Infinity
  for (const [id, w] of npcSim.positions()) {
    const d = Math.hypot(p.x - w.x, p.y - w.y)
    if (d <= NPC_TALK_RADIUS && d < bd) { bd = d; best = id }
  }
  return best
}

function Player({
  pos, facing, dir, walking, frame,
}: {
  pos: { x: number; y: number }
  facing: Facing
  dir: number
  walking: boolean
  frame: number
}) {
  const set = PLAYER_SPRITES[facing]
  const sprite = walking ? set[1 + frame] : set[0]
  return (
    <g transform={`translate(${pos.x},${pos.y})`} pointerEvents="none">
      <rect x="-16" y="0" width="32" height="5" fill="#04060f" opacity="0.5" />
      <g transform={`scale(${facing === 'side' ? dir : 1}, 1)`}>
        <PixelSprite sprite={sprite} />
      </g>
    </g>
  )
}
