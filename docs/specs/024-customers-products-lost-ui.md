# CRM-024 — Customers, Products and Lost Workspaces UI

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-14
Implementation commit: 7e5e82a9aed0da58175956308efee9131fcd84e4

## Goal

Redesign the secondary commercial workspaces—Customers, Products, and Lost
Opportunities—so they are simple, premium, fast, and consistent with FAA CRM Frontend
2.0, without duplicating the Pipeline or Opportunity detail experience.

CRM-018 is mandatory. CRM-019 owns the active Pipeline and CRM-020 owns full
Opportunity detail and commercial actions. This spec composes those contracts; it does
not change business rules, authorization, or backend data definitions.

## Dependencies

- CRM-012 — CRM Commercial Completion
- CRM-018 — Frontend Design System
- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-022 — Notifications UI
- CRM-023 — WhatsApp Inbox 2.0

## Scope

- Scan-friendly Customer list, detail, maintenance actions, and supervisor Customer CSV
  import flow.
- A deliberately small, role-aware Product catalog workspace.
- A dedicated Lost workspace for current lost Opportunities, bounded filters, existing
  aggregate history, and explicit reopen handoff.
- Shared loading, responsive, keyboard, visual, route-composition, and performance
  conventions for the three workspaces.

## Non-goals

- Changing Customer, Product, Opportunity, loss, Legendary, import, role, or soft-delete
  business rules.
- A marketing database, segmentation, inventory, pricing, SKU, categories, product
  stock, seller filtering, mobile-native UI, or a replacement Dashboard.
- Returning `PERDIDA` to Pipeline, duplicate Opportunity detail forms, a hidden Customer
  restore workflow, or module-specific deep-link hacks.
- A global browseable historical-loss episode catalogue. Frontend 2.0 owns current Lost
  Opportunities plus the existing aggregate historical/reopened statistics only.

## Shared visual, layout, and architecture contract

All three workspaces use CRM-018 semantic tokens, IBM Plex Sans, Light/Dark/System
themes, and shared Button, Input, Search, Select/Combobox, Filter, Badge, Tooltip,
Dialog, ConfirmationDialog, Surface, Skeleton, EmptyState, ErrorState, and feedback
primitives. The visual tone differs by purpose without becoming a different product:

- **Customers** is a calm relationship workspace.
- **Products** is a concise catalog/administration workspace.
- **Lost** is serious commercial history; restrained destructive red is semantic
  evidence, never a page surface or decorative theme.

Route-level workspace containers own data loading, filters, pagination/cursors, scoped
mutation reconciliation, and local dialog state. Typed API clients own request
contracts. List rows and forms are presentational/composed feature components. Do not
introduce a global state library or feature-local replacements of CRM-018 primitives.

Page identity and the relevant primary action sit above a compact search/filter row.
Lists use a table/list hybrid: semantic rows, generous identity column, quiet secondary
columns, and clear hover/press/focus feedback. A row opens its detail surface; explicit
actions remain independently reachable and never depend on hover.

## Customers workspace

### List, search, and pagination

`Customers` is for finding, inspecting, creating, and maintaining Customers quickly.
The default view is the active Customer list (`include_deleted=false`) in the existing
deterministic backend order: normalized Customer name ascending, then ID. It does not
invent a client-side sort order.

The compact default columns are:

| Priority | Information | Presentation |
| --- | --- | --- |
| Primary | Customer name, then company when present | One identity cell; company is supporting, not a competing heading. |
| Secondary | Province | Show when present; collapse before identity at constrained width. |
| Secondary | Contact evidence | One concise available email or phone; do not show both as permanent wide columns. |
| Status | Effective Legendary state | Subtle gold/champagne badge with text/icon evidence; never color-only. |

The current Customer summary has no bounded commercial aggregate. The list therefore
shows no Opportunity counts, kg, conversion, or hand-built commercial summary, and does
not make per-row Opportunity requests to manufacture one.

Search is useful but subordinate to page identity. It is debounced and bounded by the
existing Customer search contract. Resetting search restores page one. Use existing
page/total pagination with compact previous/next controls and an honest range/total; do
not disguise a partial page as a complete count. Background refresh preserves the page
and current rows whenever possible.

### Actions, permissions, and deletion

Both authenticated roles use the current Customer create/edit behavior for Customer-owned
fields: name, company, email, phone, and province. Manual Legendary historical override
is visible/editable only to `SUPERVISOR`; sellers receive neither a disabled nor a
misleading control. Effective Legendary state is shown subtly to both roles, while its
automatic/manual implementation mechanics stay out of normal seller-facing detail.

`SUPERVISOR` alone sees Customer CSV import and soft-delete actions, matching the
backend. Soft delete uses a focused confirmation that names the Customer and explains
that the Customer cannot create new Opportunities while valid commercial history remains.
It does not promise restore, hard deletion, or removal of historical evidence. Success
reconciles only the affected row/page; failure preserves content and shows safe feedback.

Create and edit are explicit CRM-018 modal/form flows, not permanently editable table
cells. Fields have visible labels, adjacent validation, Save/Cancel, scoped pending
feedback, safe Enter only from a valid form context, and dirty Escape/close protection.
Backend validation, permission, unavailable, and network errors never report fictional
success.

### Customer detail

Opening a Customer uses a generous centered CRM-018 read-first detail dialog, not a
drawer. It has a calm hierarchy:

1. identity, company, concise contact details, province, and effective Legendary state;
2. compact commercial Opportunity history; and
3. explicit Customer actions allowed by the viewer's role.

It does not expose internal IDs, turn values into a collection of pills, or become a
giant editable form. `Editar` changes only the needed scope. At constrained available
width or zoom, it becomes one ordered column with bounded internal scrolling.

Fetch Customer detail only when opened. Use bounded existing Opportunity and Lost
projections for that one selected Customer; never fetch detail per Customer row. Each
Opportunity row is compact—status, source, relevant date, and already-projected
product/quantity evidence—and opens CRM-020 rather than embedding Opportunity detail.
Current lost Opportunities may be included through the current Lost projection.
Browsable historical/reopened loss episodes are deliberately outside Frontend 2.0;
aggregate history remains the existing statistics projection and individual Opportunity
history remains available after that entity is opened.

### Customer CSV import

Customer import is a supervisor-only focused progressive dialog or bounded subflow, not
a raw CSV viewer. It follows CRM-012's persisted import contract:

1. choose one CSV and state accepted Customer columns;
2. submit a client import UUID to dry-run validation, with no Customer mutation;
3. present create, enrich, unchanged, and error counts;
4. show validation errors as a searchable/scrollable accessible row-and-field summary,
   not a giant raw CSV rendering;
5. state that confirmation commits all rows atomically or none; and
6. require explicit confirmation with returned version and file digest, then show the
   authoritative success or failure summary.

The report already provides typed row/field issues. There is no download-report
contract, so the UI provides clear in-product details rather than inventing a download.
Invalid or stale previews cannot be confirmed. Commit uses a command UUID and disables
duplicate confirmation while pending; ambiguous/failing results reconcile through the
persisted report before a deliberate retry. Enter selects/advances only safe steps and
never commits from file selection or an error list. Escape never silently discards a
selected or validated import without a discard choice.

## Products workspace

FAA's Product catalog is small. Its UI optimizes for quick scanning and safely changing
availability, not enterprise inventory management.

For a `SUPERVISOR`, fetch the existing bounded complete catalog including inactive
Products. Use one compact table/list: Product name, textual active/inactive state, and
explicit create, edit, deactivate, or reactivate actions. A compact active/inactive
count may aid orientation but must not become a metrics dashboard.

For a `VENDEDOR`, request and show only active Products through the existing
authorization contract. Do not render admin columns, disabled controls, inactive rows,
or an unavailable-product management empty state. Backend authorization remains decisive
even when controls are hidden.

Inactive rows remain readable and visibly distinct with label/icon plus restrained muted
treatment, never gray text alone. Deactivation requires confirmation explaining that it
removes the Product from future quotes but preserves historical Opportunities, quotes,
losses, and metrics. Reactivation is explicit and reconciles only its row.

Create/edit uses CRM-018 form dialogs with visible labels, adjacent duplicate/validation
errors, safe Enter, focus restoration, and dirty-close protection. Forms contain only
existing name and active-state concepts; no price, SKU, stock, category, or inventory
field is introduced. Mutations update the local bounded list without a global CRM reload
unless authoritative reconciliation requires one.

## Lost workspace

### Purpose, list, and ordering

`Lost` is a first-class commercial-history workspace outside Pipeline. It helps sellers
understand current losses, find relevant lost Opportunities, review preserved evidence,
and reopen an eligible Opportunity. It is never a fifth Pipeline column.

The default list consumes the existing current-Lost cursor projection. Its objective
order is exactly latest loss event first (`lost_at` descending, then loss-event ID
descending); React never reorders it. Each scan-friendly row shows only:

- Customer/company identity;
- loss reason;
- lost date;
- source;
- quoted Product/total-kg summary already returned by the Lost projection; and
- textual `Reabierta previamente` evidence only when the returned Opportunity's
  `is_reopened` projection is true.

The list omits assignee, full contact information, every Opportunity field, and
duplicated Pipeline status. Loss reason and date are readable primary evidence; red is
limited to loss/status cues. Opening a row invokes CRM-020 Opportunity detail, not a
second loss-detail form.

Use opaque `next_cursor` to load the next bounded page without fake totals or page
numbers. Changing a filter begins a new server projection and clears its prior cursor.
Newly reopened items leave current Lost only after backend success; quiet feedback offers
the appropriate active commercial context.

### Filters and statistics

Filters follow CRM-018's compact secondary pattern. Search and common `Motivo` remain
visible; date is compact where supported. Province, Product, source, and an exact
selected Customer belong in `Más filtros`, with active-filter count and one-action reset.
No seller/user filter exists.

Use only the current server-side combined filter contract: bounded search, one-or-more
loss reasons, Customer ID, normalized province, Product ID, source, and timezone-aware
half-open lost-date range. Search does not claim unsupported fields; a Customer picker is
a bounded Customer lookup, not Opportunity-detail enrichment. Inactive Products remain
valid historical filter values when backend rules permit them.

The optional statistics strip is compact and operational, not a second CRM-021
Dashboard. It uses only the same-filter `LostStatistics` response. Default summaries
are current lost Opportunity count/kg, historical loss-episode count, and reopened-
episode count. A compact reason distribution is optional when useful. If visualized, it
reuses CRM-021's approved chart surface, tokens, keyboard/text alternative, loading, and
reduced-motion rules; it adds neither a chart library nor broad Dashboard analytics.

Statistics explicitly label `actual` and `histórico`. Decimal kilograms preserve backend
precision. Missing/no-data never becomes fictional zero performance.

### Reopen

Reopen is an explicit CRM-020 commercial action, reachable from a current Lost row's
detail or a clearly labelled row action. Its focused confirmation states the only
backend-owned outcome: the Opportunity returns to `NEGOCIACION`. It explains that loss
reason, quote snapshot, and status/loss history remain preserved.

The mutation uses the existing idempotent command UUID and expected `PERDIDA` status.
While pending, only reopen is disabled. Validation, stale-state, permission, or conflict
errors retain history and reconcile authoritative detail; the UI never offers another
destination or treats failure as reopened. On success, remove/reconcile the row, open or
return to active Pipeline/CRM-020 context, and provide restrained feedback. A later loss
is a distinct historical episode, never visually merged with the prior loss.

## Shared navigation, loading, responsive, and accessibility behavior

CRM-018 owns the shared typed manual-router contract. Customers use `/customers/:id`;
active Opportunities use `/pipeline/opportunities/:id`; current Lost Opportunities use
`/lost/opportunities/:id`; and exact WhatsApp Conversations use
`/whatsapp/conversations/:id`. Customer-to-Opportunity and Lost-to-Opportunity open
CRM-020 through those canonical paths, never through module-specific query parameters
or legacy direct-detail routes. Typed same-app `history.state` origin/fallback preserves
the originating workspace and focused trigger where practical; it contains no arbitrary
return URL, filter blob, phone number, or temporary feature state. Direct links fall
back to their owning workspace.

Initial loads use contextual list/table, Product, Lost, detail, and import skeletons,
not full-page spinners. Distinguish initial empty data, search/filter no results,
supervisor-only capability, unavailable/deleted entity, permission denial, validation
conflict, and API failure. Background refresh preserves visible content and uses subtle
updating/error feedback rather than flashing.

Respond to available CSS width, browser zoom, App Shell sidebar state, and content.
Primary identity remains readable. Secondary columns collapse, move into an accessible
row-details popover, or are omitted before a table forces page-level horizontal overflow.
When horizontal scrolling is genuinely necessary, confine it to a labelled table region.
Dialogs have bounded heights and internal scrolling. No mobile-native redesign is needed.

WCAG 2.2 AA / CRM-018 behavior applies: semantic tables/lists, captions or useful
accessible labels, keyboard-reachable rows, `Enter` to open a focused entity where safe,
visible focus, logical Tab order, labelled fields, adjacent errors, dialog focus trap and
return, safe Escape, contextually safe Enter, and text/icon plus color for every state.
Reduced motion, contrast, and reasonable desktop pointer targets remain intact.

## Performance

- Customers use existing server pagination and debounced bounded search; Lost uses its
  cursor projection; Products may use the bounded full catalog because FAA's catalog is
  small.
- Keep list/detail requests separate. Fetch Customer, Opportunity, import, and Lost
  detail only when needed; never enrich Customer/Lost rows with per-row API calls.
- Apply scoped mutation reconciliation rather than global workspace reloads. Preserve
  visible list content during background requests and avoid unnecessary rerenders.
- Profile before virtualization or new state abstractions; any future optimization must
  preserve semantic tables, keyboard focus, selected rows, and cursor/page position.

## Acceptance criteria

- AC-01: Customers presents an active, paginated, backend-ordered list with compact
  Customer/company identity, province/contact evidence, effective Legendary state,
  debounced bounded search, and no per-row commercial enrichment.
- AC-02: Customer create/edit, manual Legendary override, soft delete, and import
  visibility follow existing `VENDEDOR`/`SUPERVISOR` authorization exactly.
- AC-03: Customer detail is a read-first CRM-018 surface with concise identity, contact,
  effective Legendary, and on-demand commercial Opportunity history that opens CRM-020.
- AC-04: Customer forms have explicit save/cancel, safe Enter/Escape, adjacent
  validation, role-safe controls, focus management, and backend-authoritative errors.
- AC-05: Supervisor Customer import uses choose → dry-run → accessible summary/errors
  → explicit atomic confirmation → result, exposes no hidden partial import, and
  prevents duplicate/stale confirmation.
- AC-06: Products is a compact catalog: supervisors manage active/inactive Products,
  while sellers see active Products only and no administrative controls.
- AC-07: Product create/edit/deactivate/reactivate uses shared dialogs, safe pending and
  confirmation behavior, and explains historical preservation without new concepts.
- AC-08: Lost is a dedicated non-Pipeline workspace whose current rows use authoritative
  latest-loss-first cursor order and concise Customer, reason, date, source, projected
  product/kg, and reopened evidence.
- AC-09: Lost filters use only supported search, reason, Customer, province, Product,
  source, and half-open date contracts; they are compact, resettable, server-authoritative,
  and contain no seller filter.
- AC-10: Lost statistics use only matching backend data, label current/historical
  evidence clearly, preserve Decimal display, and do not duplicate CRM-021.
- AC-11: Reopen is explicit, confirms the sole `NEGOCIACION` result, preserves loss
  evidence, uses the idempotent command/status contract, and reconciles only after success.
- AC-12: Customers, Lost, Opportunity detail, and WhatsApp use CRM-018 canonical
  Customer/active-Opportunity/Lost-Opportunity/Conversation paths and typed same-app
  return context without module-specific hacks.
- AC-13: Initial, background, empty, filter-empty, permission, unavailable, validation,
  and API-error states use CRM-018 patterns without routine full-page flashing.
- AC-14: Tables/lists/dialogs adapt to viewport and zoom with readable identity,
  confined overflow only when necessary, no page overflow, and no mobile-native design.
- AC-15: Semantic list/table/form/dialog behavior, keyboard opening/activation, focus,
  labels, non-color state, contrast, targets, and reduced motion meet CRM-018/WCAG.
- AC-16: List/detail separation, pagination/cursor use, scoped refresh, and bounded
  Product loading avoid frontend N+1, unnecessary global reloads, unmeasured
  virtualization, and a global state-library addition.
- AC-17: All three workspaces use CRM-018 tokens, shared primitives, IBM Plex Sans, and
  Light/Dark/System themes; their purpose-specific FAA variants remain consistent.

## Open decisions

None

## Follow-up / future specs

- CRM-021 may surface existing commercial aggregates; CRM-024 does not broaden them.
- Customer restore, segmentation, browseable historical-loss episodes, or downloadable
  import report require their own approved backend/UI contracts.
- CRM-026 verifies cross-workspace accessibility and interaction consistency without
  weakening these requirements.
