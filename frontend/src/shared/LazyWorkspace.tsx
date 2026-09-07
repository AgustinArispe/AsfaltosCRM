import { Component, type ErrorInfo, type ReactNode, Suspense } from 'react'

import { Button } from './Button'
import { LoadingState } from './StatusStates'

class WorkspaceChunkBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true }
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // The recoverable UI below intentionally avoids exposing chunk or stack details.
  }

  render(): ReactNode {
    if (!this.state.failed) return this.props.children
    return (
      <div className='ui-error-state' role='alert'>
        <p>No pudimos cargar esta sección. Revisá tu conexión e intentá nuevamente.</p>
        <Button onClick={() => window.location.reload()}>Reintentar</Button>
      </div>
    )
  }
}

export function LazyWorkspace({ children }: { children: ReactNode }) {
  return (
    <WorkspaceChunkBoundary>
      <Suspense fallback={<LoadingState label='Cargando sección…' />}>{children}</Suspense>
    </WorkspaceChunkBoundary>
  )
}
