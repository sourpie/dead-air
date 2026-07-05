// In-world conversation bubble: templated greeting, verb menu (the question
// buttons built server-side from the case), and the free-text "say anything"
// input whose replies come from the crewmate's Cognee memories.
import { useEffect, useState } from 'react'
import { useGame } from '../../state/gameStore'
import { EMOTION_LABEL, NPCS } from '../../data/npcs'
import type { LineSource, NpcId } from '../../types'
import { NPC_SPRITES } from './sprites'
import { VIEW_W } from './stationLayout'

const BUBBLE_W = 460

export function SpeechBubble({
  npc, pos, cam,
}: {
  npc: NpcId
  pos: { x: number; y: number }
  cam: { x: number; y: number }
}) {
  const { talk, loading, busyVerb, busySay, lastPlayerLine, ask, say, backToMap } = useGame()
  const [shown, setShown] = useState(0)
  const [draft, setDraft] = useState('')

  const line = talk?.npcLine ?? ''
  const done = shown >= line.length

  useEffect(() => {
    setShown(0)
    if (!line) return
    const id = window.setInterval(() => {
      setShown((s) => {
        if (s + 2 >= line.length) {
          window.clearInterval(id)
          return line.length
        }
        return s + 2
      })
    }, 18)
    return () => window.clearInterval(id)
  }, [line])

  const d = NPCS[npc]
  const rel = talk?.relationship
  const sprite = NPC_SPRITES[npc]

  const headY = pos.y - 66
  const bottomY = pos.y - 86
  let bx = pos.x + 26
  if (bx + BUBBLE_W > cam.x + VIEW_W - 16) bx = pos.x - 26 - BUBBLE_W
  bx = Math.max(cam.x + 16, Math.min(bx, cam.x + VIEW_W - 16 - BUBBLE_W))
  const H = 430
  const fy = Math.max(cam.y + 12, bottomY - H)

  return (
    <g>
      <polygon
        points={`${pos.x + (bx > pos.x ? 30 : -30)},${fy + H - 4} ${pos.x + (bx > pos.x ? 58 : -58)},${fy + H - 4} ${pos.x},${headY}`}
        fill="#e8ecf4"
      />
      <foreignObject x={bx} y={fy} width={BUBBLE_W} height={H} style={{ pointerEvents: 'auto', overflow: 'visible' }}>
        <div
          className="flex h-full flex-col justify-end"
          onClick={(e) => { e.stopPropagation(); if (!done) setShown(line.length) }}
        >
          <div className="gpanel p-3">
            <div className="flex items-center gap-2">
              <svg viewBox="0 0 48 64" width="30" height="40" shapeRendering="crispEdges" style={{ background: 'var(--color-grape)', border: `2px solid ${d.accent}` }}>
                {sprite.rows.flatMap((row, y) =>
                  [...row].map((ch, x) =>
                    ch === '.' ? null : (
                      <rect key={`${x}-${y}`} x={x * 4} y={y * 4} width="4" height="4" fill={sprite.palette[ch]} />
                    ),
                  ),
                )}
              </svg>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="chip px-1.5 py-0.5" style={{ background: d.accent, color: '#0b0f1c' }}>
                    {d.name.split(' ').pop()!.toUpperCase()}
                  </span>
                  {talk && <span className="font-body text-sm text-dim">{EMOTION_LABEL[talk.emotion] ?? talk.emotion}</span>}
                  {talk && <SourceBadge source={talk.source} />}
                </div>
                {rel && (
                  <div className="mt-1 flex items-center gap-3">
                    <MiniBar label="TRUST" value={rel.trust} color="var(--color-good)" />
                    <MiniBar label="SUS" value={rel.suspicion} color="var(--color-bad)" />
                  </div>
                )}
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); backToMap() }}
                className="btn btn-soft ml-auto shrink-0 px-2 py-1 text-[8px]"
              >
                ESC
              </button>
            </div>

            <div className="mt-2 border-t-2 border-line pt-1.5">
              {lastPlayerLine && (
                <p className="mb-1 font-body text-sm leading-tight text-dim">
                  <span className="chip text-gold" style={{ fontSize: 7 }}>YOU</span> “{lastPlayerLine}”
                </p>
              )}
              {loading || busySay || busyVerb || !talk ? (
                <p className="font-body text-lg text-dim">
                  {d.name.split(' ').pop()} is thinking<span className="blink">…</span>
                </p>
              ) : (
                <p className="font-body text-xl leading-snug text-text">
                  “{line.slice(0, shown)}”
                  {done && <span className="blink ml-1 text-gold">▼</span>}
                </p>
              )}
            </div>

            {/* the question menu (server-built verbs; confronts appear when earned) */}
            {talk && !loading && !busySay && !busyVerb && done && (
              <div className="mt-1.5 flex max-h-40 flex-col overflow-y-auto">
                {talk.verbs.map((v) => (
                  <button
                    key={v.id}
                    onClick={(e) => { e.stopPropagation(); void ask(v) }}
                    disabled={busyVerb !== null || busySay}
                    className="group flex w-full items-center gap-1.5 px-1.5 py-1 text-left font-body text-lg leading-tight text-text
                               hover:bg-cream hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <span className={`opacity-0 group-hover:opacity-100 ${v.verb === 'confront' ? 'text-coral' : 'text-gold'}`}>▶</span>
                    <span className={v.verb === 'confront' ? 'text-coral' : undefined}>
                      {busyVerb === v.id ? '…' : v.label}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* say anything — the reply comes from the crewmate's Cognee memories */}
            {talk && !loading && (
              <form
                className="mt-1.5 flex gap-1.5 border-t-2 border-line pt-1.5"
                onClick={(e) => e.stopPropagation()}
                onSubmit={(e) => {
                  e.preventDefault()
                  const text = draft.trim()
                  if (!text || busySay || busyVerb !== null) return
                  setDraft('')
                  void say(text)
                }}
              >
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  maxLength={240}
                  placeholder={`Or say anything to ${d.name.split(' ').pop()}…`}
                  disabled={busySay || busyVerb !== null}
                  className="min-w-0 flex-1 bg-grape px-2 py-1 font-body text-base text-text placeholder:text-dim focus:outline-none disabled:opacity-50"
                  style={{ border: '2px solid var(--color-line)' }}
                />
                <button
                  type="submit"
                  disabled={!draft.trim() || busySay || busyVerb !== null}
                  className="btn btn-gold shrink-0 px-2.5 py-1 text-[8px] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {busySay ? '…' : 'SAY'}
                </button>
              </form>
            )}
          </div>
        </div>
      </foreignObject>
    </g>
  )
}

export function MiniBar({ label, value, color }: { label: string; value: number; color: string }) {
  const cells = 10
  const filled = Math.round((Math.min(100, value) / 100) * cells)
  return (
    <div className="flex items-center gap-1">
      <span className="chip" style={{ color, fontSize: 7 }}>{label}</span>
      <div className="flex gap-px">
        {Array.from({ length: cells }).map((_, i) => (
          <span key={i} className="h-2 w-1" style={{ background: i < filled ? color : '#2b3350' }} />
        ))}
      </div>
    </div>
  )
}

const SOURCE_BADGE: Record<LineSource, { label: string; title: string; bg: string; fg: string }> = {
  cognee: {
    label: 'COGNEE', bg: '#4ade80', fg: '#0b0f1c',
    title: "Cognee recall generated this line from the crewmate's memory",
  },
  bedrock: {
    label: 'GLM-5', bg: '#6ee7f0', fg: '#0b0f1c',
    title: "Memories retrieved via Cognee; line written by GLM 5 on Amazon Bedrock",
  },
  script: {
    label: 'SCRIPT', bg: '#4f7df9', fg: '#0b0f1c',
    title: 'Zero-cost templated line',
  },
  fallback: {
    label: 'FALLBACK', bg: '#2b3350', fg: '#8b9bb4',
    title: 'Guardrail or network fallback — deterministic line served',
  },
}

export function SourceBadge({ source }: { source: LineSource }) {
  const b = SOURCE_BADGE[source] ?? SOURCE_BADGE.fallback
  return (
    <span title={b.title} className="chip px-1 py-0.5" style={{ background: b.bg, color: b.fg, fontSize: 7 }}>
      {b.label}
    </span>
  )
}
