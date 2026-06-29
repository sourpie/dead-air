import type { Relationship } from '../types'

function Bar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between">
        <span className="chip text-dim">{label}</span>
        <span className="font-mono text-[11px] font-bold" style={{ color }}>
          {value}
        </span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${Math.max(0, Math.min(100, value))}%`,
            background: color,
            boxShadow: `0 0 12px ${color}88`,
          }}
        />
      </div>
    </div>
  )
}

export function RelationshipMeter({ rel }: { rel: Relationship }) {
  return (
    <div className="flex flex-col gap-2.5">
      <Bar label="♥ Trust" value={rel.trust} color="var(--color-good)" />
      <Bar label="⚠ Suspicion" value={rel.suspicion} color="var(--color-bad)" />
    </div>
  )
}
