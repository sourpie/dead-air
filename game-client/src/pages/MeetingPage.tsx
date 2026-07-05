// The emergency meeting: five beans around the table, pick who to eject.
import { useState } from 'react'
import { useGame } from '../state/gameStore'
import { CREW_IDS, NPCS } from '../data/npcs'
import { BeanPortrait } from '../components/map/PixelSprite'
import { MiniBar } from '../components/map/SpeechBubble'
import { NPC_SPRITES } from '../components/map/sprites'
import type { NpcId } from '../types'

export function MeetingPage() {
  const { state, backFromMeeting, accuse, loading } = useGame()
  const [picked, setPicked] = useState<NpcId | null>(null)
  if (!state) return null
  const found = state.cluesFound.length
  const total = state.clueCatalog.length || 7

  return (
    <div className="alarm-pulse fixed inset-0 overflow-y-auto">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-10 text-center">
        <button onClick={backFromMeeting} className="mb-4 self-start font-body text-lg text-dim hover:text-text">
          ◀ keep investigating
        </button>

        <p className="chip text-coral">⚠ EMERGENCY MEETING ⚠</p>
        <h1 className="mt-3 font-display text-xl text-text sm:text-2xl" style={{ textShadow: '3px 3px 0 #e04a3f' }}>
          WHO IS THE SABOTEUR?
        </h1>
        <p className="mt-3 font-body text-xl text-dim">
          Evidence in hand: <span className="text-gold">{found}/{total} clues</span>. The one you
          eject boards the shuttle — there is no second vote.
        </p>

        {/* the table */}
        <div className="gpanel relative mx-auto mt-8 w-full max-w-2xl p-6">
          <div className="mx-auto mb-6 flex h-24 w-56 items-center justify-center bg-grape" style={{ border: '3px solid var(--color-line)' }}>
            <div className="flex h-12 w-12 items-center justify-center bg-coral" style={{ border: '3px solid #0b0f1c' }}>
              <span className="font-display text-[9px] text-grape-2">SOS</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            {CREW_IDS.map((id) => {
              const d = NPCS[id]
              const rel = state.relationships[id]
              const sel = picked === id
              return (
                <button
                  key={id}
                  onClick={() => setPicked(sel ? null : id)}
                  className={`flex flex-col items-center gap-1.5 p-2 ${sel ? 'bg-cream' : 'hover:bg-grape'}`}
                  style={{ border: sel ? '3px solid var(--color-gold)' : '3px solid transparent' }}
                >
                  <BeanPortrait sprite={NPC_SPRITES[id]} size={56} accent={d.accent} />
                  <span className="chip" style={{ color: sel ? '#0b0f1c' : d.accent }}>
                    {d.name.split(' ').pop()!.toUpperCase()}
                  </span>
                  <MiniBar label="SUS" value={rel.suspicion} color="var(--color-bad)" />
                </button>
              )
            })}
          </div>
        </div>

        <div className="mt-7 flex min-h-16 flex-col items-center gap-3">
          {picked ? (
            <>
              <p className="font-body text-2xl text-text">
                Eject <span style={{ color: NPCS[picked].accent }}>{NPCS[picked].name}</span>?
              </p>
              <button
                onClick={() => void accuse(picked)}
                disabled={loading}
                className="btn btn-pop px-8 py-4 text-xs disabled:opacity-60"
              >
                {loading ? 'EJECTING…' : `⚠ EJECT ${NPCS[picked].name.split(' ').pop()!.toUpperCase()}`}
              </button>
            </>
          ) : (
            <p className="font-body text-xl text-dim">Select a crewmate.</p>
          )}
        </div>
      </div>
    </div>
  )
}
