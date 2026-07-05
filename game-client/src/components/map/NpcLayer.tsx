// Per-frame crew rendering: walking beans with facing + 2-frame walk cycle,
// name labels, "!" badges for unvisited crew, and the chat indicator over an
// active encounter. Re-renders every animation frame via MapScene's simTick.
import { NPCS } from '../../data/npcs'
import type { NpcId } from '../../types'
import { npcSim } from './npcSim'
import { PixelSprite } from './PixelSprite'
import { CREW_SPRITES } from './sprites'

export function NpcLayer({
  visited, selectedNpc, frame, onNpcClick,
}: {
  visited: NpcId[]
  selectedNpc: NpcId | null
  frame: number
  onNpcClick: (npc: NpcId) => void
}) {
  const walkers = npcSim.positions()
  const encounters = npcSim.activeEncounters()

  return (
    <g>
      {[...walkers.entries()].map(([id, w]) => {
        const d = NPCS[id]
        const set = CREW_SPRITES[id][w.facing]
        const sprite = w.walking ? set[1 + frame] : set[0]
        const fresh = !visited.includes(id) && selectedNpc !== id
        return (
          <g
            key={id}
            transform={`translate(${Math.round(w.x)},${Math.round(w.y)})`}
            onClick={(e) => { e.stopPropagation(); onNpcClick(id) }}
            className="cursor-pointer"
          >
            <rect x="-16" y="0" width="32" height="5" fill="#04060f" opacity="0.5" />
            <g transform={`scale(${w.facing === 'side' ? w.dir : 1}, 1)`}>
              <PixelSprite sprite={sprite} />
            </g>
            {fresh && !w.talking && (
              /* transform attribute on its own group: a CSS transform animation
                 on the same element would REPLACE the translate, not compose */
              <g transform="translate(0,-76)">
                <g className="badge-pulse">
                  <rect x="-11" y="-11" width="22" height="22" fill="#0b0f1c" />
                  <rect x="-8" y="-8" width="16" height="16" fill="#f5d442" />
                  <text x="0" y="5" textAnchor="middle" fontSize="12" fill="#0b0f1c" style={{ fontFamily: 'var(--font-display)' }}>
                    !
                  </text>
                </g>
              </g>
            )}
            <text x="0" y="20" textAnchor="middle" fontSize="9" fill={d.accent} style={{ fontFamily: 'var(--font-display)' }}>
              {d.name.split(' ').pop()!.toUpperCase()}
            </text>
          </g>
        )
      })}

      {/* chat indicator above each active encounter's midpoint */}
      {encounters.map((e) => (
        <ChatIndicator key={e.id} x={e.x} y={e.y - 110} />
      ))}
    </g>
  )
}

function ChatIndicator({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x},${y})`} pointerEvents="none">
      <g className="badge-pulse">
        <rect x="-30" y="-22" width="60" height="34" fill="#e8ecf4" />
        <rect x="-27" y="-19" width="54" height="28" fill="#0b0f1c" />
        <polygon points="-6,12 8,12 -2,24" fill="#e8ecf4" />
        {[-14, 0, 14].map((dx, i) => (
          <rect key={i} x={dx - 3} y="-8" width="6" height="6" fill="#6ee7f0"
            className="chat-dot" style={{ animationDelay: `${i * 0.35}s` }} />
        ))}
      </g>
    </g>
  )
}
