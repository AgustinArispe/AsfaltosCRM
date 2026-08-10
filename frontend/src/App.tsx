import { useAuth } from './auth/AuthContext'
import { AppShell } from './layout/AppShell'
import { LoginPage } from './pages/LoginPage'
import { CustomerDetailPage } from './pages/CustomerDetailPage'
import { CustomersPage } from './pages/CustomersPage'
import { OpportunityDetailPage } from './pages/OpportunityDetailPage'
import { PipelinePage } from './pages/PipelinePage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { ProductsPage } from './pages/ProductsPage'
import { WhatsAppInboxPage } from './pages/WhatsAppInboxPage'
import { getNavigationItem } from './routing/navigation'
import { Redirect, usePathname } from './routing/router'
import {
  matchCustomerDetailRoute,
  matchOpportunityDetailRoute,
} from './routing/routes'
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

  const opportunityDetailRoute = matchOpportunityDetailRoute(pathname)
  if (opportunityDetailRoute) {
    return (
      <AppShell activeNavigationPath="/pipeline" pageTitle="Detalle de oportunidad">
        <OpportunityDetailPage
          opportunityId={opportunityDetailRoute.opportunityId}
        />
      </AppShell>
    )
  }

  const customerDetailRoute = matchCustomerDetailRoute(pathname)
  if (customerDetailRoute) {
    return (
      <AppShell activeNavigationPath="/customers" pageTitle="Ficha de cliente">
        <CustomerDetailPage customerId={customerDetailRoute.customerId} />
      </AppShell>
    )
  }

  const navigationItem = getNavigationItem(pathname)
  if (!navigationItem) {
    return <Redirect to="/pipeline" />
  }

  if (navigationItem.supervisorOnly && user?.role !== 'SUPERVISOR') {
    return <Redirect to="/pipeline" />
  }

  const pageContent =
    pathname === '/pipeline' ? (
      <PipelinePage />
    ) : pathname === '/customers' ? (
      <CustomersPage />
    ) : pathname === '/products' ? (
      <ProductsPage />
    ) : pathname === '/whatsapp' ? (
      <WhatsAppInboxPage />
    ) : (
      <PlaceholderPage
        description={navigationItem.description}
        title={navigationItem.label}
      />
    )

  return (
    <AppShell pageTitle={navigationItem.label}>
      {pageContent}
    </AppShell>
  )
}

export default function App() {
  return <RoutedApp />
}
