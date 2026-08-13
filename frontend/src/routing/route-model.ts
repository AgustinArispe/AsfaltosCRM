export type Workspace =
  | 'pipeline'
  | 'dashboard'
  | 'notifications'
  | 'whatsapp'
  | 'customers'
  | 'products'
  | 'lost'
  | 'whatsapp-sends'
  | 'users'

export type WorkspaceRoute = { kind: 'workspace'; workspace: Workspace }
export type OpportunityRoute = {
  kind: 'opportunity'
  opportunityId: number
  surface: 'pipeline' | 'lost'
}
export type CustomerRoute = { kind: 'customer'; customerId: number }
export type ConversationRoute = { kind: 'conversation'; conversationId: number }
export type BroadcastRoute = { kind: 'broadcast'; broadcastId: number }

export type CrmRoute =
  | WorkspaceRoute
  | OpportunityRoute
  | CustomerRoute
  | ConversationRoute
  | BroadcastRoute

export type RouteOrigin = WorkspaceRoute | OpportunityRoute | CustomerRoute | ConversationRoute
export type CrmHistoryState = { crmOrigin?: RouteOrigin }

const WORKSPACE_PATHS: Record<Workspace, string> = {
  pipeline: '/pipeline',
  dashboard: '/dashboard',
  notifications: '/notifications',
  whatsapp: '/whatsapp',
  customers: '/customers',
  products: '/products',
  lost: '/lost',
  'whatsapp-sends': '/whatsapp-sends',
  users: '/users',
}

function validId(value: string | undefined): number | null {
  if (!value || !/^[1-9]\d*$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) ? id : null
}

function workspaceFromPath(pathname: string): Workspace | null {
  return (
    (Object.entries(WORKSPACE_PATHS) as [Workspace, string][]).find(
      ([, path]) => path === pathname,
    )?.[0] ?? null
  )
}

export function normalizePath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith('/')) return pathname.slice(0, -1)
  return pathname || '/'
}

export function parseRoute(pathname: string): CrmRoute | null {
  const normalized = normalizePath(pathname)
  const workspace = workspaceFromPath(normalized)
  if (workspace) return { kind: 'workspace', workspace }

  const opportunity = /^\/(pipeline|lost)\/opportunities\/([1-9]\d*)$/.exec(normalized)
  if (opportunity) {
    const opportunityId = validId(opportunity[2])
    if (opportunityId) {
      return { kind: 'opportunity', opportunityId, surface: opportunity[1] as 'pipeline' | 'lost' }
    }
  }

  const customer = /^\/customers\/([1-9]\d*)$/.exec(normalized)
  if (customer) {
    const customerId = validId(customer[1])
    if (customerId) return { kind: 'customer', customerId }
  }

  const conversation = /^\/whatsapp\/conversations\/([1-9]\d*)$/.exec(normalized)
  if (conversation) {
    const conversationId = validId(conversation[1])
    if (conversationId) return { kind: 'conversation', conversationId }
  }

  const broadcast = /^\/whatsapp-sends\/([1-9]\d*)$/.exec(normalized)
  if (broadcast) {
    const broadcastId = validId(broadcast[1])
    if (broadcastId) return { kind: 'broadcast', broadcastId }
  }
  return null
}

export function pathForRoute(route: CrmRoute): string {
  switch (route.kind) {
    case 'workspace':
      return WORKSPACE_PATHS[route.workspace]
    case 'opportunity':
      return `/${route.surface}/opportunities/${route.opportunityId}`
    case 'customer':
      return `/customers/${route.customerId}`
    case 'conversation':
      return `/whatsapp/conversations/${route.conversationId}`
    case 'broadcast':
      return `/whatsapp-sends/${route.broadcastId}`
  }
}

export function owningWorkspace(route: CrmRoute): WorkspaceRoute {
  if (route.kind === 'workspace') return route
  if (route.kind === 'opportunity') return { kind: 'workspace', workspace: route.surface }
  if (route.kind === 'customer') return { kind: 'workspace', workspace: 'customers' }
  if (route.kind === 'conversation') return { kind: 'workspace', workspace: 'whatsapp' }
  return { kind: 'workspace', workspace: 'whatsapp-sends' }
}

function isRouteOrigin(value: unknown): value is RouteOrigin {
  if (!value || typeof value !== 'object' || !('kind' in value)) return false
  const candidate = value as { kind?: unknown }
  return (
    (candidate.kind === 'workspace' && Boolean(pathForMaybeRoute(value))) ||
    (candidate.kind === 'opportunity' && Boolean(pathForMaybeRoute(value))) ||
    (candidate.kind === 'customer' && Boolean(pathForMaybeRoute(value))) ||
    (candidate.kind === 'conversation' && Boolean(pathForMaybeRoute(value)))
  )
}

function pathForMaybeRoute(value: unknown): string | null {
  if (!value || typeof value !== 'object') return null
  const candidate = value as Partial<CrmRoute>
  if (candidate.kind === 'workspace' && typeof candidate.workspace === 'string') {
    return workspaceFromPath(WORKSPACE_PATHS[candidate.workspace as Workspace] ?? '')
      ? WORKSPACE_PATHS[candidate.workspace as Workspace]
      : null
  }
  if (
    candidate.kind === 'opportunity' &&
    typeof candidate.opportunityId === 'number' &&
    Number.isSafeInteger(candidate.opportunityId) &&
    candidate.opportunityId > 0 &&
    (candidate.surface === 'pipeline' || candidate.surface === 'lost')
  ) {
    return pathForRoute(candidate as OpportunityRoute)
  }
  if (
    candidate.kind === 'customer' &&
    typeof candidate.customerId === 'number' &&
    Number.isSafeInteger(candidate.customerId) &&
    candidate.customerId > 0
  ) {
    return pathForRoute(candidate as CustomerRoute)
  }
  if (
    candidate.kind === 'conversation' &&
    typeof candidate.conversationId === 'number' &&
    Number.isSafeInteger(candidate.conversationId) &&
    candidate.conversationId > 0
  ) {
    return pathForRoute(candidate as ConversationRoute)
  }
  return null
}

export function readHistoryOrigin(state: unknown): RouteOrigin | null {
  if (!state || typeof state !== 'object' || !('crmOrigin' in state)) return null
  const origin = (state as { crmOrigin?: unknown }).crmOrigin
  return isRouteOrigin(origin) ? origin : null
}
