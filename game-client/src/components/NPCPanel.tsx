import { useGame } from '../state/gameStore'
import { NPCS } from '../data/npcs'
import { RelationshipMeter } from './RelationshipMeter'
import type { NpcId } from '../types'

export function NPCPanel({ npcId }: { npcId: NpcId }) {
  const { state } = useGame()
  const npc = NPCS[npcId]
  const rel = state?.relationships[npcId]

  return (
    <div className="gpanel flex flex-col gap-4 overflow-hidden p-5">
      <div className="flex items-center gap-3">
        <div
          className="animate-float flex h-16 w-16 items-center justify-center rounded-2xl text-4xl"
          style={{ background: `color-mix(in srgb, ${npc.colorVar} 22%, transparent)`, border: `2px solid ${npc.colorVar}` }}
        >
          {npc.emoji}
        </div>
        <div>
          <h3 className="font-display text-lg font-bold leading-tight" style={{ color: npc.colorVar }}>
            {npc.name}
          </h3>
          <p className="font-body text-xs font-semibold leading-snug text-dim">{npc.role}</p>
        </div>
      </div>
      {rel && <RelationshipMeter rel={rel} />}
    </div>
  )
}
