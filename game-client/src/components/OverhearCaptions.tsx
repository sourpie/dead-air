// Letterboxed caption bar for overheard crew conversations — lines reveal one
// at a time with speaker chips in crew colors. Fetched once per encounter; the
// clue was already granted server-side, this is the flavor.
import { useEffect, useState } from 'react'
import { useGame } from '../state/gameStore'
import { NPCS } from '../data/npcs'
import { ROOM_INFO } from '../data/rooms'
import { SourceBadge } from './map/SpeechBubble'
import type { LineSource } from '../types'

const LINE_MS = 2400
const LINGER_MS = 3600

export function OverhearCaptions() {
  const playback = useGame((s) => s.overhearPlayback)
  const pending = useGame((s) => s.overhearPending)
  const dismiss = useGame((s) => s.dismissOverhear)
  const [shownCount, setShownCount] = useState(1)

  useEffect(() => {
    setShownCount(1)
    if (!playback) return
    const timers: number[] = []
    for (let i = 2; i <= playback.lines.length; i++) {
      timers.push(window.setTimeout(() => setShownCount(i), (i - 1) * LINE_MS))
    }
    timers.push(window.setTimeout(dismiss, playback.lines.length * LINE_MS + LINGER_MS))
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [playback, dismiss])

  // In earshot, exchange still generating — show the bar immediately so the
  // player knows to stay close instead of walking off.
  if (!playback && pending) {
    return (
      <div className="pointer-events-none fixed inset-x-0 bottom-16 z-40 flex justify-center px-4">
        <div
          className="animate-sheet w-full max-w-2xl bg-grape-2/92 px-4 py-3"
          style={{ borderTop: '3px solid var(--color-line)', borderBottom: '3px solid var(--color-line)' }}
        >
          <span className="chip text-teal">
            ◉ You lean in to listen — {ROOM_INFO[pending.room].name.toUpperCase()}
            <span className="blink">…</span>
          </span>
        </div>
      </div>
    )
  }

  if (!playback) return null

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-16 z-40 flex justify-center px-4">
      <div
        className="animate-sheet pointer-events-auto w-full max-w-2xl bg-grape-2/92 px-4 py-3"
        style={{ borderTop: '3px solid var(--color-line)', borderBottom: '3px solid var(--color-line)' }}
        onClick={dismiss}
      >
        <div className="mb-1.5 flex items-center gap-2">
          <span className="chip text-teal">◉ OVERHEARD — {ROOM_INFO[playback.room].name.toUpperCase()}</span>
          <SourceBadge source={playback.source as LineSource} />
          <span className="chip ml-auto text-dim">CLICK TO DISMISS</span>
        </div>
        {playback.lines.slice(0, shownCount).map((l, i) => (
          <p key={i} className="animate-rise mt-0.5 font-body text-xl leading-snug text-text">
            <span className="chip mr-2 px-1.5 py-0.5" style={{ background: NPCS[l.speaker].accent, color: '#0b0f1c' }}>
              {NPCS[l.speaker].name.split(' ').pop()!.toUpperCase()}
            </span>
            <span className="italic">“{l.text}”</span>
          </p>
        ))}
      </div>
    </div>
  )
}
