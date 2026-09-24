# CRM-053 — Opportunity Detail Soft Delete

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-24
Implementation commit: 28f5028b3b1a2a6b18575b616829b823529cc069

## Goal

Allow an authorized FAA user to remove an Opportunity from its detail view without
losing the commercial and communication evidence that belongs to it.

## Context

CRM-001 already defines `Opportunity.deleted_at`, idempotent soft deletion, retained
history, and exclusion from normal operational queries. CRM-012 defines commercial
projections that exclude soft-deleted Opportunities. The approved CRM-053 revision
allows every authenticated CRM role that can access an Opportunity Detail to request
this soft deletion; it replaces the prior supervisor-only deletion permission without
changing any other role permission.

`docs/BUSINESS_RULES.md` remains authoritative for the commercial lifecycle and
WhatsApp linking.

## Dependencies

- CRM-001 — Core CRM
- CRM-012 — CRM Commercial Completion

## Scope

- Add an authenticated-role secondary destructive action, `Eliminar oportunidad`, to
  Opportunity Detail on Pipeline, Ganadas, and Perdidas.
- Require a centered destructive confirmation modal with title `Eliminar oportunidad`,
  the message `¿Seguro que querés eliminar esta oportunidad? Esta acción la quitará de
  las vistas comerciales.`, and `Cancelar` / red `Eliminar oportunidad` actions.
- Reuse the existing idempotent soft-delete service through an authenticated DELETE
  endpoint; no new persistence field or migration is needed.
- On success, close the detail, return to the existing originating workspace, and
  remove or refresh only the deleted Opportunity's current projection without a full
  browser reload. Preserve workspace URL filters, search, scroll, and local state
  where the current workspace supports them.
- Keep error feedback in the confirmation modal, disable duplicate submissions, and
  preserve data when cancelled, closed, or dismissed with Escape.

## Non-goals

- Physical deletion, restore/undelete, bulk deletion, a new audit-log entity, or a
  new opportunity lifecycle transition.
- Deleting Customers, WhatsApp Conversations, Messages, media, quotes, status/loss
  history, notes, notifications, or other linked evidence.
- Changing opportunity visibility, commercial rules, metrics formulas, or WhatsApp
  behavior.

## Business rules

- Any authenticated current CRM role (`SUPERVISOR` or `VENDEDOR`) that can access an
  Opportunity Detail may request deletion. The action is visible to both roles and
  unauthenticated requests remain rejected.
- Deletion sets `deleted_at`; a repeated DELETE for the same existing Opportunity is
  successful and leaves the retained record unchanged after the first deletion.
- The Customer and all linked WhatsApp evidence remain intact. Existing query and
  metric semantics exclude the deleted Opportunity through `deleted_at`.
- Cancellation, Escape, or modal close produces no mutation. A failed request keeps
  the modal open with retryable Spanish feedback.

## Data model

No schema change. Reuse `Opportunity.deleted_at`, retained foreign keys, and existing
soft-delete side effects for notifications and Legendary recalculation.

## Contracts / API

- `DELETE /api/opportunities/{opportunity_id}` requires the existing authenticated
  user dependency and responds `204 No Content` for an active or already-deleted
  existing Opportunity.
- Existing normal detail/list endpoints continue returning `404` / excluding the
  soft-deleted Opportunity according to their current filters.

## State transitions

This is not a commercial status transition. It changes only the soft-delete visibility
state, preserves the Opportunity's commercial status and retained history, and has no
automatic restore path.

## Security & permissions

The endpoint uses the established authenticated-user authorization. The frontend does
not rely on controls as authorization, but renders the destructive action for both
current authenticated roles. This revision does not broaden access to hidden
workspaces, administration screens, or unrelated role-protected operations. No secret
or provider data is added.

## Edge cases

- A second request after a completed deletion is idempotent.
- While a request is pending, both confirmation actions and modal close are disabled.
- A stale detail after another actor deletes it is handled as a safe failure response;
  the workspace remains usable and no second destructive mutation occurs.
- The modal follows the existing accessible Modal behavior: initial Cancel focus,
  focus trap/restoration, Escape dismissal when not pending, and visible focus styles.

## Acceptance criteria

- AC-01: A supervisor and a vendor can open the destructive confirmation from a
  Pipeline, Ganadas, or Perdidas Opportunity Detail; unauthenticated requests are
  rejected.
- AC-02: The modal uses the required Spanish title/message, destructive red confirm
  button, Cancel action, and behaves correctly in Light and Dark themes.
- AC-03: Cancel, close, and Escape make no DELETE request and leave the detail and
  workspace unchanged.
- AC-04: Successful deletion calls the idempotent API once, closes the detail, and
  removes the Opportunity from the originating workspace without a browser reload;
  active workspace state is retained where supported.
- AC-05: Pending deletion prevents duplicate requests; failure keeps the modal open
  with a Spanish error and a usable retry path.
- AC-06: Soft deletion hides the Opportunity from operational lists and metrics while
  retaining Customer, quote/history, and WhatsApp Conversation/Message evidence.
- AC-07: Keyboard navigation, initial focus, Escape behavior, and focus restoration
  remain accessible.

## Open decisions

None.

## Follow-up / future specs

None.

## Implementation notes

Use the existing shared `ConfirmationDialog`, `Modal`, `OpportunityService`, query
filters, and workspace state patterns. Do not create a parallel delete implementation
or alter cascade constraints. Change only the delete-operation authorization; retain
all unrelated role permissions.
