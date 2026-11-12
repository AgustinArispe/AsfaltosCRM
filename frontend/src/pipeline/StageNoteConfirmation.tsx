import { type ComponentProps, useEffect, useState } from 'react'
import { ConfirmationDialog } from '../shared/ConfirmationDialog'
import { StageNoteField } from './StageNoteField'
import { StageProvinceField } from './StageProvinceField'

type Props = Omit<ComponentProps<typeof ConfirmationDialog>, 'onConfirm'> & {
  onConfirm: (note: string, province?: string) => void
  suggestProvince?: boolean
}

export function StageNoteConfirmation({
  onConfirm,
  children,
  suggestProvince = false,
  ...props
}: Props) {
  const [note, setNote] = useState('')
  const [province, setProvince] = useState('')
  useEffect(() => {
    if (!props.isOpen) {
      setNote('')
      setProvince('')
    }
  }, [props.isOpen])
  if (!props.isOpen) return null
  return (
    <ConfirmationDialog
      {...props}
      confirmDisabled={!note.trim()}
      onConfirm={() =>
        onConfirm(note.trim(), suggestProvince ? province.trim() || undefined : undefined)
      }
    >
      {children}
      <StageNoteField disabled={props.isPending} onChange={setNote} value={note} />
      {suggestProvince ? (
        <StageProvinceField disabled={props.isPending} onChange={setProvince} value={province} />
      ) : null}
    </ConfirmationDialog>
  )
}
