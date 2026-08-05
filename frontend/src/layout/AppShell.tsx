import { useEffect, useRef, type ReactNode } from 'react'

import { useAuth } from '../auth/AuthContext'
import { navigationForRole } from '../routing/navigation'
import { AppLink, usePathname } from '../routing/router'
import { Brand } from '../shared/Brand'
import { Button } from '../shared/Button'

const ROLE_LABELS = {
  SUPERVISOR: 'Supervisor',
  VENDEDOR: 'Vendedor',
} as const

export function AppShell({
  pageTitle,
  activeNavigationPath,
  children,
}: {
  pageTitle: string
  activeNavigationPath?: string
  children: ReactNode
}) {
  const { user, logout } = useAuth()
  const pathname = usePathname()
  const mainRef = useRef<HTMLElement>(null)

  useEffect(() => {
    mainRef.current?.focus({ preventScroll: true })
  }, [pathname])

  if (!user) return null
  const navigation = navigationForRole(user.role)

  return (
    <div className="min-h-dvh bg-slate-100 text-slate-900 lg:grid lg:grid-cols-[14rem_minmax(0,1fr)]">
      <a
        className="fixed left-3 top-3 z-50 -translate-y-20 rounded-[4px] bg-white px-3 py-2 text-sm font-semibold text-slate-950 shadow-sm focus:translate-y-0 focus:outline-none focus:ring-2 focus:ring-slate-500 motion-reduce:transition-none"
        href="#main-content"
      >
        Saltar al contenido
      </a>

      <aside className="border-b border-slate-700 bg-slate-800 text-slate-200 lg:sticky lg:top-0 lg:flex lg:h-dvh lg:flex-col lg:border-b-0 lg:border-r">
        <div className="border-b border-slate-700 px-4 py-3.5 lg:px-5 lg:py-4">
          <Brand inverse />
        </div>

        <nav className="overflow-x-auto px-2 py-1.5 lg:flex-1 lg:overflow-visible lg:px-3 lg:py-4" aria-label="Navegación principal">
          <ul className="flex min-w-max gap-1 lg:min-w-0 lg:flex-col">
            {navigation.map((item) => {
              const isActive = (activeNavigationPath ?? pathname) === item.path
              return (
                <li key={item.path}>
                  <AppLink
                    aria-current={isActive ? 'page' : undefined}
                    className={[
                      'ui-pressable block min-h-11 rounded-[4px] border-l-2 px-3 py-2.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-slate-300',
                      isActive
                        ? 'border-slate-100 bg-slate-700 text-white'
                        : 'border-transparent text-slate-300 hover:bg-slate-700/60 hover:text-white',
                    ].join(' ')}
                    to={item.path}
                  >
                    {item.label}
                  </AppLink>
                </li>
              )
            })}
          </ul>
        </nav>

        <p className="hidden border-t border-slate-700 px-5 py-3.5 text-[0.6875rem] leading-relaxed text-slate-400 lg:block">
          Fábrica Argentina de Asfaltos
        </p>
      </aside>

      <div className="min-w-0">
        <header className="flex min-h-[3.75rem] flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-2.5 sm:px-6 lg:px-7">
          <h1 className="text-lg font-semibold tracking-tight text-slate-950">
            {pageTitle}
          </h1>

          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <div className="min-w-0 text-right">
              <p className="truncate text-xs font-semibold text-slate-900 sm:text-sm" title={user.full_name}>
                {user.full_name}
              </p>
              <p className="text-[0.6875rem] text-slate-500">
                {ROLE_LABELS[user.role]}
              </p>
            </div>
            <Button onClick={logout} size="compact" variant="ghost">
              Cerrar sesión
            </Button>
          </div>
        </header>

        <main
          className="px-4 py-5 outline-none sm:px-6 lg:px-7 lg:py-6"
          id="main-content"
          ref={mainRef}
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
    </div>
  )
}
