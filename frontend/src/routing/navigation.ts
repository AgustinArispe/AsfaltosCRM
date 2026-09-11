import type { UserRole } from '../auth/types'

export type NavigationItem = {
  path: string
  label: string
  description: string
  supervisorOnly?: boolean
  group: 'work' | 'communication' | 'management' | 'administration'
}

export const NAV_ITEMS: readonly NavigationItem[] = [
  {
    path: '/pipeline',
    group: 'work',
    label: 'Oportunidades',
    description: 'El pipeline comercial se implementará en el siguiente módulo.',
  },
  {
    path: '/dashboard',
    group: 'work',
    label: 'Resumen comercial',
    description: 'Indicadores comerciales y operativos.',
  },
  {
    path: '/notifications',
    group: 'work',
    label: 'Notificaciones',
    description: 'Seguimientos y alertas operativas.',
  },
  {
    path: '/whatsapp',
    group: 'communication',
    label: 'WhatsApp',
    description: 'Conversaciones de WhatsApp y contexto comercial.',
  },
  {
    path: '/customers',
    group: 'management',
    label: 'Clientes',
    description: 'Gestión de clientes y su historial comercial.',
  },
  {
    path: '/products',
    group: 'management',
    label: 'Productos',
    description: 'Catálogo de productos disponibles para cotizaciones.',
  },
  {
    path: '/won',
    group: 'management',
    label: 'Ganadas',
    description: 'Historial de oportunidades comerciales ganadas.',
  },
  {
    path: '/users',
    group: 'administration',
    label: 'Usuarios',
    description: 'Administración de usuarios y acceso al CRM.',
    supervisorOnly: true,
  },
] as const

export function navigationForRole(role: UserRole): readonly NavigationItem[] {
  return NAV_ITEMS.filter((item) => !item.supervisorOnly || role === 'SUPERVISOR')
}

export function getNavigationItem(pathname: string): NavigationItem | undefined {
  return NAV_ITEMS.find((item) => item.path === pathname)
}
