import { useEffect, useMemo, useState } from 'react'
import type { ApiSession } from '../api/opportunities'
import { createProduct, listProducts, updateProduct } from '../api/products'
import { useAuth } from '../auth/AuthContext'
import { DeactivateProductModal } from '../products/DeactivateProductModal'
import { productErrorMessage } from '../products/errors'
import { ProductFormModal } from '../products/ProductFormModal'
import { ProductTable } from '../products/ProductTable'
import type { Product } from '../products/types'
import { Button } from '../shared/Button'
import { EmptyState, InlineFeedback, WorkspaceSkeleton } from '../shared/StatusStates'

function sortProducts(products: Product[]): Product[] {
  return [...products].sort((first, second) => first.name.localeCompare(second.name, 'es-AR'))
}

function replaceProduct(products: Product[], updatedProduct: Product): Product[] {
  return sortProducts(
    products.map((product) => (product.id === updatedProduct.id ? updatedProduct : product)),
  )
}

export function ProductsPage() {
  const { token, logout, user } = useAuth()
  const [products, setProducts] = useState<Product[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [operationError, setOperationError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [formProduct, setFormProduct] = useState<Product | null>(null)
  const [deactivateTarget, setDeactivateTarget] = useState<Product | null>(null)
  const [busyProductIds, setBusyProductIds] = useState<Set<number>>(new Set())
  const [announcement, setAnnouncement] = useState('')

  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  const canManage = user?.role === 'SUPERVISOR'

  useEffect(() => {
    void reloadKey
    if (!user) return
    const controller = new AbortController()
    setIsLoading(true)
    setLoadError(null)

    listProducts(canManage, { ...apiSession, signal: controller.signal })
      .then((response) => {
        setProducts(
          sortProducts(canManage ? response : response.filter((product) => product.is_active)),
        )
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setLoadError(productErrorMessage(error, 'load'))
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [apiSession, canManage, reloadKey, user])

  if (!user) return null

  const activeCount = products.filter((product) => product.is_active).length
  const inactiveCount = products.length - activeCount
  const setProductBusy = (productId: number, isBusy: boolean) => {
    setBusyProductIds((current) => {
      const next = new Set(current)
      if (isBusy) next.add(productId)
      else next.delete(productId)
      return next
    })
  }
  const openCreate = () => {
    setFormProduct(null)
    setIsFormOpen(true)
  }
  const openEdit = (product: Product) => {
    setFormProduct(product)
    setIsFormOpen(true)
  }
  const closeForm = () => {
    setIsFormOpen(false)
    setFormProduct(null)
  }

  const handleSave = async (name: string) => {
    try {
      const savedProduct = formProduct
        ? await updateProduct(formProduct.id, { name }, apiSession)
        : await createProduct(name, apiSession)
      setProducts((current) =>
        formProduct
          ? replaceProduct(current, savedProduct)
          : sortProducts([...current, savedProduct]),
      )
      closeForm()
      setAnnouncement(
        formProduct ? `${savedProduct.name} fue actualizado.` : `${savedProduct.name} fue creado.`,
      )
    } catch (error) {
      throw new Error(productErrorMessage(error, 'save'))
    }
  }

  const handleDeactivate = async () => {
    if (!deactivateTarget) return
    setProductBusy(deactivateTarget.id, true)
    try {
      const updatedProduct = await updateProduct(
        deactivateTarget.id,
        { is_active: false },
        apiSession,
      )
      setProducts((current) => replaceProduct(current, updatedProduct))
      setDeactivateTarget(null)
      setAnnouncement(
        `${updatedProduct.name} fue desactivado y ya no está disponible para nuevas cotizaciones.`,
      )
    } catch (error) {
      throw new Error(productErrorMessage(error, 'status'))
    } finally {
      setProductBusy(deactivateTarget.id, false)
    }
  }

  const handleReactivate = async (product: Product) => {
    setOperationError(null)
    setProductBusy(product.id, true)
    try {
      const updatedProduct = await updateProduct(product.id, { is_active: true }, apiSession)
      setProducts((current) => replaceProduct(current, updatedProduct))
      setAnnouncement(
        `${updatedProduct.name} fue reactivado y está disponible para nuevas cotizaciones.`,
      )
    } catch (error) {
      setOperationError(productErrorMessage(error, 'status'))
    } finally {
      setProductBusy(product.id, false)
    }
  }

  return (
    <section aria-label='Catálogo de productos' className='mx-auto max-w-5xl'>
      <div aria-live='polite' className='sr-only'>
        {announcement}
      </div>

      <div className='flex flex-wrap justify-end gap-4'>
        {canManage ? (
          <Button onClick={openCreate} variant='primary'>
            Nuevo producto
          </Button>
        ) : null}
      </div>

      {!isLoading && !loadError ? (
        <p
          className='mt-4 border-b border-[var(--divider)] px-1 pb-3 text-sm text-[var(--text-secondary)]'
          role='status'
        >
          <span className='font-semibold tabular-nums text-[var(--text-primary)]'>
            {products.length}
          </span>{' '}
          {products.length === 1 ? 'producto' : 'productos'}
          {canManage ? (
            <>
              {' · '}
              <span className='font-semibold tabular-nums text-[var(--success-text)]'>
                {activeCount}
              </span>{' '}
              {activeCount === 1 ? 'activo' : 'activos'}
              {' · '}
              <span className='font-semibold tabular-nums text-[var(--text-secondary)]'>
                {inactiveCount}
              </span>{' '}
              {inactiveCount === 1 ? 'inactivo' : 'inactivos'}
            </>
          ) : null}
        </p>
      ) : null}

      {operationError ? (
        <div className='mt-4'>
          <InlineFeedback message={operationError} onDismiss={() => setOperationError(null)} />
        </div>
      ) : null}

      <div className='mt-4'>
        {loadError ? (
          <div className='ui-panel px-5 py-6'>
            <InlineFeedback message={loadError} />
            <Button className='mt-4' onClick={() => setReloadKey((current) => current + 1)}>
              Reintentar
            </Button>
          </div>
        ) : isLoading ? (
          <WorkspaceSkeleton label='Cargando productos…' />
        ) : products.length === 0 ? (
          <EmptyState
            description={
              canManage
                ? 'Creá el catálogo que después usarás en las cotizaciones.'
                : 'Un supervisor debe activar productos para que aparezcan en este catálogo.'
            }
            icon='products'
            size='workspace'
            title='Todavía no hay productos'
          />
        ) : (
          <ProductTable
            busyProductIds={busyProductIds}
            canManage={canManage}
            onDeactivate={setDeactivateTarget}
            onEdit={openEdit}
            onReactivate={(product) => void handleReactivate(product)}
            products={products}
          />
        )}
      </div>

      <ProductFormModal
        isOpen={isFormOpen}
        onClose={closeForm}
        onSubmit={handleSave}
        product={formProduct}
      />
      <DeactivateProductModal
        onClose={() => setDeactivateTarget(null)}
        onConfirm={handleDeactivate}
        product={deactivateTarget}
      />
    </section>
  )
}
