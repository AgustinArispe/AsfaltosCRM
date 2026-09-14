# CRM-044 — Opportunity Stage Regression & Visible History

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-14
Implementation commit: N/A

## Goal

Allow an operator to move an Opportunity back one permitted Pipeline stage after an
explicit confirmation, while keeping every status change and its date visible in that
Opportunity's own history.

## Context

FAA can currently advance an Opportunity through the Pipeline and already persists
creation and status-transition rows in `opportunity_status_history`. The Opportunity
detail also receives and renders those rows. The missing behavior is an authoritative
backward transition and consistent Pipeline/detail controls for requesting it.

This feature changes the transition rules owned by CRM-001 and the state-aware actions
defined by CRM-020. `docs/BUSINESS_RULES.md` remains authoritative and must be updated
with the approved result before implementation.

## Dependencies

- CRM-001 — Core CRM
- CRM-003 — Stale Notifications
- CRM-004 — Commercial Metrics
- CRM-013 — Concurrency Hardening
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-038 — Frontend Interaction & Data Synchronization
- CRM-039 — Won Opportunity History & Active Pipeline Retention
- CRM-040 — Pipeline & Opportunity Workspace Hierarchy

## Scope

- Add an authenticated backend operation for a permitted one-stage regression.
- Expose the same permitted regression from the Pipeline drag-and-drop interaction and
  from the Opportunity detail actions.
- Require an explicit confirmation that names the current and destination stages
  before mutating.
- Reconcile Pipeline summaries and open Opportunity detail from the authoritative
  response after success.
- Continue using `OpportunityStatusHistory` as the single persisted audit trail and
  show every creation, forward movement, regression, loss, and reopen event with its
  date in the Opportunity detail.
- Add backend and frontend tests for the approved transition matrix, confirmation,
  persistence, history presentation, stale state, and failure rollback.

## Non-goals

- Arbitrary stage selection or skipping multiple stages in one action.
- Deleting, editing, or manually inserting history entries.
- Quote version history, comments on transitions, or a new generic activity entity.
- Changing the existing `PERDIDA -> NEGOCIACION` reopen workflow.
- Changing roles or Opportunity visibility.

## Business rules

- A regression moves exactly one stage backward in the approved Pipeline matrix.
- `COTIZADA -> NUEVA` is always forbidden, so `COTIZADA` has no backward action.
- `NEGOCIACION -> COTIZADA` is allowed and preserves the current quote.
- `NUEVA` has no previous stage.
- `PERDIDA` is not handled as a regression; its only return path remains the existing
  explicit reopen to `NEGOCIACION` with retained valid quote lines.
- A regression requires deliberate user confirmation and is never committed only by
  dropping a card or activating the initial detail control.
- Every successful regression records the previous state, destination state, acting
  user, and timezone-aware transition date in the existing status history.
- The regression date becomes `current_status_entered_at` and resets stage-age
  calculation exactly like any other successful status change.
- Failed, cancelled, duplicate, or stale requests create no history row and leave the
  Opportunity unchanged.

## Data model

No schema migration is expected. The existing `opportunity_status_history` row stores
`from_status`, `to_status`, `changed_at`, `changed_by_user_id`, and
`transition_kind=STATUS_CHANGED`. The parent Opportunity continues to store its current
`status`, `current_status_entered_at`, and `updated_at`.

## Contracts / API

Add a strict authenticated regression command under the existing Opportunity API. The
request carries the expected current status and target status; extra fields are
rejected. The backend locks the Opportunity, revalidates both values, applies only an
approved adjacent transition, records history atomically, resolves the active stale
notification, and returns the refreshed `OpportunityDetail` projection.

An invalid transition returns the existing typed transition error. A request whose
expected status no longer matches persisted state returns a conflict and performs no
partial write. The frontend refreshes authoritative state after a conflict and explains
that the Opportunity changed before confirmation.

The existing Opportunity detail response remains the history contract. Entries are
presented in deterministic chronological `(changed_at ASC, id ASC)` order and include
at least origin stage, destination stage, and transition date. Creation remains a
distinct `Consulta creada` event.

## State transitions

| Current state | Backward destination | Result |
| --- | --- | --- |
| `NUEVA` | None | No backward action |
| `COTIZADA` | `NUEVA` | Forbidden |
| `NEGOCIACION` | `COTIZADA` | Allowed after confirmation |
| `GANADA` | `NEGOCIACION` | Allowed after confirmation |
| `PERDIDA` | None through this command | Existing reopen workflow only |

Forward, loss, and reopen transitions continue to follow their existing rules.

## Security & permissions

The operation requires an active authenticated `SUPERVISOR` or `VENDEDOR`, matching
the existing commercial transition permissions. The authenticated user is always
stored as `changed_by_user_id`; the client cannot select or spoof the actor. Existing
all-opportunity visibility is unchanged.

## Edge cases

- Closing or cancelling the confirmation leaves the card and detail unchanged.
- Repeated clicks while pending are disabled and produce at most one committed
  transition.
- The backend rejects a stale confirmation if another user changed the state first.
- A regression preserves quote products and quantities.
- Drag cancellation or an invalid drop target causes no request.
- The optimistic Pipeline move rolls back to the authoritative source stage on failure.
- History dates are timezone-aware API values and use the existing localized display
  formatter in the Opportunity detail.

## Acceptance criteria

- AC-01: A `NEGOCIACION` Opportunity can be moved to `COTIZADA` from Pipeline and
  Opportunity detail only after a confirmation naming both stages.
- AC-02: `COTIZADA -> NUEVA`, skipped regressions, and regression from `NUEVA` are
  rejected by the backend and unavailable in the UI.
- AC-03: Cancelling confirmation, cancelling drag, or receiving an invalid/stale
  request produces no status or history change.
- AC-04: Each successful regression atomically updates status,
  `current_status_entered_at`, and `updated_at`, and appends one actor-attributed,
  timezone-aware `OpportunityStatusHistory` row.
- AC-05: The Opportunity detail visibly lists the complete ordered status history with
  each transition's source, destination, and formatted date, including regressions.
- AC-06: The current quote is preserved after regression and remains editable under
  the existing `COTIZADA` rules.
- AC-07: Active stale notification handling and Pipeline/detail reconciliation behave
  exactly as for an ordinary successful status change.
- AC-08: Both `SUPERVISOR` and `VENDEDOR` can perform an approved regression, and the
  server records the authenticated actor.
- AC-09: Backend service/API tests and frontend interaction/history tests cover the
  complete approved matrix and rollback behavior.
- AC-10: The approved behavior passes all repository quality, coverage, build, audit,
  Alembic, Docker Compose health, and browser acceptance gates.
- AC-11: A `GANADA` Opportunity can return to `NEGOCIACION` after confirmation,
  disappears from current won results, and triggers automatic Legendary
  recalculation for its Customer.

## Open decisions

None

## Follow-up / future specs

None.

## Implementation notes

Keep transition validation and history writes in `OpportunityService`, not API routes
or React components. Reuse the existing confirmation modal and generic Pipeline stage
configuration, extending it with previous-stage eligibility instead of introducing
per-stage components. Preserve ordered row locking and ensure no external I/O occurs
inside the transaction.
