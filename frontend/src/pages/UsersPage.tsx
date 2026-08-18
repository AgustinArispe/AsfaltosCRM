import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'

import type { ApiSession } from '../api/opportunities'
import { createUser, listUsers, replaceUserPassword, updateUser } from '../api/users'
import { useAuth } from '../auth/AuthContext'
import type { AuthUser, UserRole } from '../auth/types'
import { Badge } from '../shared/Badge'
import { Button } from '../shared/Button'
import { ConfirmationDialog } from '../shared/ConfirmationDialog'
import { Input, Select } from '../shared/FormControls'
import { InlineFeedback } from '../shared/InlineFeedback'
import { Modal } from '../shared/Modal'
import { EmptyState } from '../shared/StatusStates'
import { WorkspaceSkeleton } from '../shared/WorkspaceSkeleton'

type UserDraft = { fullName: string; email: string; role: UserRole; password: string }

const EMPTY_DRAFT: UserDraft = { fullName: '', email: '', role: 'VENDEDOR', password: '' }

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'No pudimos completar la operación.'
}

export function UsersPage() {
  const { token, logout } = useAuth()
  const session = useMemo<ApiSession>(
    () => ({ token: token ?? '', onUnauthorized: logout }),
    [logout, token],
  )
  const [users, setUsers] = useState<AuthUser[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [editing, setEditing] = useState<AuthUser | null>(null)
  const [passwordTarget, setPasswordTarget] = useState<AuthUser | null>(null)
  const [statusTarget, setStatusTarget] = useState<AuthUser | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [draft, setDraft] = useState<UserDraft>(EMPTY_DRAFT)
  const [password, setPassword] = useState('')
  const [operationError, setOperationError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [busyIds, setBusyIds] = useState<Set<number>>(new Set())
  const [announcement, setAnnouncement] = useState('')

  const load = useCallback(() => {
    setIsLoading(true)
    setLoadError(null)
    void listUsers(session)
      .then(setUsers)
      .catch((error: unknown) => setLoadError(errorMessage(error)))
      .finally(() => setIsLoading(false))
  }, [session])

  useEffect(load, [load])

  const closeEditor = () => {
    setEditing(null)
    setIsCreating(false)
    setDraft(EMPTY_DRAFT)
    setOperationError(null)
  }
  const openCreate = () => {
    setDraft(EMPTY_DRAFT)
    setIsCreating(true)
  }
  const openEdit = (item: AuthUser) => {
    setDraft({ fullName: item.full_name, email: item.email, role: item.role, password: '' })
    setEditing(item)
  }
  const save = async (event: FormEvent) => {
    event.preventDefault()
    setIsSaving(true)
    setOperationError(null)
    try {
      const saved = editing
        ? await updateUser(
            editing.id,
            { full_name: draft.fullName, email: draft.email, role: draft.role },
            session,
          )
        : await createUser(
            {
              full_name: draft.fullName,
              email: draft.email,
              role: draft.role,
              password: draft.password,
            },
            session,
          )
      setUsers((current) =>
        editing
          ? current.map((item) => (item.id === saved.id ? saved : item))
          : [...current, saved],
      )
      setAnnouncement(
        editing ? `${saved.full_name} fue actualizado.` : `${saved.full_name} fue creado.`,
      )
      closeEditor()
    } catch (error) {
      setOperationError(errorMessage(error))
    } finally {
      setIsSaving(false)
    }
  }
  const changePassword = async (event: FormEvent) => {
    event.preventDefault()
    if (!passwordTarget) return
    setIsSaving(true)
    setOperationError(null)
    try {
      await replaceUserPassword(passwordTarget.id, password, session)
      setAnnouncement(`La contraseña de ${passwordTarget.full_name} fue reemplazada.`)
      setPasswordTarget(null)
      setPassword('')
    } catch (error) {
      setOperationError(errorMessage(error))
    } finally {
      setIsSaving(false)
    }
  }
  const toggleActive = async (item: AuthUser) => {
    setBusyIds((current) => new Set(current).add(item.id))
    setOperationError(null)
    try {
      const saved = await updateUser(item.id, { is_active: !item.is_active }, session)
      setUsers((current) => current.map((user) => (user.id === saved.id ? saved : user)))
      setAnnouncement(`${saved.full_name} quedó ${saved.is_active ? 'activo' : 'inactivo'}.`)
      setStatusTarget(null)
    } catch (error) {
      setOperationError(errorMessage(error))
    } finally {
      setBusyIds((current) => {
        const next = new Set(current)
        next.delete(item.id)
        return next
      })
    }
  }

  return (
    <section aria-label='Administración de usuarios' className='mx-auto max-w-5xl'>
      <p aria-live='polite' className='sr-only'>
        {announcement}
      </p>
      <div className='flex justify-end'>
        <Button onClick={openCreate} variant='primary'>
          Nuevo usuario
        </Button>
      </div>
      {operationError ? (
        <div className='mt-4'>
          <InlineFeedback message={operationError} onDismiss={() => setOperationError(null)} />
        </div>
      ) : null}
      <div className='mt-4'>
        {isLoading ? (
          <WorkspaceSkeleton label='Cargando usuarios…' />
        ) : loadError ? (
          <div className='py-5'>
            <InlineFeedback message={loadError} />
            <Button className='mt-3' onClick={load}>
              Reintentar
            </Button>
          </div>
        ) : users.length === 0 ? (
          <EmptyState
            description='Creá el primer acceso para el equipo comercial.'
            icon='users'
            size='workspace'
            title='Todavía no hay usuarios'
          />
        ) : (
          <section aria-label='Usuarios de FAA' className='ui-panel overflow-x-auto'>
            <table className='w-full min-w-[42rem] border-collapse text-left text-sm'>
              <thead>
                <tr className='border-b border-[var(--divider)] text-xs text-[var(--text-secondary)]'>
                  <th className='px-4 py-3'>Usuario</th>
                  <th className='px-4 py-3'>Rol</th>
                  <th className='px-4 py-3'>Estado</th>
                  <th className='px-4 py-3 text-right'>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.map((item) => (
                  <tr
                    className='border-b border-[var(--divider)] last:border-0 hover:bg-[var(--surface-hover)]'
                    key={item.id}
                  >
                    <th className='px-4 py-3 font-semibold'>
                      <span>{item.full_name}</span>
                      <span className='mt-0.5 block font-normal text-[var(--text-secondary)]'>
                        {item.email}
                      </span>
                    </th>
                    <td className='px-4 py-3'>
                      {item.role === 'SUPERVISOR' ? 'Supervisor' : 'Vendedor'}
                    </td>
                    <td className='px-4 py-3'>
                      <Badge tone={item.is_active ? 'active' : 'neutral'}>
                        {item.is_active ? 'Activo' : 'Inactivo'}
                      </Badge>
                    </td>
                    <td className='px-4 py-3'>
                      <div className='flex justify-end gap-1'>
                        <Button onClick={() => openEdit(item)} size='compact' variant='ghost'>
                          Editar
                        </Button>
                        <Button
                          onClick={() => {
                            setPasswordTarget(item)
                            setPassword('')
                            setOperationError(null)
                          }}
                          size='compact'
                          variant='ghost'
                        >
                          Contraseña
                        </Button>
                        <Button
                          disabled={busyIds.has(item.id)}
                          onClick={() => setStatusTarget(item)}
                          size='compact'
                          variant='ghost'
                        >
                          {item.is_active ? 'Desactivar' : 'Activar'}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </div>
      <Modal
        closeDisabled={isSaving}
        description={
          editing
            ? 'Actualizá identidad y rol sin modificar la contraseña.'
            : 'Creá un acceso con uno de los roles aprobados.'
        }
        isOpen={isCreating || editing !== null}
        onClose={closeEditor}
        title={editing ? 'Editar usuario' : 'Nuevo usuario'}
      >
        <form onSubmit={(event) => void save(event)}>
          <div className='grid gap-4 px-5 py-5'>
            <Input
              autoComplete='name'
              data-modal-initial-focus
              id='user-full-name'
              label='Nombre completo'
              onChange={(event) =>
                setDraft((current) => ({ ...current, fullName: event.target.value }))
              }
              required
              value={draft.fullName}
            />
            <Input
              autoComplete='email'
              id='user-email'
              label='Email'
              onChange={(event) =>
                setDraft((current) => ({ ...current, email: event.target.value }))
              }
              required
              type='email'
              value={draft.email}
            />
            <Select
              id='user-role'
              label='Rol'
              onChange={(event) =>
                setDraft((current) => ({ ...current, role: event.target.value as UserRole }))
              }
              value={draft.role}
            >
              <option value='VENDEDOR'>Vendedor</option>
              <option value='SUPERVISOR'>Supervisor</option>
            </Select>
            {!editing ? (
              <Input
                autoComplete='new-password'
                description='Entre 8 y 128 caracteres.'
                id='user-password'
                label='Contraseña inicial'
                minLength={8}
                maxLength={128}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, password: event.target.value }))
                }
                required
                type='password'
                value={draft.password}
              />
            ) : null}
            {operationError ? <InlineFeedback message={operationError} /> : null}
          </div>
          <footer className='flex justify-end gap-2 border-t border-[var(--divider)] px-5 py-4'>
            <Button disabled={isSaving} onClick={closeEditor} type='button'>
              Cancelar
            </Button>
            <Button isLoading={isSaving} type='submit' variant='primary'>
              Guardar usuario
            </Button>
          </footer>
        </form>
      </Modal>
      <ConfirmationDialog
        confirmLabel={statusTarget?.is_active ? 'Desactivar usuario' : 'Activar usuario'}
        description={
          statusTarget?.is_active
            ? 'El acceso y las sesiones vigentes serán revocados.'
            : 'El usuario podrá volver a iniciar sesión.'
        }
        error={operationError}
        isOpen={statusTarget !== null}
        isPending={Boolean(statusTarget && busyIds.has(statusTarget.id))}
        onCancel={() => {
          setStatusTarget(null)
          setOperationError(null)
        }}
        onConfirm={() => {
          if (statusTarget) void toggleActive(statusTarget)
        }}
        pendingLabel='Guardando…'
        title={statusTarget?.is_active ? 'Desactivar acceso' : 'Activar acceso'}
        variant={statusTarget?.is_active ? 'danger' : 'primary'}
      >
        <p className='text-sm text-[var(--text-secondary)]'>{statusTarget?.full_name}</p>
      </ConfirmationDialog>
      <Modal
        closeDisabled={isSaving}
        description='Este reemplazo no requiere conocer la contraseña anterior.'
        isOpen={passwordTarget !== null}
        onClose={() => {
          setPasswordTarget(null)
          setOperationError(null)
        }}
        title='Reemplazar contraseña'
      >
        <form onSubmit={(event) => void changePassword(event)}>
          <div className='grid gap-4 px-5 py-5'>
            <Input
              autoComplete='new-password'
              data-modal-initial-focus
              description='Entre 8 y 128 caracteres.'
              id='replacement-password'
              label='Nueva contraseña'
              maxLength={128}
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              required
              type='password'
              value={password}
            />
            {operationError ? <InlineFeedback message={operationError} /> : null}
          </div>
          <footer className='flex justify-end gap-2 border-t border-[var(--divider)] px-5 py-4'>
            <Button disabled={isSaving} onClick={() => setPasswordTarget(null)} type='button'>
              Cancelar
            </Button>
            <Button isLoading={isSaving} type='submit' variant='primary'>
              Reemplazar
            </Button>
          </footer>
        </form>
      </Modal>
    </section>
  )
}
