import { ApiError } from '../api/client'

type PipelineAction = 'load' | 'quote' | 'transition' | 'lose'

const NETWORK_MESSAGE =
  'No pudimos conectar con el servidor. Revisá tu conexión e intentá nuevamente.'

export function pipelineErrorMessage(error: unknown, action: PipelineAction): string {
  if (!(error instanceof ApiError)) return NETWORK_MESSAGE

  if (error.status === 401) return 'Tu sesión expiró. Volvé a ingresar.'
  if (error.status === 404) {
    return 'La oportunidad ya no está disponible. Actualizá el pipeline.'
  }
  if (action === 'quote' && error.status === 409) {
    return 'Uno de los productos ya no está activo o la oportunidad cambió de estado.'
  }
  if (action === 'quote' && error.status === 422) {
    return 'Revisá los productos y cantidades antes de confirmar la cotización.'
  }
  if (action === 'lose' && error.status === 422) {
    return 'Seleccioná un motivo válido para marcar la oportunidad como perdida.'
  }
  if (error.status === 409 || error.status === 422) {
    return 'La transición ya no es válida. El pipeline se mantuvo sin cambios.'
  }
  if (action === 'load') {
    return 'No pudimos cargar el pipeline. Intentá nuevamente.'
  }
  return 'No pudimos completar la operación. Intentá nuevamente.'
}
