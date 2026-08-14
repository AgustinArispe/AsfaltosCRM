import { Skeleton } from './StatusStates'

export function WorkspaceSkeleton({ label }: { label: string }) {
  return (
    <div aria-busy='true' className='ui-panel overflow-hidden p-4' role='status'>
      <span className='sr-only'>{label}</span>
      <div aria-hidden='true' className='space-y-3'>
        <Skeleton className='block h-4 w-36' />
        <Skeleton className='block h-11 w-full' />
        <Skeleton className='block h-14 w-full' />
        <Skeleton className='block h-14 w-full' />
        <Skeleton className='block h-14 w-4/5' />
      </div>
    </div>
  )
}
