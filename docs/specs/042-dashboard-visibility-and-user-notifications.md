# CRM-042 — Dashboard Visibility and Per-user Lead Notifications

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-09
Implementation commit: a219c17bbb2edfec66d5303f54df2f2aa78e8db4

## Goal

Refine the existing Dashboard's commercial hierarchy, hide product surfaces that are
not currently presented to CRM users, and notify every active user when a new lead is
created while preserving independent read state.

## Context

CRM-041 supplies the authoritative period outcomes and active Pipeline snapshot.
CRM-003 and CRM-022 supply the existing internal notification event and UI. The current
notification table stores one global `read_at`, so independent user acknowledgement
requires a minimal recipient-state table and migration.

## Dependencies

- CRM-003 — Stale Opportunity Notifications
- CRM-022 — Notifications UI
- CRM-041 — Dashboard Commercial Overview and Outcome Navigation

## Scope

- Strengthen the existing result and active-opportunity hierarchy without redesigning
  the rest of Dashboard.
- Format the selected period in commercial Spanish and remove snapshot timestamp UI.
- Keep loss outcomes visible on Dashboard without linking to the Lost workspace.
- Hide Lost and WhatsApp Broadcast workspaces from navigation and redirect every direct
  frontend route owned by them to Dashboard.
- Store one logical notification plus one per-active-user recipient state and create a
  `NEW_LEAD` event for every Opportunity created through the shared creation service.
- Make notification lists, unread counts, single-read and read-all user-specific.

## Non-goals

- Removing Lost or Broadcast backend code, contracts, data, or history.
- Changing loss lifecycle, won history, attention semantics, Pipeline cards,
  Opportunity Detail, WhatsApp Inbox, or the global design system.
- External email or push notifications.

## Business rules

- A new Opportunity creates exactly one `NEW_LEAD` logical notification and a recipient
  state for every user active at creation time.
- Recipient membership is fixed at event creation; inactive users receive no row and
  later activation does not backfill old events.
- Reading is independent per recipient. New-lead notifications never count as stale
  follow-ups in Dashboard `Necesita atención`.
- Lead-intake replay returns its existing result before Opportunity creation and cannot
  duplicate the logical event or recipients.

## Data model

- Add `NEW_LEAD` to `notification_type_enum`.
- Add `notification_recipients`: identity primary key, `notification_id`, `user_id`,
  nullable `read_at`, recipient cleanup cascading with its logical notification, user
  deletion restricted, and a unique constraint on `(notification_id, user_id)`.
- Retain nullable `notifications.read_at` as a legacy compatibility column, but stop
  reading or writing it in application behavior; all current state lives on recipients.
- Existing notifications are copied to every currently active user. Their former
  global `read_at` is copied to each generated recipient, preserving known global state
  without inventing different historical user states.

## Contracts / API

- Existing notification response shape remains compatible: `read_at` is projected from
  the authenticated user's recipient row.
- Existing list and read endpoints retain their paths; their results and counts become
  user-specific. An optional notification-type filter supports authoritative stale-only
  Dashboard attention.
- `NEW_LEAD` responses reference the Opportunity already present in the contract.

## State transitions

- Recipient `read_at`: `NULL -> timezone-aware timestamp`; repeated reads are
  idempotent.
- Logical stale resolution remains unchanged. `NEW_LEAD` is an informational event and
  has no automatic resolution transition.

## Security & permissions

- Every notification query and mutation is scoped to `CurrentUser`; a user cannot read
  or alter another user's receipt.
- Only active users selected inside the Opportunity-creation transaction receive new
  events.

## Edge cases

- Creation with no active users still stores the single logical event and no receipts.
- Concurrent or repeated intake cannot duplicate the event because the existing unique
  notification constraint and intake idempotency remain authoritative.
- Downgrade restores a conservative global `read_at`: it is set only when all existing
  recipients for a logical notification are read. Recipient rows are then removed; the
  logical notification data is preserved.

## Acceptance criteria

- AC-01: New Opportunities from normal creation and production web intake create one
  logical `NEW_LEAD` notification for all and only active users.
- AC-02: User-specific list totals, unread filters, read and read-all operations do not
  change another user's state.
- AC-03: An idempotent intake replay creates no additional event or recipient.
- AC-04: Dashboard outcomes prioritize won/lost counts and kilograms; conversions are
  secondary and loss information has no Lost-workspace affordance.
- AC-05: The period label is Spanish and human-readable; active total/stages are clear,
  COTIZADA uses FAA yellow, the bar is stronger, and no snapshot timestamp is shown.
- AC-06: Lost and Broadcast navigation entries are absent and their workspace/detail
  routes redirect to Dashboard.
- AC-07: A new-lead notification is labelled `Nueva oportunidad recibida` and opens its
  Opportunity on the accessible Pipeline surface.
- AC-08: Targeted backend, frontend, and three scoped browser checks pass before the
  single final repository gate.

## Open decisions

None.

## Follow-up / future specs

None.

## Implementation notes

Reuse `OpportunityService.create_opportunity_in_transaction` as the common creation
boundary. Preserve existing notification HTTP paths and derive response `read_at` from
the joined recipient entity. Do not add query indexes without measured need.
