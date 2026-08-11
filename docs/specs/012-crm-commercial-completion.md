# CRM-012 — CRM Commercial Completion

Status: Approved
Owner: FAA CRM team
Last updated: 2026-08-11
Implementation commit: N/A

## Goal

Complete every remaining commercial backend capability of FAA CRM before the final
frontend redesign and production rollout. This is the last backend business module.

## Context

CRM-001 through CRM-004 implement the core commercial domain, trusted web intake,
stale notifications, and backend metrics. CRM-005 through CRM-011 implement the
WhatsApp domain, API, storage, provider, Inbox, and Broadcast execution. This spec
closes the remaining commercial backend scope without redesigning the frontend or
redefining the completed WhatsApp modules.

The governing Legendary and reopen rules in `docs/BUSINESS_RULES.md` are aligned with
this approved scope. CRM-001 retains the currently implemented manual override and
normal terminal-state behavior until CRM-012 is implemented.

## Dependencies

- CRM-001 — Core CRM
- CRM-002 — Web Lead Intake
- CRM-003 — Stale Opportunity Notifications
- CRM-004 — Commercial Metrics

## Scope

- Add append-only internal Opportunity Notes with immutable revisions, authorship,
  timestamps, optional pinning, and backend search.
- Add automatic Legendary qualification while preserving the independent manual
  historical override, plus a reusable recomputation service and CLI.
- Add a first-class backend Lost Opportunities workspace with search, filters,
  statistics, and preserved loss history outside the active Pipeline.
- Add an explicit, auditable, idempotent workflow for reopening `PERDIDA`
  Opportunities only to `NEGOCIACION`.
- Add all-or-nothing Customer CSV import with dry-run preview, typed validation
  reports, conservative identity resolution, durable idempotency, and audit evidence.
- Complete the operational WordPress/CF7 production integration for CRM-002 with
  deployment documentation, HMAC validation, replay verification, smoke tests, and
  safe monitoring.
- Extend existing services and projections where responsibilities are already shared;
  do not fork Customer identity, Opportunity transitions, metrics, intake security,
  or audit rules.

## Non-goals

- Frontend implementation or the final visual redesign.
- Dashboard UI or Lost Opportunities statistics UI.
- Native mobile or mobile-specific behavior.
- Meta production provisioning, credential setup, or live Meta smoke tests.
- WhatsApp Broadcast improvements, campaign authoring, or notification UI.
- New lead sources, products, pricing, stock, quote versioning, or seller-restricted
  visibility.
- Automatic opportunity creation from Customer import.
- Fuzzy Customer matching, destructive merge, or bulk Customer overwrite.
- A general job queue, Redis, Celery, or a new workflow/orchestration framework.

## Business rules

### Opportunity Notes

- A Note belongs to exactly one Opportunity and remains available when that
  Opportunity reaches `GANADA` or `PERDIDA`.
- Note bodies are bounded Unicode multiline plain text. Intentional line breaks and
  lightweight text characters are preserved, but HTML is neither accepted as a
  rendering contract nor rendered or executed by any consumer.
- Creating a Note appends revision 1. Editing body or pin state appends the next
  immutable revision; no prior revision is updated or deleted.
- Every revision records its authenticated actor and aware UTC timestamp. Current
  body and pin state are derived from the latest revision.
- Search applies to the current revision of non-deleted Opportunities. Revision
  history remains retrievable for audit but superseded text does not make a current
  Note match search.
- Notes may be created, revised, pinned, and read in open or terminal Opportunities.
  Opportunity soft deletion retains Note history but makes it non-actionable through
  normal operational endpoints.

### Automatic Legendary

- The automatic rule qualifies a Customer when its first non-soft-deleted `GANADA`
  Opportunity, ordered by `(created_at, id)`, is at least three calendar years old.
- Age uses that first won Opportunity's `created_at` and an aware `now`. Three years
  elapse on its Buenos Aires calendar anniversary; February 29 reaches its third
  anniversary on February 28 in a non-leap year.
- Manual `legendary_historical_override` and automatic qualification are independent
  persisted components. Effective Legendary state is exactly:
  `legendary_historical_override OR legendary_automatic`.
- A true manual override always makes the effective state true, regardless of the
  automatic result.
- Automatic recomputation must never write, clear, or derive the manual override.
  Manual override changes must never write the automatic component.
- Relevant Opportunity creation, `GANADA` transition, and soft deletion invoke the
  shared recomputation operation transactionally. A bounded CLI recomputes Customers
  for time-only maturation and backfill using the same service.
- Customer responses expose the manual component, automatic component, effective
  state, and last automatic evaluation timestamp. No gamification or additional
  Legendary tier is introduced.

### Lost Opportunities Workspace

- `PERDIDA` Opportunities are absent from the active Pipeline query and are available
  through a dedicated Lost Opportunities read service. The CRM-004 metrics pipeline
  snapshot remains an analytical endpoint and is not the active Kanban query.
- The workspace is globally visible to both current roles and supports bounded search
  plus filters for loss reason, Customer, province, Product, source, and loss date.
- Date filters use the latest transition into `PERDIDA`, are timezone-aware, and use a
  half-open UTC interval after boundary conversion.
- Search matches safe operational identifiers and current Customer name/company,
  without fuzzy identity resolution or seller-specific filtering.
- Product filters use retained quote lines. Inactive Products remain valid historical
  filter values.
- Statistics apply the same dimensions to two explicit projections: current Lost
  Opportunities and immutable historical loss episodes. They include current-lost
  count/kilograms, total loss episodes, reopened episodes, counts and kilograms by
  loss reason, Product, source, and loss-time province, plus a loss-date timeline.
  Zero denominators remain `null` where a ratio is returned.
- Reopening removes the Opportunity from the current Lost workspace and returns it to
  the active Pipeline. Historical loss episodes remain queryable and continue to
  support historical metrics.

### Opportunity Reopen

- Only a non-deleted Opportunity currently in `PERDIDA` may be reopened, and its only
  target is `NEGOCIACION`. Direct reopen to `NUEVA`, `COTIZADA`, or `GANADA` is
  prohibited, and `GANADA` is not reopenable.
- Reopen requires the retained quote to contain at least one Product with a positive
  quantity. It does not add or edit quote lines; a loss without a retained valid quote
  is not eligible for reopen under this scope.
- The destination is backend-owned and is not accepted as a client-selected field.
- Reopen clears the current `loss_reason` only because the Opportunity is no longer
  in `PERDIDA`; the prior reason, Customer/province evidence, and quote snapshot remain
  on its immutable loss episode.
- Existing quote lines, Customer, source, assignee, original `created_at`, and all
  earlier status/loss history remain unchanged.
- Reopen appends a `REOPENED` status-history entry, records actor and timestamp, and
  resets `current_status_entered_at`. It never appends a creation history entry.
- A reopened Opportunity is marked `is_reopened=true`, increments its derived reopen
  count, and counts as reopened, never as newly created. A later valid transition back
  to `PERDIDA` appends a new loss episode and reason without changing any prior episode.
- Reopen resolves no historical row. Its new active stage participates normally in
  CRM-003 stale-notification eligibility from the reopen timestamp.

### Customer Import

- CSV import accepts only Customer fields already owned by CRM-001: `name`,
  `company`, `email`, `phone`, and `province`. It cannot set IDs, deletion fields,
  timestamps, roles, Legendary state, Opportunities, or arbitrary columns.
- Input is a bounded UTF-8 CSV with a required header, deterministic row numbers, and
  backend-configured file, row, and field limits. An optional UTF-8 BOM is accepted;
  malformed encoding, structure, headers, or values are reportable validation errors.
- Dry-run normalizes every row and uses the existing `CustomerIdentityResolver` with
  the exact conservative email/phone rules. It creates no Customer and returns a
  complete typed row report with `CREATE`, `ENRICH`, `UNCHANGED`, or `ERROR`, safe
  reason codes, normalized previews, and aggregate counts.
- One active exact match may be reused. Import may fill only empty Customer fields;
  it never overwrites a nonempty value. Ambiguous active matches, deleted matches,
  conflicting identity signals, and multiple CSV rows targeting the same identity are
  errors rather than guesses.
- A name-only valid row creates a new Customer and receives no fuzzy deduplication.
  Empty required names and invalid provided email/phone values are errors.
- A commit is allowed only for the exact validated file digest and normalized preview
  version. It re-resolves every identity under locks immediately before writing.
  Changed resolution makes the whole commit fail with a new dry-run required.
- All Customer creates/enrichments and the committed import audit transition occur in
  one PostgreSQL transaction. Any row or persistence failure rolls back every
  Customer change; partial import is prohibited.
- Stable import and command UUIDs make dry-run and commit replays idempotent. Reusing
  either UUID for different normalized input is a conflict.

### WordPress Production Integration

- CRM-002 remains the sole business contract: each valid new CF7 submission creates
  one `WEB` Opportunity, preserves the immutable intake snapshot, and never replaces
  the existing CF7 email delivery.
- Production delivery is server-to-server over HTTPS to `POST /api/intake/web`.
  WordPress creates one stable external submission ID per CF7 submission and reuses it
  with the identical normalized body for every delivery retry.
- WordPress serializes the UTF-8 JSON body once and signs the exact transmitted bytes
  with the existing `X-Intake-Timestamp` and `X-Intake-Signature` HMAC-SHA256 contract.
  The signing secret is backend/WordPress server configuration and is never stored in
  frontend code, source control, request logs, or responses.
- The existing five-minute signature freshness, constant-time comparison, immutable
  payload replay, and changed-payload conflict rules remain unchanged. Production
  integration does not add a second authentication or intake path.
- A production runbook documents CF7 mapping, secret installation/rotation procedure,
  endpoint and TLS configuration, retries, timeout behavior, rollback/disable steps,
  smoke tests, monitoring, alert ownership, and recovery from CRM unavailability.
- Safe monitoring distinguishes accepted new submissions, identical replays,
  authentication rejection, idempotency conflict, validation failure, and application
  failure. Logs and metric labels exclude body fields, signatures, secrets, Customer
  identity, and free-text messages.

## Data model

All new timestamps are timezone-aware and persisted in UTC. Every schema change is
delivered through Alembic with typed SQLAlchemy 2.x models and `RESTRICT` foreign keys
for retained commercial history.

### Notes

- `opportunity_notes`: immutable logical Note identity, Opportunity FK, original
  author FK, and creation timestamp.
- `opportunity_note_revisions`: Note FK, positive revision number, bounded plain-text
  body, `is_pinned`, revision actor FK, `created_at`, optional prior-revision FK, and
  UUID command key. Unique `(note_id, revision_number)` and command constraints make
  the append boundary durable.
- Application services expose no update/delete operation for either table. Indexes
  support latest-revision lookup, pinned-first ordering, Opportunity history, and
  PostgreSQL full-text search over current revisions.

### Legendary evidence

- `customers` gains separate `legendary_automatic` and
  `legendary_automatic_evaluated_at` fields. Existing
  `legendary_historical_override` remains unchanged.
- `customer_legendary_events` is append-only and records typed manual or automatic
  component changes, before/after component values, effective before/after state,
  first won Opportunity ID and creation timestamp, actor when user-driven, and UTC
  occurrence time. It stores typed scalar evidence, not generic JSON.
- Existing Customers are backfilled with automatic false and are then evaluated by
  the production recomputation CLI before automatic state is treated as complete.

### Opportunity lifecycle evidence

- `opportunity_status_history` gains typed transition kind (`CREATED`,
  `STATUS_CHANGED`, `LOST`, or `REOPENED`). Existing rows are deterministically
  backfilled from their stored from/to states. History remains immutable.
- `opportunity_loss_events` appends one row for every `LOST` transition with the unique
  status-history FK, Opportunity/Customer FKs, from-state, reason, loss timestamp,
  actor, loss-time Customer display/province snapshot, source, and quoted total
  kilograms.
- `opportunity_loss_product_snapshots` stores the loss-event FK, Product FK and name
  snapshot, and Decimal quantity for every quote line present at loss time. A loss
  without a quote has no child rows and a zero total.
- `opportunity_reopen_events` appends one row with unique status-history FK, the exact
  loss-event FK being reopened, fixed `NEGOCIACION` target evidence, actor, UTC
  timestamp, and unique command UUID. It never updates the referenced loss event.
- Existing currently lost Opportunities are backfilled with one loss event and current
  Customer/province/quote evidence; no pre-feature reopen history exists to infer.
- No separate mutable Lost Opportunity copy is created. The current workspace reads
  Opportunities; historical statistics read immutable loss/reopen evidence so later
  Customer or quote edits cannot rewrite prior loss results.

### Import audit

- `customer_import_batches` stores client import UUID, immutable file SHA-256,
  sanitized source filename, typed state (`VALID` or `INVALID`, then `COMMITTED` for a
  valid commit), schema/version, actor, row/action/error counts, and timestamps.
- `customer_import_rows` stores the bounded normalized row snapshot, proposed action,
  resolved Customer ID when unambiguous, and row number. Typed child issue rows store
  stable field/reason codes and safe messages; raw CSV or generic JSON is not stored.
- A committed batch stores its commit UUID, actor, and committed timestamp. Unique
  import/command constraints prevent duplicate application. Validation artifacts may
  persist, but dry-run never writes Customer rows.

## Contracts / API

All new CRM routes require an active user, use strict Pydantic request models with
`extra="forbid"`, aware datetimes, bounded limits, and deterministic opaque keyset
cursors. Existing core error semantics remain in use.

### Notes

- `POST /api/opportunities/{opportunity_id}/notes` appends revision 1 from UUID
  `client_generated_id`, body, and optional `is_pinned`.
- `GET /api/opportunities/{opportunity_id}/notes` supports bounded `search`, `pinned`,
  `limit`, and cursor parameters and returns only current revisions, pinned first then
  newest with stable ID tie-breakers.
- `POST /api/opportunities/{opportunity_id}/notes/{note_id}/revisions` accepts UUID
  `command_id`, `expected_revision`, and at least one body/pin change; it appends one
  revision or returns a revision conflict.
- `GET /api/opportunities/{opportunity_id}/notes/{note_id}/revisions` returns the
  complete chronological immutable revision history.

### Legendary

- Existing Customer list/detail responses add `legendary_automatic`,
  `legendary_automatic_evaluated_at`, and effective `is_legendary`; the existing manual
  override field and supervisor-only mutation remain compatible.
- A strictly typed recomputation service supports one Customer and bounded batches.
  `python -m app.scripts.recompute_legendary_customers` invokes the same service,
  supports safe resume/batch options, uses aware UTC now, and exits nonzero on invalid
  configuration or incomplete processing. No public recompute endpoint is required.

### Lost workspace and reopen

- `GET /api/lost-opportunities` supports `search`, repeated typed `reason`, positive
  `customer_id`, normalized `province`, positive `product_id`, typed `source`,
  `lost_from`, `lost_to`, `limit`, and cursor filters.
- `GET /api/lost-opportunities/statistics` applies the same filter values to current
  rows and loss-time snapshots and returns the typed current/historical counts, Decimal
  kilograms, groupings, timeline, and reopened evidence defined in this spec.
- `POST /api/opportunities/{opportunity_id}/reopen` accepts UUID `command_id` and the
  expected current status. It accepts no target-status field, validates the retained
  quote, transitions only to `NEGOCIACION`, and returns Opportunity detail with
  `is_reopened=true` and `reopen_count`. Identical replay is successful; changed key
  reuse or stale state is a conflict.

### Customer import

- `POST /api/customer-imports/dry-run` accepts multipart CSV plus strict metadata with
  UUID `client_import_id`. It returns the persisted typed validation report and never
  mutates Customers.
- `GET /api/customer-imports/{batch_id}` returns the authenticated report with bounded
  row/issue pagination.
- `POST /api/customer-imports/{batch_id}/commit` accepts UUID `command_id`, expected
  batch version, and file digest confirmation. It returns exact created/enriched/
  unchanged counts and Customer IDs only after the single transaction commits.
- Invalid or stale previews cannot commit. An identical completed command returns the
  original result; changed replay returns conflict.

### WordPress production boundary

No new lead-intake endpoint or payload is introduced. The runbook and contract tests
use CRM-002's exact raw-body signature, headers, status behavior, stable external ID,
and response fields. Operational smoke tools must generate synthetic non-customer test
data, require explicit production confirmation, and never print secrets or signatures.

## State transitions

Opportunity lifecycle extends CRM-001 with one exceptional transition:

```text
PERDIDA -> NEGOCIACION
```

The target is fixed and backend-owned. Direct `PERDIDA -> NUEVA`,
`PERDIDA -> COTIZADA`, and `PERDIDA -> GANADA` transitions are invalid. All ordinary
CRM-001 transitions remain unchanged. A reopened Opportunity may later progress
normally to `GANADA` or return to `PERDIDA`, producing a new immutable loss episode.
`GANADA` remains terminal.

Note state is an append-only revision sequence:

```text
revision N -- edit or pin change --> revision N+1
```

Import lifecycle is:

```text
DRY RUN -> VALID -> COMMITTED
        -> INVALID
```

Only `VALID -> COMMITTED` mutates Customers. A failed commit transaction leaves the
batch valid and retryable with no partial Customer changes. `COMMITTED` is terminal.

Legendary effective state has no independent mutable field: it is projected as manual
override OR automatic state. Recomputing one component cannot transition the other.

## Idempotency and concurrency

- Note creation/revision commands use durable UUID uniqueness, expected revision, and
  row locks. Concurrent edits produce one accepted next revision and one conflict,
  never two revision numbers or overwritten text.
- Reopen locks the Opportunity, validates `PERDIDA`, appends status history, clears the
  current loss reason, updates the timer, and records the command in one transaction.
- Legendary recomputation and relevant Opportunity mutations share a Customer-scoped
  transaction/advisory lock so a concurrent win/create/delete cannot publish stale
  automatic state. Batch lock ordering is stable.
- Import commit acquires its batch lock and sorted existing Customer identity advisory
  locks, re-resolves the whole preview, then writes in one transaction. It never holds
  unresolved process-local state as a correctness boundary.
- Database constraints, not in-memory checks alone, enforce note revision, reopen
  command, import command, and import identity idempotency.
- WordPress transport retries reuse the stable external submission ID and normalized
  payload; CRM-002 remains the durable replay boundary.

## Security & permissions

- Both active `SUPERVISOR` and `VENDEDOR` users may read Lost workspace data and create,
  read, revise, or pin Opportunity Notes under global Opportunity visibility.
- Reopen uses the same authenticated sales-transition permission as existing core
  Opportunity transitions. Import is restricted to `SUPERVISOR` because it performs
  bulk Customer mutations.
- Manual Legendary override remains supervisor-only. Automatic CLI execution is an
  operational backend action and never invents a CRM user actor.
- Request actors, authors, and command actors come only from authentication; clients
  cannot select audit user IDs.
- Notes and imported text are stored/rendered as text. CSV formulas are never executed;
  exported diagnostic content must neutralize spreadsheet formula injection.
- Import reports, logs, metrics, and CLI output exclude raw CSV, HMAC values, secrets,
  complete Customer identity, and unbounded note bodies.
- WordPress signing material remains server-only and all production delivery uses
  verified TLS. Authentication errors remain generic.
- No new role, seller visibility rule, hard-delete contract, generic JSON payload, or
  untyped audit metadata is introduced.

## Edge cases

- Empty/whitespace Notes, over-limit bodies, HTML rendering attempts, stale revision
  numbers, changed UUID replay, missing authors, and notes for deleted Opportunities
  fail without appending a partial revision.
- Pin and body edits arriving together create one revision. A no-op revision is
  rejected; identical command replay returns the original revision.
- Exactly the three-year anniversary of the first `GANADA` Opportunity's creation is
  eligible for automatic Legendary. No `GANADA` Opportunity remains automatic false;
  manual true still makes effective state true.
- A manual override change concurrent with automatic recomputation preserves both
  requested components and computes their OR after locking.
- A Lost filter with no quote lines does not match a Product filter but remains
  visible without that filter. Null province is represented explicitly in statistics,
  and later Customer/product/quote edits cannot alter a loss-time snapshot.
- Concurrent reopen attempts append one `REOPENED` event. A later lose action appends
  a distinct `LOST` event and cannot alter the earlier reason.
- Reopen without a retained valid quote, or with a requested `NUEVA`, `COTIZADA`, or
  `GANADA` target, fails without changing status or appending history.
- CSV blank lines, duplicate headers, unexpected columns, malformed quotes, mixed
  identity signals, duplicate in-file identities, deleted matches, and a database
  conflict are reported or rolled back deterministically.
- A Customer changed after dry-run invalidates the preview at commit; no unaffected
  rows are imported as a fallback.
- WordPress timeout after CRM commit is retried with the same external ID and returns
  the original result. Bad/stale signatures and changed replays create no Customer or
  Opportunity.

## Acceptance criteria

- AC-01: Notes in open, won, or lost Opportunities preserve multiline plain text,
  author, UTC timestamp, optional pin, and immutable revision history with no HTML
  execution or application delete/update of prior revisions.
- AC-02: Current Notes are searchable and deterministically paginated; idempotent and
  concurrent create/edit/pin commands cannot duplicate revisions or overwrite history.
- AC-03: Automatic Legendary becomes true exactly when the first `GANADA` Opportunity
  is at least three calendar years old, effective state is manual OR automatic, and
  recomputation never changes the manual override.
- AC-04: The shared Legendary service, Opportunity hooks, and bounded CLI produce the
  same timezone-aware result and remain correct under concurrent commercial changes.
- AC-05: The Lost workspace excludes active Pipeline rows and supports combined search,
  reason, Customer, province, Product, source, and loss-date filters with stable pages.
- AC-06: Lost statistics return consistent filtered counts, Decimal kilograms,
  dimensions, timeline, and reopened evidence without duplicating CRM-004 formulas.
- AC-07: Reopen applies only to current `PERDIDA` with a retained valid quote, targets
  only `NEGOCIACION`, rejects direct `NUEVA`/`COTIZADA`/`GANADA`, preserves quote and
  every loss entry, appends actor/status evidence, resets the timer, and marks/counts
  the Opportunity as reopened rather than created.
- AC-08: Reopen replay and concurrency append one effect; re-loss appends a new reasoned
  episode and never mutates the previous loss or reopen history.
- AC-09: Customer import dry-run parses and validates the complete CSV through the
  existing identity resolver and returns deterministic create/enrich/unchanged/error
  evidence without mutating Customers.
- AC-10: A valid import commits every Customer action and audit row in one PostgreSQL
  transaction; any stale resolution or injected row/database failure leaves zero
  partial Customer changes.
- AC-11: Import UUID/digest replay, changed-key conflicts, sorted advisory locks, and
  concurrent commits produce one durable batch result without duplicate Customers.
- AC-12: WordPress production documentation and contract smoke tests prove exact-body
  HMAC verification, timestamp freshness, stable-ID replay, changed replay rejection,
  CF7 email continuity, rollback, and safe monitoring without changing CRM-002 rules.
- AC-13: Both active roles retain global read visibility, import/manual override remain
  supervisor-only, and append-only Note, Legendary, lifecycle, and import evidence
  reconstructs actor, time, command, and business outcome without unsafe payloads.
- AC-14: New and modified Python is fully typed and passes strict gates with no `Any`,
  casts, or `type: ignore`; known contracts use DTOs/models rather than magic
  dictionaries.
- AC-15: Migration, service, API, CLI, transaction rollback, idempotency, concurrency,
  security, HMAC, search/filter/statistics, and production smoke-contract tests cover
  this scope and all repository quality, Alembic, Docker, backend, and frontend gates
  pass before implementation is considered complete.

## Open decisions

None

## Follow-up / future specs

- Final CRM frontend redesign, including Notes and Lost Opportunities workspace UI.
- Dashboard UI, mobile-specific work, and notification UI remain outside this backend
  completion module.
- Meta production provisioning and any future Broadcast improvements remain governed
  separately from CRM-012.

## Implementation notes

Extend `OpportunityService`, `OpportunityQueryService`, `CustomerService`,
`MetricsService`, `CustomerIdentityResolver`, CRM-002 intake security, and existing UTC/
advisory-lock helpers where their responsibilities already apply. Keep Note commands,
Legendary evaluation, Lost read projections, Customer import, and WordPress operational
instrumentation in separate strictly typed services and keep routers/CLI thin.

Use PostgreSQL transactions and row/advisory locks as the correctness boundary. Reuse
existing normalization, Decimal, pagination, auth, audit, and error conventions. Do not
duplicate transition rules, identity matching, metrics formulas, HMAC verification, or
Customer enrichment policy, and do not introduce `Any`, casts, type ignores, generic
JSON audit payloads, or process-memory correctness.
