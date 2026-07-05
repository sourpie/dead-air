// The static station world (memoized by MapScene): space backdrop, hull, room
// floor plates with seams and signs, per-room props, and examine-spot markers.
// Pure rect clusters — same pixel technique as the Maple Street build.
import { ROOM_INFO } from '../../data/rooms'
import type { RoomId } from '../../types'
import {
  HALL, ROOM_RECTS, SPURS, WORLD_H, WORLD_W, type Rect, type Spot,
} from './stationLayout'

const ROOM_ACCENT: Record<RoomId, string> = {
  cafeteria: '#f5d442',
  medbay: '#5fd346',
  engine: '#e04a3f',
  storage: '#ef7d57',
  comms: '#38c3e8',
  quarters: '#9a5ce0',
}

export function StationWorld({
  sabotageRoom, spots, examined, onSpot,
}: {
  sabotageRoom: RoomId
  spots: Spot[]
  examined: Set<string>
  onSpot: (s: Spot) => void
}) {
  return (
    <g>
      <SpaceBackdrop />

      {/* corridors first, rooms on top */}
      <FloorPlate r={HALL} />
      {SPURS.map((s, i) => <FloorPlate key={i} r={s} />)}

      {(Object.entries(ROOM_RECTS) as Array<[RoomId, Rect]>).map(([id, r]) => (
        <Room key={id} id={id} r={r} accent={ROOM_ACCENT[id]} isScene={id === sabotageRoom} />
      ))}

      {/* per-room props (flavor rect clusters) */}
      <CafeteriaProps />
      <MedbayProps />
      <EngineProps sabotaged={sabotageRoom === 'engine'} />
      <StorageProps />
      <CommsProps />
      <QuartersProps />

      {/* examine spot markers */}
      {spots.filter((s) => s.kind === 'examine').map((s) => (
        <g
          key={s.id}
          transform={`translate(${s.x},${s.y})`}
          onClick={(e) => { e.stopPropagation(); onSpot(s) }}
          className="cursor-pointer hover:brightness-125"
        >
          <rect x="-14" y="-14" width="28" height="28" fill="#0b0f1c" />
          <rect x="-11" y="-11" width="22" height="22" fill={examined.has(s.id) ? '#2b3350' : '#f5d442'} />
          <text x="0" y="6" textAnchor="middle" fontSize="13" fill={examined.has(s.id) ? '#8b9bb4' : '#0b0f1c'}
            style={{ fontFamily: 'var(--font-display)' }}>
            {examined.has(s.id) ? '·' : '?'}
          </text>
          {!examined.has(s.id) && (
            <g className="badge-pulse">
              <rect x="-2" y="-30" width="4" height="8" fill="#f5d442" />
            </g>
          )}
        </g>
      ))}
    </g>
  )
}

function SpaceBackdrop() {
  return (
    <g>
      <rect x="0" y="0" width={WORLD_W} height={WORLD_H} fill="#04060f" />
      {Array.from({ length: 120 }).map((_, i) => (
        <rect
          key={i}
          x={(i * 211) % WORLD_W}
          y={(i * 137) % WORLD_H}
          width={i % 7 === 0 ? 3 : 2}
          height={i % 7 === 0 ? 3 : 2}
          fill={i % 3 === 0 ? '#e8ecf4' : '#4c5876'}
          className={i % 5 === 0 ? 'star-twinkle' : undefined}
          style={i % 5 === 0 ? { animationDelay: `${(i % 9) * 0.4}s` } : undefined}
        />
      ))}
      {/* a slow drifting planet */}
      <g className="space-drift">
        <rect x="120" y="1280" width="90" height="60" fill="#1c2333" />
        <rect x="135" y="1265" width="60" height="90" fill="#1c2333" />
        <rect x="150" y="1295" width="30" height="16" fill="#2b3350" />
      </g>
    </g>
  )
}

function FloorPlate({ r }: { r: Rect }) {
  return (
    <g>
      <rect x={r.x - 12} y={r.y - 12} width={r.w + 24} height={r.h + 24} fill="#2b3350" />
      <rect x={r.x} y={r.y} width={r.w} height={r.h} fill="#3a4466" />
      {/* floor seams */}
      {Array.from({ length: Math.floor(r.w / 64) }).map((_, i) => (
        <rect key={`v${i}`} x={r.x + (i + 1) * 64} y={r.y} width="2" height={r.h} fill="#262b44" />
      ))}
      {Array.from({ length: Math.floor(r.h / 64) }).map((_, i) => (
        <rect key={`h${i}`} x={r.x} y={r.y + (i + 1) * 64} width={r.w} height="2" fill="#262b44" />
      ))}
    </g>
  )
}

function Room({ id, r, accent, isScene }: { id: RoomId; r: Rect; accent: string; isScene: boolean }) {
  return (
    <g>
      <FloorPlate r={r} />
      {/* wall band with accent edge */}
      <rect x={r.x} y={r.y} width={r.w} height="10" fill="#141a2e" />
      <rect x={r.x} y={r.y + 10} width={r.w} height="3" fill={accent} opacity="0.7" />
      <Sign x={r.x + r.w / 2} y={r.y + 34} w={ROOM_INFO[id].name.length * 12 + 40} text={ROOM_INFO[id].name.toUpperCase()} color={accent} />
      {isScene && (
        <>
          {/* hazard tape across the crime scene */}
          {[r.y + 60, r.y + r.h - 40].map((ty, k) => (
            <g key={k}>
              <rect x={r.x + 16} y={ty} width={r.w - 32} height="10" fill="#f5d442" />
              {Array.from({ length: Math.floor((r.w - 32) / 26) }).map((_, i) => (
                <rect key={i} x={r.x + 20 + i * 26} y={ty + 2} width="10" height="6" fill="#0b0f1c" />
              ))}
            </g>
          ))}
          <Sign x={r.x + r.w / 2} y={r.y + 78} w={190} text="!! CRIME SCENE !!" color="#e04a3f" />
        </>
      )}
    </g>
  )
}

/* ── per-room props ──────────────────────────────────────────────────── */

function CafeteriaProps() {
  const r = ROOM_RECTS.cafeteria
  const cx = r.x + r.w / 2
  return (
    <g pointerEvents="none">
      {/* round table (pixel octagon) + emergency button */}
      <rect x={cx - 70} y={r.y + 90} width="140" height="70" fill="#2b3350" />
      <rect x={cx - 84} y={r.y + 104} width="168" height="42" fill="#2b3350" />
      <rect x={cx - 60} y={r.y + 100} width="120" height="50" fill="#38405e" />
      <rect x={cx - 14} y={r.y + 112} width="28" height="22" fill="#e04a3f" />
      <rect x={cx - 8} y={r.y + 106} width="16" height="8" fill="#f06a5f" />
      {/* vending machine */}
      <rect x={r.x + 30} y={r.y + 60} width="44" height="76" fill="#1c2333" />
      <rect x={r.x + 36} y={r.y + 68} width="32" height="40" fill="#38c3e8" opacity="0.5" />
      <rect x={r.x + 36} y={r.y + 114} width="32" height="10" fill="#0b0f1c" />
    </g>
  )
}

function MedbayProps() {
  const r = ROOM_RECTS.medbay
  return (
    <g pointerEvents="none">
      <rect x={r.x + 40} y={r.y + 70} width="90" height="40" fill="#e8ecf4" />
      <rect x={r.x + 48} y={r.y + 62} width="74" height="10" fill="#5fd346" opacity="0.6" />
      <rect x={r.x + 250} y={r.y + 70} width="60" height="90" fill="#1c2333" />
      <rect x={r.x + 258} y={r.y + 80} width="44" height="50" fill="#5fd346" opacity="0.35" />
    </g>
  )
}

function EngineProps({ sabotaged }: { sabotaged: boolean }) {
  const r = ROOM_RECTS.engine
  return (
    <g pointerEvents="none">
      <rect x={r.x + 40} y={r.y + 80} width="120" height="120" fill="#1c2333" />
      <rect x={r.x + 56} y={r.y + 96} width="88" height="88" fill={sabotaged ? '#e04a3f' : '#38405e'} opacity={sabotaged ? 0.8 : 1} />
      {sabotaged && (
        <>
          <rect x={r.x + 70} y={r.y + 60} width="8" height="8" fill="#8b9bb4" className="steam" />
          <rect x={r.x + 96} y={r.y + 52} width="6" height="6" fill="#8b9bb4" className="steam" style={{ animationDelay: '0.8s' }} />
        </>
      )}
      {[0, 1, 2].map((i) => (
        <rect key={i} x={r.x + 200 + i * 40} y={r.y + 100} width="24" height="60" fill="#2b3350" />
      ))}
    </g>
  )
}

function StorageProps() {
  const r = ROOM_RECTS.storage
  return (
    <g pointerEvents="none">
      {[[30, 60], [90, 60], [30, 130], [330, 70], [390, 100]].map(([dx, dy], i) => (
        <g key={i}>
          <rect x={r.x + dx} y={r.y + dy} width="52" height="46" fill="#4a3b28" />
          <rect x={r.x + dx + 4} y={r.y + dy + 4} width="44" height="10" fill="#6b5638" />
          <rect x={r.x + dx + 20} y={r.y + dy + 18} width="12" height="12" fill="#f5d442" opacity="0.6" />
        </g>
      ))}
    </g>
  )
}

function CommsProps() {
  const r = ROOM_RECTS.comms
  return (
    <g pointerEvents="none">
      <rect x={r.x + 260} y={r.y + 60} width="120" height="50" fill="#1c2333" />
      <rect x={r.x + 268} y={r.y + 68} width="104" height="26" fill="#38c3e8" opacity="0.4" />
      {[0, 1, 2, 3].map((i) => (
        <rect key={i} x={r.x + 272 + i * 26} y={r.y + 72} width="16" height={8 + (i % 3) * 6} fill="#6ee7f0" className="chat-dot" style={{ animationDelay: `${i * 0.3}s` }} />
      ))}
      <rect x={r.x + 60} y={r.y + 70} width="10" height="70" fill="#2b3350" />
      <rect x={r.x + 40} y={r.y + 56} width="50" height="12" fill="#2b3350" />
    </g>
  )
}

function QuartersProps() {
  const r = ROOM_RECTS.quarters
  return (
    <g pointerEvents="none">
      {[0, 1, 2].map((i) => (
        <g key={i}>
          <rect x={r.x + 40 + i * 120} y={r.y + 70} width="80" height="40" fill="#2b3350" />
          <rect x={r.x + 44 + i * 120} y={r.y + 74} width="30" height="14" fill="#8b9bb4" />
        </g>
      ))}
      <rect x={r.x + 40} y={r.y + 200} width="200" height="30" fill="#1c2333" />
    </g>
  )
}

/* ── shared bits ─────────────────────────────────────────────────────── */

export function Sign({ x, y, w, text, color }: { x: number; y: number; w: number; text: string; color: string }) {
  return (
    <g transform={`translate(${x},${y})`} pointerEvents="none">
      <rect x={-w / 2 - 3} y="-17" width={w + 6} height="34" fill={color} />
      <rect x={-w / 2} y="-14" width={w} height="28" fill="#0b0f1c" />
      <text x="0" y="5" textAnchor="middle" fontSize="11" fill={color} style={{ fontFamily: 'var(--font-display)' }}>
        {text}
      </text>
    </g>
  )
}

export function Prompt({ x, y, label }: { x: number; y: number; label: string }) {
  const w = label.length * 9 + 46
  return (
    <g transform={`translate(${x},${y - 92})`} pointerEvents="none">
      <g className="badge-pulse">
        <rect x={-w / 2} y="-14" width={w} height="26" fill="#0b0f1c" />
        <rect x={-w / 2 + 3} y="-11" width={w - 6} height="20" fill="#f5d442" />
        <text x="0" y="4" textAnchor="middle" fontSize="10" fill="#0b0f1c" style={{ fontFamily: 'var(--font-display)' }}>
          [E] {label}
        </text>
      </g>
    </g>
  )
}
