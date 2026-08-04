import { useEffect, useRef, useState, type FormEvent } from 'react'

import { LoadingState } from '../shared/LoadingState'
import { Modal } from '../shared/Modal'
import type {
  OpportunitySummary,
  Product,
  QuoteProductInput,
} from './types'

type QuoteLine = {
  key: number
  productId: string
  quantity: string
}

type LineErrors = Record<number, { product?: string; quantity?: string }>

function initialLine(): QuoteLine {
  return { key: 0, productId: '', quantity: '' }
}

export function QuoteModal({
  opportunity,
  products,
  isLoadingProducts,
  productsError,
  onRetryProducts,
  onClose,
  onConfirm,
}: {
  opportunity: OpportunitySummary | null
  products: Product[] | null
  isLoadingProducts: boolean
  productsError: string | null
  onRetryProducts: () => void
  onClose: () => void
  onConfirm: (products: QuoteProductInput[]) => Promise<void>
}) {
  const [lines, setLines] = useState<QuoteLine[]>([initialLine()])
  const [lineErrors, setLineErrors] = useState<LineErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const nextKeyRef = useRef(1)

  useEffect(() => {
    setLines([initialLine()])
    setLineErrors({})
    setSubmitError(null)
    setIsSubmitting(false)
    nextKeyRef.current = 1
  }, [opportunity?.id])

  const updateLine = (
    key: number,
    field: 'productId' | 'quantity',
    value: string,
  ) => {
    setLines((current) =>
      current.map((line) =>
        line.key === key ? { ...line, [field]: value } : line,
      ),
    )
    setLineErrors((current) => ({ ...current, [key]: {} }))
    setSubmitError(null)
  }

  const addLine = () => {
    setLines((current) => [
      ...current,
      { key: nextKeyRef.current++, productId: '', quantity: '' },
    ])
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
      setSubmitError(
        error instanceof Error
          ? error.message
          : 'No pudimos guardar la cotización.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  const selectedProductIds = new Set(
    lines.map((line) => line.productId).filter(Boolean),
  )
  const allProductsSelected = Boolean(
    products && products.length > 0 && selectedProductIds.size >= products.length,
  )

  return (
    <Modal
      closeDisabled={isSubmitting}
      description={
        opportunity
          ? `Registrá los productos cotizados para ${opportunity.customer.name}.`
          : undefined
      }
      isOpen={Boolean(opportunity)}
      onClose={onClose}
      title="Cotizar oportunidad"
    >
      {isLoadingProducts || (!products && !productsError) ? (
        <LoadingState label="Cargando productos…" />
      ) : productsError ? (
        <div className="space-y-3 px-5 py-5">
          <p className="text-sm text-red-800" role="alert">{productsError}</p>
          <button
            className="min-h-11 border border-slate-300 px-3 py-2 text-sm font-semibold outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500"
            onClick={onRetryProducts}
            type="button"
          >
            Reintentar
          </button>
        </div>
      ) : products?.length === 0 ? (
        <p className="px-5 py-6 text-sm text-slate-600" role="status">
          No hay productos activos disponibles para cotizar.
        </p>
      ) : (
        <form aria-busy={isSubmitting} noValidate onSubmit={handleSubmit}>
          <div className="max-h-[55vh] space-y-3 overflow-y-auto px-5 py-5">
            {lines.map((line, index) => {
              const errors = lineErrors[line.key]
              const productErrorId = `quote-product-${line.key}-error`
              const quantityErrorId = `quote-quantity-${line.key}-error`

              return (
                <fieldset className="border border-slate-200 bg-slate-50 p-3" key={line.key}>
                  <legend className="px-1 text-xs font-semibold text-slate-600">
                    Producto {index + 1}
                  </legend>
                  <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_9rem_auto] sm:items-end">
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-800" htmlFor={`quote-product-${line.key}`}>
                        Producto
                      </label>
                      <select
                        aria-describedby={errors?.product ? productErrorId : undefined}
                        aria-invalid={Boolean(errors?.product)}
                        autoFocus={index === 0}
                        className="min-h-11 w-full border border-slate-300 bg-white px-3 py-2 text-base outline-none focus:border-amber-600 focus:ring-2 focus:ring-amber-200"
                        disabled={isSubmitting}
                        id={`quote-product-${line.key}`}
                        onChange={(event) => updateLine(line.key, 'productId', event.target.value)}
                        value={line.productId}
                      >
                        <option value="">Seleccionar</option>
                        {products?.map((product) => (
                          <option
                            disabled={
                              selectedProductIds.has(String(product.id)) &&
                              line.productId !== String(product.id)
                            }
                            key={product.id}
                            value={product.id}
                          >
                            {product.name}
                          </option>
                        ))}
                      </select>
                      {errors?.product ? (
                        <p className="mt-1 text-xs font-medium text-red-700" id={productErrorId}>
                          {errors.product}
                        </p>
                      ) : null}
                    </div>

                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-800" htmlFor={`quote-quantity-${line.key}`}>
                        Cantidad (kg)
                      </label>
                      <input
                        aria-describedby={errors?.quantity ? quantityErrorId : undefined}
                        aria-invalid={Boolean(errors?.quantity)}
                        className="min-h-11 w-full border border-slate-300 bg-white px-3 py-2 text-base tabular-nums outline-none focus:border-amber-600 focus:ring-2 focus:ring-amber-200"
                        disabled={isSubmitting}
                        id={`quote-quantity-${line.key}`}
                        inputMode="decimal"
                        min="0.001"
                        onChange={(event) => updateLine(line.key, 'quantity', event.target.value)}
                        step="0.001"
                        type="number"
                        value={line.quantity}
                      />
                      {errors?.quantity ? (
                        <p className="mt-1 text-xs font-medium text-red-700" id={quantityErrorId}>
                          {errors.quantity}
                        </p>
                      ) : null}
                    </div>

                    <button
                      aria-label={`Quitar producto ${index + 1}`}
                      className="min-h-11 px-3 py-2 text-sm font-medium text-red-700 outline-none hover:bg-red-50 focus-visible:ring-2 focus-visible:ring-red-600 disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={lines.length === 1 || isSubmitting}
                      onClick={() => removeLine(line.key)}
                      type="button"
                    >
                      Quitar
                    </button>
                  </div>
                </fieldset>
              )
            })}

            <button
              className="min-h-11 border border-dashed border-slate-400 px-3 py-2 text-sm font-semibold text-slate-700 outline-none hover:border-slate-600 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500 disabled:cursor-not-allowed disabled:opacity-45"
              disabled={allProductsSelected || isSubmitting}
              onClick={addLine}
              title={allProductsSelected ? 'Todos los productos activos ya fueron agregados' : undefined}
              type="button"
            >
              + Agregar producto
            </button>

            {submitError ? (
              <p className="border-l-2 border-red-600 bg-red-50 px-3 py-2 text-sm font-medium text-red-800" role="alert">
                {submitError}
              </p>
            ) : null}
          </div>

          <footer className="flex flex-col-reverse gap-2 border-t border-slate-200 px-5 py-4 sm:flex-row sm:justify-end">
            <button
              className="min-h-11 border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-amber-500 disabled:opacity-40"
              disabled={isSubmitting}
              onClick={onClose}
              type="button"
            >
              Cancelar
            </button>
            <button
              className="min-h-11 bg-amber-500 px-4 py-2 text-sm font-bold text-slate-950 outline-none hover:bg-amber-400 focus-visible:ring-2 focus-visible:ring-amber-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:bg-amber-300 disabled:text-slate-600"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? 'Guardando…' : 'Confirmar cotización'}
            </button>
          </footer>
        </form>
      )}
    </Modal>
  )
}
