import { useAuth } from './auth/AuthContext'
import { AppShell } from './layout/AppShell'
import { CustomerDetailPage } from './pages/CustomerDetailPage'
import { CustomersPage } from './pages/CustomersPage'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { LostPage } from './pages/LostPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { OpportunityDetailPage } from './pages/OpportunityDetailPage'
import { PipelinePage } from './pages/PipelinePage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { ProductsPage } from './pages/ProductsPage'
import { UsersPage } from './pages/UsersPage'
import { WhatsAppBroadcastsPage } from './pages/WhatsAppBroadcastsPage'
import { WhatsAppInboxPage } from './pages/WhatsAppInboxPage'
import { getNavigationItem } from './routing/navigation'
import { parseRoute, pathForRoute } from './routing/route-model'
import { Redirect, usePathname } from './routing/router'
import { LoadingState } from './shared/LoadingState'
import { ThemeProvider } from './theme/ThemeProvider'

function legacyCanonicalPath(pathname: string): string | null {
  const opportunity = /^\/opportunities\/([1-9]\d*)$/.exec(pathname)
  if (opportunity) return `/pipeline/opportunities/${opportunity[1]}`
  return null
}

function RoutedApp() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const pathname = usePathname()

  if (isLoading) return <LoadingState fullscreen label='Restaurando sesión…' />
  if (!isAuthenticated) return pathname === '/login' ? <LoginPage /> : <Redirect to='/login' />
  if (pathname === '/' || pathname === '/login') return <Redirect to='/pipeline' />

  const legacyPath = legacyCanonicalPath(pathname)
  if (legacyPath) return <Redirect to={legacyPath} />

  const route = parseRoute(pathname)
  if (!route) return <Redirect to='/pipeline' />

  if (route.kind === 'opportunity') {
    return (
      <AppShell
        activeNavigationPath={route.surface === 'lost' ? '/lost' : '/pipeline'}
        pageTitle={route.surface === 'lost' ? 'Perdidas' : 'Pipeline'}
      >
        {route.surface === 'pipeline' ? (
          <PipelinePage selectedOpportunityId={route.opportunityId} />
        ) : null}
        <OpportunityDetailPage opportunityId={route.opportunityId} surface={route.surface} />
      </AppShell>
    )
  }
  if (route.kind === 'customer') {
    return (
      <AppShell activeNavigationPath='/customers' pageTitle='Ficha de cliente'>
        <CustomerDetailPage customerId={route.customerId} />
      </AppShell>
    )
  }
  if (route.kind === 'conversation') {
    return (
      <AppShell activeNavigationPath='/whatsapp' pageTitle='WhatsApp'>
        <WhatsAppInboxPage
          initialConversationId={route.conversationId}
          key={route.conversationId}
        />
      </AppShell>
    )
  }
  if (route.kind === 'broadcast') {
    return (
      <AppShell activeNavigationPath='/whatsapp-sends' pageTitle='Envíos masivos'>
        <WhatsAppBroadcastsPage broadcastId={route.broadcastId} />
      </AppShell>
    )
  }

  const navigationItem = getNavigationItem(pathForRoute(route))
  if (!navigationItem) return <Redirect to='/pipeline' />
  if (navigationItem.supervisorOnly && user?.role !== 'SUPERVISOR')
    return <Redirect to='/pipeline' />

  const pageContent =
    route.workspace === 'pipeline' ? (
      <PipelinePage />
    ) : route.workspace === 'dashboard' ? (
      <DashboardPage />
    ) : route.workspace === 'notifications' ? (
      <NotificationsPage />
    ) : route.workspace === 'customers' ? (
      <CustomersPage />
    ) : route.workspace === 'products' ? (
      <ProductsPage />
    ) : route.workspace === 'lost' ? (
      <LostPage />
    ) : route.workspace === 'whatsapp' ? (
      <WhatsAppInboxPage />
    ) : route.workspace === 'whatsapp-sends' ? (
      <WhatsAppBroadcastsPage />
    ) : route.workspace === 'users' ? (
      <UsersPage />
    ) : (
      <PlaceholderPage description={navigationItem.description} title={navigationItem.label} />
    )

  return <AppShell pageTitle={navigationItem.label}>{pageContent}</AppShell>
}

export default function App() {
  return (
    <ThemeProvider>
      <RoutedApp />
    </ThemeProvider>
  )
}
