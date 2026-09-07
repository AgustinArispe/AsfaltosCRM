# CRM-038 — Frontend Interaction and Data Synchronization

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-07
Implementation commit: `97ab453`

## Goal

Make the commercial frontend feel immediate, stable, and trustworthy by preserving
the mounted Opportunity workspace across modal navigation, applying authoritative
mutation responses locally, narrowing background reconciliation, and requesting only
the data affected by each Dashboard or Pipeline action.

The user must see that a mutation is pending and then saved without full-page loading,
visible board flicker, lost filters, or broad unrelated refetches. The server remains
the source of truth and failures preserve a consistent, recoverable UI.

## Context

The current frontend uses a small custom History API router and page-local React state;
it does not use React Query, SWR, or another server-state library. Pipeline initially
loads one paginated list per configured stage. Its card-level drag/status flow already
performs an optimistic local replacement and rollback, but Opportunity Detail uses a
separate local copy and several successful mutations increment a key that reloads the
whole detail. Switching between `/pipeline` and
`/pipeline/opportunities/<id>` also changes the routed child composition around the
board and risks remounting/refetching that workspace.

Dashboard currently launches commercial metrics, the current Pipeline snapshot,
notification/follow-up evidence, WhatsApp waiting evidence, and catalogs from effects
with overly broad dependencies. A commercial filter therefore refetches operational
indicators that do not depend on it. The global AppShell notification attention
provider can also own the same active-notification evidence requested independently by
Dashboard.

The authenticated Opportunity mutation endpoints already return an authoritative
`OpportunityDetail`; several frontend API functions currently narrow that response to
`OpportunitySummary`. CRM-038 aligns the frontend boundary with the existing contract
and consumes those responses rather than adding backend calls.

This spec changes frontend interaction and synchronization only. The separately
approved product decision that current `GANADA` Opportunities remain on the active
board for a rolling 30-day window belongs to future CRM-039 and is not implemented by
CRM-038.

## Dependencies

- CRM-018 — Frontend Design System
- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-021 — Dashboard & Metrics
- CRM-022 — Notifications UI
- CRM-023 — WhatsApp Inbox 2.0
- CRM-025 — WhatsApp Broadcast UI
- CRM-037 — Compact Opportunity Detail Modal

## Scope

### Persistent Opportunity workspace

- Keep the Pipeline workspace mounted while an Opportunity Detail route is opened over
  it and while that detail is closed back to Pipeline.
- Establish one stable route/layout boundary for the Pipeline board and its optional
  route-driven detail modal. The modal URL remains deep-linkable and browser Back and
  Forward remain authoritative.
- Preserve the mounted board's applied filters, search draft and debounced value,
  sorting, optional filters, stage-age preference, loaded products, mutation state,
  and per-column/board scroll when detail opens and closes.
- Opening a direct Opportunity URL without an existing mounted Pipeline must load the
  board and detail once. This initial load is not treated as a background refetch.
- Keep Lost-origin Opportunity Detail behavior working. CRM-038 may use an equivalent
  stable owner layout for Lost where needed to synchronize reopening or loss
  navigation, but it does not redesign the Lost workspace.
- Route navigation must not reload the browser document or remount AppShell merely to
  show or close an Opportunity modal.

### Opportunity workspace state and synchronization

- Introduce the smallest typed workspace-level state boundary needed to share the
  authoritative Opportunity collection, selected detail, catalog cache, request
  status, and mutation operations between Pipeline and Opportunity Detail.
- Keep this state scoped to the mounted owning workspace. Do not introduce an
  application-wide entity store or a new server-state dependency.
- Define typed upsert/remove helpers that project an authoritative
  `OpportunityDetail` into the `OpportunitySummary` used by board cards without
  discarding the full detail needed by an open modal.
- Correct frontend API return types to match the existing backend
  `OpportunityDetail` responses for quote creation, quote-product update, assignee
  update, status transitions, loss, and reopen operations.
- Treat each accepted mutation response as the immediate authoritative representation
  of that Opportunity. Update the detail and board projection atomically from that
  response.
- Move or remove the affected board card according to the board's configured stages
  and current filters. CRM-038 retains the existing stage set and does not add the
  CRM-039 30-day `GANADA` cutoff.
- A mutation response that does not contain sufficient authoritative state may trigger
  one narrow `GET /opportunities/<id>` reconciliation. It must not trigger a complete
  board or Dashboard reload.
- Keep Notes synchronization local to the Opportunity context; creating a Note does
  not reload the Opportunity or board.

### Mutation pending and failure behavior

- Preserve stable board and detail content during all background persistence and
  reconciliation.
- Expose a restrained pending state on the affected control/card/section and prevent
  conflicting duplicate commands for the same Opportunity.
- Optimistic mutations are permitted where the transition is deterministic and the
  previous state is retained for rollback. Non-optimistic mutations still keep current
  content visible until the response arrives.
- On success, replace optimistic data with the authoritative response and announce the
  saved state accessibly.
- On a definitive failure, restore the last authoritative Opportunity in both detail
  and board, keep the modal and filters open, and show contextual actionable feedback.
- On an ambiguous transport outcome, do not assert success or blindly roll forward.
  Keep the last authoritative UI, explain that confirmation is required, and permit a
  narrow entity reconciliation or manual board refresh according to the operation's
  existing idempotency guarantees.
- Ignore stale responses that belong to an older selection, filter generation, manual
  refresh, or mutation version.

### Pipeline manual refresh

- The visible `Actualizar` action means: fetch the current Opportunity data needed by
  the Opportunity board.
- It refreshes only the board dataset using the current server-side board filters. It
  must not refresh Dashboard, WhatsApp, notifications, catalogs, or the browser
  document.
- It preserves search, filters, sorting, stage-age preference, selection, open detail,
  modal draft where safe, and scroll.
- Stable board content remains visible while requests run. A compact pending indicator
  and an accessible live announcement communicate progress.
- Successful stage results are reconciled into one coherent board generation. A
  partial stage/page failure must not present a mixture as a fully current board:
  retain the last authoritative data for failed scopes, apply successful scopes only
  when their boundaries are known, identify that the refresh is partial, and offer
  retry. Initial load failure remains an initial error state.
- Concurrent manual refresh requests are deduplicated or the prior request is
  cancelled. A late older refresh cannot overwrite newer mutation data.
- CRM-038 preserves the existing opportunity-list API. A new aggregate Pipeline
  endpoint is not required because current stage requests already run in parallel;
  backend work requires separate evidence and approval.

### Dashboard dependency boundaries

- Refactor Dashboard data orchestration into independently keyed resources without
  changing its visual composition:
  1. period-and-dimension commercial metrics: overview, products, sources, provinces,
     and timeline;
  2. dimension-only current Pipeline snapshot;
  3. stale/follow-up total;
  4. unread-notification total;
  5. WhatsApp waiting evidence;
  6. stable product catalog.
- Each resource owns its request status, last successful value, scoped error,
  cancellation/version guard, and explicit dependency key.
- Changing date range refetches only period-dependent commercial metrics. It does not
  refetch the current Pipeline snapshot, operational attention, or catalog.
- Changing source, product, or province refetches commercial metrics and the current
  Pipeline snapshot because those endpoints consume dimension filters. It does not
  refetch follow-up, unread, WhatsApp waiting, or catalog evidence.
- Dashboard must consume the existing AppShell active-notification attention value
  where it represents the same backend projection instead of issuing a duplicate
  request. If `unread` and `active/follow-up` remain distinct contracts, they remain
  separately named and must not be conflated.
- A Dashboard manual refresh may explicitly refresh all Dashboard-owned resources, but
  must not force global workspace remounts or restart unrelated pollers.
- Background refresh keeps each last successful section visible and reports errors at
  that resource boundary.
- CRM-038 does not alter metric formulas, labels, charts, order, or visual hierarchy.

### Catalog reuse

- Within a mounted Opportunity workspace, active products are loaded at most once for
  concurrent or repeated quote flows unless the user explicitly retries a failed
  catalog request or the catalog is intentionally invalidated after a product change
  in its owning administration workspace.
- Pipeline and its open Opportunity Detail share the same in-flight request and last
  successful active-product collection.
- Dashboard retains one stable catalog request independent of metric filter changes.
- No cross-session persistent product cache is introduced.

### Route/workspace lazy loading

- Convert safe, non-primary workspaces to route-level dynamic imports with bounded
  Suspense/loading fallbacks: Dashboard, WhatsApp Inbox, WhatsApp Broadcasts, Users,
  Products, Customers, and Lost where dependency boundaries permit.
- Keep the initial authenticated route and Pipeline shell responsive; Pipeline may
  remain eagerly loaded as the default commercial workspace.
- Do not split components so finely that ordinary interaction causes repeated loading
  boundaries or network waterfalls.
- A lazy chunk failure presents a recoverable Spanish error and retry/reload guidance;
  authentication and authorization checks continue before protected content is
  presented.
- Hiding Broadcasts from production navigation belongs to CRM-042; CRM-038 only makes
  its existing workspace lazy.

### Measurement and regression evidence

- Add deterministic frontend tests that count API requests and component mounts for
  representative navigation and mutation journeys.
- Capture a before/after request matrix in the implementation evidence for initial
  Pipeline load, detail open, detail close, detail mutation, manual board refresh,
  Dashboard date-filter change, Dashboard dimension-filter change, and repeated quote
  opening.
- Use React render/mount instrumentation only in tests or development diagnostics; do
  not ship user tracking or a production profiling dependency.

## Non-goals

- Implementing CRM-039 won-history, its `GANADA` rolling 30-day board cutoff, a
  `Ganadas` workspace, or related backend queries.
- Implementing CRM-040 Pipeline or Opportunity Detail visual redesign.
- Redesigning Dashboard visuals, information hierarchy, metrics, charts, terminology,
  or layout.
- Redesigning sidebar, navigation, icons, global typography, or Spanish terminology.
- Redesigning dark theme or introducing new color/style tokens for visual polish.
- Adding `ARCHIVADA`, manual archival, new Opportunity states, transitions, or business
  rules.
- Changing metric formulas, WhatsApp waiting semantics, notification semantics, or
  provider polling.
- Adding new polling to Pipeline, Dashboard, catalogs, or Opportunity Detail.
- Adding React Query, SWR, Redux, Zustand, or another global data/state library unless
  a new approved revision documents evidence that the scoped React architecture cannot
  meet the acceptance criteria.
- Backend, persistence, Alembic, domain, permission, or API changes. Investigation has
  found the existing Opportunity mutation responses sufficient; any newly discovered
  backend requirement must stop implementation and return the spec to Draft review.
- Speculative memoization, virtualization, request batching, prefetching, or component
  splitting without measured benefit to an in-scope journey.
- Changing existing notification or WhatsApp polling intervals.

## Business rules

- `docs/BUSINESS_RULES.md` remains authoritative for Opportunity transitions,
  terminal states, quote requirements, loss/reopen behavior, permissions,
  notifications, metrics, and WhatsApp.
- Server responses are authoritative. Optimistic UI predicts only an already permitted
  command and never creates a new transition or bypasses backend validation.
- A visible saved state is never inferred merely because a request was sent.
- `Actualizar` refreshes only current Opportunity-board data and is always deliberate.
- Opportunity mutations synchronize every currently mounted representation of the
  same Opportunity before reporting success.
- Existing global Opportunity visibility remains unchanged.

## Data model

No persistence or schema change.

Frontend workspace state may keep typed `OpportunitySummary` and
`OpportunityDetail` projections indexed by Opportunity ID, request generations, the
last authoritative value needed for rollback, and a shared in-memory active-product
catalog. These are ephemeral client representations, not new business entities.

CRM-038 does not persist filters or scroll beyond the lifetime of the mounted
workspace. Existing sidebar/theme persistence is unchanged.

## Contracts / API

No backend contract change.

CRM-038 consumes the existing contracts:

- `GET /opportunities` for the configured board stages and current server-side source
  filter;
- `GET /opportunities/<id>` for initial/deep-linked detail and narrow reconciliation;
- existing quote, quote-product, assignee, move-to-negotiation, win, lose, and reopen
  mutations, whose responses are `OpportunityDetail`;
- existing metrics, Pipeline metrics, notification, WhatsApp conversation, and product
  endpoints.

Frontend API declarations must represent actual response models. A full
`OpportunityDetail` may be projected to a summary locally; it must not be falsely
narrowed at the transport boundary simply because a card needs fewer fields.

No request may omit authentication, authorization handling, AbortSignal support, or
existing optimistic-concurrency fields. No cache may cross users or authentication
sessions.

## State transitions

No domain transition changes.

The client synchronization lifecycle is:

1. retain the last authoritative entity and mark only the affected operation pending;
2. apply a deterministic optimistic projection when safe;
3. send exactly one mutation command;
4. on success, atomically upsert the returned authoritative detail and board summary;
5. perform at most one entity-scoped reconciliation only when response contents are
   insufficient;
6. on definitive failure, roll back every mounted projection to the retained
   authoritative value and display contextual feedback;
7. on stale response, discard it without overwriting a newer generation.

Navigating between board and route-driven detail changes selection and URL, not the
owning workspace's lifecycle.

## Security & permissions

- Existing authentication, role authorization, route guards, and Opportunity action
  visibility remain unchanged.
- Lazy loading must not expose protected content before authentication/role checks.
- Client cache/state is cleared when its authenticated owner unmounts or the session
  ends. No data is written to localStorage or sessionStorage by CRM-038.
- Optimistic UI does not grant authority; all commands remain validated by FastAPI.
- Errors expose existing safe messages and never reveal provider, SQL, token, or stack
  details.

## Edge cases

- A direct detail URL has no warm board state and performs one legitimate initial board
  load plus one detail load.
- Browser Back/Forward changes selected detail without resetting the board.
- Opening Opportunity B while A's request is pending cannot render A into B.
- Closing a detail while its request or mutation is pending cannot update an unmounted
  modal; an authoritative board update may still complete when safe.
- A card that no longer matches current filters after mutation is removed from the
  projected board without clearing those filters.
- A transition to `PERDIDA` removes the card from Pipeline and moves detail navigation
  to its existing Lost surface without first reloading the board.
- A successful reopen uses the returned `NEGOCIACION` detail and makes the card
  available to the mounted Pipeline projection without a broad reload. The Lost list
  may reconcile its affected row locally or narrowly when mounted.
- Manual refresh overlapping a mutation cannot overwrite a mutation response with a
  snapshot started earlier. Generation/version ordering determines which response is
  eligible to commit.
- One failed stage/page during manual refresh retains prior data for that scope and
  marks the board as partially refreshed; counts must not claim complete freshness.
- A failed background Dashboard resource leaves unrelated successful sections and
  their last data intact.
- Changing filters rapidly aborts or ignores obsolete requests.
- Multiple quote controls opened while the catalog is loading share one request.
- Failed catalog loading can be retried without discarding quote draft state.
- Lazy chunk loading at a slow connection uses one stable fallback and does not flash
  the authentication screen.
- Unauthorized responses continue to end the session through the existing centralized
  handler.

## Acceptance criteria

- AC-01: From an already loaded `/pipeline`, opening
  `/pipeline/opportunities/<id>` preserves the same mounted Pipeline workspace and
  issues zero additional four-stage `GET /opportunities` list sequences.
- AC-02: Closing that detail back to `/pipeline` preserves filters, search, sort,
  stage-age preference, loaded cards, and board/column scroll, and issues zero
  additional stage-list requests.
- AC-03: Browser Back and Forward open/close the route-driven detail over the same
  mounted board; a direct detail URL remains loadable and performs no duplicate board
  generation after its initial load.
- AC-04: Quote creation, quote-product update, assignee update, move to negotiation,
  win, lose, and reopen frontend clients consume their existing authoritative
  `OpportunityDetail` responses and update every mounted projection of that
  Opportunity without a complete board reload.
- AC-05: A successful detail mutation that returns sufficient data performs zero
  follow-up `GET /opportunities/<id>` calls; an insufficient response is allowed at
  most one documented entity-scoped reconciliation and never a stage-list refresh.
- AC-06: During background mutation/reconciliation, stable board and detail content
  remain visible, only affected controls/entities indicate pending state, focus stays
  usable, and no full-page/modal loading replacement or layout flicker occurs.
- AC-07: A definitive optimistic-mutation failure restores the prior authoritative
  stage, detail, products, and metadata consistently, leaves selection/filters/scroll
  intact, and provides contextual visible plus accessible feedback.
- AC-08: Pipeline `Actualizar` starts only the current board dataset requests, does not
  reload the document or remount AppShell/Pipeline, and does not request Dashboard,
  WhatsApp, notification, or product-catalog endpoints.
- AC-09: Manual refresh preserves open detail, filters, search, sort, stage-age state,
  and scroll; a partial request failure retains truthful previous data for failed
  scopes, identifies partial freshness, and offers retry without clearing the board.
- AC-10: Request-generation tests prove that an older manual refresh, filter request,
  detail fetch, or mutation response cannot overwrite a newer authoritative mutation
  or selection.
- AC-11: Changing only Dashboard date range refetches overview, product, source,
  province, and timeline period metrics, but performs zero Pipeline-snapshot,
  follow-up, unread-notification, WhatsApp-waiting, or product-catalog requests.
- AC-12: Changing Dashboard source, product, or province refetches the commercial
  metrics and dimension-dependent current Pipeline snapshot, but performs zero
  follow-up, unread-notification, WhatsApp-waiting, or catalog requests.
- AC-13: Dashboard operational resources retain independent loading/error/last-success
  state, and equivalent active-notification evidence is not requested simultaneously
  by both Dashboard and AppShell.
- AC-14: Repeated or concurrent quote opening within one mounted Opportunity workspace
  issues at most one successful active-product catalog request unless the user retries
  a failure or an explicit catalog invalidation occurred.
- AC-15: Dashboard, WhatsApp Inbox, WhatsApp Broadcasts, and admin-heavy workspaces are
  loaded through safe route/workspace chunks; Pipeline remains usable as the initial
  authenticated workspace, and lazy loading preserves route guards and recoverable
  Spanish loading/error states.
- AC-16: No new polling interval, global data library, backend route, persistence
  field, migration, Opportunity rule, metric formula, or visual redesign is introduced.
- AC-17: Implementation evidence records exact before/after request counts and mount
  counts for the eight specified journeys; all in-scope after-counts match AC-01–AC-15
  and no undocumented request regression remains.
- AC-18: Focus restoration, modal trapping, live pending/success/error announcements,
  keyboard navigation, and reduced-motion behavior continue passing focused
  accessibility tests.
- AC-19: Frontend TypeScript, Biome lint/format, unit tests, coverage, build, npm audit,
  Docker Compose health checks, browser journeys, and relevant visual regression pass;
  mandatory backend Ruff, mypy strict, pytest/coverage, compileall, and Alembic gates
  also remain green before implementation commit and push.

## Open decisions

None

## Follow-up / future specs

- CRM-039 — Won Opportunity History and rolling 30-day `GANADA` visibility in the
  active Pipeline, based on the authoritative current `GANADA` entry timestamp.
- CRM-040 — Pipeline and Opportunity Detail visual hierarchy.
- CRM-041 — Dashboard commercial hierarchy and won/lost navigation.
- CRM-042 — Navigation, compact sidebar, icon consistency, Broadcast visibility, and
  Spanish terminology.
- CRM-043 — Dark theme and global visual consistency.

## Implementation notes

Prefer a persistent `OpportunityWorkspace` route/layout component containing the
Pipeline state boundary, board outlet, and optional route-driven detail overlay. Keep
the custom router if it can preserve component identity cleanly; CRM-038 does not
authorize a router migration. A reducer plus narrowly scoped contexts/hooks is likely
sufficient. Separate state from visual components and avoid passing an unbounded
all-purpose context value through the entire application.

Use typed request generations or per-entity mutation versions with AbortController.
For manual multi-stage refresh, stage/page completion must be tracked explicitly so a
partial result is distinguishable from a complete snapshot. Apply the authoritative
mutation response after any older refresh snapshot, or merge by protected entity
version, rather than relying only on arrival order.

Dashboard may use multiple focused hooks or one orchestrator composed from independent
resource hooks. Dependency keys must be explicit and testable. Reuse AppShell
notification attention through its existing context where semantics match; do not
silently equate unread and active/follow-up totals.

Use `React.lazy` and `Suspense` at stable workspace boundaries. Do not add artificial
delays or eager prefetch all lazy chunks, which would defeat the request/bundle goal.
