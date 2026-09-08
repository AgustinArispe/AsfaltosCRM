# CRM-039 — Won Opportunity History and Active Pipeline Retention

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-07
Implementation commit: 459634e

## Goal

Keep the active Opportunities board operationally bounded while preserving every won
Opportunity as permanent commercial history. A `GANADA` Opportunity remains visible
in the board for exactly the rolling 30-day interval after entering `GANADA`, then
disappears from that board without being deleted, archived, mutated, or assigned a new
status. Authenticated users can review all won Opportunities through a dedicated,
server-paginated `Ganadas` workspace with useful commercial filters and totals.

## Context

The current Opportunity lifecycle is
`NUEVA -> COTIZADA -> NEGOCIACION -> GANADA`. `GANADA` is terminal. Every successful
transition writes `Opportunity.current_status_entered_at` and an
`OpportunityStatusHistory` row from the same aware timestamp. The existing Pipeline
loads one status-filtered `GET /api/opportunities` sequence for each of `NUEVA`,
`COTIZADA`, `NEGOCIACION`, and `GANADA`; its `GANADA` query currently has no age bound,
so that column grows indefinitely.

CRM-012 established a dedicated Pérdidas read projection with authenticated filters,
cursor pagination, statistics, and route-driven Opportunity detail. Its separation of
active work from terminal history is the architectural precedent, but its immutable
loss-event snapshots and reopen evidence exist because a lost Opportunity can later
leave `PERDIDA`. A won Opportunity cannot leave `GANADA`, cannot have its quote or
assignment changed, and therefore does not need a parallel won-event entity or copied
quote snapshot.

CRM-038 keeps the mounted Pipeline stable across route-driven detail, applies
authoritative mutation responses locally, and protects state from stale requests.
CRM-039 must extend that behavior narrowly; it must not reintroduce a broad board
refetch or workspace remount.

## Dependencies

- CRM-001 — Core CRM
- CRM-004 — Commercial Metrics
- CRM-012 — CRM Commercial Completion
- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-024 — Customers, Products & Lost UI
- CRM-038 — Frontend Interaction and Data Synchronization

## Scope

### Won-history read projection

- Add an authenticated backend read service and typed API for all non-deleted
  Opportunities whose current status is `GANADA`.
- Use `Opportunity.current_status_entered_at` as the victory timestamp (`won_at`) in
  the read contract. Do not add or persist a second `won_at` field.
- Support server-side filtering by victory-date range, bounded customer/company
  search, Product, source/origin, province, and responsible user.
- Return deterministic keyset/cursor pages ordered by victory timestamp descending and
  Opportunity ID descending. The frontend never loads the complete history.
- Return selected-period totals for won Opportunity count and won kilograms from a
  server aggregate using exactly the same filters as the list.
- Supply bounded historical filter options needed by both roles without depending on
  the supervisor-only Users administration endpoint. Inactive Products and inactive
  responsible users that still occur in won history remain valid filter values.
- Add a lazy-loaded `Ganadas` workspace and a stable route-driven historical detail
  surface. Opening and closing detail preserves the mounted history filters, loaded
  pages, and scroll.

### Active-board retention

- Mark Pipeline list requests explicitly as active-board requests so the generic
  Opportunity list remains backward compatible for Customer/history consumers.
- For an active-board request with `status=GANADA`, return only rows in the rolling
  server-authoritative interval `(as_of - 30 days, as_of]`, where `as_of` is one aware
  UTC value captured by the backend for that request.
- `NUEVA`, `COTIZADA`, and `NEGOCIACION` active-board results are unchanged by the
  retention parameter.
- Apply the same `as_of` and cutoff to both the page query and its `total` count.
- Keep the existing Pipeline stage request topology and CRM-038 partial-refresh,
  generation, optimistic rollback, and entity reconciliation behavior.
- When a mounted board contains a `GANADA` card approaching its expiry, schedule one
  one-shot expiry boundary. At the boundary, remove the deterministically expired
  local card and perform at most one narrow background refresh of the `GANADA` stage
  for server reconciliation. This is not an interval, general poller, or four-stage
  board refresh.
- Recompute the next one-shot expiry whenever the authoritative `GANADA` stage changes,
  and cancel it when the workspace unmounts. Background expiry reconciliation keeps
  stable board and detail content visible and is protected from stale responses by
  CRM-038 request/entity generations.

### Ganadas workspace

- Use visible Spanish terminology: workspace title `Ganadas`, date label
  `Fecha de ganancia`, quantity label `Kg ganados`, responsible label `Responsable`,
  and action `Abrir oportunidad`.
- Default to the current Buenos Aires calendar month, matching the established
  commercial Dashboard convention. Offer `Este mes`, `Últimos 3 meses`, `Este año`,
  `Personalizado`, and `Todo el historial`; `Restablecer` returns to `Este mes`.
- Show a compact summary of total won Opportunities and total won kilograms for the
  applied filters, followed by the result list/table. Do not add charts, distributions,
  conversion rates, forecasts, or duplicate Dashboard analytics.
- Prioritize victory date, customer/company, quoted Products, won kilograms, origin,
  province, responsible user, and detail access.
- Preserve commercially relevant columns at narrow widths through a responsive record
  layout or an internally bounded horizontal table region; never create document-level
  horizontal overflow and never hide the only detail action.
- Keep a last successful page and summary visible during background retry where safe.
  Distinguish initial loading, loading more, empty unfiltered period, no filter match,
  partial list/summary error, and recoverable request failure.
- Encode the applied period and supported dimensions in validated URL query parameters
  so a direct URL and future Dashboard link reproduce the same Ganadas view.

### Detail behavior

- Add `won` as an Opportunity-detail presentation surface with canonical route
  `/won/opportunities/<id>` and owning workspace `/won`.
- A list row opens the existing Opportunity detail using one entity detail request,
  without reloading the Ganadas list or active Pipeline.
- A `GANADA` detail remains subject to current terminal-state rules: no status,
  reopen, quote, Product, assignee, loss, or delete command is introduced or exposed.
- Existing Notes and WhatsApp behaviors remain available exactly where current
  business rules allow them; “historical/read-only” describes the won lifecycle and
  quote projection, not a new prohibition on terminal Opportunity Notes.
- A non-`GANADA` Opportunity opened through the won surface does not masquerade as
  historical won data. It redirects to its existing canonical Pipeline or Pérdidas
  surface after the authoritative detail response.
- The existing Opportunity-detail visual hierarchy is unchanged; its redesign belongs
  to CRM-040.

### Dashboard and navigation boundaries

- Make `/won` capable of accepting the future Dashboard-selected period and dimensions
  through its URL filter contract.
- Do not redesign or reorder Dashboard and do not add Dashboard KPI/cards/charts in
  CRM-039. CRM-041 owns the monthly won/lost hierarchy and links.
- Add only one ordinary `Ganadas` navigation entry adjacent to `Perdidas` in the
  existing management group so the new history is discoverable before CRM-042. Do not
  otherwise rename, reorder, restyle, collapse, or redesign navigation/sidebar.
- CRM-042 may later revise the label or placement without changing the `/won` contract.

### Performance evidence

- Add won-history list and statistics queries to the repository's PostgreSQL EXPLAIN
  performance coverage using a large deterministic historical dataset.
- Statistics execute as SQL aggregates. The service must not materialize every won
  Opportunity or quote line in Python.
- Page hydration must use bounded eager/select-in loading and a bounded number of SQL
  statements per page; it must not issue one detail query per result row.
- The existing partial `ix_opportunities_status_entered_at` index is the default plan
  for current implementation. Investigation with 50,000 transactional probe rows
  produced a backward index scan plus incremental tie-break sort in approximately
  0.027 ms for the first 21 rows. A temporary
  `(current_status_entered_at DESC, id DESC) WHERE status='GANADA' AND deleted_at IS NULL`
  probe reduced that to approximately 0.018 ms, which is not sufficient evidence for
  a production migration.
- CRM-039 therefore authorizes no schema/index change. If implementation-time realistic
  EXPLAIN evidence fails the repository performance budget, stop and return the spec
  to review rather than adding an unapproved migration.

## Non-goals

- Adding `ARCHIVADA`, a manual archive action, an archive timestamp, a won-event table,
  a won snapshot table, or any new Opportunity status or transition.
- Deleting, soft-deleting, mutating, reopening, or moving old `GANADA` Opportunities
  merely because they cross the 30-day board boundary.
- Adding `won_at`; changing how `current_status_entered_at` or status history is written;
  or changing the terminal semantics of `GANADA`.
- Changing Customer, Product, quote, Web intake, WordPress HMAC/idempotency, WhatsApp,
  notification, Legendary, Pérdidas, or reopen business behavior.
- Replacing the existing custom router, CRM-038 Opportunity workspace/reducer, or data
  synchronization architecture.
- Loading the complete won history in the frontend, client-side aggregation, offset
  pagination for history, aggressive polling, or broad Pipeline refetches.
- Redesigning Pipeline cards, columns, Opportunity Detail, Dashboard, sidebar,
  navigation system, icons, terminology outside this feature, or dark mode. Those
  concerns belong to CRM-040 through CRM-043.
- Cloning Pérdidas-only loss reasons, immutable loss episodes, reopen statistics, or
  loss-time snapshots into Ganadas.
- Adding Dashboard links in this spec; CRM-039 supplies their destination and filter
  contract, while CRM-041 owns their visual placement.
- New won analytics beyond filtered count and kilograms.

## Business rules

- `docs/BUSINESS_RULES.md` remains authoritative. `GANADA` is terminal and globally
  visible to both current roles under the existing Opportunity visibility model.
- The authoritative victory time is the aware timestamp at which the Opportunity
  entered its current `GANADA` status. In the current domain this is
  `Opportunity.current_status_entered_at`, corroborated by the matching immutable
  `OpportunityStatusHistory.changed_at` transition to `GANADA`.
- A won Opportunity is active-board-visible while
  `current_status_entered_at > as_of - 30 days` and
  `current_status_entered_at <= as_of`. At exactly 720 elapsed hours it is no longer
  active-board-visible.
- The 30-day rule is an elapsed-duration rule, not “current month”, 30 Buenos Aires
  calendar dates, or a manual archival decision.
- Board visibility is a read-projection rule only. Crossing the cutoff writes no row,
  emits no status history, resolves no notification, and invokes no commercial side
  effect.
- Every non-deleted current `GANADA` Opportunity remains available in Ganadas regardless
  of age. Existing soft-deleted Opportunity behavior remains unchanged and normal read
  endpoints do not expose soft-deleted rows.
- Won count is the count of filtered non-deleted current `GANADA` Opportunities whose
  victory timestamp is in the selected half-open period.
- Won kilograms are the Decimal sum of all retained quoted Product quantities on those
  filtered Opportunities. A Product filter selects Opportunities containing that
  Product; the headline total remains the complete quoted kilograms of the selected
  Opportunities, matching Pérdidas workspace selection semantics. The row may also show
  each Product's own quantity.
- Because `GANADA` has no exit/reopen path and terminal quote/assignment mutation is
  prohibited, one current won Opportunity represents one permanent win. No episode
  deduplication or snapshot entity is required.
- Search matches current Customer name or company and safe numeric Opportunity/Customer
  IDs. It does not perform fuzzy identity matching or broaden global visibility.
- Historical display uses current Customer/Product/user master-data labels and the
  immutable terminal quote quantities. Point-in-time copies of master-data labels are
  not introduced by this scope.

## Data model

No persistence schema change.

- `Opportunity.status == GANADA` identifies the history population.
- `Opportunity.current_status_entered_at` is the authoritative victory timestamp.
- `OpportunityStatusHistory` remains corroborating audit evidence and is not joined for
  every history row because the current status/timestamp is sufficient under terminal
  semantics.
- `OpportunityProduct.quantity_kg` provides retained terminal quote quantities.
- Current `Customer`, `Product`, and assigned `User` relationships provide display and
  filter labels under existing FK/integrity rules.
- Existing indexes used by the projection include
  `ix_opportunities_status_entered_at`, `ix_opportunities_assignee_status`,
  `ix_opportunities_source_created_at`, the Opportunity primary key, and
  `ix_opportunity_products_product_opportunity`/the composite Product-line primary key.

No Alembic migration is authorized by this Draft.

## Contracts / API

### Active-board list

Extend the compatible existing endpoint:

```text
GET /api/opportunities
  ?status=GANADA
  &active_board=true
  &page=1
  &page_size=100
  [&source=WEB|WHATSAPP]
```

- `active_board` defaults to `false` so Customer and other existing generic list
  consumers do not silently lose older won Opportunities.
- When `active_board=true` and `status=GANADA`, the backend captures one aware UTC
  `as_of`, applies the strict rolling cutoff to both count and rows, and retains the
  existing `PaginatedResponse[OpportunitySummary]` shape.
- When `active_board=true` and status is `NUEVA`, `COTIZADA`, or `NEGOCIACION`, the
  result is behaviorally identical to the current query.
- An unfiltered `active_board=true` request is invalid (`422`) rather than ambiguously
  mixing active stages and terminal history. Pipeline continues to request one explicit
  status at a time.
- Existing page ordering remains `(created_at DESC, id DESC)`; frontend-selected
  Pipeline sorting remains a local projection. The retention cutoff applies before
  pagination and `total`.

### Won history list

```text
GET /api/won-opportunities
  ?search=<bounded text>
  &product_id=<positive id>
  &source=WEB|WHATSAPP
  &province=<bounded normalized text>
  &assigned_user_id=<positive id>
  &won_from=<aware datetime>
  &won_to=<aware datetime>
  &limit=20
  &cursor=<opaque cursor>
```

- All filters are optional at the API boundary. `limit` defaults to 20 and is bounded
  to 1–100. Blank normalized search/province values behave as absent.
- If both dates are supplied, `won_from < won_to`; invalid, reversed, or naive values
  return a safe typed validation error.
- Date filtering is half-open: `won_from <= current_status_entered_at < won_to`.
- Ordering is always `(current_status_entered_at DESC, id DESC)`.
- The opaque cursor encodes and validates the final `(won_at, opportunity_id)` key.
  The next page uses strict lexicographic “less than” conditions and the same filters.
- A malformed cursor returns a safe conflict/validation response consistent with the
  Pérdidas cursor contract; it never produces a server error or reveals internals.
- Response:

```text
{
  "items": [
    {
      "opportunity": <OpportunitySummary>,
      "won_at": <aware datetime>,
      "won_total_kg": <Decimal string>
    }
  ],
  "next_cursor": <string|null>
}
```

`won_at` equals `opportunity.current_status_entered_at`; the explicit alias makes the
historical contract legible and is not a second stored value.

### Won statistics

```text
GET /api/won-opportunities/statistics?<same non-pagination filters>
```

Response:

```text
{
  "won_count": <integer>,
  "won_quantity_kg": <Decimal string>
}
```

- List and statistics share one typed filter builder so they cannot drift.
- The count and Decimal sum are SQL aggregates. Empty results return `0` and
  `"0.000"`, not `null` and not frontend-computed values.

### Historical filter options

```text
GET /api/won-opportunities/filter-options
```

Return bounded, deduplicated, label-sorted options observed in non-deleted current won
history:

```text
{
  "products": [{"id": <id>, "name": <name>, "is_active": <bool>}],
  "provinces": [<nonblank string>],
  "responsible_users": [{"id": <id>, "full_name": <name>, "is_active": <bool>}]
}
```

- Unassigned Opportunities are represented by the UI's static `Sin responsable`
  choice, encoded with a dedicated boolean/query value rather than ID `0`; the API may
  expose `unassigned=true` mutually exclusively with `assigned_user_id`.
- This endpoint exposes no email, password/auth state, or administration action and is
  available to both authenticated roles because both already see all Opportunities and
  their assignee names.
- Source options come from the existing typed `LeadSource` presentation mapping and do
  not require a catalog request.

### URL contract

- `/won` and `/won/opportunities/<id>` are authenticated application routes.
- The workspace supports validated query keys `period`, `from`, `to`, `source`,
  `product`, `province`, `responsible`, and `unassigned`. Unknown/invalid values are
  ignored with a safe canonical replacement, not sent to the backend.
- `from` and `to` are UI calendar dates. The frontend serializes them into aware
  Buenos Aires boundaries; a custom visible end date is inclusive and becomes the
  next local midnight in the API's exclusive `won_to`.
- Future Dashboard navigation supplies an explicit applied period; opening bare
  `/won` uses the current-month default.

## State transitions

CRM-039 adds no state transition.

```text
NEGOCIACION -> GANADA   (existing command)
GANADA -> <none>        (terminal, unchanged)
```

The active-board projection changes over time only:

```text
GANADA and age < 30 days  -> visible in active board + visible in Ganadas
GANADA and age >= 30 days -> absent from active board + visible in Ganadas
```

The second line is not a persisted transition, archive operation, mutation, or audit
event.

## Security & permissions

- All new API and application routes require the existing authenticated session.
- Both `SUPERVISOR` and `VENDEDOR` retain global read visibility consistent with current
  Opportunity and Pérdidas workspaces. Responsible filtering never changes visibility.
- Existing role/action rules remain authoritative; the filter-options projection does
  not grant access to Users administration.
- Detail commands continue to be validated by existing backend services. The won
  surface cannot make a terminal Opportunity mutable through hidden or crafted UI.
- Soft-deleted Opportunities remain excluded. Customer/Product/User `RESTRICT`
  integrity and existing inactive-record behavior remain unchanged.
- No secret, HMAC, WordPress intake payload, WhatsApp provider evidence, or customer
  private contact field is added to list/statistics responses.
- CRM-002 Web intake creation, signature validation, replay/idempotency, and immutable
  intake evidence are untouched.

## Edge cases

- At 29 days, 23 hours, 59 minutes, and 59.999… seconds after entry, a `GANADA` row is
  visible on the active board. At exactly 30 elapsed 24-hour days it is excluded.
- The rolling cutoff uses aware UTC instants; Buenos Aires calendar/DST boundaries do
  not alter the 720-hour duration. History date filters, by contrast, use Buenos Aires
  calendar boundaries serialized to aware half-open instants.
- A transition timestamp marginally after the request's captured `as_of` is excluded
  from that snapshot and appears on the next narrow/manual request. Normal commands use
  backend UTC now, so this is principally clock/data-corruption protection.
- Count and page rows use the same captured `as_of`, preventing an Opportunity from
  expiring between the two SQL statements within one request.
- A browser tab left open across expiry removes the due card via its one-shot boundary
  and reconciles only `GANADA`. If that reconciliation fails, the deterministic expired
  card remains absent, the rest of the last successful board stays visible, and scoped
  feedback offers a manual board refresh. No saved-state claim is made for unknown new
  wins.
- A win mutation received immediately before an older expiry response is protected by
  CRM-038 entity/request generations and remains in the `GANADA` column.
- Manual `Actualizar` still performs the four current stage requests and preserves all
  CRM-038 UI state; the server retention filter prevents old `GANADA` rows from being
  reintroduced.
- A `GANADA` Opportunity older than 30 days can still be opened from `/won`; a legacy or
  bookmarked Pipeline detail URL may load the same authoritative detail, but the card
  does not return to the board.
- New wins inserted before an existing history cursor do not duplicate later pages.
  They appear after a deliberate first-page refresh.
- Identical victory timestamps are deterministically ordered by descending Opportunity
  ID and paginated without gaps/duplicates.
- Product filtering includes inactive retained Products. Responsible filtering
  includes inactive assigned users and supports `Sin responsable`.
- Customer/company, Product, province, or responsible display names may reflect later
  master-data corrections; the victory instant and terminal quote quantities do not
  change.
- Soft deletion through existing permitted behavior removes the row from board,
  history, and metrics consistently without deleting its retained database evidence.
- An empty current month explains that no Opportunities were won in that period and
  offers `Todo el historial`; a filter-produced empty state offers filter reset.
- A list request can succeed while statistics fail, or vice versa. Each resource keeps
  independent last-successful/loading/error state and never labels partial evidence as
  complete.
- Direct `/won/opportunities/<id>`, browser Back/Forward, reload, unauthorized access,
  invalid ID, non-`GANADA` status, and missing/deleted Opportunity all resolve through
  typed existing route/error behavior.

## Acceptance criteria

- AC-01: Marking a valid `NEGOCIACION` Opportunity won writes one transition to
  `GANADA`; `current_status_entered_at` and that history row's `changed_at` are the same
  aware instant and no `won_at`, archive row, or additional status is persisted.
- AC-02: At a fixed server `as_of`, a `GANADA` Opportunity entered 29 days 23:59:59 ago
  is returned by `active_board=true`; one entered exactly 30 days ago and one older than
  30 days are not returned.
- AC-03: The exact active interval is `(as_of - 30 days, as_of]` in UTC. Boundary tests
  cover Buenos Aires local-midnight/date conversion and prove that the retention rule
  remains 720 elapsed hours.
- AC-04: Active-board results and totals for `NUEVA`, `COTIZADA`, and `NEGOCIACION` are
  byte-for-byte/semantically unchanged by CRM-039; generic list calls without
  `active_board=true` remain backward compatible.
- AC-05: An old non-deleted `GANADA` Opportunity absent from Pipeline is returned by
  `/api/won-opportunities`, contributes once to won statistics, and opens through
  `/won/opportunities/<id>`.
- AC-06: Won history filters independently and in supported combinations by aware
  victory range, customer/company or numeric search, Product, source, normalized
  province, responsible user, and unassigned state; list and totals use identical
  selection semantics.
- AC-07: Custom history dates serialize inclusive Buenos Aires calendar dates into an
  aware half-open API interval. Bare `/won` defaults to the current Buenos Aires month,
  and `Todo el historial` removes both API date bounds.
- AC-08: Won history returns deterministic cursor pages ordered by
  `(won_at DESC, opportunity_id DESC)` with no duplicate or skipped row when multiple
  Opportunities share a timestamp; malformed cursors fail safely.
- AC-09: Statistics return the server-calculated count and Decimal kilograms for the
  complete filtered result, including zero results, without loading all rows or quote
  lines into application/frontend memory.
- AC-10: Product-filter headline kilograms sum the complete retained quotes of matching
  Opportunities; this rule is documented and covered by a multi-Product fixture.
- AC-11: The filter-options endpoint is usable by both roles, includes inactive
  historical Product/user values and `Sin responsable` support, and exposes no
  supervisor-only user administration data.
- AC-12: The Ganadas workspace shows the approved compact summary and commercially
  relevant evidence, supports load-more cursor pagination, has meaningful initial,
  empty, no-match, loading-more, partial-error, and retry states, and never aggregates
  full history in the client.
- AC-13: Opening historical detail from a mounted Ganadas workspace performs one detail
  request and zero Pipeline/stage-list requests; closing or browser Back returns to the
  same mounted filters, pages, and scroll without list refetch or workspace remount.
- AC-14: A `GANADA` detail exposes no reopen, status, quote/Product, assignee, loss, or
  deletion control. Existing allowed Notes/WhatsApp behavior and Opportunity audit
  history remain available.
- AC-15: A non-`GANADA` ID at the won-detail route redirects to the existing canonical
  Pipeline/Pérdidas surface and never renders as a won-history record.
- AC-16: A mounted Pipeline automatically removes a card at its authoritative 30-day
  expiry, performs at most one narrow `GANADA` reconciliation, and performs zero
  `NUEVA`/`COTIZADA`/`NEGOCIACION`, Dashboard, WhatsApp, notification, catalog, or full
  document refresh requests.
- AC-17: A narrow expiry response started before a successful win mutation cannot
  remove or overwrite the newer authoritative card/detail. Failed expiry reconciliation
  retains stable content and truthful scoped feedback.
- AC-18: Pipeline detail open/close, mutation atomicity, rollback, manual refresh,
  filters, sorting, stage-age preference, scroll, shared catalog, and AppShell/Pipeline
  mount counts continue to satisfy every relevant CRM-038 acceptance/request invariant.
- AC-19: `/won` is lazy-loaded, authenticated, directly addressable, represented by one
  minimally invasive `Ganadas` entry next to `Perdidas`, and its URL-filter contract can
  reproduce a supplied Dashboard period without a Dashboard redesign.
- AC-20: At 390 px and supported desktop widths the Ganadas workspace creates no
  document/body horizontal overflow; all evidence and actions remain reachable, focus
  order is logical, labels are programmatic, and detail focus is restored on close.
- AC-21: Query-count tests prove a bounded number of SQL statements per 20-row page and
  no N+1 detail hydration. Large-history EXPLAIN evidence uses the existing index,
  avoids sort spill/temporary I/O, and stays within repository performance budgets for
  list, filtered list, active-board `GANADA`, and statistics queries.
- AC-22: Existing commercial metrics continue to determine won counts/kilograms from
  current `GANADA` plus `current_status_entered_at`; period metrics are not truncated to
  30 days. The analytical `/metrics/pipeline` contract is not changed by CRM-039.
- AC-23: Existing terminal-state, permissions, Customer/Product integrity, Pérdidas,
  reopen, Legendary, CRM-002/Web intake, WordPress HMAC/idempotency, notifications, and
  WhatsApp tests remain green.
- AC-24: Backend pytest/coverage, Ruff lint/format, mypy strict, compileall, Alembic
  check/current, reproducible locks, pip audit, frontend tests/coverage, Biome,
  TypeScript, production build, npm audit, Docker Compose health/proxy/migration smoke,
  and complete browser/accessibility/visual gates pass before implementation commit.

## Open decisions

None

## Follow-up / future specs

- CRM-040 — Pipeline and Opportunity Detail visual hierarchy.
- CRM-041 — Dashboard commercial hierarchy and monthly won/lost navigation. It will
  link won outcomes to CRM-039's `/won` URL-filter contract.
- CRM-042 — Navigation, compact sidebar, icons, Broadcast visibility, and global
  Spanish terminology. It may revise Ganadas placement/label without changing history
  behavior.
- CRM-043 — Dark theme and global visual consistency.

## Implementation notes

Prefer a focused `WonOpportunityQueryService` rather than extending the loss-event
service. Build one shared typed filter-condition helper for list/statistics/options.
For page hydration, select the bounded Opportunity IDs/aggregate kilograms first, then
load their Customer, assignee, and Product lines in a bounded second query while
restoring cursor order; do not call `get_detail` once per item.

Use SQL `count` and a per-Opportunity quote-total subquery for statistics so joining
multiple Product lines never multiplies Opportunity count or totals. Implement Product
selection with `EXISTS`; after selection, sum the entire quote to preserve the headline
total rule. Use `Decimal` end to end.

Pass an explicit aware `as_of` into the active-board query service from a clock boundary
that tests can fix. Do not accept a client-supplied cutoff or `as_of`. A single request
must reuse the same value for count and page selection.

Extend the CRM-038 Pipeline request helper with `active_board=true`. Add a focused
expiry hook that derives the earliest `GANADA` expiry from authoritative summary
timestamps and schedules `setTimeout` only for that boundary. On expiry, dispatch the
minimum removal/replacement actions through the existing reducer and use the existing
stage/request-generation protections. Do not add an interval.

Keep the won route as one lazy workspace owner analogous to the persistent Pipeline
shape: `WonPage` receives an optional selected ID and renders the existing detail modal
over the retained history state. Extend the typed route model and history-origin logic;
do not introduce a router package. Add query-string observation/navigation narrowly so
filter URLs remain authoritative without causing AppShell remounts.

The analytical `/metrics/pipeline` endpoint remains an all-status current database
snapshot as defined by CRM-004/CRM-021. CRM-039 changes the operational board query,
not historical period metrics or that analytical contract. CRM-041 may later change
how those concepts are labelled/presented, but must not conflate them silently.
