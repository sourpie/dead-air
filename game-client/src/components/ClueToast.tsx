import { useEffect } from 'react'
import { useGame } from '../state/gameStore'

export function ClueToasts() {
  const toasts = useGame((s) => s.toasts)
  return (
    <div className="pointer-events-none fixed bottom-24 right-5 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <Toast key={t.id} id={t.id} icon={t.clue.icon} title={t.clue.title} />
      ))}
    </div>
  )
}

function Toast({ id, icon, title }: { id: number; icon: string; title: string }) {
  const remove = useGame((s) => s.removeToast)
  useEffect(() => {
    const h = setTimeout(() => remove(id), 3000)
    return () => clearTimeout(h)
  }, [id, remove])
  return (
    <div className="animate-toast gcard flex w-72 items-center gap-3 px-4 py-3">
      <span className="text-3xl">{icon}</span>
      <div>
        <div className="chip font-bold text-coral">🔍 New clue!</div>
        <div className="font-display text-sm font-semibold leading-tight text-ink">{title}</div>
      </div>
    </div>
  )
}
