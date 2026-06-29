import { useGame } from '../state/gameStore'

export function EvidenceBoard() {
  const { state, catalog, toggleNotebook, goToSolve } = useGame()
  const found = new Set(state?.cluesFound ?? [])
  const clues = catalog?.clues ?? []
  const total = clues.length || 5
  const notebook = state?.notebook ?? []

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-grape-2/70 backdrop-blur-sm" onClick={toggleNotebook}>
      <aside
        className="animate-rise h-full w-full max-w-md overflow-y-auto border-l border-line bg-grape p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-1 flex items-start justify-between">
          <div>
            <h2 className="font-display text-2xl font-bold text-text">🔍 Evidence Board</h2>
            <p className="chip text-dim">
              {found.size} of {total} clues found
            </p>
          </div>
          <button onClick={toggleNotebook} className="btn btn-soft px-3 py-1.5 text-sm">
            ✕
          </button>
        </div>

        {/* progress pips */}
        <div className="mb-5 mt-3 flex gap-1.5">
          {Array.from({ length: total }).map((_, i) => (
            <div
              key={i}
              className="h-2 flex-1 rounded-full transition-all"
              style={{ background: i < found.size ? 'var(--color-gold)' : 'rgba(255,255,255,0.12)' }}
            />
          ))}
        </div>

        <div className="grid gap-3">
          {clues.map((c) => {
            const got = found.has(c.id)
            return (
              <div
                key={c.id}
                className={got ? 'gcard animate-pop p-4' : 'gpanel p-4 opacity-80'}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{got ? c.icon : '🔒'}</span>
                  <div className="min-w-0">
                    {got ? (
                      <>
                        <div className="font-display text-sm font-bold text-ink">{c.title}</div>
                        <div className="chip text-good">collected</div>
                      </>
                    ) : (
                      <>
                        <div className="font-display text-sm font-bold text-dim">??? Locked clue</div>
                        <div className="font-body text-xs text-dim">{c.hint}</div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {notebook.length > 0 && (
          <div className="mt-6">
            <p className="chip mb-2 text-dim">Detective notes</p>
            <ul className="flex flex-col gap-2">
              {notebook.map((n, i) => (
                <li key={i} className="rounded-xl bg-white/6 px-3 py-2 font-body text-sm text-text/85">
                  • {n}
                </li>
              ))}
            </ul>
          </div>
        )}

        <button onClick={goToSolve} className="btn btn-gold mt-6 w-full px-5 py-3 text-base">
          ⚖️ I'm ready — Solve the Case
        </button>
      </aside>
    </div>
  )
}
