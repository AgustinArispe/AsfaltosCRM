import type { UserRole } from '../auth/types'

export type NavigationItem = {
  path: string
  label: string
  description: string
  supervisorOnly?: boolean
}

export const NAV_ITEMS: readonly NavigationItem[] = [
  {
    path: '/pipeline',
    label: 'Pipeline',
    description: 'El pipeline comercial se implementará en el siguiente módulo.',
  },
  {
    path: '/customers',
    label: 'Clientes',
    description: 'Gestión de clientes y su historial comercial.',
  },
  {
    path: '/whatsapp',
    label: 'WhatsApp',
    description: 'Conversaciones de WhatsApp y contexto comercial.',
  },
  {
    path: '/products',
    label: 'Productos',
    description: 'Catálogo de productos disponibles para cotizaciones.',
  },
  {
    path: '/users',
    label: 'Usuarios',
    description: 'La administración de usuarios se incorporará en una próxima etapa.',
    supervisorOnly: true,
  },
] as const

export function navigationForRole(role: UserRole): readonly NavigationItem[] {
  return NAV_ITEMS.filter((item) => !item.supervisorOnly || role === 'SUPERVISOR')
}

export function getNavigationItem(pathname: string): NavigationItem | undefined {
  return NAV_ITEMS.find((item) => item.path === pathname)
}
