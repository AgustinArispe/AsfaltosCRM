import { useCallback, useRef, useState } from 'react'

import type { ApiSession } from '../api/opportunities'
import { listActiveProducts } from '../api/products'
import type { Product } from './types'

export type ActiveProductCatalog = {
  products: Product[] | null
  isLoading: boolean
  error: string | null
  load: () => Promise<Product[]>
  retry: () => Promise<Product[]>
}

export function useActiveProductCatalog(session: ApiSession): ActiveProductCatalog {
  const [products, setProducts] = useState<Product[] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const productsRef = useRef<Product[] | null>(null)
  const requestRef = useRef<Promise<Product[]> | null>(null)

  const load = useCallback((): Promise<Product[]> => {
    if (productsRef.current) return Promise.resolve(productsRef.current)
    if (requestRef.current) return requestRef.current
    setIsLoading(true)
    setError(null)
    const request = listActiveProducts(session)
      .then((items) => {
        const active = items.filter((item) => item.is_active)
        productsRef.current = active
        setProducts(active)
        return active
      })
      .catch((caught: unknown) => {
        setError('No pudimos cargar los productos. Intentá nuevamente.')
        throw caught
      })
      .finally(() => {
        requestRef.current = null
        setIsLoading(false)
      })
    requestRef.current = request
    return request
  }, [session])

  const retry = useCallback(() => {
    productsRef.current = null
    setProducts(null)
    return load()
  }, [load])

  return { products, isLoading, error, load, retry }
}
