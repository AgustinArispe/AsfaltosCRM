# CRM-062 — Customer notes and optional stage notes

Status: Approved
Last updated: 2026-11-24

## Request and scope

Offer an optional, recommended stage note on each manual stage change. The
transition remains in activity with its actor and date even without a note.
Keep existing product, quantity, loss reason, province and transition rules.

Add Para recordar to the customer sheet and WhatsApp CRM context. Both CRM
roles can add, edit, pin and archive short internal customer notes. Keep the
original author and creation time. Show pinned notes first, with at most three
per customer. The WhatsApp panel shows a compact preview. Allow a customer
note to be entered alongside a stage note and save it in the same transaction
as the stage change. Notes stay with the customer across opportunities.

## Acceptance criteria

- All manual transitions accept omitted, null or whitespace-only notes. A
  supplied stage note stays in opportunity activity and customer stage history.
- Customer notes are scoped to the customer, preserve authorship, and are
  visible from the sheet and WhatsApp. Only active notes appear. Pinning is
  bounded and serialized per customer.
- A stage change can save either note or both. Cancelled, invalid and replayed
  transitions do not duplicate customer notes or leave partial writes.
- Existing data and automatic intake remain valid through the migration.

## Non-goals

Automatic profiling, historical inference, external messages and reminders.

## Open decisions

None.
