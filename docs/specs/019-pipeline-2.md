# CRM-019 — Pipeline 2.0

Status: Draft
Owner: FAA CRM team
Last updated: 2026-08-13
Implementation commit: N/A

## Goal

Redesign the FAA sales Pipeline as a premium, extremely scannable, high-capacity Kanban. Sellers must be able to understand many active leads quickly and open commercial detail only when it is needed.

## Context

The Pipeline is the CRM home workspace. The current implementation already loads the four active statuses, keeps `PERDIDA` out of that query, opens detail on a card, and uses the existing commercial transition endpoints. It also fetches paginated stage results to completion, embeds Customer and quoted-product summaries in every Opportunity summary, and has keyboard-capable DnD. CRM-019 replaces its presentation and interaction foundation; it does not change those business contracts.

`docs/BUSINESS_RULES.md` remains authoritative for commercial state, roles, visibility, Legendary qualification, quote validity, loss, and reopening. CRM-018 is the mandatory visual, interaction, accessibility, responsive, component, theme, and performance foundation. Nothing in this spec may silently contradict it.

## Dependencies

- CRM-001 — Core CRM
- CRM-003 — Stale Opportunity Notifications
- CRM-010 — WhatsApp Inbox Frontend
- CRM-012 — CRM Commercial Completion
- CRM-018 — Frontend Design System

## Scope

- Make `/pipeline` the primary FAA working board with exactly four visible active columns: `NUEVA`, `COTIZADA`, `NEGOCIACION`, and `GANADA`.
- Define dense, minimal Opportunity cards, objective per-column ordering, compact controls, card activation, accessible DnD, and explicit non-drag progression.
- Apply the shared FAA App Shell, Light/Dark/System themes, semantic tokens, IBM Plex Sans typography, rounded geometry, loading states, and accessibility behavior from CRM-018.
- Define the handoff from a card to the future CRM-020 centered Opportunity Detail modal, including the WhatsApp shortcut contract it will own.
- Use CRM-018's canonical active-Opportunity path
  `/pipeline/opportunities/:id` for that detail selection.
- Preserve the existing typed Opportunity, Customer, Product, and commercial command APIs. The spec identifies how their currently available data is used; it does not authorize a new endpoint, a new global state library, or a backend redesign.

## Non-goals

- Redesigning Opportunity, Customer, Legendary, quote, loss, reopen, or role business rules.
- Manual ranking, persistence of arbitrary within-column card order, seller/user filters, or a `PERDIDA` column in the active board.
- Showing all Customer/contact, quote, product, kilogram, province, assignee, or timestamp data on a card.
- A mobile-native product, a marketing-site visual language, or an industrial theme.
- Defining the full CRM-020 detail layout, redesigning the WhatsApp Inbox, or opening an external `wa.me` flow.
- New backend endpoints unless a later approved spec identifies and resolves a real contract blocker.

## Business rules and board model

### Active columns and status evidence

- The board renders the configured active sequence `NUEVA -> COTIZADA -> NEGOCIACION -> GANADA`. It is not implemented as one component per status; a shared column component consumes the stage configuration.
- `PERDIDA` is absent from the active Kanban and remains in the dedicated Lost workspace defined by CRM-012. Loss is an explicit commercial action, never a drag destination.
- Column headers contain only the localized stage name and, when the number is known exactly, a useful current-result count. They do not contain decorative metrics.
- Status is primarily communicated by the column label and position. All columns use the shared neutral FAA surface and border system; subtle semantic edge or header evidence may distinguish stages, but not four unrelated saturated colours. `GANADA` may use the restrained success token. FAA yellow remains the selective identity/action/focus accent, not a universal stage colour.

### Opportunity card

Cards are compact, quiet clickable surfaces with enough hierarchy to scan without opening detail. Their default content, in visual order, is:

1. primary Customer identity;
2. one supporting identity line only when it adds information;
3. compact lead-source evidence; and
4. the effective Legendary marker when applicable.

Identity follows this deterministic rule:

- A nonblank `customer.company` is primary and the nonblank Customer name is the supporting line.
- Without a company, the Customer name is primary and there is no supporting line.
- If normalized company and Customer name are equal, show the value once as primary.
- A malformed embedded Customer falls back to `Cliente #<customer_id>` when its ID is present, otherwise `Cliente sin identificar`; it does not cause a per-card fetch.

Source is concise text with an accessible name (for example, `Web` or `WhatsApp`), not an oversized decorative badge. Legendary uses the server-provided effective `customer.is_legendary` value, never a frontend recomputation or the manual component alone. Its antique-gold/champagne semantic treatment includes the text or accessible name `Legendario`; colour alone never carries that state.

Phone, WhatsApp number, email, quoted Products, kilograms, province, assignee, creation time, time in stage, and a redundant status label are not shown by default. `Mostrar antigüedad de etapa` is an optional compact view setting under `Más filtros`. When enabled it adds a clearly labelled, muted elapsed value calculated from `current_status_entered_at`; it is off by default and has no commercial effect.

An attention marker is optional. It may appear only when a bounded, already-loaded CRM-003/CRM-022 notification projection proves an unresolved attention state for this Opportunity. It has a textual accessible name, causes no per-card request, and is omitted when that evidence is unavailable.

### Ordering, counts, and filters

There is no manual ordering. Each filtered column is objectively ordered using stable ties:

| User sort | Per-column order |
| --- | --- |
| `Más recientes` (default) | `created_at DESC, id DESC` |
| `Más antiguas` | `created_at ASC, id ASC` |
| `Más tiempo en etapa` | `current_status_entered_at ASC, id ASC` |
| `Menos tiempo en etapa` | `current_status_entered_at DESC, id DESC` |

The existing Opportunity list contract is already server-ordered by `created_at DESC, id DESC` and accepts `status` and `source`, but has no search, product, or sort query parameter. CRM-019 therefore uses these bounded rules rather than implying unsupported server behavior:

- The board requests each active status through the existing paginated list endpoint until its reported `total` has been loaded. A selected `source` is passed to that endpoint, so it remains server-filtered and its result/count is exact.
- Search is a debounced local projection over the returned Customer name and company. Sort, optional time-in-stage display, and Product matching are also local operations over that same complete in-memory board projection.
- Product choices are derived from quoted Product lines returned with the board. They include inactive historical Products if they occur in a loaded quote; an unquoted `NUEVA` Opportunity cannot match a Product filter. CRM-019 does not claim a server-side Product filter.
- Search, Product, and source combine with AND. Filter controls are compact and secondary: persistent search, sort, and source controls; Product and the time-in-stage display preference under `Más filtros`; a visible active-filter count; and one clear/reset action. No seller filter or permanent filter wall is added.

Counts always describe the same currently visible filtered projection as the cards. When all pages were loaded, the count is exact. If a later measured performance change uses a partial page/window, the header must not present a partial value as a total: it either labels it `N cargadas` or hides the count until an exact supported total exists. Filtering changes only the visible projection, never the business status or persisted order.

## Interaction and state transitions

### Card activation and detail handoff

The primary usable card surface navigates through CRM-018 to
`/pipeline/opportunities/:id`, which opens the centered CRM-020 Opportunity Detail
modal over Pipeline; it is not a permanent drawer. Enter opens the focused card.
Normal pointer activation remains reliable because a discernible drag movement threshold
separates click from drag; users never need a tiny drag handle.

CRM-019 does not define the detail body. It requires CRM-020 to provide a generous, read-first dialog with a clear explicit `Editar` action, commercial actions, history/notes access, and the WhatsApp shortcut described below. Detail data may be fetched when that modal opens; the board summary is not enriched one card at a time.

The detail action area is the explicit non-drag alternative for every permitted move. It is available by opening the card with mouse or Enter, so no critical card action is hover-only.

### Drag and drop

DnD is an interaction layer over the existing backend-owned commercial transitions:

- A draggable card uses essentially its whole primary surface. Busy, terminal, or otherwise ineligible cards are not advertised as draggable.
- Only the immediately valid configured destination is presented as a valid target. `NUEVA -> COTIZADA` is a quote intent: dropping there opens the CRM-020 quote flow and leaves the card in `NUEVA` until the quote command succeeds. It never silently changes status.
- `COTIZADA -> NEGOCIACION` and `NEGOCIACION -> GANADA` call their existing commands. A card may move optimistically only for these currently safe transitions; it shows local pending feedback and rolls back to its prior authoritative summary with a useful error if the backend rejects it.
- `GANADA` has no outbound drag destination. Moving to loss is available only through the deliberate loss workflow in detail, with the required reason and confirmation.
- Dropping inside the source column creates no mutation and no order change. Invalid targets are neither styled nor announced as valid, and never call an API.

Keyboard DnD follows the current accessible DnD model: Space picks up the focused eligible card, arrow keys select an allowed destination, Space or Enter completes, and Escape cancels. Enter before pickup opens detail. Announce pickup, valid destination, completed move, cancellation, and backend rollback only when the information changes. After a successful move, focus follows the same card in its destination column; after cancel or rejected change it remains on the source card. Quote-flow focus moves into the dialog and returns to the initiating card on cancellation, or the moved card after success. Motion and announcements follow CRM-018 reduced-motion and live-region rules.

### WhatsApp shortcut

The card never exposes a phone number or WhatsApp number. CRM-020 may expose one quiet, labelled WhatsApp action in its detail modal. It must:

1. use the existing authenticated WhatsApp conversation listing/search contract only on this explicit action, searching the normalized Customer phone first when present and Customer/company identity otherwise;
2. accept an exact normalized external-phone match first, otherwise a result whose returned Customer ID equals the Opportunity Customer ID. If more than one Customer match remains, preserve the existing Inbox priority order rather than inventing a local ranking; and
3. navigate through CRM-018's canonical `/whatsapp/conversations/:id` contract, which
   opens that existing conversation in the CRM WhatsApp workspace.

The action never opens `wa.me` or another external flow. If no safely verified internal conversation is found, it shows the backend-supported safe state `No existe una conversación interna vinculada` and offers no invented send/create action. It does not alter the WhatsApp backend contract.

## Layout, responsive behavior, and states

### Board density and available space

The Pipeline occupies the App Shell main work area and respects actual CSS viewport, browser zoom, sidebar state, and content width rather than device labels. A column has a minimum practical width of `15rem` and a compact shared-token gap. Four columns fit without horizontal scrolling when the board has about `63rem` of usable width. At a common 1280 CSS-pixel laptop width this normally permits four columns with the sidebar collapsed; at roughly 1024 CSS pixels or equivalent browser zoom, three readable columns remain visible and the fourth is reached with board-local horizontal scroll. At wider common laptop/desktop widths, four columns remain visible with the expanded sidebar.

The sidebar remains permanently available as defined by CRM-018; collapsing it is the first space-saving control and the board reflows immediately. Card type is never reduced below CRM-018's comfortable small-text scale merely to fit another column. Long identity text truncates safely with an accessible full-name mechanism.

Horizontal overflow belongs only to the labelled board region when the available container cannot hold four minimum columns. It provides a visible native scroll path, keyboard focus, and an understandable scroll hint; it must not create horizontal page overflow. Column headers remain visible while a bounded board/column list scrolls when that layout is used, without creating fragile competing page scroll regions.

Cards use shared spacing and surface tokens to maximize useful vertical density without cramping. Board, column, and card surfaces adapt through CRM-018 semantic Light and Dark tokens; no component hardcodes a theme colour.

### Loading, refresh, mutation, empty, and error states

- Initial board load shows four contextual column skeletons with header/count/card shapes, not a full-page spinner.
- Refresh preserves the last good board while it refetches. It avoids flashing or routine reordering; a subtle refreshing/stale indicator communicates the state. CRM-019 does not add polling or a change feed. Any user-triggered or later background refresh must defer nonessential resorting while a drag or mutation is in progress.
- A quote, transition, or loss marks only the affected card/action pending. It does not block the entire board.
- An empty active Pipeline, an empty individual stage, no matches after filtering, and initial-load failure are distinct compact states. A no-match state includes reset; a failed initial load provides retry. Empty columns use quiet text, not decorative illustrations.
- A refresh error keeps existing cards and exposes non-blocking stale/error feedback. A rejected mutation preserves or restores the authoritative card and gives a meaningful, actionable error.

## Accessibility, permissions, and performance

- CRM-018's WCAG 2.2 AA target applies. Cards, controls, horizontal board region, DnD, menus, dialogs, and feedback use semantic HTML, accessible names, visible focus, logical Tab/Shift+Tab order, sufficient contrast, non-colour status evidence, and reasonable pointer targets.
- Card accessible names state the useful identity and source without reading hidden contact, quote, or assignee metadata. Column labels and counts have useful singular/plural names. Live regions are concise and do not announce routine visual refreshes.
- Escape closes the top safe dialog/popover; dialog focus is trapped and returns to its trigger. Enter confirms only contextually safe primary actions. It never submits multiline content or a destructive action accidentally; destructive loss uses its deliberate confirmation flow.
- Both existing roles see the same active Pipeline. No seller/user filtering or client-derived permission rule is introduced. The backend remains authoritative for every state change and any resulting rejection.
- The board uses the summary's embedded Customer, Product, and timing data. It makes no per-card API request, N+1 frontend enrichment, or eager detail request. Detail is fetched on activation where needed.
- Search is debounced; a single-card mutation replaces only that summary and its affected column projection. Avoid rerendering the entire board unnecessarily. Virtualization, a new cache/state library, or a different frontend framework require measured evidence and a separately approved decision. Charts are out of scope and cannot degrade Pipeline interaction.

## Acceptance criteria

- AC-01: `/pipeline` renders exactly the configured `NUEVA`, `COTIZADA`, `NEGOCIACION`, and `GANADA` active columns; `PERDIDA` is absent and remains in its dedicated Lost workspace.
- AC-02: Column headers use the common FAA semantic visual system, contain only useful stage/count orientation, and never rely on four unrelated saturated colours or colour alone.
- AC-03: Cards are high-density and show only deterministic Customer/company identity, source, and effective Legendary evidence by default; excluded contact, quote, assignee, location, timestamp, and redundant status metadata is not rendered.
- AC-04: Legendary uses effective backend state with an antique-gold/champagne, textually accessible treatment; time in stage is off by default and available only through the documented compact view preference.
- AC-05: Every column uses objective stable ordering with `Más recientes` as `created_at DESC, id DESC`; users can select oldest and both documented time-in-stage orders, and a same-column drop never persists order.
- AC-06: Search, sort, source, Product, active-filter indication, `Más filtros`, and reset follow the compact CRM-018 filter pattern. Source uses its existing list contract; search/Product/sort use only the complete loaded projection and do not claim unsupported backend filtering.
- AC-07: Exact filtered column counts match visible cards after all result pages load; a partial future projection uses an honest loaded-count or no aggregate count.
- AC-08: Card activation uses CRM-018's `/pipeline/opportunities/:id` route to open the
  centered, read-first CRM-020 detail modal; it does not define a competing
  drawer/detail layout and retains an explicit non-drag action path through detail.
- AC-09: The whole usable card surface supports reliable pointer DnD while normal click and Enter open detail. Keyboard users can pick up, move among valid destinations, complete, and cancel DnD with the documented Space/arrow/Enter/Escape model.
- AC-10: Only valid commercial transitions are presented; `NUEVA -> COTIZADA` opens quote flow without premature movement, subsequent valid moves reconcile with the backend, rejection rolls back, and loss is outside normal DnD.
- AC-11: The CRM-020 WhatsApp action never displays a card phone number or opens an external flow; it verifies an existing internal conversation before handing it to CRM-023 selection, otherwise presents the defined safe state.
- AC-12: Initial loading uses board skeletons; refresh preserves cards; affected-card pending, retryable error, empty Pipeline, empty column, and no-results states are distinguishable and compact.
- AC-13: The board responds to container width, sidebar state, and zoom with `15rem` minimum columns, four-column fit around `63rem`, accessible board-local scrolling only when needed, and no horizontal page overflow.
- AC-14: Light, Dark, and System themes, semantic tokens, IBM Plex Sans, rounded geometry, focus, reduced motion, semantic status communication, dialog behavior, and keyboard interactions comply with CRM-018 and WCAG 2.2 AA where applicable.
- AC-15: Pipeline loading and interaction make no per-card/N+1 enrichment request, defer detail fetches until activation, avoid unnecessary whole-board rerenders, and introduce no global state library without measured evidence and explicit approval.
- AC-16: CRM-020 through CRM-026 may specialize this Pipeline contract but must not silently contradict CRM-018 or CRM-019.

## Open decisions

None.

## Follow-up / future specs

- CRM-020 — Opportunity Detail & Quote Flow: implements the centered read-first detail modal, quote intent, explicit commercial actions, history/notes access, and the WhatsApp action surface required here.
- CRM-022 — Notifications: may provide the bounded unresolved-attention projection required before a Pipeline card renders an attention marker.
- CRM-023 — WhatsApp Inbox 2.0: defines the internal selected-conversation navigation contract consumed by CRM-020; it does not require a new WhatsApp backend endpoint.
- CRM-024 — Customers / Products / Lost: owns the Lost workspace presentation and related specialized Customer/Product views.
- CRM-026 — Final Accessibility & UX Polish: verifies cross-module conformance without weakening the ACs in this spec.

## Implementation notes

Implement within the existing React/Vite/TypeScript/Tailwind architecture. Route-level composition owns Pipeline screen state; a Pipeline feature hook/service owns typed board fetching, local projection, mutations, and cancellation; shared CRM-018 primitives own controls, surfaces, dialog semantics, feedback, and tokens. Keep commercial command/API ownership in the existing typed API client. Reuse the configured stage collection and shared `PipelineColumn`/card primitives instead of one-off feature variants.
