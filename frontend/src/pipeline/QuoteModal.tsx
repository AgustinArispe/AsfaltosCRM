import { type KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '../shared/Button'
import { formatQuantityKg, sumQuantitiesKg } from '../shared/formatters'
import { LoadingState } from '../shared/LoadingState'
import { Modal } from '../shared/Modal'
import type { OpportunitySummary, Product, QuoteProductInput } from './types'

type QuoteLine = {
  key: number
  productId: string
  quantity: string
}

type QuoteStep = 'product' | 'quantity' | 'review'

function initialLines(opportunity: OpportunitySummary | null): QuoteLine[] {
  if (!opportunity) return []
  return opportunity.products.map((quotedProduct, index) => ({
    key: index,
    productId: String(quotedProduct.product.id),
    quantity: quotedProduct.quantity_kg,
  }))
}

function lineSnapshot(lines: QuoteLine[]): string {
  return JSON.stringify(lines.map(({ productId, quantity }) => ({ productId, quantity })))
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
  const initial = useMemo(() => initialLines(opportunity), [opportunity])
  const [lines, setLines] = useState<QuoteLine[]>(initial)
  const [step, setStep] = useState<QuoteStep>(
    mode === 'edit' && initial.length ? 'review' : 'product',
  )
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [editingKey, setEditingKey] = useState<number | null>(null)
  const [productError, setProductError] = useState<string | null>(null)
  const [quantityError, setQuantityError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showDiscardPrompt, setShowDiscardPrompt] = useState(false)
  const nextKeyRef = useRef(initial.length)
  const discardPromptRef = useRef<HTMLDivElement>(null)
  const productRef = useRef<HTMLSelectElement>(null)
  const quantityRef = useRef<HTMLInputElement>(null)
  const reviewRef = useRef<HTMLHeadingElement>(null)

  // biome-ignore lint/correctness/useExhaustiveDependencies: reset only when the modal identity or mode changes.
  useEffect(() => {
    const next = initialLines(opportunity)
    setLines(next)
    setStep(mode === 'edit' && next.length ? 'review' : 'product')
    setProductId('')
    setQuantity('')
    setEditingKey(null)
    setProductError(null)
    setQuantityError(null)
    setSubmitError(null)
    setShowDiscardPrompt(false)
    setIsSubmitting(false)
    nextKeyRef.current = next.length
  }, [opportunity?.id, mode])

  useEffect(() => {
    if (isLoadingProducts || !products) return
    if (showDiscardPrompt) {
      discardPromptRef.current?.querySelector<HTMLButtonElement>('button')?.focus()
      return
    }
    if (step === 'product') productRef.current?.focus()
    if (step === 'quantity') quantityRef.current?.focus()
    if (step === 'review') reviewRef.current?.focus()
  }, [isLoadingProducts, products, showDiscardPrompt, step])

  const existingProducts = opportunity?.products.map((item) => item.product) ?? []
  const availableProducts = [
    ...(products ?? []),
    ...existingProducts.filter(
      (existing) => !products?.some((product) => product.id === existing.id),
    ),
  ]
  const selectedProduct = availableProducts.find((product) => String(product.id) === productId)
  const selectedProductIds = new Set(
    lines.filter((line) => line.key !== editingKey).map((line) => line.productId),
  )
  const dirty =
    lineSnapshot(lines) !== lineSnapshot(initial) || Boolean(productId || quantity || editingKey)

  const resetEditor = () => {
    setProductId('')
    setQuantity('')
    setEditingKey(null)
    setProductError(null)
    setQuantityError(null)
  }

  const chooseProduct = () => {
    const numericProductId = Number(productId)
    if (!Number.isInteger(numericProductId) || numericProductId <= 0) {
      setProductError('Seleccioná un producto.')
      productRef.current?.focus()
      return
    }
    if (selectedProductIds.has(productId)) {
      setProductError('Este producto ya fue agregado.')
      productRef.current?.focus()
      return
    }
    setProductError(null)
    setStep('quantity')
  }

  const addProduct = () => {
    const numericQuantity = Number(quantity)
    if (!Number.isFinite(numericQuantity) || numericQuantity <= 0) {
      setQuantityError('Ingresá una cantidad mayor que cero.')
      quantityRef.current?.focus()
      return
    }
    const line: QuoteLine = {
      key: editingKey ?? nextKeyRef.current++,
      productId,
      quantity,
    }
    setLines((current) =>
      editingKey === null
        ? [...current, line]
        : current.map((item) => (item.key === editingKey ? line : item)),
    )
    resetEditor()
    setSubmitError(null)
    setStep('review')
  }

  const editLine = (line: QuoteLine) => {
    setProductId(line.productId)
    setQuantity(line.quantity)
    setEditingKey(line.key)
    setProductError(null)
    setQuantityError(null)
    setStep('product')
  }

  const removeLine = (key: number) => {
    setLines((current) => current.filter((line) => line.key !== key))
    setSubmitError(null)
  }

  const requestClose = () => {
    if (isSubmitting) return
    if (step === 'quantity') {
      setStep('product')
      return
    }
    if (step === 'product' && editingKey !== null) {
      resetEditor()
      setStep('review')
      return
    }
    if (dirty) {
      setShowDiscardPrompt(true)
      return
    }
    onClose()
  }

  const handleProductKeyDown = (event: KeyboardEvent<HTMLSelectElement>) => {
    if (event.key !== 'Enter' || event.nativeEvent.isComposing) return
    event.preventDefault()
    chooseProduct()
  }

  const handleQuantityKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'Enter' || event.nativeEvent.isComposing) return
    event.preventDefault()
    addProduct()
  }

  const submit = async () => {
    if (lines.length === 0 || isSubmitting) return
    const quoteProducts = lines.map((line) => ({
      product_id: Number(line.productId),
      quantity_kg: Number(line.quantity),
    }))
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

  const totalQuantity = sumQuantitiesKg(lines.map((line) => line.quantity))
  const activeProductIds = availableProducts
    .filter((item) => item.is_active)
    .map((item) => String(item.id))
  const allProductsSelected =
    activeProductIds.length > 0 &&
    activeProductIds.every((activeProductId) =>
      lines.some((line) => line.productId === activeProductId),
    )

  return (
    <Modal
      closeDisabled={isSubmitting}
      description={
        opportunity ? `Armá la cotización vigente para ${opportunity.customer.name}.` : undefined
      }
      isOpen={isOpen ?? Boolean(opportunity)}
      onClose={requestClose}
      size='large'
      title={mode === 'edit' ? 'Editar cotización' : 'Cotizar oportunidad'}
    >
      {isLoadingProducts || (!products && !productsError) ? (
        <LoadingState label='Cargando productos…' />
      ) : productsError ? (
        <div className='space-y-3 px-6 py-6'>
          <p className='text-sm text-[var(--destructive-text)]' role='alert'>
            {productsError}
          </p>
          <Button onClick={onRetryProducts}>Reintentar</Button>
        </div>
      ) : products?.length === 0 && existingProducts.length === 0 ? (
        <p className='px-6 py-7 text-sm text-[var(--text-secondary)]' role='status'>
          No hay productos activos disponibles para cotizar.
        </p>
      ) : showDiscardPrompt ? (
        <div className='quote-discard px-6 py-8' ref={discardPromptRef}>
          <h3>¿Descartar los cambios?</h3>
          <p>La cotización no se modificará hasta que confirmes el envío final.</p>
          <div className='mt-6 flex flex-wrap justify-end gap-2'>
            <Button data-modal-initial-focus onClick={() => setShowDiscardPrompt(false)}>
              Seguir editando
            </Button>
            <Button onClick={onClose} variant='danger'>
              Descartar cambios
            </Button>
          </div>
        </div>
      ) : (
        <div className='quote-flow' aria-busy={isSubmitting}>
          <ol aria-label='Progreso de la cotización' className='quote-flow__steps'>
            {[
              ['product', '1', 'Producto'],
              ['quantity', '2', 'Cantidad'],
              ['review', '3', 'Revisión'],
            ].map(([value, number, label]) => (
              <li aria-current={step === value ? 'step' : undefined} key={value}>
                <span>{number}</span>
                {label}
              </li>
            ))}
          </ol>

          <div className='quote-flow__body'>
            {step === 'product' ? (
              <section aria-labelledby='quote-product-step'>
                <p className='quote-flow__eyebrow'>Paso 1 de 3</p>
                <h3 id='quote-product-step'>
                  {editingKey === null ? 'Elegí un producto' : 'Cambiar producto'}
                </h3>
                <p className='quote-flow__description'>
                  Seleccioná un producto del catálogo vigente.
                </p>
                <label className='ui-label mt-6' htmlFor='quote-product'>
                  Producto
                </label>
                <select
                  aria-describedby={productError ? 'quote-product-error' : undefined}
                  aria-invalid={Boolean(productError)}
                  className='ui-field quote-flow__main-control'
                  data-modal-initial-focus
                  disabled={isSubmitting}
                  id='quote-product'
                  onChange={(event) => {
                    setProductId(event.target.value)
                    setProductError(null)
                  }}
                  onKeyDown={handleProductKeyDown}
                  ref={productRef}
                  value={productId}
                >
                  <option value=''>Seleccionar producto</option>
                  {availableProducts.map((product) => (
                    <option
                      disabled={
                        (!product.is_active && productId !== String(product.id)) ||
                        selectedProductIds.has(String(product.id))
                      }
                      key={product.id}
                      value={product.id}
                    >
                      {product.name}
                      {!product.is_active ? ' (inactivo histórico)' : ''}
                    </option>
                  ))}
                </select>
                {productError ? (
                  <p className='ui-field-error' id='quote-product-error'>
                    {productError}
                  </p>
                ) : null}
                <div className='quote-flow__actions'>
                  {lines.length > 0 ? (
                    <Button
                      onClick={() => {
                        resetEditor()
                        setStep('review')
                      }}
                      variant='ghost'
                    >
                      Volver a revisión
                    </Button>
                  ) : (
                    <Button onClick={requestClose} variant='ghost'>
                      Cancelar
                    </Button>
                  )}
                  <Button disabled={!productId} onClick={chooseProduct} variant='primary'>
                    Continuar con cantidad
                  </Button>
                </div>
              </section>
            ) : null}

            {step === 'quantity' ? (
              <section aria-labelledby='quote-quantity-step'>
                <p className='quote-flow__eyebrow'>Paso 2 de 3</p>
                <h3 id='quote-quantity-step'>Indicá la cantidad</h3>
                <p className='quote-flow__description'>
                  {selectedProduct?.name ?? 'Producto seleccionado'} · en kilogramos
                </p>
                <label className='ui-label mt-6' htmlFor='quote-quantity'>
                  Cantidad (kg)
                </label>
                <input
                  aria-describedby={quantityError ? 'quote-quantity-error' : undefined}
                  aria-invalid={Boolean(quantityError)}
                  className='ui-field quote-flow__quantity-control tabular-nums'
                  disabled={isSubmitting}
                  id='quote-quantity'
                  inputMode='decimal'
                  min='0.001'
                  onChange={(event) => {
                    setQuantity(event.target.value)
                    setQuantityError(null)
                  }}
                  onKeyDown={handleQuantityKeyDown}
                  ref={quantityRef}
                  step='0.001'
                  type='number'
                  value={quantity}
                />
                {quantityError ? (
                  <p className='ui-field-error' id='quote-quantity-error'>
                    {quantityError}
                  </p>
                ) : null}
                <div className='quote-flow__actions'>
                  <Button onClick={() => setStep('product')} variant='ghost'>
                    Volver al producto
                  </Button>
                  <Button disabled={!quantity} onClick={addProduct} variant='primary'>
                    {editingKey === null ? 'Agregar producto' : 'Guardar línea'}
                  </Button>
                </div>
              </section>
            ) : null}

            {step === 'review' ? (
              <section aria-labelledby='quote-review-step'>
                <p className='quote-flow__eyebrow'>Paso 3 de 3</p>
                <div className='quote-review__heading'>
                  <div>
                    <h3 id='quote-review-step' ref={reviewRef} tabIndex={-1}>
                      Revisá la cotización
                    </h3>
                    <p className='quote-flow__description'>
                      La confirmación reemplaza la cotización vigente.
                    </p>
                  </div>
                  <strong>{formatQuantityKg(totalQuantity)}</strong>
                </div>
                <ul className='quote-review__lines'>
                  {lines.map((line) => {
                    const product = availableProducts.find(
                      (item) => String(item.id) === line.productId,
                    )
                    return (
                      <li key={line.key}>
                        <span>
                          <b>{product?.name ?? 'Producto no disponible'}</b>
                          {product && !product.is_active ? <small>Inactivo histórico</small> : null}
                        </span>
                        <strong>{formatQuantityKg(line.quantity)}</strong>
                        <span className='quote-review__line-actions'>
                          <Button
                            disabled={isSubmitting}
                            onClick={() => editLine(line)}
                            size='compact'
                            variant='ghost'
                          >
                            Editar
                          </Button>
                          <Button
                            disabled={isSubmitting}
                            onClick={() => removeLine(line.key)}
                            size='compact'
                            variant='ghost'
                          >
                            Quitar
                          </Button>
                        </span>
                      </li>
                    )
                  })}
                </ul>
                <Button
                  disabled={allProductsSelected || isSubmitting}
                  onClick={() => {
                    resetEditor()
                    setStep('product')
                  }}
                  variant='secondary'
                >
                  Agregar otro producto
                </Button>
                {submitError ? (
                  <p className='quote-flow__error' role='alert'>
                    {submitError}
                  </p>
                ) : null}
              </section>
            ) : null}
          </div>

          {step === 'review' ? (
            <footer className='quote-flow__footer'>
              <Button disabled={isSubmitting} onClick={requestClose}>
                Cancelar
              </Button>
              <Button
                disabled={lines.length === 0}
                isLoading={isSubmitting}
                onClick={() => void submit()}
                variant='primary'
              >
                {mode === 'edit' ? 'Guardar cambios' : 'Confirmar cotización'}
              </Button>
            </footer>
          ) : null}
        </div>
      )}
    </Modal>
  )
}
