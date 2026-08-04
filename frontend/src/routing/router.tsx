import {
  useEffect,
  useSyncExternalStore,
  type AnchorHTMLAttributes,
  type MouseEvent,
} from 'react'

import { LoadingState } from '../shared/LoadingState'

function normalizePath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith('/')) {
    return pathname.slice(0, -1)
  }
  return pathname || '/'
}

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

type AppLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  to: string
}

export function AppLink({ to, onClick, ...props }: AppLinkProps) {
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
    navigate(to)
  }

  return <a {...props} href={to} onClick={handleClick} />
}

export function Redirect({ to }: { to: string }) {
  useEffect(() => navigate(to, { replace: true }), [to])
  return <LoadingState fullscreen label="Redirigiendo…" />
}
