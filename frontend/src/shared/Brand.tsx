export function BrandWordmark({ variant }: { variant: 'light' | 'dark' }) {
  const dark = variant === 'dark'

  return (
    <svg
      aria-hidden='true'
      className={`pulse-brand__wordmark pulse-brand__wordmark--${variant}`}
      viewBox={dark ? '190 0 341 157' : '132 0 248 157'}
    >
      <image
        height='157'
        href={dark ? '/pulse-brand-lockup-dark.png' : '/pulse-brand-lockup-light.png'}
        width={dark ? '531' : '380'}
      />
    </svg>
  )
}

export function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className={`pulse-brand${collapsed ? ' pulse-brand--collapsed' : ''}`}>
      {collapsed ? (
        <img
          alt=''
          aria-hidden='true'
          className='pulse-brand__icon'
          src='/pulse-brand-favicon.png'
        />
      ) : (
        <>
          <BrandWordmark variant='light' />
          <BrandWordmark variant='dark' />
        </>
      )}
      <span className='sr-only'>PULSE CRM — Seguí el ritmo de tus ventas</span>
    </div>
  )
}
