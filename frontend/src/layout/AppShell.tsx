import { type ReactNode, useEffect, useId, useMemo, useRef, useState } from 'react'

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
  '/whatsapp': 'whatsapp',
  '/customers': 'users',
  '/products': 'products',
  '/lost': 'pipeline',
  '/whatsapp-sends': 'send',
  '/users': 'users',
}

function AccountDisclosure({
  collapsed = false,
  email,
  fullName,
  logout,
  preference,
  role,
  setPreference,
}: {
  collapsed?: boolean
  email: string
  fullName: string
  logout: () => void
  preference: ReturnType<typeof useTheme>['preference']
  role: string
  setPreference: ReturnType<typeof useTheme>['setPreference']
}) {
  const [isOpen, setIsOpen] = useState(false)
  const disclosureId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!isOpen) return
    const closeOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setIsOpen(false)
    }
    const closeWithEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setIsOpen(false)
      triggerRef.current?.focus()
    }
    document.addEventListener('mousedown', closeOutside)
    document.addEventListener('keydown', closeWithEscape)
    return () => {
      document.removeEventListener('mousedown', closeOutside)
      document.removeEventListener('keydown', closeWithEscape)
    }
  }, [isOpen])

  return (
    <div className='ui-account' ref={rootRef}>
      <button
        aria-controls={disclosureId}
        aria-expanded={isOpen}
        aria-label={`Cuenta de ${fullName}`}
        className={`ui-account__trigger ui-pressable ${collapsed ? 'ui-account__trigger--collapsed' : ''}`}
        onClick={() => setIsOpen((current) => !current)}
        ref={triggerRef}
        type='button'
      >
        <span aria-hidden='true' className='ui-account__avatar'>
          {fullName.slice(0, 1).toUpperCase()}
        </span>
        {collapsed ? null : (
          <span className='min-w-0 flex-1 text-left'>
            <span className='block truncate font-semibold'>{fullName}</span>
            <span className='block truncate text-xs text-[var(--text-tertiary)]'>{role}</span>
          </span>
        )}
        {collapsed ? null : <Icon aria-hidden='true' name='chevron-right' />}
      </button>
      {isOpen ? (
        <div className='ui-account__popover' id={disclosureId}>
          <div className='ui-account__identity'>
            <strong>{fullName}</strong>
            <span>{role}</span>
            <span>{email}</span>
          </div>
          <label className='ui-account__theme' htmlFor={`${disclosureId}-theme`}>
            <span>Tema</span>
            <select
              id={`${disclosureId}-theme`}
              onChange={(event) => setPreference(event.target.value as typeof preference)}
              value={preference}
            >
              <option value='system'>Sistema</option>
              <option value='light'>Claro</option>
              <option value='dark'>Oscuro</option>
            </select>
          </label>
          <button className='ui-account__logout' onClick={logout} type='button'>
            <Icon name='logout' />
            Cerrar sesión
          </button>
        </div>
      ) : null}
    </div>
  )
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
        {navigation.map((item, index) => {
          const isActive = (activeNavigationPath ?? pathname) === item.path
          const startsGroup = index > 0 && navigation[index - 1]?.group !== item.group
          const icon = NAVIGATION_ICONS[item.path] ?? 'dashboard'
          const notificationLabel =
            item.path === '/notifications' && effectiveNotificationCount > 0
              ? `${item.label}, ${effectiveNotificationCount} notificaciones activas sin leer`
              : item.label
          return (
            <li className={startsGroup ? 'ui-sidebar-group-start' : undefined} key={item.path}>
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
  const mobileNavigationRef = useRef<HTMLElement>(null)
  const mobileNavigationTriggerRef = useRef<HTMLButtonElement>(null)
  const [isCollapsed, setIsCollapsed] = useState(
    () => window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true',
  )
  const [isMobileNavigationOpen, setIsMobileNavigationOpen] = useState(false)
  const wasMobileNavigationOpenRef = useRef(false)
  const apiSession = useMemo(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )

  useEffect(() => {
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(isCollapsed))
  }, [isCollapsed])

  useEffect(() => {
    void pathname
    setIsMobileNavigationOpen(false)
    mainRef.current?.focus({ preventScroll: true })
  }, [pathname])

  useEffect(() => {
    if (!isMobileNavigationOpen) {
      if (wasMobileNavigationOpenRef.current) mobileNavigationTriggerRef.current?.focus()
      wasMobileNavigationOpenRef.current = false
      return
    }
    wasMobileNavigationOpenRef.current = true
    mobileNavigationRef.current?.querySelector<HTMLButtonElement>('button')?.focus()
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsMobileNavigationOpen(false)
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [isMobileNavigationOpen])

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
        <aside className='ui-sidebar sticky top-0 hidden h-dvh flex-col lg:flex'>
          <div className='ui-sidebar__brand flex min-h-[4.5rem] items-center justify-between gap-2 px-3'>
            <Brand collapsed={isCollapsed} />
            <IconButton
              icon='menu'
              label={isCollapsed ? 'Expandir navegación' : 'Contraer navegación'}
              onClick={() => setIsCollapsed((current) => !current)}
              size='compact'
            />
          </div>
          <SidebarNavigation
            activeNavigationPath={activeNavigationPath}
            isCollapsed={isCollapsed}
            navigation={navigation}
            notificationCount={notificationCount}
            pathname={pathname}
          />
          <div className='ui-sidebar__footer p-2'>
            <AccountDisclosure
              collapsed={isCollapsed}
              email={user.email}
              fullName={user.full_name}
              logout={logout}
              preference={preference}
              role={ROLE_LABELS[user.role]}
              setPreference={setPreference}
            />
          </div>
        </aside>
        {isMobileNavigationOpen ? (
          <div className='fixed inset-0 z-50 lg:hidden'>
            <button
              aria-label='Cerrar navegación'
              className='absolute inset-0 bg-black/45'
              onClick={() => setIsMobileNavigationOpen(false)}
              type='button'
            />
            <aside
              aria-label='Navegación móvil'
              className='ui-sidebar relative flex h-dvh w-[min(20rem,88vw)] flex-col shadow-[var(--shadow-overlay)]'
              ref={mobileNavigationRef}
            >
              <div className='flex min-h-[4.5rem] items-center justify-between border-b border-[var(--divider)] px-3'>
                <Brand />
                <IconButton
                  icon='chevron-left'
                  label='Cerrar navegación'
                  onClick={() => setIsMobileNavigationOpen(false)}
                  size='compact'
                />
              </div>
              <SidebarNavigation
                activeNavigationPath={activeNavigationPath}
                isCollapsed={false}
                navigation={navigation}
                notificationCount={notificationCount}
                pathname={pathname}
              />
              <div className='ui-sidebar__footer p-3'>
                <AccountDisclosure
                  email={user.email}
                  fullName={user.full_name}
                  logout={logout}
                  preference={preference}
                  role={ROLE_LABELS[user.role]}
                  setPreference={setPreference}
                />
              </div>
            </aside>
          </div>
        ) : null}
        <main
          className='min-w-0 overflow-x-clip px-4 py-5 sm:px-6 lg:px-8 lg:py-7'
          id='main-content'
          ref={mainRef}
          tabIndex={-1}
        >
          <div className='mb-5 flex min-h-11 items-center gap-3'>
            <IconButton
              className='lg:hidden'
              icon='menu'
              label='Abrir navegación'
              onClick={() => setIsMobileNavigationOpen(true)}
              ref={mobileNavigationTriggerRef}
            />
            <div className='min-w-0'>
              <h1
                className='truncate rounded-[var(--radius-control)] text-[length:var(--text-title-size)] font-bold leading-[var(--text-title-line)] tracking-[-0.025em] text-[var(--brand-deep)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]'
                data-page-heading
                tabIndex={-1}
              >
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
