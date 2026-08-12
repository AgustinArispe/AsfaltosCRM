import { ApiError } from '../api/client'

export function productErrorMessage(error: unknown, operation: 'load' | 'save' | 'status'): string {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return 'No tenés permiso para administrar productos.'
    }
    if (error.status === 404) {
      return 'El producto ya no está disponible.'
    }
    if (error.status === 409) {
      return 'Ya existe un producto con ese nombre.'
    }
    if (error.status === 422) {
      return 'Revisá el nombre ingresado e intentá nuevamente.'
    }
  }

  if (operation === 'load') {
    return 'No pudimos cargar los productos. Revisá tu conexión e intentá nuevamente.'
  }
  if (operation === 'status') {
    return 'No pudimos actualizar el estado del producto. Intentá nuevamente.'
  }
  return 'No pudimos guardar el producto. Intentá nuevamente.'
}
