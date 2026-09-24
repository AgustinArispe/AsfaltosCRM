export function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className={`pulse-brand${collapsed ? ' pulse-brand--collapsed' : ''}`}>
      <img alt='' aria-hidden='true' className='pulse-brand__icon' src='/pulse-brand-touch.png' />
      <span className='sr-only'>PULSE CRM</span>
    </div>
  )
}
