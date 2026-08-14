import { type ReactNode, useEffect, useMemo, useRef, useState } from 'react'

import { useAuth } from '../auth/AuthContext'
import {
  NotificationAttentionBoundary,
  useNotificationAttentionContext,
} from '../notifications/NotificationAttention'
import { navigationForRole } from '../routing/navigation'
import { AppLink, usePathname } from '../routing/router'
import { Brand } from '../shared/Brand'
import { Icon, type IconName } from '../shared/Icon'
import { IconButton } from '../shared/IconButton'
import { NotificationBadge } from '../shared/StatusStates'
import { useTheme } from '../theme/ThemeProvider'

const ROLE_LABELS = { SUPERVISOR: 'Supervisor', VENDEDOR: 'Vendedor' } as const
const SIDEBAR_STORAGE_KEY = 'faa-crm.sidebar-collapsed'

const NAVIGATION_ICONS: Record<string, IconName> = {
  '/pipeline': 'pipeline',
  '/dashboard': 'dashboard',
  '/notifications': 'inbox',
  '/whatsapp': 'inbox',
  '/customers': 'users',
  '/products': 'products',
  '/lost': 'pipeline',
  '/whatsapp-sends': 'send',
  '/users': 'users',
}

function SidebarNavigation({
  activeNavigationPath,
  isCollapsed,
  navigation,
  notificationCount,
  pathname,
}: {
  activeNavigationPath: string | undefined
  isCollapsed: boolean
  navigation: ReturnType<typeof navigationForRole>
  notificationCount: number | undefined
  pathname: string
}) {
  const attention = useNotificationAttentionContext()
  const effectiveNotificationCount = notificationCount ?? attention?.count ?? 0
  return (
    <nav aria-label='Navegación principal' className='min-h-0 flex-1 overflow-y-auto px-2 py-3'>
      <ul className='space-y-1'>
        {navigation.map((item) => {
          const isActive = (activeNavigationPath ?? pathname) === item.path
          const icon = NAVIGATION_ICONS[item.path] ?? 'dashboard'
          const notificationLabel =
            item.path === '/notifications' && effectiveNotificationCount > 0
              ? `${item.label}, ${effectiveNotificationCount} notificaciones activas sin leer`
              : item.label
          return (
            <li key={item.path}>
              <AppLink
                aria-current={isActive ? 'page' : undefined}
                aria-label={isCollapsed ? notificationLabel : undefined}
                className={[
                  'ui-sidebar-link ui-pressable',
                  isCollapsed ? 'justify-center px-0' : 'justify-start px-3',
                  isActive ? 'ui-sidebar-link--active' : '',
                ].join(' ')}
                title={isCollapsed ? notificationLabel : undefined}
                to={item.path}
              >
                <Icon className='size-5 shrink-0' name={icon} />
                {isCollapsed ? null : <span className='truncate'>{item.label}</span>}
                {!isCollapsed && item.path === '/notifications' ? (
                  <NotificationBadge count={effectiveNotificationCount} />
                ) : null}
                {isCollapsed && item.path === '/notifications' ? (
                  <span className='absolute right-1 top-1'>
                    <NotificationBadge count={effectiveNotificationCount} />
                  </span>
                ) : null}
              </AppLink>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

export function AppShell({
  pageTitle,
  activeNavigationPath,
  notificationCount,
  children,
}: {
  pageTitle: string
  activeNavigationPath?: string
  notificationCount?: number
  children: ReactNode
}) {
  const { token, user, logout } = useAuth()
  const { preference, setPreference } = useTheme()
  const pathname = usePathname()
  const mainRef = useRef<HTMLElement>(null)
  const [isCollapsed, setIsCollapsed] = useState(
    () => window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true',
  )
  const apiSession = useMemo(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )

  useEffect(() => {
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(isCollapsed))
  }, [isCollapsed])

  useEffect(() => {
    void pathname
    mainRef.current?.focus({ preventScroll: true })
  }, [pathname])

  if (!user) return null
  const navigation = navigationForRole(user.role)

  return (
    <NotificationAttentionBoundary session={apiSession}>
      <div
        className='grid min-h-dvh bg-[var(--canvas)] text-[var(--text-primary)] transition-[grid-template-columns] duration-200 motion-reduce:transition-none lg:grid-cols-[var(--sidebar-width)_minmax(0,1fr)]'
        style={{ '--sidebar-width': isCollapsed ? '4.75rem' : '16rem' } as React.CSSProperties}
      >
        <a className='ui-skip-link' href='#main-content'>
          Saltar al contenido
        </a>
        <aside className='sticky top-0 hidden h-dvh flex-col border-r border-[var(--border-default)] bg-[var(--surface)] lg:flex'>
          <div className='flex min-h-[4.5rem] items-center justify-between gap-2 border-b border-[var(--border-default)] px-3'>
            <Brand collapsed={isCollapsed} />
            <IconButton
              icon='menu'
              label={isCollapsed ? 'Expandir navegación' : 'Contraer navegación'}
              onClick={() => setIsCollapsed((current) => !current)}
            />
          </div>
          <SidebarNavigation
            activeNavigationPath={activeNavigationPath}
            isCollapsed={isCollapsed}
            navigation={navigation}
            notificationCount={notificationCount}
            pathname={pathname}
          />
          <div className='border-t border-[var(--border-default)] p-2'>
            {isCollapsed ? (
              <IconButton icon='logout' label='Cerrar sesión' onClick={logout} />
            ) : (
              <>
                <div className='mb-2 px-2 py-1'>
                  <p className='truncate text-sm font-semibold'>{user.full_name}</p>
                  <p className='text-xs text-[var(--text-secondary)]'>{ROLE_LABELS[user.role]}</p>
                </div>
                <label className='sr-only' htmlFor='theme-preference'>
                  Tema
                </label>
                <select
                  className='ui-sidebar-theme-select'
                  id='theme-preference'
                  onChange={(event) => setPreference(event.target.value as typeof preference)}
                  value={preference}
                >
                  <option value='system'>Tema: sistema</option>
                  <option value='light'>Tema: claro</option>
                  <option value='dark'>Tema: oscuro</option>
                </select>
                <button className='ui-sidebar-logout' onClick={logout} type='button'>
                  <Icon name='logout' /> Cerrar sesión
                </button>
              </>
            )}
          </div>
        </aside>
        <main
          className='min-w-0 px-4 py-5 sm:px-6 lg:px-8 lg:py-7'
          id='main-content'
          ref={mainRef}
          tabIndex={-1}
        >
          <div className='mb-6 flex min-h-11 items-center gap-3'>
            <div className='min-w-0'>
              <p className='text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-tertiary)]'>
                FAA CRM
              </p>
              <h1 className='truncate text-xl font-semibold tracking-tight sm:text-2xl'>
                {pageTitle}
              </h1>
            </div>
          </div>
          {children}
        </main>
      </div>
    </NotificationAttentionBoundary>
  )
}
