# CRM-001 — Core CRM

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-10
Implementation commit: `e75aa5a`, `822adb6`, `672c71f`, `c46174a`, `4a02da2`, `5d90058`, `e95a4e1`

## Goal

Provide the authenticated FAA CRM for managing customers, products, users, and the commercial opportunity pipeline.

## Context

This is the core persistence and domain behavior described by `docs/BUSINESS_RULES.md`.

## Dependencies

- None

## Scope

Customer, User, Product, Opportunity, quote lines, status history, authentication, role authorization, CRUD/query behavior, and core opportunity transitions.

## Non-goals

No mobile application, campaign management, restricted opportunity visibility, or automatic Legendario qualification is implemented here.

## Business rules

- A Customer may have many Opportunities; every Opportunity has one Customer.
- Implemented sources are `WEB` and `WHATSAPP`.
- Pipeline states are `NUEVA`, `COTIZADA`, `NEGOCIACION`, `GANADA`, and terminal `PERDIDA`; normal transitions cannot skip stages.
- Moving to `COTIZADA` requires at least one active Product and a positive Decimal quantity in kilograms for every line. `NUEVA` may be marked `PERDIDA` without a quote.
- `GANADA` and `PERDIDA` are terminal for normal operation. Quote lines cannot be edited in either terminal state.
- Every creation and status transition writes `OpportunityStatusHistory`, and `current_status_entered_at` is updated on each transition.
- Products can be deactivated but are not physically deleted. Existing quote lines and historical metrics remain valid.
- Customers and Opportunities are soft-deleted; deleted rows are hidden from normal operational queries while history remains addressable where explicitly requested.
- Implemented roles are `SUPERVISOR` and `VENDEDOR`. Authenticated users can view all opportunities; administrative actions require supervisor authorization.

## Data model

- `customers`: required nonblank `name`; optional `company`, `email`, `phone`, `province`; `legendary_historical_override`; timestamps and `deleted_at`.
- `users`: `full_name`, normalized unique email, password hash, role, active flag, and timestamps.
- `products`: normalized unique name, active flag, timestamps.
- `opportunities`: customer FK, optional assigned-user FK, source, status, loss reason, current-status timestamp, timestamps, and `deleted_at`.
- `opportunity_products`: composite opportunity/product key and positive `quantity_kg` (`Decimal`, three fractional digits).
- `opportunity_status_history`: from/to states, timestamp, opportunity FK, and optional user FK. Creation has a null `from_status`.
- Foreign keys use `RESTRICT`; indexes support active/deleted, pipeline, assignee, and source queries.

## Contracts / API

Authenticated REST endpoints expose login/current-user, customer, product, user, and opportunity CRUD and transition operations under `/api`. Opportunity responses include customer, assignee, quote lines, and status history. Requests use strict Pydantic schemas, enums, positive IDs, and Decimal quantities.

## State transitions

`NUEVA -> COTIZADA -> NEGOCIACION -> GANADA` is the normal path. From `NUEVA`, `COTIZADA`, or `NEGOCIACION`, an opportunity may transition to `PERDIDA` with a categorized loss reason. Quote replacement is allowed only in `COTIZADA` or `NEGOCIACION`; assignment changes do not create status history or reset the status timer. Every successful transition resolves its active stale notification.

## Security & permissions

JWT bearer authentication requires an active user. Passwords are hashed; tokens and passwords are never returned. Supervisors manage users/products, assign opportunities, set historical Legendary override, and soft-delete customers/opportunities. Vendors can perform permitted sales actions but cannot perform those administrative operations.

## Edge cases

- Blank names, invalid enums, invalid foreign keys, duplicate normalized names/emails, duplicate quote products, nonpositive quantities, invalid loss reasons, and illegal transitions are rejected.
- Deletion is idempotent and does not cascade away commercial history.
- Existing inactive products remain in historical quote lines but cannot be newly added.
- Query results exclude soft-deleted opportunities and are deterministic for pagination.

## Acceptance criteria

- AC-01: A new opportunity is created in `NUEVA` with a creation history row.
- AC-02: Only the normal pipeline transitions and the documented loss transitions are accepted.
- AC-03: `NUEVA -> COTIZADA` rejects empty, duplicate, inactive-new, or nonpositive quote lines.
- AC-04: Quote quantities persist as Decimal kilograms and can be replaced only in open quoted states.
- AC-05: Each successful status change records from/to history and updates `current_status_entered_at`.
- AC-06: `GANADA` and `PERDIDA` reject further transitions and quote edits.
- AC-07: Customer, product, user, and opportunity endpoints enforce authentication and role rules.
- AC-08: Soft-deleted customers/opportunities are omitted from default operational queries while retained rows remain available to explicit history queries.
- AC-09: Deactivated products remain in historical quotes and metrics but cannot be added to a new quote.
- AC-10: Model constraints reject blank names, duplicate normalized identities/names, invalid FKs, and invalid loss-state combinations.

## Open decisions

None

## Follow-up / future specs

- Automatic three-consecutive-year Legendario qualification is an approved future business rule but is not implemented by this module; only the historical override exists.

## Implementation notes

`OpportunityService` owns transactional transitions and row locking; query services eager-load summary relations. No new behavior is authorized by this retrospective spec.
