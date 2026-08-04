import { ApiError } from '../api/client'

export function customerErrorMessage(
  error: unknown,
  operation: 'load' | 'save' | 'delete',
): string {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return 'No tenés permiso para realizar esta acción.'
    }
    if (error.status === 404) {
      return 'El cliente ya no está disponible.'
    }
    if (error.status === 409) {
      return 'El cliente cambió o ya no está disponible. Actualizá la página e intentá nuevamente.'
    }
    if (error.status === 422) {
      return 'Revisá los datos ingresados e intentá nuevamente.'
    }
  }

  if (operation === 'load') {
    return 'No pudimos cargar los clientes. Revisá tu conexión e intentá nuevamente.'
  }
  if (operation === 'delete') {
    return 'No pudimos eliminar el cliente. Intentá nuevamente.'
  }
  return 'No pudimos guardar el cliente. Revisá los datos e intentá nuevamente.'
}
