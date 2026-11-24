export function showModalWithScrollLock(dialog: HTMLDialogElement) {
  const root = document.documentElement
  if (!root.querySelector('dialog[open]')) {
    root.toggleAttribute('data-modal-scrollbar-gutter', window.innerWidth > root.clientWidth)
  }
  dialog.showModal()
}
