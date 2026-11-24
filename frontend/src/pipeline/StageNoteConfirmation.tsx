import { type ComponentProps, useEffect, useState } from 'react'
import { ConfirmationDialog } from '../shared/ConfirmationDialog'
import { StageNoteField } from './StageNoteField'
import { StageProvinceField } from './StageProvinceField'

type Props = Omit<ComponentProps<typeof ConfirmationDialog>, 'onConfirm'> & {
  onConfirm: (note: string, province?: string, customerNote?: string) => void
  suggestProvince?: boolean
}

export function StageNoteConfirmation({
  onConfirm,
  children,
  suggestProvince = false,
  ...props
}: Props) {
  const [note, setNote] = useState('')
  const [customerNote, setCustomerNote] = useState('')
  const [province, setProvince] = useState('')
  useEffect(() => {
    if (!props.isOpen) {
      setNote('')
      setCustomerNote('')
      setProvince('')
    }
  }, [props.isOpen])
  if (!props.isOpen) return null
  return (
    <ConfirmationDialog
      {...props}
      onConfirm={() =>
        onConfirm(
          note.trim(),
          suggestProvince ? province.trim() || undefined : undefined,
          customerNote.trim() || undefined,
        )
      }
    >
      {children}
      <StageNoteField
        customerNote={customerNote}
        onCustomerNoteChange={setCustomerNote}
        disabled={props.isPending}
        onChange={setNote}
        value={note}
      />
      {suggestProvince ? (
        <StageProvinceField disabled={props.isPending} onChange={setProvince} value={province} />
      ) : null}
    </ConfirmationDialog>
  )
}
