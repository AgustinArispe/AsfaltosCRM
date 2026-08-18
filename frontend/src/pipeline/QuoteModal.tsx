import { type FormEvent, useEffect, useRef, useState } from 'react'
import { Button } from '../shared/Button'
import { LoadingState } from '../shared/LoadingState'
import { Modal } from '../shared/Modal'
import type { OpportunitySummary, Product, QuoteProductInput } from './types'

type QuoteLine = {
  key: number
  productId: string
  quantity: string
}

type LineErrors = Record<number, { product?: string; quantity?: string }>

function initialLine(): QuoteLine {
  return { key: 0, productId: '', quantity: '' }
}

function initialLines(opportunity: OpportunitySummary | null): QuoteLine[] {
  if (!opportunity || opportunity.products.length === 0) return [initialLine()]
  return opportunity.products.map((quotedProduct, index) => ({
    key: index,
    productId: String(quotedProduct.product.id),
    quantity: quotedProduct.quantity_kg,
  }))
}

export function QuoteModal({
  opportunity,
  products,
  isLoadingProducts,
  productsError,
  onRetryProducts,
  onClose,
  onConfirm,
  mode = 'create',
  isOpen,
}: {
  opportunity: OpportunitySummary | null
  products: Product[] | null
  isLoadingProducts: boolean
  productsError: string | null
  onRetryProducts: () => void
  onClose: () => void
  onConfirm: (products: QuoteProductInput[]) => Promise<void>
  mode?: 'create' | 'edit'
  isOpen?: boolean
}) {
  const [lines, setLines] = useState<QuoteLine[]>(() => initialLines(opportunity))
  const [lineErrors, setLineErrors] = useState<LineErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const nextKeyRef = useRef(1)
  const firstProductRef = useRef<HTMLSelectElement>(null)

  // biome-ignore lint/correctness/useExhaustiveDependencies: reset only when the modal identity or mode changes.
  useEffect(() => {
    const nextLines = initialLines(opportunity)
    setLines(nextLines)
    setLineErrors({})
    setSubmitError(null)
    setIsSubmitting(false)
    nextKeyRef.current = nextLines.length
  }, [opportunity?.id, mode])

  useEffect(() => {
    if (opportunity && products && !isLoadingProducts) firstProductRef.current?.focus()
  }, [isLoadingProducts, opportunity, products])

  const updateLine = (key: number, field: 'productId' | 'quantity', value: string) => {
    setLines((current) =>
      current.map((line) => (line.key === key ? { ...line, [field]: value } : line)),
    )
    setLineErrors((current) => ({ ...current, [key]: {} }))
    setSubmitError(null)
  }

  const addLine = () => {
    setLines((current) => [...current, { key: nextKeyRef.current++, productId: '', quantity: '' }])
  }

  const removeLine = (key: number) => {
    setLines((current) => current.filter((line) => line.key !== key))
    setLineErrors((current) => {
      const next = { ...current }
      delete next[key]
      return next
    })
  }

  const validate = (): QuoteProductInput[] | null => {
    const errors: LineErrors = {}
    const selectedProducts = new Set<number>()
    const result: QuoteProductInput[] = []

    for (const line of lines) {
      const productId = Number(line.productId)
      const quantity = Number(line.quantity)
      const lineError: { product?: string; quantity?: string } = {}

      if (!Number.isInteger(productId) || productId <= 0) {
        lineError.product = 'Seleccioná un producto.'
      } else if (selectedProducts.has(productId)) {
        lineError.product = 'Este producto ya fue agregado.'
      } else {
        selectedProducts.add(productId)
      }

      if (!Number.isFinite(quantity) || quantity <= 0) {
        lineError.quantity = 'Ingresá una cantidad mayor que cero.'
      }

      if (lineError.product || lineError.quantity) {
        errors[line.key] = lineError
      } else {
        result.push({ product_id: productId, quantity_kg: quantity })
      }
    }

    setLineErrors(errors)
    if (Object.keys(errors).length > 0 || result.length === 0) {
      setSubmitError('Revisá los productos y cantidades indicados.')
      return null
    }
    return result
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const quoteProducts = validate()
    if (!quoteProducts) return

    setIsSubmitting(true)
    setSubmitError(null)
    try {
      await onConfirm(quoteProducts)
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'No pudimos guardar la cotización.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const selectedProductIds = new Set(lines.map((line) => line.productId).filter(Boolean))
  const existingProducts = opportunity?.products.map((item) => item.product) ?? []
  const availableProducts = [
    ...(products ?? []),
    ...existingProducts.filter(
      (existing) => !products?.some((product) => product.id === existing.id),
    ),
  ]
  const allProductsSelected = Boolean(
    products && products.length > 0 && selectedProductIds.size >= availableProducts.length,
  )

  return (
    <Modal
      closeDisabled={isSubmitting}
      description={
        opportunity
          ? `Registrá los productos cotizados para ${opportunity.customer.name}.`
          : undefined
      }
      isOpen={isOpen ?? Boolean(opportunity)}
      onClose={onClose}
      title={mode === 'edit' ? 'Editar cotización' : 'Cotizar oportunidad'}
    >
      {isLoadingProducts || (!products && !productsError) ? (
        <LoadingState label='Cargando productos…' />
      ) : productsError ? (
        <div className='space-y-3 px-5 py-5'>
          <p className='text-sm text-[var(--destructive-text)]' role='alert'>
            {productsError}
          </p>
          <Button onClick={onRetryProducts}>Reintentar</Button>
        </div>
      ) : products?.length === 0 ? (
        <p className='px-5 py-6 text-sm text-[var(--text-secondary)]' role='status'>
          No hay productos activos disponibles para cotizar.
        </p>
      ) : (
        <form aria-busy={isSubmitting} noValidate onSubmit={handleSubmit}>
          <div className='max-h-[55vh] space-y-3 overflow-y-auto px-5 py-5'>
            {lines.map((line, index) => {
              const errors = lineErrors[line.key]
              const productErrorId = `quote-product-${line.key}-error`
              const quantityErrorId = `quote-quantity-${line.key}-error`

              return (
                <fieldset
                  className='rounded-[var(--radius-control)] border border-[var(--subtle-border)] bg-[var(--surface-interactive)] p-3'
                  key={line.key}
                >
                  <legend className='px-1 text-xs font-semibold text-[var(--text-secondary)]'>
                    Producto {index + 1}
                  </legend>
                  <div className='grid gap-3 sm:grid-cols-[minmax(0,1fr)_9rem_auto] sm:items-end'>
                    <div>
                      <label className='ui-label' htmlFor={`quote-product-${line.key}`}>
                        Producto
                      </label>
                      <select
                        aria-describedby={errors?.product ? productErrorId : undefined}
                        aria-invalid={Boolean(errors?.product)}
                        className='ui-field text-base'
                        data-modal-initial-focus={index === 0 ? true : undefined}
                        disabled={isSubmitting}
                        id={`quote-product-${line.key}`}
                        onChange={(event) => updateLine(line.key, 'productId', event.target.value)}
                        ref={index === 0 ? firstProductRef : undefined}
                        value={line.productId}
                      >
                        <option value=''>Seleccionar</option>
                        {availableProducts.map((product) => (
                          <option
                            disabled={
                              (!product.is_active && line.productId !== String(product.id)) ||
                              (selectedProductIds.has(String(product.id)) &&
                                line.productId !== String(product.id))
                            }
                            key={product.id}
                            value={product.id}
                          >
                            {product.name}
                            {!product.is_active ? ' (inactivo)' : ''}
                          </option>
                        ))}
                      </select>
                      {errors?.product ? (
                        <p
                          className='mt-1 text-xs font-medium text-[var(--destructive-text)]'
                          id={productErrorId}
                        >
                          {errors.product}
                        </p>
                      ) : null}
                    </div>

                    <div>
                      <label className='ui-label' htmlFor={`quote-quantity-${line.key}`}>
                        Cantidad (kg)
                      </label>
                      <input
                        aria-describedby={errors?.quantity ? quantityErrorId : undefined}
                        aria-invalid={Boolean(errors?.quantity)}
                        className='ui-field text-base tabular-nums'
                        disabled={isSubmitting}
                        id={`quote-quantity-${line.key}`}
                        inputMode='decimal'
                        min='0.001'
                        onChange={(event) => updateLine(line.key, 'quantity', event.target.value)}
                        step='0.001'
                        type='number'
                        value={line.quantity}
                      />
                      {errors?.quantity ? (
                        <p
                          className='mt-1 text-xs font-medium text-[var(--destructive-text)]'
                          id={quantityErrorId}
                        >
                          {errors.quantity}
                        </p>
                      ) : null}
                    </div>

                    <Button
                      aria-label={`Quitar producto ${index + 1}`}
                      disabled={lines.length === 1 || isSubmitting}
                      onClick={() => removeLine(line.key)}
                      variant='ghost'
                    >
                      Quitar
                    </Button>
                  </div>
                </fieldset>
              )
            })}

            <Button
              className='border-dashed'
              disabled={allProductsSelected || isSubmitting}
              onClick={addLine}
              title={
                allProductsSelected ? 'Todos los productos activos ya fueron agregados' : undefined
              }
            >
              + Agregar producto
            </Button>

            {submitError ? (
              <p
                className='rounded-[var(--radius-control)] border border-[var(--destructive-border)] bg-[var(--destructive-subtle)] px-3 py-2 text-sm font-medium text-[var(--destructive-text)]'
                role='alert'
              >
                {submitError}
              </p>
            ) : null}
          </div>

          <footer className='flex flex-col-reverse gap-2 border-t border-[var(--subtle-border)] px-5 py-4 sm:flex-row sm:justify-end'>
            <Button disabled={isSubmitting} onClick={onClose}>
              Cancelar
            </Button>
            <Button disabled={isSubmitting} type='submit' variant='primary'>
              {isSubmitting
                ? 'Guardando…'
                : mode === 'edit'
                  ? 'Guardar cambios'
                  : 'Confirmar cotización'}
            </Button>
          </footer>
        </form>
      )}
    </Modal>
  )
}
