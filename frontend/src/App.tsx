import { useAuth } from './auth/AuthContext'
import { AppShell } from './layout/AppShell'
import { LoginPage } from './pages/LoginPage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { getNavigationItem } from './routing/navigation'
import { Redirect, usePathname } from './routing/router'
import { LoadingState } from './shared/LoadingState'

function RoutedApp() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const pathname = usePathname()

  if (isLoading) {
    return <LoadingState fullscreen label="Restaurando sesión…" />
  }

  if (!isAuthenticated) {
    return pathname === '/login' ? <LoginPage /> : <Redirect to="/login" />
  }

  if (pathname === '/' || pathname === '/login') {
    return <Redirect to="/pipeline" />
  }

  const navigationItem = getNavigationItem(pathname)
  if (!navigationItem) {
    return <Redirect to="/pipeline" />
  }

  if (navigationItem.supervisorOnly && user?.role !== 'SUPERVISOR') {
    return <Redirect to="/pipeline" />
  }

  return (
    <AppShell pageTitle={navigationItem.label}>
      <PlaceholderPage
        description={navigationItem.description}
        title={navigationItem.label}
      />
    </AppShell>
  )
}

export default function App() {
  return <RoutedApp />
}
