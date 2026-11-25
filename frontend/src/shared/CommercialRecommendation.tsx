import { type ReactNode, useId } from 'react'
import { Icon } from './Icon'

export function CommercialRecommendation({
  children,
  title,
}: {
  children: ReactNode
  title: string
}) {
  const headingId = useId()
  return (
    <aside aria-labelledby={headingId} className='commercial-recommendation'>
      <h2 id={headingId}>
        <Icon name='target' /> {title}
      </h2>
      <p>{children}</p>
    </aside>
  )
}
