import type { SVGAttributes } from 'react'

export type IconName =
  | 'alert'
  | 'bell'
  | 'check'
  | 'check-circle'
  | 'chevron-left'
  | 'chevron-right'
  | 'clock'
  | 'close'
  | 'dashboard'
  | 'chart-bars'
  | 'coins'
  | 'document'
  | 'filter'
  | 'flag'
  | 'globe'
  | 'handshake'
  | 'inbox'
  | 'logout'
  | 'menu'
  | 'moon'
  | 'pause-circle'
  | 'pipeline'
  | 'plus'
  | 'layers'
  | 'map-pin'
  | 'profile'
  | 'pencil'
  | 'products'
  | 'refresh'
  | 'search'
  | 'send'
  | 'settings'
  | 'sun'
  | 'users'
  | 'whatsapp'
  | 'target'
  | 'trophy'
  | 'x-circle'

const PATHS: Record<IconName, string> = {
  alert: 'M12 4 3.5 19h17L12 4Zm0 5v4m0 3h.01',
  bell: 'M18 9a6 6 0 0 0-12 0c0 7-3 7-3 7h18s-3 0-3-7M10 20h4',
  check: 'm5 12 4 4L19 6',
  'check-circle': 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-13-1 3 3 5-6',
  'chevron-left': 'm14 6-6 6 6 6',
  'chevron-right': 'm10 6 6 6-6 6',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-13v5l3 2',
  close: 'm6 6 12 12M18 6 6 18',
  dashboard: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',
  'chart-bars': 'M5 20V10h4v10H5Zm6 0V4h4v16h-4Zm6 0v-7h4v7h-4Z',
  coins:
    'M12 8c4.4 0 8-1.3 8-3s-3.6-3-8-3-8 1.3-8 3 3.6 3 8 3Zm8-3v5c0 1.7-3.6 3-8 3s-8-1.3-8-3V5m16 5v5c0 1.7-3.6 3-8 3s-8-1.3-8-3v-5m16 5v4c0 1.7-3.6 3-8 3s-8-1.3-8-3v-4',
  document: 'M7 3h7l4 4v14H7V3Zm7 0v5h5M10 12h5m-5 4h5',
  filter: 'M4 6h16M7 12h10M10 18h4',
  flag: 'M5 21V5m0 0c5-3 9 3 14 0v10c-5 3-9-3-14 0',
  globe:
    'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-18c2.2 2.4 3.4 5.4 3.4 9S14.2 18.6 12 21M12 3C9.8 5.4 8.6 8.4 8.6 12s1.2 6.6 3.4 9M3.5 9h17m-17 6h17',
  handshake:
    'm3 12 4-4 4 2 2-2 4 4m-9 4 2 2c.8.8 2 .8 2.8 0l4.2-4.2M3 12l5 5m13-5-5 5m5-5-4-4-4 4-2-2',
  inbox: 'M4 5h16v14H4zM4 14h4l2 3h4l2-3h4M8 9h8',
  logout: 'M10 5H5v14h5M14 8l4 4-4 4M9 12h9',
  menu: 'M4 7h16M4 12h16M4 17h16',
  moon: 'M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z',
  'pause-circle': 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM10 9v6m4-6v6',
  pipeline: 'M5 6h14M5 12h14M5 18h14M8 4v4m7 2v4m-4 2v4',
  plus: 'M12 5v14M5 12h14',
  layers: 'm12 3 9 5-9 5-9-5 9-5Zm-9 10 9 5 9-5m-18 5 9 5 9-5',
  'map-pin': 'M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Zm-5 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  profile: 'M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4.5 21a7.5 7.5 0 0 1 15 0',
  pencil: 'm4 20 4.2-1 10.9-10.9a2.1 2.1 0 0 0-3-3L5.2 16 4 20Zm10.6-13.4 3 3M4 20h5',
  products: 'm5 8 7-4 7 4-7 4-7-4Zm0 0v8l7 4 7-4V8M12 12v8',
  refresh: 'M20 6v5h-5M4 18v-5h5M18.4 9A7 7 0 0 0 6.7 6.7L4 11m16 2-2.7 4.3A7 7 0 0 1 5.6 15',
  search: 'm20 20-4.5-4.5M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z',
  send: 'm4 4 16 8-16 8 3-8-3-8Zm3 8h13',
  settings:
    'M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19 12l2-1-2-3-2 .5-1.5-1L15 5h-6l-.5 2.5-1.5 1L5 8l-2 3 2 1v2l-2 1 2 3 2-.5 1.5 1L9 21h6l.5-2.5 1.5-1 2 .5 2-3-2-1v-2Z',
  sun: 'M12 3v2M12 19v2M3 12h2M19 12h2m-2.6-6.6-1.4 1.4M7 17l-1.4 1.4m0-12L7 7m10 10 1.4 1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  users:
    'M16 20v-1.5A4.5 4.5 0 0 0 11.5 14h-3A4.5 4.5 0 0 0 4 18.5V20M10 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm8 1a2.5 2.5 0 1 0 0-5M20 20v-1.5a4.5 4.5 0 0 0-2.5-4',
  whatsapp:
    'M20.5 11.5a8.5 8.5 0 0 1-12.7 7.4L3.5 20l1.2-4.1A8.5 8.5 0 1 1 20.5 11.5ZM8.2 7.7c.3-.5.6-.5.9-.5h.4c.2 0 .4.1.5.4l1 2.2c.1.3.1.5-.1.8l-.8 1c.9 1.8 2.2 3 4 3.8l.9-1.1c.2-.3.5-.3.8-.2l2.1 1c.3.2.4.4.4.7v.5c0 .4-.2.8-.6 1-1 .5-2 .5-3 .2-3.9-1.1-6.9-4-8-7.9-.2-.7-.1-1.3.2-1.9Z',
  target:
    'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-4a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0-3a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
  trophy:
    'M8 4h8v3c0 4-1.8 7-4 7s-4-3-4-7V4Zm0 2H4v2c0 2.2 1.8 4 4 4m8-6h4v2c0 2.2-1.8 4-4 4m-4 2v4m-4 3h8',
  'x-circle': 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-12-3 6 6m0-6-6 6',
}

export function Icon({
  name,
  className = 'size-5',
  ...props
}: { name: IconName } & SVGAttributes<SVGSVGElement>) {
  return (
    <svg
      aria-hidden='true'
      className={className}
      data-icon={name}
      fill='none'
      stroke='currentColor'
      strokeLinecap='round'
      strokeLinejoin='round'
      strokeWidth='1.8'
      viewBox='0 0 24 24'
      {...props}
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
