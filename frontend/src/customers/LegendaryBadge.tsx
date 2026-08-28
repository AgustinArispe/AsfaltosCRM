import { Badge } from '../shared/Badge'

export function LegendaryBadge() {
  return (
    <Badge className='legendary-badge' tone='legendary'>
      <svg aria-hidden='true' className='size-3 fill-[var(--legendary-text)]' viewBox='0 0 20 20'>
        <path d='m10 1.8 2.45 4.97 5.49.8-3.97 3.86.94 5.47L10 14.32 5.09 16.9l.94-5.47-3.97-3.86 5.49-.8L10 1.8Z' />
      </svg>
      Legendario
    </Badge>
  )
}
