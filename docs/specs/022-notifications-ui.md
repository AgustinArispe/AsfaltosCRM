# CRM-022 — Notifications UI

Status: Draft
Owner: FAA CRM team
Last updated: 2026-08-13
Implementation commit: N/A

## Goal

Create a simple, premium operational notification workspace that attracts attention only when it is necessary, lets the FAA team acknowledge and revisit stale-Opportunity evidence, and never feels like a noisy social-media inbox.

## Context

CRM-003 owns the only implemented notification type, OPPORTUNITY_STALE. Notifications are global team records with independent read_at and resolved_at timestamps: reading acknowledges attention, while an Opportunity status change or soft deletion resolves active stale evidence. The backend preserves the row and offers authenticated paginated listing, single read, and active-only read-all commands.

The current frontend has no notification API module, page, list, sidebar badge, or notification route. Its AppShell/navigation and internal router are the future integration boundaries. The current direct Opportunity route, /opportunities/:id, fetches a non-deleted Opportunity including PERDIDA; Pipeline list queries exclude PERDIDA. CRM-018 is mandatory for the permanent sidebar, themes, tokens, accessibility, responsive behavior, shared components, motion, and performance. CRM-019 and CRM-020 own the future Pipeline and centered Opportunity detail experience.

## Dependencies

- CRM-003 — Stale Opportunity Notifications
- CRM-018 — Frontend Design System
- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-021 — Dashboard & Metrics

## Scope

- Define Notifications as the dedicated App Shell sidebar workspace directly below Dashboard.
- Define the global sidebar attention badge, chronological list/history, compact All/Unread view, read acknowledgement, existing active-only read-all command, and safe Opportunity navigation.
- Define polling, loading/empty/error, keyboard/accessibility, responsive, visual, performance, and frontend-ownership behavior using only current notification contracts.
- Define the exact cross-workspace consistency required of the sidebar, Dashboard attention summary, Pipeline, Opportunity detail, and notification history.

## Non-goals

- Redesigning stale-notification generation, threshold, resolution, persistence, roles, or global read semantics.
- Email, push, browser notifications, sounds, deletion, dismiss/snooze behavior, complex preferences, seller filtering, or a top-navbar/dropdown notification system.
- Redesigning Pipeline, Opportunity detail, Lost workspace, backend contracts, or state management; adding new endpoints; or implementing this spec.
- A mobile-specific notification centre, oversized red counters, attention-seeking loops, or social-media-inbox styling.

## Business rules and existing contracts

### Authoritative state

CRM-003 and docs/BUSINESS_RULES.md remain authoritative:

- The only current type is OPPORTUNITY_STALE, created for an open Opportunity that has remained in NUEVA, COTIZADA, or NEGOCIACION at least the configured threshold without a status change.
- Notification state is global to the team. A read does not belong to one user or device, does not delete evidence, and does not resolve the notification.
- A transition out of its stale state or Opportunity soft deletion resolves the active stale notification. Quote edits and assignee edits do not resolve it.
- Resolved records are historical evidence. A later stale stage may create a new record for the same Opportunity.

The UI renders read and resolved as independent facts. An item can be unread but resolved because its Opportunity changed state before anyone acknowledged it. It must not be visually rewritten as deleted or silently treated as active attention.

### Existing API use

| Existing contract | Required UI use |
| --- | --- |
| GET /notifications | Bounded authenticated pagination with deterministic created_at DESC, id DESC ordering. The page uses page/page_size and returned total; each row already includes type, timestamps, Opportunity status/current-stage timestamp, and Customer name/company. No per-row enrichment is allowed. |
| GET /notifications?include_resolved=true | The Todas view. It is the complete chronological history, including read and resolved records. |
| GET /notifications?unread_only=true&include_resolved=true | The Sin leer view. It truthfully includes both active and resolved records whose read_at is null. |
| GET /notifications?unread_only=true | A compact page_size=1 badge/attention query. Its total is the exact number of unread active notifications, matching the backend's current operational attention semantics. |
| POST /notifications/{id}/read | Idempotent acknowledgement on opening one row. It sets read_at only and returns the authoritative item. |
| POST /notifications/read-all | Existing active-only bulk acknowledgement. It marks unresolved unread rows only and returns updated_count; it does not delete, resolve, or mark historical resolved unread rows. |

No frontend-local read state, per-device persistence, notification type filter, deletion, or client-computed stale definition is authorized.

## Sidebar destination and attention badge

Notifications is a dedicated sidebar destination immediately below Dashboard in the CRM-018 order. It exists for both SUPERVISOR and VENDEDOR; current backend visibility is global and no seller restriction is introduced. The sidebar is the only global notification navigation pattern—there is no primary top-navbar bell, dropdown feed, or duplicate notification centre.

The AppShell attention query represents unread active notifications only. When its exact total is zero, no badge is rendered. When positive:

- expanded sidebar shows a compact count, visually secondary to the navigation label but clearly noticeable;
- collapsed sidebar preserves the count or compact overflow token beside the icon, active-route marker, tooltip, and accessible label;
- visible count may cap at 99+, but the accessible name contains the exact returned total, for example 123 notificaciones activas sin leer;
- the badge uses CRM-018 NotificationBadge and FAA semantic accent/selective surface tokens, not a large destructive-red blob. Shape, text/icon, and accessible name communicate attention independently of colour.

The badge does not claim all unread historical records are current attention. A resolved record with read_at null remains visible in Sin leer history but does not keep the active-attention badge on. This precisely matches the existing read-all and Dashboard active-summary semantics.

## Notifications page

### List model and visual hierarchy

The page title is Notificaciones. Below it, a quiet description may explain that the list records commercial follow-ups and that acknowledgement does not erase history. A compact CRM-018 SegmentedControl offers only:

- Todas — default, chronological complete history using include_resolved=true.
- Sin leer — unread history using unread_only=true and include_resolved=true.

There is no manual sorting, search, source/product/seller filter, permanent filter wall, or pagination disguised as a dashboard. The default and every loaded page use the server's newest-first stable order: created_at DESC, then id DESC. A clear Load more control is shown only when loaded item count is lower than returned total.

The list uses semantic ol or ul/listitem structure. Each calm, rounded row is a single readable operational summary, not a card full of Customer CRM data. In visual and reading order it contains:

1. concise action reason, currently Seguimiento pendiente;
2. Customer/company identity from the embedded notification Opportunity;
3. a short operational explanation, for example La oportunidad sigue sin cambio de etapa;
4. useful relative and absolute creation time using shared formatters;
5. current referenced Opportunity status when it clarifies why the history remains relevant; and
6. independent acknowledgement/resolution evidence.

A nonblank company is supporting identity when Customer name is primary; if the normalised values are equal, display it once. Missing/malformed embedded identity uses a safe Cliente sin identificar fallback without fetching. Internal notification, Opportunity, and Customer IDs are never shown.

Unread active rows receive restrained surface/weight/icon emphasis. Read rows are quieter. Resolved history carries a textual Resuelta marker and does not appear as an actionable current follow-up. Both read/unread and active/resolved state use text or icons as well as token-driven colour; no value is communicated solely by colour. There are no hover-only actions.

### Read acknowledgement and history

Opening a notification is the normal acknowledgement gesture:

1. activation begins the idempotent POST /notifications/{id}/read request and gives local pending feedback only for that row;
2. it opens the deterministic Opportunity target without waiting for a slow acknowledgement response;
3. on success, the local row is reconciled to returned read_at and the AppShell active-unread badge refreshes;
4. on failure, the row remains visibly unread and a non-blocking recoverable feedback state explains that acknowledgement could not be saved. The target navigation is not falsely reported as a successful read.

Visiting /notifications alone never silently marks all records read. This avoids a global side effect merely for looking at history and keeps the badge until its individual active items are acknowledged.

When unread active records exist, the page exposes the existing command with the exact label Marcar activas como leídas, not the misleading label Marcar todas. It requires no destructive confirmation but shows pending/disabled feedback to prevent duplicate submits. Success applies returned updated_count, updates only applicable locally loaded active rows or refetches the current view, refreshes the badge, and announces concise completion. It neither resolves/deletes records nor claims to affect unread resolved history.

Every read record remains visible in Todas. Reading is acknowledgement, not deletion. Resolved history remains visible irrespective of read state, subject only to the user's selected segmented view.

## Opportunity navigation and historical safety

A notification's primary row activation is an Opportunity-context request; its read action is not a separate tiny required target. Navigation is status-aware but backend detail remains authoritative:

| Referenced state | Required destination behavior |
| --- | --- |
| NUEVA, COTIZADA, NEGOCIACION, or GANADA | When an approved CRM-019/CRM-020 route-selection contract exists, open the matching Opportunity in the Pipeline context and centered CRM-020 detail. Do not fabricate a new Pipeline status or move a card. |
| PERDIDA | Do not route to the active Pipeline Kanban. Use the Lost workspace/detail contract only when CRM-024 owns it; until then use the current direct Opportunity detail route if the entity is available. |
| Deleted/unavailable or failed detail fetch | Preserve the notification as a historical row and show a precise, safe Oportunidad no disponible state. Do not crash, infer a replacement Customer, or navigate to a nonexistent Pipeline column. |

The current reliable route is /opportunities/:id, which can fetch any non-deleted Opportunity including PERDIDA but renders the legacy full-page detail. It is the safe fallback while the required route-to-centered-detail selection contract is unresolved. A 404 after activation keeps the user in a safe historical-target state and restores logical focus to the Notifications list/relevant row on return. Notification rows never cause status, quote, loss, reopen, or Customer mutations.

## Relationship to Dashboard and other workspaces

CRM-021 may show compact attention summaries, but CRM-022 owns the complete list/history and read acknowledgement UI. The Dashboard and sidebar use the same exact active-unread query definition; they do not independently infer stale state from Opportunities or use conflicting counts. Dashboard may link to /notifications only after this route exists, but does not read or resolve a notification merely by showing its summary.

Pipeline and CRM-020 own Opportunity presentation and commercial action rules. Notifications may request a valid context but never define the detail body, a loss/reopen workflow, or an external WhatsApp action.

## Loading, refresh, and performance

Initial load uses a small list skeleton with rows matching final density. It is not a full-page spinner. The list request is bounded by existing page_size limits and initially requests only one page; Load more performs the next explicit page request. Background refresh preserves current rows and scroll position.

Notification polling is intentionally lighter than the five-second WhatsApp change-feed cadence because this API has no notification change cursor and stale notifications are generated by the existing backend process. While the document is visible, online, and authenticated:

- AppShell checks active unread attention on a shared configurable 60-second cadence with page_size=1.
- The Notifications page refreshes its first loaded page on the same configurable 60-second cadence, without overlapping requests. Browser focus, visibility return, and online reconnect trigger one immediate refresh.
- A route-local page may supply fresh active-unread evidence to the AppShell badge to avoid unnecessary duplicate work, but ownership remains narrow; no global state library is introduced.
- Polling pauses offline/background, aborts obsolete work, retains last-good data on recoverable error, and never resets filter, list scroll, or keyboard focus.

Newer first-page records reconcile by stable notification ID. If the user is at the list top, new rows can appear at the top with a restrained count/status update. If the user has scrolled away, the list retains its visual anchor and offers a quiet Nuevas notificaciones control to apply the refreshed top rows. Loaded pages de-duplicate by ID; offset pagination is never presented as a cursor or as a complete unchanging snapshot.

The page performs no Opportunity or Customer row requests. Opening a row is the first time it may fetch Opportunity detail, and only the selected entity is fetched. Badge and list data remain small, typed, and independently retryable.

## Empty, error, responsive, and motion behavior

The page distinguishes:

- no notifications yet in Todas;
- no unread notifications in Sin leer;
- initial list failure with Retry; and
- a background-refresh failure with retained content and unobtrusive stale/retry feedback.

No state uses a decorative illustration, fake count, or full-page spinner after initial rendering. API errors do not erase previous history, change a read state locally, or remove the badge without backend confirmation.

At all CRM-018 supported laptop/desktop widths and zoom levels, the list uses available content space, safe wrapping/truncation of long Spanish Customer/company names, and no horizontal page overflow. The permanent sidebar collapses according to CRM-018 while retaining its badge/tooltip/accessibility label. This spec does not create a mobile-specific centre.

Motion is minimal and functional: short opacity/transform feedback for new-row insertion, row acknowledgement, badge count change, and segmented-control selection. There are no looping pulses, shaking rows, red flashes, or attention animation. prefers-reduced-motion makes state changes immediate or minimally faded and never suppresses content.

## Keyboard, accessibility, security, and architecture

- Rows are semantic keyboard-reachable links/buttons with useful accessible names containing reason, Customer/company identity, current status/resolution when relevant, read state, and age/time without reciting hidden CRM fields. Enter opens the target; Space activates a button-pattern row where used.
- The All/Unread SegmentedControl follows its CRM-018 keyboard/selected-state contract. Escape only closes a safe topmost overlay; the list itself does not consume Escape. Focus remains logical after a row update, bulk acknowledgement, pagination, retry, or return from Opportunity context.
- Visible focus, semantic list/heading/landmark structure, sufficient Light/Dark contrast, non-colour state evidence, accessible badge counts, 44-by-44 targets where practical, reduced motion, and restrained live regions target WCAG 2.2 AA. Polling does not announce every refreshed row; only a user-initiated acknowledgement, an actionable error, or the optional new-items affordance receives concise live feedback.
- Both current roles use authenticated same-origin notification endpoints through the existing API/session boundary. The feature exposes no secrets, raw backend internals, or untrusted HTML. Backend authorization remains decisive.
- A typed frontend/src/api/notifications.ts module will own list/read/read-all contracts. An AppShell-owned attention hook owns the small global badge projection; a Notifications feature hook owns list pages, selected filter, polling, deduplication, pending rows, and error translation. Feature views compose CRM-018 shared primitives and receive typed data/callbacks only. No visual component calls APIs and no global state library is added.

## Backend contract gaps

- The notification response has no availability/deleted flag for its referenced Opportunity. The UI can safely discover an unavailable entity only when the selected detail request returns 404; it must preserve the historical row rather than claiming availability.
- There is no notification change cursor or count-only endpoint. The exact active-unread badge total is still available through the existing bounded page_size=1 response; list refresh uses bounded polling and stable-ID reconciliation rather than inventing realtime semantics.
- POST /notifications/read-all intentionally affects only active unread rows. It cannot truthfully be labelled as marking all historical unread rows read, so the UI uses Marcar activas como leídas.
- The existing response does not offer an Opportunity-to-Pipeline centered-dialog route/selection representation. This is a frontend cross-spec gap, not authorization to add a backend endpoint.

## Acceptance criteria

- AC-01: Notifications is a dedicated sidebar destination directly below Dashboard for both roles; no top-navbar/dropdown notification system is added.
- AC-02: Expanded and collapsed sidebar states show a compact, accessible badge only for the exact unread active notification total and preserve orientation, tooltip, and active state.
- AC-03: The default Todas page is a newest-first semantic chronological history including resolved/read records; read acknowledgement never deletes or hides history.
- AC-04: Each quiet list row communicates stale reason, Customer/Opportunity identity, useful time, current relevant state, and independent read/resolved evidence without excess CRM metadata or colour-only state.
- AC-05: Opening one row invokes idempotent backend read acknowledgement, reconciles only authoritative success, refreshes attention state, and keeps navigation usable/recoverable if acknowledgement fails.
- AC-06: The explicitly labelled active-only read-all action uses the existing backend command, prevents duplicates, does not delete/resolve history, and never claims to acknowledge resolved unread records.
- AC-07: Compact Todas/Sin leer segmented views use the documented API combinations, no manual ordering, and no complex filtering system.
- AC-08: Active Opportunity notifications use Pipeline plus CRM-020 detail only after an approved route-selection contract; PERDIDA never routes to the active Kanban, and unavailable targets remain safe historical rows.
- AC-09: CRM-021 Dashboard, the sidebar badge, and this workspace share the exact active-unread attention definition and do not mutate/read notifications by rendering summaries.
- AC-10: Initial, refresh, new-item, load-more, offline/reconnect, no-history, no-unread, and error states preserve list stability and use scoped feedback without routine full-page spinners.
- AC-11: Visible/online polling is bounded, non-overlapping, abortable, focus/scroll-preserving, and does not announce every update or perform N+1 requests.
- AC-12: Keyboard rows, segmented control, focus, meaningful accessible names, live feedback, non-colour status, contrast, reduced motion, and semantic list structure meet CRM-018/WCAG 2.2 AA requirements.
- AC-13: Available-space responsive layout, sidebar collapse, long labels, and zoom preserve a readable desktop/laptop workspace with no page-level horizontal overflow.
- AC-14: The feature consumes only existing typed notification/Opportunity contracts, fetches detail only after explicit row activation, adds no global state library, and follows CRM-018 Light/Dark/System, IBM Plex Sans, token, rounded-geometry, and motion rules.

## Open decisions

- **Opportunity context routing is a blocker.** CRM-019 and CRM-020 require active Opportunities to use Pipeline plus a centered detail dialog, but neither currently owns a route/URL selection contract for an Opportunity ID. CRM-024 has not yet defined the Lost workspace route/detail handoff. The existing direct /opportunities/:id route is a safe fallback but does not meet that preferred Frontend 2.0 presentation. Before CRM-022 can be Approved, approve one cross-spec owner and deterministic route contract for active, lost, and unavailable notification targets; do not invent a query parameter or backend endpoint to close the gap.

## Follow-up / future specs

- CRM-023 — WhatsApp Inbox 2.0: may share AppShell badge/polling infrastructure only if its existing global conversation semantics remain independent.
- CRM-024 — Customers / Products / Lost: owns Lost workspace and its selected-Opportunity navigation contract.
- CRM-026 — Final Accessibility & UX Polish: verifies list, badge, polling, and cross-route focus conformance.

## Implementation notes

Implement only after this Draft is approved and the cross-spec Opportunity routing decision is resolved. Preserve CRM-003 global read/resolved semantics and existing API pagination. Add focused API/hook/component tests for exact badge totals, history/read transitions, bulk active-only acknowledgement, stable polling reconciliation, 404 target safety, keyboard focus, and no-N+1 behavior; do not alter notification generation or backend contracts as incidental UI work.
