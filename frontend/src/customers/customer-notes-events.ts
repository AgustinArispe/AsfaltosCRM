export const CUSTOMER_NOTES_CHANGED = 'faa-customer-notes-changed'

export function notifyCustomerNotesChanged(customerId: number) {
  window.dispatchEvent(new CustomEvent(CUSTOMER_NOTES_CHANGED, { detail: customerId }))
}
