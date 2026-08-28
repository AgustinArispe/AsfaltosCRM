import { type AnchorHTMLAttributes, type MouseEvent, useEffect, useSyncExternalStore } from 'react'

import { LoadingState } from '../shared/StatusStates'
import {
  type CrmHistoryState,
  type CrmRoute,
  normalizePath,
  pathForRoute,
  type RouteOrigin,
  readHistoryOrigin,
} from './route-model'

function subscribeToLocation(onStoreChange: () => void) {
  window.addEventListener('popstate', onStoreChange)
  return () => window.removeEventListener('popstate', onStoreChange)
}

function getPathname() {
  return normalizePath(window.location.pathname)
}

export function usePathname(): string {
  return useSyncExternalStore(subscribeToLocation, getPathname, () => '/')
}

export function navigate(to: string, options: { replace?: boolean } = {}) {
  const target = normalizePath(to)
  if (target === getPathname()) return

  if (options.replace) {
    window.history.replaceState(null, '', target)
  } else {
    window.history.pushState(null, '', target)
  }
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function navigateRoute(
  route: CrmRoute,
  options: { replace?: boolean; origin?: RouteOrigin } = {},
) {
  const target = pathForRoute(route)
  const state: CrmHistoryState | null = options.origin ? { crmOrigin: options.origin } : null
  if (options.replace) {
    window.history.replaceState(state, '', target)
  } else {
    window.history.pushState(state, '', target)
  }
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function navigateToHistoryOrigin(fallback: CrmRoute) {
  const origin = readHistoryOrigin(window.history.state)
  navigateRoute(origin ?? fallback)
}

type AppLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  to: string | CrmRoute
  origin?: RouteOrigin
}

export function AppLink({ to, origin, onClick, ...props }: AppLinkProps) {
  const target = typeof to === 'string' ? normalizePath(to) : pathForRoute(to)
  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(event)
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return
    }
    event.preventDefault()
    if (typeof to === 'string') navigate(target)
    else navigateRoute(to, { origin })
  }

  return <a {...props} href={target} onClick={handleClick} />
}

export function Redirect({ to }: { to: string }) {
  useEffect(() => navigate(to, { replace: true }), [to])
  return <LoadingState mode='fullscreen' label='Redirigiendo…' />
}
