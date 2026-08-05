import type { ReactNode } from 'react'

export type BadgeTone =
  | 'neutral'
  | 'new'
  | 'quoted'
  | 'negotiation'
  | 'won'
  | 'lost'
  | 'legendary'
  | 'active'

const TONE_CLASSES: Record<BadgeTone, string> = {
  neutral: 'border-slate-200 bg-slate-50 text-slate-600',
  new: 'border-slate-300 bg-slate-50 text-slate-700',
  quoted: 'border-blue-200 bg-blue-50 text-blue-800',
  negotiation: 'border-amber-200 bg-amber-50 text-amber-900',
  won: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  lost: 'border-rose-200 bg-rose-50 text-rose-800',
  legendary: 'border-[#d8c49c] bg-[#faf6ec] text-[#72572f]',
  active: 'border-emerald-200 bg-emerald-50 text-emerald-800',
}

export function Badge({
  tone = 'neutral',
  children,
  className = '',
}: {
  tone?: BadgeTone
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-[3px] border px-2 py-0.5 text-xs font-semibold leading-5 ${TONE_CLASSES[tone]} ${className}`}
    >
      {children}
    </span>
  )
}
