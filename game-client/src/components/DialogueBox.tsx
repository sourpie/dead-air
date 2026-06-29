import { useGame } from '../state/gameStore'
import { EMOTION_LABEL, NPCS } from '../data/npcs'
import { ChoiceButton } from './ChoiceButton'

export function DialogueBox() {
  const { talk, loading, busyChoice, choose, selectedNpc } = useGame()
  if (!selectedNpc) return null
  const npc = NPCS[selectedNpc]

  return (
    <div className="flex min-h-[340px] flex-col gap-4">
      {loading || !talk ? (
        <div className="gcard flex flex-1 items-center justify-center px-6 py-12">
          <span className="animate-pulse font-body text-sm font-semibold text-ink-dim">
            {npc.name} is choosing their words…
          </span>
        </div>
      ) : (
        <>
          {/* Speech bubble */}
          <div key={talk.nodeId} className="gcard animate-pop relative px-6 py-5">
            <span
              className="absolute -top-2 left-8 h-4 w-4 rotate-45 bg-cream"
              style={{ borderTopLeftRadius: 2 }}
            />
            <div className="mb-2 flex items-center gap-2">
              <span className="text-2xl">{npc.emoji}</span>
              <span className="font-display text-base font-bold" style={{ color: npc.accent }}>
                {npc.name}
              </span>
              <span className="font-body text-xs font-semibold text-ink-dim">
                {EMOTION_LABEL[talk.emotion] ?? talk.emotion}
              </span>
              <SourceBadge source={talk.source} />
            </div>
            <p className="font-body text-xl font-semibold leading-relaxed text-ink">“{talk.npcLine}”</p>
          </div>

          {/* Choices */}
          <div className="flex flex-col gap-2">
            {talk.choices.length === 0 ? (
              <p className="rounded-2xl bg-white/6 px-4 py-3 font-body text-sm text-dim">
                💬 {npc.name.split(' ')[0]} has nothing more to say. Visit someone else, advance the day,
                or solve the case.
              </p>
            ) : (
              talk.choices.map((c, i) => (
                <ChoiceButton
                  key={c.id}
                  choice={c}
                  index={i}
                  busy={busyChoice === c.id}
                  disabled={busyChoice !== null}
                  onClick={() => choose(c.id)}
                />
              ))
            )}
          </div>
        </>
      )}
    </div>
  )
}

function SourceBadge({ source }: { source: 'cognee' | 'fallback' }) {
  const live = source === 'cognee'
  return (
    <span
      title={
        live
          ? 'Generated through Cognee recall from this neighbour’s memory'
          : 'Authored fallback line (Cognee unavailable or guardrail tripped)'
      }
      className="ml-auto rounded-full px-2 py-0.5 font-mono text-[10px] font-bold"
      style={{
        background: live ? 'rgba(67,209,122,0.16)' : 'rgba(255,201,77,0.18)',
        color: live ? '#1f9e54' : '#a9791a',
      }}
    >
      {live ? '● COGNEE' : '○ SCRIPT'}
    </span>
  )
}
