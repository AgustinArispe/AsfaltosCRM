import type { ReactNode } from 'react'

import { Button, type ButtonVariant } from './Button'
import { InlineFeedback } from './InlineFeedback'
import { Modal } from './Modal'

export function ConfirmationDialog({
  isOpen,
  title,
  description,
  children,
  confirmLabel,
  pendingLabel,
  isPending = false,
  error,
  variant = 'primary',
  onCancel,
  onConfirm,
}: {
  isOpen: boolean
  title: string
  description?: string
  children: ReactNode
  confirmLabel: string
  pendingLabel: string
  isPending?: boolean
  error?: string | null
  variant?: Extract<ButtonVariant, 'primary' | 'danger'>
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <Modal
      closeDisabled={isPending}
      description={description}
      isOpen={isOpen}
      onClose={onCancel}
      title={title}
    >
      <div className='space-y-3 px-5 py-5'>
        {error ? <InlineFeedback message={error} /> : null}
        {children}
      </div>
      <footer className='flex flex-wrap justify-end gap-3 border-t border-[var(--border-default)] px-5 py-4'>
        <Button data-modal-initial-focus disabled={isPending} onClick={onCancel}>
          Cancelar
        </Button>
        <Button disabled={isPending} onClick={onConfirm} variant={variant}>
          {isPending ? pendingLabel : confirmLabel}
        </Button>
      </footer>
    </Modal>
  )
}
