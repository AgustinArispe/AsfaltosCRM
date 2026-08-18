import { useCallback, useEffect, useMemo, useState } from 'react'
import { listCustomers } from '../api/customers'
import { uploadWhatsAppMedia } from '../api/whatsapp'
import {
  confirmBroadcast,
  createBroadcast,
  getBroadcast,
  listBroadcastAttempts,
  listBroadcastAuditEvents,
  listBroadcastRecipients,
  listBroadcasts,
  listBroadcastTemplates,
  processBroadcast,
  retryBroadcast,
  selectBroadcastRecipients,
  startBroadcast,
  updateBroadcast,
  validateBroadcast,
} from '../api/whatsapp-broadcasts'
import { useAuth } from '../auth/AuthContext'
import type {
  Broadcast,
  BroadcastAttempt,
  BroadcastAuditEvent,
  BroadcastRecipient,
  BroadcastTemplate,
  BroadcastValidation,
  RecipientStatus,
} from '../broadcasts/types'
import type { CustomerSummary } from '../customers/types'
import { AppLink, navigateRoute } from '../routing/router'
import { Badge, type BadgeTone } from '../shared/Badge'
import { Button } from '../shared/Button'
import { LoadingState } from '../shared/LoadingState'
import { Modal } from '../shared/Modal'
import { EmptyState } from '../shared/StatusStates'
import { FilterControl, SearchField, Toolbar } from '../shared/Workspace'

const STEP_LABELS = ['Contenido', 'Parámetros', 'Clientes', 'Elegibilidad', 'Revisión'] as const

function statusTone(status: Broadcast['status']): BadgeTone {
  if (status === 'COMPLETED') return 'won'
  if (status === 'PROCESSING') return 'negotiation'
  if (status === 'CONFIRMED') return 'quoted'
  return 'neutral'
}

function recipientTone(status: RecipientStatus): BadgeTone {
  if (status === 'DELIVERED' || status === 'READ') return 'won'
  if (status === 'FAILED') return 'lost'
  if (status === 'UNKNOWN') return 'unknown'
  if (status === 'DRAFT' || status === 'READY') return 'quoted'
  if (status === 'IN_PROGRESS' || status === 'ACCEPTED' || status === 'SENT') return 'negotiation'
  return 'neutral'
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : 'No pudimos completar la operación.'
}

export function WhatsAppBroadcastsPage({ broadcastId }: { broadcastId?: number }) {
  const { token, logout } = useAuth()
  const session = useMemo(() => ({ token: token ?? '', onUnauthorized: logout }), [logout, token])
  const [items, setItems] = useState<Broadcast[]>([])
  const [detail, setDetail] = useState<Broadcast | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isNewOpen, setIsNewOpen] = useState(false)

  const refresh = useCallback(async () => {
    setError(null)
    try {
      if (broadcastId) {
        setDetail(await getBroadcast(broadcastId, session))
      } else {
        setItems((await listBroadcasts(session)).items)
      }
    } catch (caught) {
      setError(errorText(caught))
    } finally {
      setIsLoading(false)
    }
  }, [broadcastId, session])

  useEffect(() => {
    void refresh()
  }, [refresh])

  if (isLoading) return <LoadingState label='Cargando envíos…' />
  if (error && !detail && items.length === 0) {
    return (
      <section aria-live='polite'>
        <p role='alert'>{error}</p>
        <Button onClick={() => void refresh()} type='button'>
          Reintentar
        </Button>
      </section>
    )
  }
  if (detail) return <BroadcastDetail broadcast={detail} onRefresh={refresh} session={session} />

  return (
    <section className='space-y-5' aria-labelledby='broadcast-history-title'>
      <header className='flex flex-wrap items-center justify-between gap-3'>
        <div>
          <h2 className='text-lg font-semibold' id='broadcast-history-title'>
            Envíos masivos recientes
          </h2>
          <p className='text-sm text-[var(--text-secondary)]'>
            Plantillas aprobadas a Clientes seleccionados, con elegibilidad y consentimiento
            auditables.
          </p>
        </div>
        <Button onClick={() => setIsNewOpen(true)} type='button' variant='primary'>
          Nuevo envío masivo
        </Button>
      </header>
      {error ? <p role='alert'>{error}</p> : null}
      {items.length === 0 ? (
        <EmptyState
          description='Los envíos confirmados aparecerán aquí con su evidencia de elegibilidad y consentimiento.'
          icon='send'
          size='workspace'
          title='Todavía no hay envíos masivos'
        />
      ) : (
        <div className='ui-panel overflow-x-auto'>
          <table className='w-full text-left text-sm'>
            <thead className='border-b border-[var(--border-default)] text-xs text-[var(--text-secondary)]'>
              <tr>
                <th className='p-3'>Envío</th>
                <th className='p-3'>Contenido</th>
                <th className='p-3'>Estado</th>
                <th className='p-3'>Clientes</th>
                <th className='p-3'>Resultados</th>
                <th className='p-3'>Actualizado</th>
              </tr>
            </thead>
            <tbody>
              {items.map((broadcast) => (
                <tr
                  className='border-b border-[var(--border-subtle)] last:border-0'
                  key={broadcast.id}
                >
                  <td className='p-3 font-medium'>
                    <AppLink to={{ kind: 'broadcast', broadcastId: broadcast.id }}>
                      {broadcast.label}
                    </AppLink>
                  </td>
                  <td className='p-3'>
                    {broadcast.template_name}
                    <span className='block text-xs text-[var(--text-secondary)]'>
                      {broadcast.template_language}
                    </span>
                  </td>
                  <td className='p-3'>
                    <Badge tone={statusTone(broadcast.status)}>{broadcast.status}</Badge>
                  </td>
                  <td className='p-3 tabular-nums'>{broadcast.recipient_count}</td>
                  <td className='p-3 text-xs tabular-nums text-[var(--text-secondary)]'>
                    {outcomeSummary(broadcast)}
                  </td>
                  <td className='p-3 text-[var(--text-secondary)]'>
                    {new Date(broadcast.updated_at).toLocaleString('es-AR')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <BroadcastCreation isOpen={isNewOpen} onClose={() => setIsNewOpen(false)} session={session} />
    </section>
  )
}

function outcomeSummary(broadcast: Broadcast): string {
  const outcomes = broadcast.outcomes
  if (!outcomes) return 'Sin resultados todavía'
  return (
    [
      outcomes.delivered ? `${outcomes.delivered} entregados` : null,
      outcomes.read ? `${outcomes.read} leídos` : null,
      outcomes.failed ? `${outcomes.failed} fallidos` : null,
      outcomes.unknown ? `${outcomes.unknown} inciertos` : null,
      outcomes.skipped ? `${outcomes.skipped} omitidos` : null,
    ]
      .filter((item): item is string => item !== null)
      .join(' · ') || 'Pendiente'
  )
}

function BroadcastCreation({
  isOpen,
  initialDraft = null,
  onClose,
  session,
}: {
  isOpen: boolean
  initialDraft?: Broadcast | null
  onClose: () => void
  session: { token: string; onUnauthorized: () => void }
}) {
  const [step, setStep] = useState(0)
  const [templates, setTemplates] = useState<BroadcastTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<BroadcastTemplate | null>(null)
  const [label, setLabel] = useState('')
  const [parameters, setParameters] = useState<Record<string, string>>({})
  const [headerMediaRef, setHeaderMediaRef] = useState<string | null>(null)
  const [headerMediaName, setHeaderMediaName] = useState<string | null>(null)
  const [headerMediaPreview, setHeaderMediaPreview] = useState<string | null>(null)
  const [customers, setCustomers] = useState<CustomerSummary[]>([])
  const [selectedCustomers, setSelectedCustomers] = useState<CustomerSummary[]>([])
  const [broadcast, setBroadcast] = useState<Broadcast | null>(null)
  const [validation, setValidation] = useState<BroadcastValidation | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) return
    void listBroadcastTemplates(session)
      .then(setTemplates)
      .catch((caught: unknown) => setError(errorText(caught)))
  }, [isOpen, session])
  useEffect(() => {
    if (!isOpen || !initialDraft) return
    setStep(0)
    setBroadcast(initialDraft)
    setLabel(initialDraft.label)
    setParameters(
      Object.fromEntries(initialDraft.parameters.map((item) => [item.name, item.value])),
    )
    setHeaderMediaRef(initialDraft.header_media_ref)
    setHeaderMediaName(initialDraft.header_media_ref ? 'Medio de encabezado seleccionado' : null)
    setValidation(null)
  }, [initialDraft, isOpen])
  useEffect(() => {
    if (!initialDraft || templates.length === 0) return
    setSelectedTemplate(
      templates.find((item) => item.external_id === initialDraft.template_external_id) ?? null,
    )
  }, [initialDraft, templates])
  useEffect(() => {
    if (step !== 2) return
    void listCustomers({ page: 1, pageSize: 30 }, session)
      .then((page) => setCustomers(page.items))
      .catch((caught: unknown) => setError(errorText(caught)))
  }, [session, step])

  const createAndAdvance = async () => {
    if (
      !selectedTemplate ||
      !label.trim() ||
      selectedTemplate.parameter_names.some((name) => !parameters[name]?.trim())
    )
      return
    setPending(true)
    setError(null)
    try {
      const draftInput = {
        label,
        template_external_id: selectedTemplate.external_id,
        parameters: selectedTemplate.parameter_names.map((name) => ({
          name,
          value: parameters[name].trim(),
        })),
        header_media_ref: headerMediaRef,
      }
      const saved = broadcast
        ? await updateBroadcast(
            broadcast.id,
            { ...draftInput, expected_version: broadcast.version },
            session,
          )
        : await createBroadcast(
            { ...draftInput, client_generated_id: crypto.randomUUID() },
            session,
          )
      setBroadcast(saved)
      setValidation(null)
      setStep(broadcast ? 3 : 2)
    } catch (caught) {
      setError(errorText(caught))
    } finally {
      setPending(false)
    }
  }
  const saveRecipients = async () => {
    if (!broadcast || selectedCustomers.length === 0) return
    setPending(true)
    setError(null)
    try {
      const selected = await selectBroadcastRecipients(
        broadcast.id,
        {
          command_id: crypto.randomUUID(),
          expected_version: broadcast.version,
          customer_ids: selectedCustomers.map((customer) => customer.id),
        },
        session,
      )
      setBroadcast((current) =>
        current
          ? { ...current, version: selected.version, recipient_count: selected.selected_count }
          : current,
      )
      setStep(3)
    } catch (caught) {
      setError(errorText(caught))
    } finally {
      setPending(false)
    }
  }
  const runValidation = async () => {
    if (!broadcast) return
    setPending(true)
    setError(null)
    try {
      const result = await validateBroadcast(broadcast.id, broadcast.version, session)
      setValidation(result)
      setStep(4)
    } catch (caught) {
      setError(errorText(caught))
    } finally {
      setPending(false)
    }
  }
  const confirm = async () => {
    if (!broadcast || !validation?.validation_token) return
    setPending(true)
    setError(null)
    try {
      const confirmed = await confirmBroadcast(
        broadcast.id,
        {
          command_id: crypto.randomUUID(),
          expected_version: validation.version,
          validation_token: validation.validation_token,
        },
        session,
      )
      navigateRoute({ kind: 'broadcast', broadcastId: confirmed.id })
    } catch (caught) {
      setError(errorText(caught))
    } finally {
      setPending(false)
    }
  }
  const canContinue = Boolean(
    selectedTemplate &&
      label.trim() &&
      selectedTemplate.parameter_names.every((name) => parameters[name]?.trim()),
  )
  const uploadHeaderMedia = async (file: File) => {
    if (!selectedTemplate) return
    const mediaType = selectedTemplate.header_type === 'IMAGE' ? 'IMAGE' : 'DOCUMENT'
    setPending(true)
    setError(null)
    try {
      const uploaded = await uploadWhatsAppMedia(file, mediaType, session)
      setHeaderMediaRef(uploaded.media_ref)
      setHeaderMediaName(file.name)
      setHeaderMediaPreview(mediaType === 'IMAGE' ? URL.createObjectURL(file) : null)
    } catch (caught) {
      setError(errorText(caught))
    } finally {
      setPending(false)
    }
  }
  return (
    <Modal
      description='Enviá una plantilla aprobada a Clientes seleccionados; el CRM valida elegibilidad y consentimiento.'
      isOpen={isOpen}
      onClose={onClose}
      size='large'
      title='Nuevo envío masivo'
    >
      <div className='p-5'>
        <ol aria-label='Progreso de creación' className='mb-5 flex flex-wrap gap-2'>
          {STEP_LABELS.map((item, index) => (
            <li key={item}>
              <Badge tone={index === step ? 'quoted' : 'neutral'}>
                {index + 1}. {item}
              </Badge>
            </li>
          ))}
        </ol>
        {error ? <p role='alert'>{error}</p> : null}
        {step < 2 ? (
          <>
            <label className='block text-sm font-medium'>
              Nombre operativo
              <input
                className='ui-field mt-1 w-full'
                onChange={(event) => setLabel(event.target.value)}
                value={label}
              />
            </label>
            <fieldset className='mt-4'>
              <legend className='text-sm font-medium'>Template preparado</legend>
              <div className='mt-2 grid gap-2'>
                {templates.map((template) => (
                  <label
                    className='ui-pressable rounded-[var(--radius-control)] border border-[var(--border-default)] p-3'
                    key={template.external_id}
                  >
                    <input
                      checked={selectedTemplate?.external_id === template.external_id}
                      name='template'
                      onChange={() => {
                        setSelectedTemplate(template)
                        setParameters({})
                      }}
                      type='radio'
                    />{' '}
                    <span className='ml-2 font-medium'>{template.name}</span>
                    <span className='ml-2 text-xs text-[var(--text-secondary)]'>
                      {template.language} · {template.category}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
            {selectedTemplate ? (
              <div className='mt-4 space-y-3'>
                {selectedTemplate.parameter_names.map((name) => (
                  <label className='block text-sm font-medium' key={name}>
                    {name}
                    <input
                      className='ui-field mt-1 w-full'
                      onChange={(event) =>
                        setParameters((current) => ({ ...current, [name]: event.target.value }))
                      }
                      value={parameters[name] ?? ''}
                    />
                  </label>
                ))}
                {selectedTemplate.header_media_required ? (
                  <div className='space-y-2'>
                    <label className='block text-sm font-medium'>
                      Encabezado{' '}
                      {selectedTemplate.header_type === 'IMAGE' ? 'de imagen' : 'PDF/documento'}
                      <input
                        accept={
                          selectedTemplate.header_type === 'IMAGE' ? 'image/*' : 'application/pdf'
                        }
                        className='mt-1 block w-full text-sm'
                        disabled={pending}
                        onChange={(event) => {
                          const [file] = Array.from(event.target.files ?? [])
                          if (file) void uploadHeaderMedia(file)
                        }}
                        type='file'
                      />
                    </label>
                    {headerMediaPreview ? (
                      <img
                        alt='Vista previa del encabezado seleccionado'
                        className='max-h-32 rounded-md'
                        src={headerMediaPreview}
                      />
                    ) : null}
                    {headerMediaName ? <p className='text-sm'>{headerMediaName}</p> : null}
                    {headerMediaRef ? (
                      <Button
                        onClick={() => {
                          setHeaderMediaRef(null)
                          setHeaderMediaName(null)
                          setHeaderMediaPreview(null)
                        }}
                        type='button'
                        variant='ghost'
                      >
                        Quitar medio
                      </Button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}
            <div className='mt-6 flex justify-end'>
              <Button
                disabled={
                  !canContinue ||
                  pending ||
                  (selectedTemplate?.header_media_required && !headerMediaRef)
                }
                onClick={() => void createAndAdvance()}
                type='button'
                variant='primary'
              >
                Continuar a clientes
              </Button>
            </div>
          </>
        ) : null}
        {step === 2 ? (
          <>
            <p className='text-sm text-[var(--text-secondary)]'>
              Seleccioná Clientes explícitamente. No se infiere una audiencia.
            </p>
            <ul className='mt-3 max-h-72 overflow-y-auto'>
              {customers.map((customer) => (
                <li className='border-b border-[var(--border-subtle)] py-2' key={customer.id}>
                  <label>
                    <input
                      checked={selectedCustomers.some((item) => item.id === customer.id)}
                      onChange={(event) =>
                        setSelectedCustomers((current) =>
                          event.target.checked
                            ? [...current, customer]
                            : current.filter((item) => item.id !== customer.id),
                        )
                      }
                      type='checkbox'
                    />{' '}
                    <span className='ml-2'>
                      {customer.name}
                      {customer.company ? ` · ${customer.company}` : ''}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
            <p className='mt-3 text-sm tabular-nums'>
              {selectedCustomers.length} Customers seleccionados
            </p>
            <div className='mt-6 flex justify-between'>
              <Button onClick={() => setStep(0)} type='button' variant='ghost'>
                Editar borrador
              </Button>
              <Button
                disabled={pending || selectedCustomers.length === 0}
                onClick={() => void saveRecipients()}
                type='button'
                variant='primary'
              >
                Revisar elegibilidad
              </Button>
            </div>
          </>
        ) : null}
        {step === 3 ? (
          <>
            <h3 className='text-base font-semibold'>Validación de elegibilidad</h3>
            <p className='mt-2 text-sm text-[var(--text-secondary)]'>
              El backend vuelve a validar consentimiento y datos antes de habilitar la confirmación.
            </p>
            <div className='mt-6 flex justify-between'>
              <Button onClick={() => setStep(broadcast ? 0 : 2)} type='button' variant='ghost'>
                Volver
              </Button>
              <Button
                disabled={pending}
                onClick={() => void runValidation()}
                type='button'
                variant='primary'
              >
                Validar envío
              </Button>
            </div>
          </>
        ) : null}
        {step === 4 && validation ? (
          <>
            <h3 className='text-base font-semibold'>Resumen final</h3>
            <dl className='mt-3 grid grid-cols-2 gap-3 text-sm'>
              <div>
                <dt className='text-[var(--text-secondary)]'>Aptos</dt>
                <dd className='font-semibold'>{validation.eligible_count}</dd>
              </div>
              <div>
                <dt className='text-[var(--text-secondary)]'>Excluidos</dt>
                <dd className='font-semibold'>{validation.excluded_count}</dd>
              </div>
            </dl>
            {validation.issue_categories.map((issue) => (
              <p className='mt-2 text-sm' key={issue.category}>
                {issue.category}: {issue.count}
              </p>
            ))}
            {validation.valid ? (
              <p className='mt-4 text-sm'>
                Al confirmar, contenido y destinatarios quedarán bloqueados.
              </p>
            ) : (
              <p className='mt-4 text-sm' role='alert'>
                Corregí las exclusiones antes de confirmar; no hay envíos parciales.
              </p>
            )}
            <div className='mt-6 flex justify-between'>
              <Button onClick={() => setStep(2)} type='button' variant='ghost'>
                Volver
              </Button>
              <Button
                disabled={!validation.valid || pending}
                onClick={() => void confirm()}
                type='button'
                variant='primary'
              >
                Confirmar y bloquear envío
              </Button>
            </div>
          </>
        ) : null}
      </div>
    </Modal>
  )
}

function BroadcastDetail({
  broadcast,
  onRefresh,
  session,
}: {
  broadcast: Broadcast
  onRefresh: () => Promise<void>
  session: { token: string; onUnauthorized: () => void }
}) {
  const [recipients, setRecipients] = useState<BroadcastRecipient[]>([])
  const [recipientCursor, setRecipientCursor] = useState<string | null>(null)
  const [recipientStatus, setRecipientStatus] = useState<RecipientStatus | ''>('')
  const [recipientSearch, setRecipientSearch] = useState('')
  const [selectedRecipient, setSelectedRecipient] = useState<BroadcastRecipient | null>(null)
  const [attempts, setAttempts] = useState<BroadcastAttempt[]>([])
  const [attemptCursor, setAttemptCursor] = useState<string | null>(null)
  const [auditEvents, setAuditEvents] = useState<BroadcastAuditEvent[]>([])
  const [auditCursor, setAuditCursor] = useState<string | null>(null)
  const [isEditingDraft, setIsEditingDraft] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const refreshRecipients = useCallback(async () => {
    const page = await listBroadcastRecipients(broadcast.id, session, {
      status: recipientStatus || undefined,
      search: recipientSearch,
    })
    setRecipients(page.items)
    setRecipientCursor(page.next_cursor)
  }, [broadcast.id, recipientSearch, recipientStatus, session])
  useEffect(() => {
    void refreshRecipients().catch((caught: unknown) => setError(errorText(caught)))
  }, [refreshRecipients])
  useEffect(() => {
    void listBroadcastAuditEvents(broadcast.id, session)
      .then((page) => {
        setAuditEvents(page.items)
        setAuditCursor(page.next_cursor)
      })
      .catch((caught: unknown) => setError(errorText(caught)))
  }, [broadcast.id, session])
  useEffect(() => {
    if (broadcast.status !== 'PROCESSING') return
    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') void onRefresh()
    }, 15_000)
    return () => window.clearInterval(interval)
  }, [broadcast.status, onRefresh])
  const command = async (kind: 'start' | 'process') => {
    setPending(true)
    setError(null)
    try {
      if (kind === 'start') await startBroadcast(broadcast.id, crypto.randomUUID(), session)
      else await processBroadcast(broadcast.id, crypto.randomUUID(), session)
      await onRefresh()
    } catch (caught) {
      setError(errorText(caught))
    } finally {
      setPending(false)
    }
  }
  const loadMoreRecipients = async () => {
    if (!recipientCursor) return
    const page = await listBroadcastRecipients(broadcast.id, session, {
      cursor: recipientCursor,
      status: recipientStatus || undefined,
      search: recipientSearch,
    })
    setRecipients((current) => [...current, ...page.items])
    setRecipientCursor(page.next_cursor)
  }
  const showAttempts = async (recipient: BroadcastRecipient) => {
    setSelectedRecipient(recipient)
    try {
      const page = await listBroadcastAttempts(broadcast.id, recipient.id, session)
      setAttempts(page.items)
      setAttemptCursor(page.next_cursor)
    } catch (caught) {
      setError(errorText(caught))
    }
  }
  const loadMoreAttempts = async () => {
    if (!selectedRecipient || !attemptCursor) return
    const page = await listBroadcastAttempts(
      broadcast.id,
      selectedRecipient.id,
      session,
      attemptCursor,
    )
    setAttempts((current) => [...current, ...page.items])
    setAttemptCursor(page.next_cursor)
  }
  const loadMoreAuditEvents = async () => {
    if (!auditCursor) return
    const page = await listBroadcastAuditEvents(broadcast.id, session, auditCursor)
    setAuditEvents((current) => [...current, ...page.items])
    setAuditCursor(page.next_cursor)
  }
  const retry = async (recipient: BroadcastRecipient) => {
    setPending(true)
    setError(null)
    try {
      await retryBroadcast(broadcast.id, recipient.id, crypto.randomUUID(), session)
      await Promise.all([onRefresh(), refreshRecipients()])
    } catch (caught) {
      setError(errorText(caught))
    } finally {
      setPending(false)
    }
  }
  return (
    <section className='space-y-5' aria-labelledby='broadcast-detail-title'>
      <header className='flex flex-wrap items-start justify-between gap-3'>
        <div>
          <AppLink className='text-sm text-[var(--text-link)]' to='/whatsapp-sends'>
            Volver a envíos
          </AppLink>
          <h2 className='mt-2 text-lg font-semibold' id='broadcast-detail-title'>
            {broadcast.label}
          </h2>
          <p className='text-sm text-[var(--text-secondary)]'>
            {broadcast.template_name} · {broadcast.template_language}
          </p>
        </div>
        <Badge tone={statusTone(broadcast.status)}>{broadcast.status}</Badge>
      </header>
      {error ? <p role='alert'>{error}</p> : null}
      <div className='lost-statistics'>
        <p>
          <span className='block text-xs text-[var(--text-secondary)]'>Clientes</span>
          {broadcast.recipient_count}
        </p>
        <p>
          <span className='block text-xs text-[var(--text-secondary)]'>Versión</span>
          {broadcast.version}
        </p>
        <p>
          <span className='block text-xs text-[var(--text-secondary)]'>Estado</span>
          {broadcast.status}
        </p>
      </div>
      {broadcast.status === 'CONFIRMED' ? (
        <Button
          disabled={pending}
          onClick={() => void command('start')}
          type='button'
          variant='primary'
        >
          Iniciar procesamiento
        </Button>
      ) : null}
      {broadcast.status === 'DRAFT' ? (
        <Button onClick={() => setIsEditingDraft(true)} type='button' variant='primary'>
          Editar borrador
        </Button>
      ) : null}
      {broadcast.status === 'PROCESSING' ? (
        <Button
          disabled={pending}
          onClick={() => void command('process')}
          type='button'
          variant='primary'
        >
          Procesar siguiente lote
        </Button>
      ) : null}
      <section className='ui-panel p-4' aria-labelledby='recipient-results-title'>
        <h3 className='font-semibold' id='recipient-results-title'>
          Resultados por destinatario
        </h3>
        <Toolbar aria-label='Filtrar resultados de destinatarios' className='mt-3'>
          <SearchField
            id='broadcast-recipient-search'
            label='Buscar destinatario'
            onChange={(event) => setRecipientSearch(event.target.value)}
            placeholder='Buscar cliente'
            value={recipientSearch}
          />
          <FilterControl
            id='broadcast-recipient-status'
            label='Filtrar resultado'
            onChange={(event) => setRecipientStatus(event.target.value as RecipientStatus | '')}
            value={recipientStatus}
          >
            <option value=''>Todos</option>
            <option value='DELIVERED'>Entregados</option>
            <option value='READ'>Leídos</option>
            <option value='FAILED'>Fallidos</option>
            <option value='UNKNOWN'>Inciertos</option>
            <option value='BLOCKED'>Omitidos</option>
          </FilterControl>
        </Toolbar>
        <ul className='mt-3 divide-y divide-[var(--border-subtle)]'>
          {recipients.map((recipient) => (
            <li
              className='flex flex-wrap items-center justify-between gap-2 py-3'
              key={recipient.id}
            >
              <span>
                {recipient.customer_display_name}
                <span className='ml-2 text-xs text-[var(--text-secondary)]'>
                  {recipient.phone_display}
                </span>
              </span>
              <span className='flex items-center gap-2'>
                <Badge tone={recipientTone(recipient.status)}>{recipient.status}</Badge>
                {recipient.conversation_id ? (
                  <AppLink
                    className='text-sm text-[var(--text-link)]'
                    to={{ kind: 'conversation', conversationId: recipient.conversation_id }}
                  >
                    Abrir conversación
                  </AppLink>
                ) : null}
              </span>
              {recipient.safe_reason ? (
                <p className='w-full text-xs text-[var(--text-secondary)]'>
                  {recipient.safe_reason}
                </p>
              ) : null}
              <div className='flex w-full flex-wrap gap-2'>
                <Button onClick={() => void showAttempts(recipient)} type='button' variant='ghost'>
                  Ver intentos
                </Button>
                {recipient.status === 'UNKNOWN' ? (
                  <p className='text-xs text-[var(--warning-text)]'>
                    Entrega incierta: reenviar podría duplicar el envío.
                  </p>
                ) : null}
                {recipient.retry_eligible ? (
                  <Button
                    disabled={pending}
                    onClick={() => void retry(recipient)}
                    type='button'
                    variant='ghost'
                  >
                    Reintentar fallo definitivo
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
        {recipientCursor ? (
          <Button onClick={() => void loadMoreRecipients()} type='button' variant='ghost'>
            Cargar más resultados
          </Button>
        ) : null}
      </section>
      {selectedRecipient ? (
        <section className='ui-panel p-4' aria-labelledby='attempt-history-title'>
          <h3 className='font-semibold' id='attempt-history-title'>
            Intentos de {selectedRecipient.customer_display_name}
          </h3>
          <ul className='mt-3 divide-y divide-[var(--border-subtle)] text-sm'>
            {attempts.map((attempt) => (
              <li className='py-2' key={attempt.id}>
                Intento {attempt.attempt_number}: {attempt.outcome} ·{' '}
                {new Date(attempt.occurred_at).toLocaleString('es-AR')}
                {attempt.safe_reason ? (
                  <span className='block text-xs'>{attempt.safe_reason}</span>
                ) : null}
              </li>
            ))}
          </ul>
          {attemptCursor ? (
            <Button onClick={() => void loadMoreAttempts()} type='button' variant='ghost'>
              Cargar más intentos
            </Button>
          ) : null}
        </section>
      ) : null}
      <section className='ui-panel p-4' aria-labelledby='broadcast-audit-title'>
        <h3 className='font-semibold' id='broadcast-audit-title'>
          Auditoría
        </h3>
        <ul className='mt-3 divide-y divide-[var(--border-subtle)] text-sm'>
          {auditEvents.map((event) => (
            <li className='py-2' key={event.id}>
              {event.event_type}
              {event.reason_code ? ` · ${event.reason_code}` : ''}
              <span className='ml-2 text-xs text-[var(--text-secondary)]'>
                {new Date(event.occurred_at).toLocaleString('es-AR')}
              </span>
            </li>
          ))}
        </ul>
        {auditCursor ? (
          <Button onClick={() => void loadMoreAuditEvents()} type='button' variant='ghost'>
            Cargar más eventos
          </Button>
        ) : null}
      </section>
      <BroadcastCreation
        initialDraft={broadcast}
        isOpen={isEditingDraft}
        onClose={() => {
          setIsEditingDraft(false)
          void onRefresh()
        }}
        session={session}
      />
    </section>
  )
}
