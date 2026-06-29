import type { Choice } from '../types'

export function ChoiceButton({
  choice,
  index,
  disabled,
  busy,
  onClick,
}: {
  choice: Choice
  index: number
  disabled?: boolean
  busy?: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="group flex w-full items-center gap-3 rounded-2xl bg-white/6 px-4 py-3 text-left transition
                 hover:translate-x-1 hover:bg-white/12 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/10 font-display text-sm font-bold text-dim transition group-hover:bg-coral group-hover:text-white">
        {busy ? '…' : index + 1}
      </span>
      <span className="font-body text-[15px] font-semibold leading-snug text-text">{choice.text}</span>
      <span className="ml-auto text-dim opacity-0 transition group-hover:opacity-100">→</span>
    </button>
  )
}
