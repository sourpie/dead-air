import { useGame } from '../state/gameStore'
import { HowItWorks } from '../components/HowItWorks'
import { CREW_IDS, NPCS } from '../data/npcs'
import { NPC_SPRITES } from '../components/map/sprites'
import type { NpcId } from '../types'

const STEPS = [
  ['🗣', 'INTERROGATE', 'Question 5 crew members. Every answer comes from what they actually remember.'],
  ['👂', 'EAVESDROP', 'The crew talk to each other on the map. Get close to overhear — from afar you only see THAT they talked.'],
  ['?', 'COLLECT EVIDENCE', 'Search rooms, pull the door log, catch statements that contradict the facts.'],
  ['⚠', 'CALL THE MEETING', 'Eject the saboteur. A new culprit, motive and alibi every run.'],
] as const

export function StartPage() {
  const { startGame, loading, error, toggleHowItWorks, showHowItWorks } = useGame()

  return (
    <div className="mx-auto min-h-screen max-w-4xl px-4 py-10 text-center sm:px-6">
      {/* title */}
      <div className="animate-rise">
        <p className="chip text-teal">— INCIDENT REPORT K7/099 —</p>
        <h1 className="mt-5 font-display text-3xl leading-relaxed text-cream sm:text-5xl" style={{ textShadow: '4px 4px 0 #e04a3f, 8px 8px 0 #0b0f1c' }}>
          DEAD<span className="text-coral">//</span><span className="text-gold">AIR</span>
        </h1>
        <p className="mt-2 font-display text-[10px] text-dim">SABOTAGE ON STATION K-7</p>
        <p className="mx-auto mt-5 max-w-xl font-body text-2xl leading-tight text-dim">
          Overnight, someone cut a life system. Five crew. One saboteur. Interrogate them —
          but careful: <span className="text-gold">they remember every word you say.</span>
        </p>
      </div>

      {/* mission */}
      <div className="animate-rise gcard mx-auto mt-7 max-w-2xl p-4" style={{ animationDelay: '80ms' }}>
        <p className="chip text-magenta">** YOUR MISSION **</p>
        <p className="mt-1.5 font-body text-xl leading-tight text-ink">
          Gather <b>7 clues</b> in 4 shifts → break the saboteur's alibi → eject the right crewmate
          → earn <b>★★★</b>
        </p>
      </div>

      {/* how to play */}
      <div className="animate-rise mt-7 grid gap-3 text-left sm:grid-cols-2" style={{ animationDelay: '140ms' }}>
        {STEPS.map(([icon, title, body], i) => (
          <div key={i} className="gpanel flex gap-3 p-3.5">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center bg-gold font-display text-sm text-ink">
              {icon}
            </span>
            <div>
              <h3 className="chip text-gold">{i + 1}. {title}</h3>
              <p className="mt-1 font-body text-lg leading-tight text-dim">{body}</p>
            </div>
          </div>
        ))}
      </div>

      {/* the crew */}
      <div className="animate-rise mt-8" style={{ animationDelay: '200ms' }}>
        <p className="chip mb-3 text-dim">— THE CREW OF K-7 —</p>
        <div className="flex flex-wrap items-end justify-center gap-5 sm:gap-8">
          {CREW_IDS.map((id, i) => {
            const sprite = NPC_SPRITES[id]
            return (
              <div key={id} className="animate-pop flex flex-col items-center gap-2" style={{ animationDelay: `${260 + i * 90}ms` }}>
                <svg viewBox="0 0 60 80" className="h-24 w-18 sm:h-28 sm:w-21" shapeRendering="crispEdges">
                  <g className="npc-bob" style={{ animationDelay: `${i * 0.4}s` }}>
                    {sprite.rows.flatMap((row, y) =>
                      [...row].map((ch, x) =>
                        ch === '.' ? null : (
                          <rect key={`${x}-${y}`} x={x * 5} y={y * 5} width="5" height="5" fill={sprite.palette[ch]} />
                        ),
                      ),
                    )}
                  </g>
                </svg>
                <span className="chip" style={{ color: NPCS[id].accent }}>{NPCS[id].name.split(' ').pop()!.toUpperCase()}</span>
                <span className="max-w-32 font-body text-base leading-none text-dim">{roleHint(id)}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* CTA */}
      <div className="animate-rise mt-9 flex flex-col items-center gap-4" style={{ animationDelay: '320ms' }}>
        <button onClick={() => startGame()} disabled={loading} className="btn btn-pop px-8 py-4 text-sm disabled:opacity-60 sm:text-base">
          {loading ? 'GENERATING MYSTERY…' : <span><span className="blink">▶</span> BOARD THE STATION</span>}
        </button>
        <button onClick={() => toggleHowItWorks(true)} className="font-body text-lg text-dim underline-offset-4 hover:text-text hover:underline">
          how does crew memory work?
        </button>
      </div>

      {error && (
        <p className="animate-rise gcard mx-auto mt-6 max-w-lg p-3 font-body text-lg text-bad">{error}</p>
      )}

      {showHowItWorks && <HowItWorks />}
    </div>
  )
}

function roleHint(id: NpcId): string {
  return {
    oda: 'runs the station',
    vega: 'keeps it breathing',
    lin: 'sees the nights',
    rio: 'hears everything',
    nova: 'wants the chair',
  }[id]
}
