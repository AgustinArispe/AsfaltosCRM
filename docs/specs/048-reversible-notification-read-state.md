# CRM-048 — Reversible Notification Read State

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-18
Implementation commit: N/A

## Goal

Allow a user to return an already-read CRM notification to the unread state so it
remains visible as personal follow-up, while preserving the existing open-and-read
interaction and Opportunity navigation.

## Context

CRM-022 defines the Notifications workspace and opening acknowledgement. CRM-042
stores read state per recipient. The current state transition is one-way
(`NULL -> read_at`), although the existing recipient model can represent both read and
unread without a persistence change.

## Dependencies

- CRM-022 — Notifications UI
- CRM-042 — Dashboard Visibility and Per-user Lead Notifications

## Scope

- Add an authenticated, user-scoped command that sets one notification recipient to
  either read or unread.
- Add a compact row action whose label and icon expose the inverse of the current
  state.
- Reconcile the row, selected notification view, and active-unread sidebar/header
  attention count without a full page reload.
- Preserve the existing behavior that opening an unread notification marks it read
  and navigates to its Opportunity.
- Cover state transitions, idempotency, ownership, accessibility, and Light/Dark
  presentation with backend and frontend tests.

## Non-goals

- Changing notification creation, recipient assignment, resolution, retention,
  polling, or bulk-read semantics.
- Creating notification copies, snooze/reminder scheduling, deletion, or changing
  Opportunity navigation.
- Adding a database migration or a new frontend state-management dependency.

## Business rules

- Read/unread remains personal to the authenticated recipient and never changes
  another user's receipt.
- Changing read state does not create, resolve, delete, or duplicate a logical
  notification.
- Opening an unread notification keeps the existing read acknowledgement and
  navigation behavior.
- A resolved historical notification may be marked read or unread, but it does not
  contribute to the active-unread attention count.

## Data model

No schema change. `notification_recipients.read_at` remains authoritative:

- unread: `read_at IS NULL`;
- read: `read_at` contains the first successful transition time for the current read
  cycle.

## Contracts / API

- Add `PUT /notifications/{notification_id}/read-state` with the strict request body
  `{ "is_read": boolean }`.
- Return the existing `NotificationResponse`, including the authenticated recipient's
  authoritative `read_at`.
- Preserve `POST /notifications/{notification_id}/read` for open-and-read behavior and
  compatibility.
- Requests for a notification outside the authenticated user's recipient set return
  the existing not-found response and reveal no notification metadata.

## State transitions

- unread -> read: set a timezone-aware UTC `read_at` when it is currently null.
- read -> unread: set `read_at` to null.
- unread -> unread and read -> read are successful no-ops.
- A repeated read request preserves the existing timestamp; retries do not fabricate
  a new notification or another recipient.

## Security & permissions

- Authentication and recipient ownership checks remain identical to the existing
  single-read command.
- The command locks and mutates only the authenticated user's recipient row.
- Both current roles, `SUPERVISOR` and `VENDEDOR`, retain the same access.

## Edge cases

- Toggling a resolved notification updates only historical personal read state and not
  the active attention count.
- In the `Sin leer` view, a successful unread -> read transition removes the row and
  decrements that view's total; read -> unread is available from views containing read
  rows.
- A failed request retains the last authoritative visual state and reports a
  recoverable inline error.
- The row action never activates Opportunity navigation; the rest of the row keeps its
  current navigation target.

## Acceptance criteria

- AC-01: A read recipient can be marked unread and an unread recipient can be marked
  read through an idempotent authenticated API without creating records.
- AC-02: Repeated requests for either target state are safe, preserve ownership, and
  preserve the existing timestamp for repeated read requests.
- AC-03: Opening an unread notification still acknowledges it and navigates to the same
  Opportunity route as before.
- AC-04: Every row exposes a compact native-button inverse action with a clear Spanish
  accessible name, tooltip, visible keyboard focus, and no nested interactive control.
- AC-05: A successful action immediately reconciles row styling/text and the current
  list without a document reload; a failed action leaves the prior state visible.
- AC-06: The active-unread attention badge changes by exactly one for active
  notifications, remains unchanged for resolved history, and is reconciled with the
  backend refresh path.
- AC-07: Read and unread styling remains distinguishable by text/icon as well as color
  in Light and Dark modes, using existing semantic tokens.
- AC-08: Focused backend, frontend, and Docker Compose browser checks plus all required
  repository gates pass.

## Open decisions

None.

## Follow-up / future specs

None.

## Implementation notes

Prefer one typed service method that sets the desired boolean state. Keep the existing
read endpoint as a thin compatibility wrapper. Use the existing notification response
and attention context rather than a global store or a list reload.
