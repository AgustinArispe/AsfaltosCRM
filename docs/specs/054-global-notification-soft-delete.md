# CRM-054 — Global Notification Soft Delete

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-24
Implementation commit: f7d0fd22e10a563a35ca8abe2cf5952d60e76b6a

## Goal

Allow either authenticated CRM role to remove a notification globally from the
Notifications workspace, shared unread attention, and all team members' notification
lists while retaining the underlying operational evidence.

## Context

`docs/BUSINESS_RULES.md` defines notifications as global team events with per-user
read state. CRM-042 introduced recipient rows, and CRM-048 added personal read-state
changes. The approved user decision for this feature is different: deletion is global,
not personal, and is available to both current roles, `SUPERVISOR` and `VENDEDOR`.

## Dependencies

- CRM-022 — Notifications UI
- CRM-042 — Dashboard Visibility and Per-user Lead Notifications
- CRM-048 — Reversible Notification Read State

## Scope

- Add a secondary destructive action, `Eliminar notificación`, to each visible
  notification row for both authenticated CRM roles.
- Require a centered destructive confirmation dialog with title `Eliminar notificación`,
  a plain-Spanish explanation that it removes the notification for the entire team,
  `Cancelar`, and a red `Eliminar notificación` confirmation action.
- Add an authenticated, idempotent global soft-delete command for an event visible to
  the caller. It hides the notification for every recipient without deleting the
  notification row, recipient receipts, or Opportunity relationship.
- Reconcile the initiating workspace row, totals, unread attention, pending updates,
  and feedback without a browser reload. Other open sessions reconcile through the
  existing bounded notification refresh/focus/online path.

## Non-goals

- Physical deletion, restore/undelete, bulk deletion, personal-only dismissal, or a
  new notification type.
- Changing notification generation thresholds, read/unread behavior, resolution rules,
  Opportunity lifecycle, metrics formulas, or WhatsApp behavior.
- Deleting Opportunities, Customers, recipient evidence, timeline/history, or creating
  a new realtime transport.

## Business rules

- Deletion is global: once confirmed, the event is absent from every user's list,
  active/unread totals, and sidebar attention count.
- Both current authenticated roles may delete an event they can currently access; an
  unauthenticated caller or a caller without a recipient record receives the existing
  not-found/authentication behavior and cannot discover hidden event data.
- Deletion sets a timezone-aware `deleted_at` timestamp and preserves the notification,
  all recipient read receipts, and its linked Opportunity. Repeating DELETE for an
  existing visible-or-already-deleted event is successful and never creates duplicate
  effects.
- A deleted active stale event is intentionally not regenerated while its Opportunity
  remains in the same active status. The existing status-change resolution flow remains
  responsible for ending that event; a future eligible stale episode may create its own
  event under the existing rules.
- Delete confirmation is required. Escape, close, and Cancel do not mutate data;
  pending submission prevents duplicate requests; failure leaves the dialog open with
  retryable Spanish feedback.

## Data model

- Add nullable, timezone-aware `notifications.deleted_at` through an Alembic migration.
- Retain `notification_recipients` and all foreign keys; no recipient row is deleted.
- Normal notification reads, counts, and mutations exclude soft-deleted events.

## Contracts / API

- Add `DELETE /notifications/{notification_id}`. It requires the existing
  authenticated-user dependency and returns `204 No Content` for an event visible to
  the caller, including an already soft-deleted event.
- Existing list, unread-count, read, read-state, and read-all contracts exclude a
  deleted event. Existing callers keep their response shapes.

## State transitions

- visible -> deleted: set `deleted_at` once in UTC; preserve all remaining fields.
- deleted -> deleted: successful idempotent no-op.
- There is no restore transition in this feature.

## Security & permissions

- Authentication remains mandatory. Both current roles may execute the command only
  for a notification for which they have a recipient record.
- The frontend control is discoverable to both roles but is never the authorization
  boundary. No hidden workspace, administrative action, secret, or unrelated role
  permission changes.

## Edge cases

- A row removed from `Todas`, `Sin leer`, or `Seguimientos activos` updates only that
  workspace projection and retains its current filter/search/scroll state where
  supported.
- For an unread active notification, deletion immediately removes one local attention
  count; authoritative refresh reconciles every count afterwards.
- A concurrent delete is safe because the event is locked before setting `deleted_at`.
- A stale row opened or toggled after another user deletes it receives the existing
  safe not-found failure and does not navigate or mutate a deleted event.
- The dialog uses the existing accessible confirmation primitive: native controls,
  initial Cancel focus, focus trap/restoration, Escape dismissal while idle, visible
  focus, and status/error announcements.

## Acceptance criteria

- AC-01: Both supervisor and vendor see the compact destructive row action and can
  open the required global-delete confirmation; it is distinguishable in Light and
  Dark themes and accessible by keyboard.
- AC-02: Cancel, close, and Escape leave the notification, recipient evidence, totals,
  and workspace unchanged.
- AC-03: An authenticated caller can soft-delete a visible event; the API is idempotent,
  while unauthenticated and non-recipient callers cannot delete it.
- AC-04: A successful delete removes the event immediately from the initiator's current
  view and corrects totals/attention without a page reload; other sessions reconcile
  using their existing notification refresh path.
- AC-05: Pending deletion prevents duplicate submissions. A failure shows Spanish
  feedback, preserves the dialog/row, and allows retry.
- AC-06: Deleted events are excluded from all notification queries and counts, but the
  Notification, NotificationRecipient read evidence, and related Opportunity remain
  persisted and unaffected.
- AC-07: Focus, accessible names, Escape behavior, error announcement, responsive
  layout, backend/frontend/browser coverage, migration checks, and required quality
  gates pass.

## Open decisions

None.

## Follow-up / future specs

None.

## Implementation notes

Reuse the shared confirmation dialog, typed notifications API, notification attention
context, and `NotificationService`. Keep global-event locking and query filtering in
the service layer; do not physically cascade or create a parallel notification state
store.
