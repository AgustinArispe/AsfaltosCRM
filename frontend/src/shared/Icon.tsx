import type { SVGAttributes } from 'react'

export type IconName =
  | 'alert'
  | 'bell'
  | 'check'
  | 'chevron-left'
  | 'chevron-right'
  | 'clock'
  | 'dashboard'
  | 'inbox'
  | 'logout'
  | 'menu'
  | 'moon'
  | 'pipeline'
  | 'products'
  | 'search'
  | 'send'
  | 'settings'
  | 'sun'
  | 'users'

const PATHS: Record<IconName, string> = {
  alert: 'M12 4 3.5 19h17L12 4Zm0 5v4m0 3h.01',
  bell: 'M18 9a6 6 0 0 0-12 0c0 7-3 7-3 7h18s-3 0-3-7M10 20h4',
  check: 'm5 12 4 4L19 6',
  'chevron-left': 'm14 6-6 6 6 6',
  'chevron-right': 'm10 6 6 6-6 6',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-13v5l3 2',
  dashboard: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',
  inbox: 'M4 5h16v14H4zM4 14h4l2 3h4l2-3h4M8 9h8',
  logout: 'M10 5H5v14h5M14 8l4 4-4 4M9 12h9',
  menu: 'M4 7h16M4 12h16M4 17h16',
  moon: 'M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z',
  pipeline: 'M5 5h14M5 12h9M5 19h5M16 9v6M13 12h6',
  products: 'm5 8 7-4 7 4-7 4-7-4Zm0 0v8l7 4 7-4V8M12 12v8',
  search: 'm20 20-4.5-4.5M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z',
  send: 'm4 4 16 8-16 8 3-8-3-8Zm3 8h13',
  settings:
    'M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19 12l2-1-2-3-2 .5-1.5-1L15 5h-6l-.5 2.5-1.5 1L5 8l-2 3 2 1v2l-2 1 2 3 2-.5 1.5 1L9 21h6l.5-2.5 1.5-1 2 .5 2-3-2-1v-2Z',
  sun: 'M12 3v2M12 19v2M3 12h2M19 12h2m-2.6-6.6-1.4 1.4M7 17l-1.4 1.4m0-12L7 7m10 10 1.4 1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  users:
    'M16 20v-1.5A4.5 4.5 0 0 0 11.5 14h-3A4.5 4.5 0 0 0 4 18.5V20M10 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm8 1a2.5 2.5 0 1 0 0-5M20 20v-1.5a4.5 4.5 0 0 0-2.5-4',
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
      fill='none'
      stroke='currentColor'
      strokeLinecap='round'
      strokeLinejoin='round'
      strokeWidth='1.7'
      viewBox='0 0 24 24'
      {...props}
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
