import { apiRequest } from './client'
import type { ApiSession } from './opportunities'
import type { Product } from '../pipeline/types'

export function listActiveProducts(session: ApiSession) {
  return apiRequest<Product[]>('/products', session)
}
