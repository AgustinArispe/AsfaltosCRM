import { useEffect, useMemo, useState } from 'react'

import {
  createCustomer,
  deleteCustomer,
  listCustomers,
  updateCustomer,
} from '../api/customers'
import type { ApiSession } from '../api/opportunities'
import { useAuth } from '../auth/AuthContext'
import { CustomerFormModal } from '../customers/CustomerFormModal'
import { CustomerTable } from '../customers/CustomerTable'
import { DeleteCustomerModal } from '../customers/DeleteCustomerModal'
import { customerErrorMessage } from '../customers/errors'
import type {
  CustomerSummary,
  CustomerWritePayload,
} from '../customers/types'
import { InlineFeedback } from '../shared/InlineFeedback'
import { LoadingState } from '../shared/LoadingState'
import { Button } from '../shared/Button'

const PAGE_SIZE = 20
const SEARCH_DEBOUNCE_MS = 300

export function CustomersPage() {
  const { token, logout, user } = useAuth()
  const [customers, setCustomers] = useState<CustomerSummary[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [formCustomer, setFormCustomer] = useState<CustomerSummary | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<CustomerSummary | null>(null)
  const [announcement, setAnnouncement] = useState('')

  const apiSession = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timeoutId)
  }, [searchInput])

  useEffect(() => {
    const controller = new AbortController()
    setIsLoading(true)
    setLoadError(null)

    listCustomers(
      { page, pageSize: PAGE_SIZE, search: search || undefined },
      { ...apiSession, signal: controller.signal },
    )
      .then((response) => {
        setCustomers(response.items)
        setTotal(response.total)
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setLoadError(customerErrorMessage(error, 'load'))
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [apiSession, page, reloadKey, search])

  if (!user) return null

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const openCreate = () => {
    setFormCustomer(null)
    setIsFormOpen(true)
  }
  const openEdit = (customer: CustomerSummary) => {
    setFormCustomer(customer)
    setIsFormOpen(true)
  }
  const closeForm = () => {
    setIsFormOpen(false)
    setFormCustomer(null)
  }

  const handleSave = async (payload: CustomerWritePayload) => {
    try {
      const savedCustomer = formCustomer
        ? await updateCustomer(formCustomer.id, payload, apiSession)
        : await createCustomer(payload, apiSession)
      closeForm()
      setAnnouncement(
        formCustomer
          ? `${savedCustomer.name} fue actualizado.`
          : `${savedCustomer.name} fue creado.`,
      )
      setReloadKey((current) => current + 1)
    } catch (error) {
      throw new Error(customerErrorMessage(error, 'save'))
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteCustomer(deleteTarget.id, apiSession)
      const deletedName = deleteTarget.name
      setDeleteTarget(null)
      setAnnouncement(`${deletedName} fue eliminado del CRM.`)
      if (customers.length === 1 && page > 1) setPage((current) => current - 1)
      else setReloadKey((current) => current + 1)
    } catch (error) {
      throw new Error(customerErrorMessage(error, 'delete'))
    }
  }

  return (
    <section aria-labelledby="customers-workspace-title" className="mx-auto max-w-[90rem]">
      <div aria-live="polite" className="sr-only">{announcement}</div>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-950" id="customers-workspace-title">
            Cartera de clientes
          </h2>
          <p className="mt-0.5 text-sm text-slate-600">
            Consultá y mantené actualizados los datos comerciales de FAA.
          </p>
        </div>
        <Button onClick={openCreate} variant="primary">
          Nuevo cliente
        </Button>
      </div>

      <div className="ui-panel mt-4 p-3.5">
        <label className="ui-label" htmlFor="customer-search">
          Buscar clientes
        </label>
        <div className="flex max-w-2xl items-center rounded-[4px] border border-slate-300 bg-white focus-within:border-slate-500 focus-within:ring-2 focus-within:ring-slate-500/20">
          <svg aria-hidden="true" className="ml-3 size-4 shrink-0 text-slate-500" fill="none" viewBox="0 0 20 20">
            <circle cx="8.5" cy="8.5" r="5.5" stroke="currentColor" strokeWidth="1.7" />
            <path d="m12.5 12.5 4 4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.7" />
          </svg>
          <input
            className="min-h-11 min-w-0 flex-1 border-0 bg-transparent px-3 py-2 text-base text-slate-950 outline-none placeholder:text-slate-400"
            id="customer-search"
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Nombre, empresa, email o teléfono"
            type="search"
            value={searchInput}
          />
        </div>
      </div>

      <div className="mt-4">
        {loadError ? (
          <div className="ui-panel px-5 py-6">
            <InlineFeedback message={loadError} />
            <Button className="mt-4" onClick={() => setReloadKey((current) => current + 1)}>
              Reintentar
            </Button>
          </div>
        ) : isLoading ? (
          <LoadingState label="Cargando clientes…" />
        ) : customers.length === 0 ? (
          <div className="ui-panel px-5 py-9 text-center">
            <h3 className="text-base font-semibold text-slate-950">
              {search ? 'No encontramos clientes' : 'Todavía no hay clientes'}
            </h3>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-600">
              {search
                ? 'Probá con otro nombre, empresa, email o teléfono.'
                : 'Creá el primer cliente para comenzar a registrar oportunidades.'}
            </p>
          </div>
        ) : (
          <>
            <CustomerTable
              customers={customers}
              onDelete={setDeleteTarget}
              onEdit={openEdit}
              role={user.role}
            />
            <nav
              aria-label="Paginación de clientes"
              className="ui-panel mt-3 flex flex-wrap items-center justify-between gap-3 px-4 py-2.5"
            >
              <p className="text-sm text-slate-600">
                {total} {total === 1 ? 'cliente' : 'clientes'}
              </p>
              <div className="flex items-center gap-3">
                <Button
                  disabled={page <= 1 || isLoading}
                  onClick={() => setPage((current) => current - 1)}
                  size="compact"
                >
                  Anterior
                </Button>
                <span className="text-sm font-medium tabular-nums text-slate-700">
                  Página {page} de {totalPages}
                </span>
                <Button
                  disabled={page >= totalPages || isLoading}
                  onClick={() => setPage((current) => current + 1)}
                  size="compact"
                >
                  Siguiente
                </Button>
              </div>
            </nav>
          </>
        )}
      </div>

      <CustomerFormModal
        customer={formCustomer}
        isOpen={isFormOpen}
        onClose={closeForm}
        onSubmit={handleSave}
        role={user.role}
      />
      <DeleteCustomerModal
        customer={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </section>
  )
}
