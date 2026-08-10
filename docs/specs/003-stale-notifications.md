# CRM-003 — Stale Opportunity Notifications

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-10
Implementation commit: `e006fc9`

## Goal

Give the team an internal reminder when an open opportunity remains in its current stage without a status change for the configured threshold.

## Context

This is an internal, global team notification. It is not an email reminder and is governed by the stale-opportunity rule in `docs/BUSINESS_RULES.md`.

## Dependencies

- CRM-001 — Core CRM

## Scope

Notification persistence, eligibility, generation/deduplication, read/resolved state, opportunity-side resolution, CLI generation, and authenticated API access.

## Non-goals

No email delivery, per-user notification visibility, scheduler infrastructure, or new notification types is implemented.

## Business rules

- The only implemented type is `OPPORTUNITY_STALE`.
- An opportunity in `NUEVA`, `COTIZADA`, or `NEGOCIACION` is eligible when `current_status_entered_at <= now - threshold_days`.
- The threshold is measured in whole configured days and must be positive.
- Notifications are global for the team, not assigned to a seller.
- Changing opportunity status or soft-deleting the opportunity resolves its active stale notification. Editing products or assignment does not.

## Data model

`notifications` contains type, opportunity FK, `created_at`, `read_at`, and `resolved_at`. A partial unique index permits at most one unresolved notification per opportunity/type. Foreign keys use `RESTRICT`; indexes support active and unread lists.

## Contracts / API

Authenticated routes are `/api/notifications`, `/api/notifications/read-all`, and `/api/notifications/{id}/read`. Listing supports pagination, `unread_only`, and `include_resolved`; ordering is deterministic by newest creation then ID. The CLI `python -m app.scripts.generate_notifications` reads positive `STALE_OPPORTUNITY_DAYS`, uses UTC now, and reports the number created.

## State transitions

Generation creates an unresolved unread row if the partial unique constraint has no active row. Marking read sets `read_at` only and is idempotent. Resolution sets `resolved_at`; it does not erase the row. A later stale period after a new stage entry can generate a new active notification.

## Security & permissions

The API requires an active JWT user. Visibility and read state are global to the team; there is no per-user read record. The CLI uses backend configuration and does not expose secrets.

## Edge cases

- Exact threshold equality is eligible; newer timestamps, terminal statuses, and deleted opportunities are not.
- Concurrent generators are safe and create one active row.
- Read and resolve are independently idempotent; reading does not resolve.
- Naive datetimes and invalid thresholds/configuration are rejected.

## Acceptance criteria

- AC-01: Eligible open opportunities produce one `OPPORTUNITY_STALE` notification.
- AC-02: Generation is idempotent, including concurrent generation.
- AC-03: Equality at the threshold is eligible and newer/terminal/deleted opportunities are excluded.
- AC-04: Status transitions and soft deletion resolve the active stale row.
- AC-05: Quote edits and assignment changes leave the active stale row unresolved.
- AC-06: Marking one notification read is idempotent and does not resolve it.
- AC-07: Read-all affects only unread unresolved notifications and returns the affected count.
- AC-08: API authentication, filters, pagination, and deterministic ordering are enforced.
- AC-09: The CLI rejects invalid threshold configuration and generates using UTC time.
- AC-10: A later eligible stage entry can create a new notification after the prior one is resolved.

## Open decisions

None

## Follow-up / future specs

- Deployment scheduling for the existing CLI is operational work and is not part of the implemented module.

## Implementation notes

`NotificationService` performs generation and resolution. Opportunity transitions call resolution in their transaction so a status change and its reminder state remain coherent.
