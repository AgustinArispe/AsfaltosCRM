import { lazy } from 'react'

import { useAuth } from './auth/AuthContext'
import { AppShell } from './layout/AppShell'
import { LoginPage } from './pages/LoginPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { OpportunityDetailPage } from './pages/OpportunityDetailPage'
import { PipelinePage } from './pages/PipelinePage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { getNavigationItem } from './routing/navigation'
import { parseRoute, pathForRoute } from './routing/route-model'
import { Redirect, usePathname } from './routing/router'
import { LazyWorkspace } from './shared/LazyWorkspace'
import { LoadingState } from './shared/StatusStates'
import { ThemeProvider } from './theme/ThemeProvider'

const CustomerDetailPage = lazy(() =>
  import('./pages/CustomerDetailPage').then((module) => ({ default: module.CustomerDetailPage })),
)
const CustomersPage = lazy(() =>
  import('./pages/CustomersPage').then((module) => ({ default: module.CustomersPage })),
)
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })),
)
const LostPage = lazy(() =>
  import('./pages/LostPage').then((module) => ({ default: module.LostPage })),
)
const ProductsPage = lazy(() =>
  import('./pages/ProductsPage').then((module) => ({ default: module.ProductsPage })),
)
const UsersPage = lazy(() =>
  import('./pages/UsersPage').then((module) => ({ default: module.UsersPage })),
)
const WhatsAppBroadcastsPage = lazy(() =>
  import('./pages/WhatsAppBroadcastsPage').then((module) => ({
    default: module.WhatsAppBroadcastsPage,
  })),
)
const WhatsAppInboxPage = lazy(() =>
  import('./pages/WhatsAppInboxPage').then((module) => ({ default: module.WhatsAppInboxPage })),
)

function legacyCanonicalPath(pathname: string): string | null {
  const opportunity = /^\/opportunities\/([1-9]\d*)$/.exec(pathname)
  if (opportunity) return `/pipeline/opportunities/${opportunity[1]}`
  return null
}

function RoutedApp() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const pathname = usePathname()

  if (isLoading) return <LoadingState mode='fullscreen' label='Restaurando sesión…' />
  if (!isAuthenticated) return pathname === '/login' ? <LoginPage /> : <Redirect to='/login' />
  if (pathname === '/' || pathname === '/login') return <Redirect to='/pipeline' />

  const legacyPath = legacyCanonicalPath(pathname)
  if (legacyPath) return <Redirect to={legacyPath} />

  const route = parseRoute(pathname)
  if (!route) return <Redirect to='/pipeline' />

  if (
    (route.kind === 'workspace' && route.workspace === 'pipeline') ||
    (route.kind === 'opportunity' && route.surface === 'pipeline')
  ) {
    const selectedOpportunityId = route.kind === 'opportunity' ? route.opportunityId : undefined
    return (
      <AppShell activeNavigationPath='/pipeline' pageTitle='Pipeline'>
        <PipelinePage selectedOpportunityId={selectedOpportunityId} />
      </AppShell>
    )
  }
  if (route.kind === 'opportunity') {
    return (
      <AppShell activeNavigationPath='/lost' pageTitle='Perdidas'>
        <LazyWorkspace>
          <OpportunityDetailPage opportunityId={route.opportunityId} surface='lost' />
        </LazyWorkspace>
      </AppShell>
    )
  }
  if (route.kind === 'customer') {
    return (
      <AppShell activeNavigationPath='/customers' pageTitle='Ficha de cliente'>
        <LazyWorkspace>
          <CustomerDetailPage customerId={route.customerId} />
        </LazyWorkspace>
      </AppShell>
    )
  }
  if (route.kind === 'conversation') {
    return (
      <AppShell activeNavigationPath='/whatsapp' pageTitle='WhatsApp'>
        <LazyWorkspace>
          <WhatsAppInboxPage
            initialConversationId={route.conversationId}
            key={route.conversationId}
          />
        </LazyWorkspace>
      </AppShell>
    )
  }
  if (route.kind === 'broadcast') {
    return (
      <AppShell activeNavigationPath='/whatsapp-sends' pageTitle='Envíos masivos'>
        <LazyWorkspace>
          <WhatsAppBroadcastsPage broadcastId={route.broadcastId} />
        </LazyWorkspace>
      </AppShell>
    )
  }

  const navigationItem = getNavigationItem(pathForRoute(route))
  if (!navigationItem) return <Redirect to='/pipeline' />
  if (navigationItem.supervisorOnly && user?.role !== 'SUPERVISOR')
    return <Redirect to='/pipeline' />

  const pageContent =
    route.workspace === 'dashboard' ? (
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

  return (
    <AppShell pageTitle={navigationItem.label}>
      <LazyWorkspace>{pageContent}</LazyWorkspace>
    </AppShell>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <RoutedApp />
    </ThemeProvider>
  )
}
