import { apiRequest } from './client'
import type { ApiSession } from './opportunities'
import type { Product, ProductUpdatePayload } from '../products/types'

export function listActiveProducts(session: ApiSession) {
  return apiRequest<Product[]>('/products', session)
}

export function listProducts(
  includeInactive: boolean,
  session: ApiSession,
) {
  const query = includeInactive ? '?include_inactive=true' : ''
  return apiRequest<Product[]>(`/products${query}`, session)
}

export function createProduct(name: string, session: ApiSession) {
  return apiRequest<Product>('/products', {
    ...session,
    method: 'POST',
    body: { name },
  })
}

export function updateProduct(
  productId: number,
  payload: ProductUpdatePayload,
  session: ApiSession,
) {
  return apiRequest<Product>(`/products/${productId}`, {
    ...session,
    method: 'PATCH',
    body: payload,
  })
}
