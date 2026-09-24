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
          <img
            alt=''
            aria-hidden='true'
            className='pulse-brand__lockup pulse-brand__lockup--light'
            src='/pulse-brand-lockup-light.png'
          />
          <img
            alt=''
            aria-hidden='true'
            className='pulse-brand__lockup pulse-brand__lockup--dark'
            src='/pulse-brand-lockup-dark.png'
          />
        </>
      )}
      <span className='sr-only'>PULSE CRM — Seguí el ritmo de tus ventas</span>
    </div>
  )
}
