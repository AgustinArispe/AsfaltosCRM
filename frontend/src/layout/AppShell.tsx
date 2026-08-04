import { useEffect, useRef, type ReactNode } from 'react'

import { useAuth } from '../auth/AuthContext'
import { navigationForRole } from '../routing/navigation'
import { AppLink, usePathname } from '../routing/router'
import { Brand } from '../shared/Brand'

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
    <div className="min-h-dvh bg-slate-100 text-slate-900 lg:grid lg:grid-cols-[15rem_minmax(0,1fr)]">
      <a
        className="fixed left-3 top-3 z-50 -translate-y-20 bg-white px-3 py-2 text-sm font-semibold text-slate-950 shadow-sm focus:translate-y-0 focus:outline-none focus:ring-2 focus:ring-amber-500 motion-reduce:transition-none"
        href="#main-content"
      >
        Saltar al contenido
      </a>

      <aside className="border-b border-slate-800 bg-slate-950 text-slate-200 lg:sticky lg:top-0 lg:flex lg:h-dvh lg:flex-col lg:border-b-0 lg:border-r">
        <div className="border-b border-slate-800 px-5 py-4 lg:px-6 lg:py-5">
          <Brand inverse />
        </div>

        <nav className="overflow-x-auto px-3 py-2 lg:flex-1 lg:overflow-visible lg:px-4 lg:py-5" aria-label="Navegación principal">
          <ul className="flex min-w-max gap-1 lg:min-w-0 lg:flex-col">
            {navigation.map((item) => {
              const isActive = (activeNavigationPath ?? pathname) === item.path
              return (
                <li key={item.path}>
                  <AppLink
                    aria-current={isActive ? 'page' : undefined}
                    className={[
                      'block min-h-11 border-l-2 px-3 py-2.5 text-sm font-medium outline-none transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-amber-400 motion-reduce:transition-none',
                      isActive
                        ? 'border-amber-400 bg-slate-800 text-white'
                        : 'border-transparent text-slate-300 hover:bg-slate-900 hover:text-white',
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

        <p className="hidden border-t border-slate-800 px-6 py-4 text-xs leading-relaxed text-slate-500 lg:block">
          Fábrica Argentina de Asfaltos
        </p>
      </aside>

      <div className="min-w-0">
        <header className="flex min-h-16 flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-3 sm:px-7 lg:px-9">
          <h1 className="text-xl font-semibold tracking-tight text-slate-950">
            {pageTitle}
          </h1>

          <div className="flex min-w-0 items-center gap-3 sm:gap-4">
            <div className="min-w-0 text-right">
              <p className="truncate text-sm font-medium text-slate-900" title={user.full_name}>
                {user.full_name}
              </p>
              <p className="text-xs font-medium text-slate-500">
                {ROLE_LABELS[user.role]}
              </p>
            </div>
            <button
              className="min-h-11 border border-slate-300 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700 outline-none transition-colors duration-150 hover:border-slate-400 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
              onClick={logout}
              type="button"
            >
              Cerrar sesión
            </button>
          </div>
        </header>

        <main
          className="px-5 py-7 outline-none sm:px-7 lg:px-9 lg:py-8"
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
