# CRM-020 — Opportunity Detail & Quote Flow

Status: Draft
Owner: FAA CRM team
Last updated: 2026-08-13
Implementation commit: N/A

## Goal

Define the primary Opportunity interaction surface: a premium centered detail dialog with progressive disclosure, fast keyboard interaction, commercial actions, notes/history, scoped editing, internal WhatsApp navigation, and a simple step-by-step quote flow.

## Context

CRM-019 makes the Pipeline card the entry point for Opportunity detail. The current frontend opens a right drawer and a separate dense quote dialog; the backend already owns detail, status history, quote create/update, loss, reopen, Customer update, Opportunity Notes, and internal WhatsApp conversation queries. CRM-020 redesigns the frontend interaction over those authoritative contracts. It neither changes commercial rules nor adds pricing, quote versions, or a WhatsApp provider flow.

`docs/BUSINESS_RULES.md` remains authoritative. CRM-018 and CRM-019 are mandatory dependencies: their semantic FAA design system, centered-dialog philosophy, accessibility/keyboard rules, Pipeline transitions, card handoff, and WhatsApp selection contract apply without exception.

## Dependencies

- CRM-001 — Core CRM
- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API
- CRM-010 — WhatsApp Inbox Frontend
- CRM-012 — CRM Commercial Completion
- CRM-018 — Frontend Design System
- CRM-019 — Pipeline 2.0

## Scope

- Replace the Pipeline detail drawer with one large, centered, read-first Opportunity dialog and a responsive two-zone layout.
- Show only useful commercial and Customer information, status history, and integrated Notes; reveal editing and focused action flows explicitly.
- Define valid state-aware commercial actions, quote create/update, loss, reopen, and the handoff to an existing internal WhatsApp conversation.
- Reuse the current authenticated Opportunity, Customer, Note, Product, User, and WhatsApp APIs through typed feature services. Keep the backend authoritative.
- Define loading, errors, conflicts, focus, unsaved-data, performance, and projection reconciliation behavior for detail actions.

## Non-goals

- Redesigning Opportunity, Customer, quote, loss, Legendary, reopen, or role business rules; adding backend fields/endpoints; or changing API ownership.
- A drawer, full-page replacement detail screen, generic multipurpose form framework, pricing, monetary totals, SKU, stock, quote version history, or arbitrary activity records not supplied by existing contracts.
- Redesigning the Pipeline, Lost workspace, Customer workspace, or WhatsApp Inbox.
- External WhatsApp/`wa.me` navigation, a new frontend framework, or a global state library without measured evidence and separate approval.

## Detail dialog and information hierarchy

### Shell and layout

- Activating a CRM-019 Pipeline card opens one centered modal dialog, never a drawer. Its inline size is at most `72rem`; its block size leaves a visible viewport margin; its body, not the page, scrolls when needed.
- On sufficient available container width, the body is two zones: a primary commercial zone of roughly two thirds and a narrower contextual zone of at least `18rem`. Primary content always receives the larger share.
- When available width, browser zoom, or content no longer supports both zones, they become one ordered column: identity/actions, commercial information, then activity/Notes. The dialog retains bounded internal scrolling and never creates page-level horizontal overflow.
- Header identity remains visible within the dialog while its body scrolls where practical. It contains Customer/company identity, current status, source, effective Legendary evidence, and the restrained action group—not an internal Opportunity ID.
- Calm shared surfaces, labels, spacing, and semantic status evidence separate sections. Pills are reserved for compact status/source/Legendary evidence, not every value. FAA yellow is selective action/focus identity; `GANADA` and loss use shared semantic states without colour-only meaning.

### Read-first information

Opening detail shows information, never a screen of editable inputs. The primary zone orders Customer/company identity and state, current quote, useful Customer commercial contact/responsible-user data, then quieter creation/current-stage dates. It never exposes an internal ID.

The current quote is a readable compact list of Product and quantity, including a historical-inactive marker when returned line data requires it. `NUEVA` shows the quiet empty state and `Cotizar`. No price, monetary total, SKU, stock, quote-version history, or implementation-only Legendary mechanics is shown.

The contextual zone uses one shallow segmented control, `Actividad | Notas`, rather than nested tabs. `Actividad` is default and presents supplied status history in newest-first stable `(changed_at DESC, id DESC)` order, with transition text and time; an actor is shown only if a current response supplies a useful name. The current API has no quote version history, so no fictional quote-history panel appears.

`Notas` uses the existing Notes projection: pinned current notes first, then current revisions newest-first as the backend supplies them. Each note renders plain text, author and revision time, and optional pinned evidence. Notes and activity remain available in terminal states; HTML is never interpreted. Their empty, loading, page-continuation, retry, and error states remain local to the contextual zone and do not block identity or commercial actions.

### Notes composition

`Agregar nota` is a clear non-hover action in the Notes context. It expands a bounded multiline plain-text composer in that zone with visible `Guardar nota` and `Cancelar`; it does not open another dialog. A note is appended with one client-generated command UUID and its authoritative response reconciles the current projection. Existing note body/revision operations remain append-only; this spec introduces neither deletion nor overwrite.

Enter adds a newline. `Ctrl+Enter`/`Cmd+Enter` submits only a valid nonempty note when no IME composition is active; the visible save button is equivalent. Escape cancels an untouched composer, but asks before discarding a dirty draft. Errors appear beside the composer. A failed note save preserves its draft and reuses the same command UUID only for a transport retry of that exact unchanged note; a 409/revision conflict reloads current Notes and never overwrites another revision.

## Scoped editing and commercial actions

### Explicit edit model

The header `Editar` action opens a focused edit state within the same dialog layer; it does not make the large detail a giant form. Its scope follows data ownership:

- Customer identity/contact edit contains only name, company, email, phone, and province through the existing Customer update contract. It clearly states that the change applies to that Customer across FAA CRM.
- `Responsable` is a separate supervisor-only edit using the existing user list and Opportunity assignee contract. `VENDEDOR` sees the assigned value but no assignment control.
- Source, Opportunity status, effective Legendary evidence, commercial history, and quote lines are not generic editable fields. Quote changes use the dedicated quote flow; manual Legendary administration remains Customer-owned rather than exposing automatic/manual mechanics here.

Edit state starts with original server values and isolates only the selected scope. It has clear Save/Cancel actions, adjacent validation errors, pending feedback, and authoritative reconciliation after save. Escape or close returns to read-first detail when clean; with modifications it asks for deliberate discard versus continue editing. Enter may submit only a valid single-line safe scoped form, never a multiline Note or destructive action. Validation, permission, conflict, or network errors leave inputs intact and explain the next safe action.

### State-aware actions

The action group presents only operations permitted by current authoritative state and role. It never displays an invalid action merely to rely on a backend rejection.

| Opportunity state | Permitted commercial actions in detail |
| --- | --- |
| `NUEVA` | `Cotizar`, `Marcar perdida`, WhatsApp, scoped edit |
| `COTIZADA` | `Editar cotización`, `Pasar a negociación`, `Marcar perdida`, WhatsApp, scoped edit |
| `NEGOCIACION` | `Editar cotización`, `Marcar ganada`, `Marcar perdida`, WhatsApp, scoped edit |
| `GANADA` | WhatsApp, scoped edit, Notes; no quote or status mutation |
| `PERDIDA` | `Reabrir` only when returned quote lines prove a retained positive quote, WhatsApp, scoped edit, Notes; no quote edit or ordinary transition |

`Pasar a negociación` and `Marcar ganada` invoke only their existing valid transition commands. They are clearly labelled primary actions when applicable, have brief pending feedback, and reconcile the returned authoritative Opportunity. `Marcar perdida` is destructive: it switches the same dialog layer to a focused loss-reason and confirmation step, rather than crowding read detail or stacking a child dialog. It offers only existing loss reasons, requires one before confirmation, and explains that the Opportunity leaves active Pipeline after successful backend completion.

`Reabrir` is explicit but not an ordinary forward transition. Its focused confirmation says the backend destination is `NEGOCIACION`; it requires no client-selected destination and sends the existing UUID command plus expected `PERDIDA` status. If the backend rejects changed state or quote eligibility, detail is refreshed and the error is shown. Success reconciles the dialog, Pipeline, and Lost projection; no action claims a lost Opportunity can reopen elsewhere.

## Quote flow

### One dialog layer and progressive steps

Selecting `Cotizar` from `NUEVA`, including CRM-019's `NUEVA -> COTIZADA` drop intent, or `Editar cotización` from the two editable open statuses replaces the main dialog body with quote flow. It remains one dialog layer with a visible `Volver al detalle` path; the detail dialog is not left behind as a second stacked modal. The same rule applies to scoped edit, loss confirmation, discard confirmation, and quote review.

Quote creation and update use a repeated sequence, not a dense editable table:

1. choose one Product from a text-first, highly scannable visual selection of the existing catalog;
2. enter its positive quantity in kilograms in a dedicated numeric step;
3. confirm/add that line;
4. show the added Product and quantity as a compact editable summary row;
5. repeat by adding another Product as needed; then
6. review the complete quote and deliberately confirm it.

The Product choice is an accessible radio/list selection with visible name and active availability, not an invented image, price, category, or SKU. Only active Products are eligible for a new line. In update mode, an already quoted inactive Product remains a clearly historical row and may retain/change its quantity as the current backend allows, but it cannot be newly added. Duplicate Products are prevented before review and still validated by the backend.

The quantity step labels kilograms, uses decimal numeric input semantics, and places focus directly in that input after selection. A line can be edited by returning to its choose/quantity steps or removed before final confirmation. The review lists Products, quantities, and supported total quoted kilograms only; it never invents money or pricing. `Confirmar cotización` is the only final mutation control and is visually unambiguous.

### Quote keyboard, cancellation, and reconciliation

- Enter selects a focused Product, then advances from valid quantity to `Agregar producto`. It never confirms the whole quote from a Product selection, quantity field, review row, or unrelated control.
- After adding a line, focus moves to the next meaningful control: add another Product or review. In review, Enter activates the clearly focused final confirmation only.
- Escape returns one quote step when a prior step exists; at the root it returns to detail when draft is clean. A dirty draft asks for deliberate discard, never silently closes or loses it. Focus returns to the invoking action/step.
- While submit is pending, final confirmation is disabled and announced; duplicate activation is impossible. The unfinished draft remains in memory until success or explicit confirmed discard.

For create, `POST /opportunities/{id}/quote` is the only operation that changes `NUEVA` to `COTIZADA`. Cancellation leaves it `NUEVA`; validation/conflict/failure leaves or reconciles it to backend-authoritative state and preserves local draft for safe correction/retry. For update, the existing replacement endpoint is used only for `COTIZADA` and `NEGOCIACION`; terminal Opportunities never receive the action.

On success, close quote subflow, refresh/reconcile detail, update relevant Pipeline/Lost projection from response or bounded reload, and provide restrained success feedback. An ambiguous network failure is never auto-retried because quote commands currently have no idempotency key: first refresh authoritative detail; keep the draft visible and allow a deliberate next action only after reconciliation.

## WhatsApp, feedback, and consistency

### WhatsApp handoff

WhatsApp is an obvious but restrained labelled action in detail, not a phone number on the Pipeline card. On explicit use, it follows CRM-019:

1. query the existing authenticated conversation list/search contract, using normalized Customer phone first when present and Customer/company identity otherwise;
2. prefer an exact normalized external-phone match, otherwise a returned matching Customer ID, preserving existing Inbox priority when multiple Customer matches remain; and
3. hand the verified local conversation ID to CRM-023's internal conversation-selection navigation contract so CRM WhatsApp opens that exact conversation.

It never uses `wa.me` or creates/sends a conversation. With no safely verified internal conversation, it displays `No existe una conversación interna vinculada` and no unsupported fallback action.

### Pending, stale, and conflict behavior

- The dialog renders immediately from Pipeline summary, then fetches detail. A skeleton occupies only unavailable data; Activity uses the returned detail history and Notes load independently when their context is opened. A 404/unavailable resource closes to a safe state with feedback and focus restoration; recoverable errors offer local retry.
- Every mutation disables only its affected action/scope, preserves unaffected detail, and reconciles authoritative response data. Background refreshes do not flash the full dialog, steal focus, or discard local dirty work.
- API validation errors stay adjacent to the relevant control. A 403 removes or stops the unavailable action with a useful explanation; a 404/409 state conflict refreshes detail and tells the user what changed. No client fabricates success.
- Current Note revision and reopen contracts carry explicit expected values and must surface conflicts without overwrite. Quote, Customer, and assignee writes require the unresolved conditional-update decision below before this spec can be approved.

## Accessibility, permissions, and performance

- CRM-018's WCAG 2.2 AA target applies: semantic dialog name/description, focus trap, visible focus, logical Tab/Shift+Tab order, accessible labels, contrast, non-colour status evidence, concise live regions, reasonable pointer targets, and `prefers-reduced-motion` support.
- Escape closes only the top safe state. Dialog close restores focus to Pipeline card/trigger; quote/edit/loss subflows return focus to their detail action. Dirty form, quote, or Note state always receives a discard choice. Enter is only a contextually safe primary action; Space/Enter activate ordinary controls.
- Both `SUPERVISOR` and `VENDEDOR` see the same Opportunities and permitted commercial actions. Existing server authorization remains decisive. Only `SUPERVISOR` receives assignee-edit controls; this adds no seller visibility restriction.
- Initial dialog uses already-loaded summary. It fetches one detail resource (including the current history contract) on activation and lazy-loads Notes on demand; it makes no N+1 prefetch across Pipeline cards. Product catalog and supervisor user list are fetched only when relevant flow opens and cached for that dialog session where safe.
- Shared CRM-018 primitives own dialog, segmented control, fields, feedback, confirmation, and tokens. Route composition and a typed Opportunity feature hook own dialog state, cancellation, drafts, and projection reconciliation; API modules own request contracts. No global state framework is introduced.

## Acceptance criteria

- AC-01: A Pipeline card opens one centered, large, bounded CRM-020 dialog—not a drawer—with a primary commercial zone and narrower Activity/Notes zone on available desktop space.
- AC-02: At narrow available widths or zoom, the dialog falls back to ordered single column with bounded internal scroll and no page-level horizontal overflow.
- AC-03: Detail opens read-first, shows useful Customer/company identity, status, source, effective Legendary state, current commercial data, relevant dates, and no internal IDs or invented commercial fields.
- AC-04: `Editar` is explicit and scoped to Customer-owned contact identity and, for supervisors, assignee; it preserves original values, has Save/Cancel and adjacent validation, and never makes full detail a permanent form.
- AC-05: Action group shows only current valid state/role actions, performs valid negotiation/win transitions, and uses focused confirmation for destructive loss.
- AC-06: WhatsApp finds and verifies existing internal conversation before handing local ID to CRM-023 selection; it never opens `wa.me` and exposes defined safe no-conversation state.
- AC-07: Activity uses supplied status history without fictional quote versions; Notes shows current pinned/newest order, author/time, loading/error/pagination states, and supports multiline add-note with explicit safe shortcut.
- AC-08: Quote creation/update uses one dialog layer and documented progressive Product → quantity → add-line → review flow, not a dense editable table.
- AC-09: Quote flow supports multiple Products, edits/removes lines, excludes new inactive/duplicate Products, retains historical inactive lines when allowed, and displays only supported kilograms/total kilograms.
- AC-10: Quote keyboard behavior has documented safe Enter/Escape/focus sequence, prevents duplicate final submit, and preserves dirty/failed draft until explicit discard or authoritative success.
- AC-11: CRM-019 `NUEVA -> COTIZADA` opens this quote flow; cancellation/failure leaves or reconciles Opportunity as `NUEVA`, while success updates detail and Pipeline only after authoritative quote operation succeeds.
- AC-12: Loss requests an existing required reason and removes Opportunity from active Pipeline only after success; eligible reopen explicitly returns only to backend-owned `NEGOCIACION` and reconciles Pipeline/Lost views.
- AC-13: Effective Legendary status is subtle, textual, and seller-relevant; automatic and manual implementation mechanics are not exposed in read detail.
- AC-14: Pending, stale data, validation, 403, 404, 409, concurrent update, and recoverable network states preserve safe local work, refresh/reconcile authoritative data, and never silently report/overwrite newer state.
- AC-15: Dialog focus, focus restoration, safe Escape/Enter, dirty-discard protection, semantic controls, contrast, live feedback, and reduced motion comply with CRM-018 and WCAG 2.2 AA where applicable.
- AC-16: Detail feels immediate from summary data; detail/Notes/catalog/user requests are on-demand, no Pipeline-card N+1 prefetch occurs, and no global state library is introduced.

## Open decisions

- **Conditional mutation concurrency is a blocker.** Existing Customer update, Opportunity assignee update, and quote-product replacement endpoints do not accept an expected `updated_at`/revision value. A client-side refresh cannot close the time-of-check/time-of-use gap, so it cannot guarantee the required non-overwrite of a newer Customer, assignee, or quote change. Before CRM-020 can be Approved, an explicit backend-authoritative conditional-update/conflict contract must be approved for these writes, or the user must explicitly relax that requirement.

## Follow-up / future specs

- CRM-021 — Dashboard & Metrics: may consume authoritative commercial data but does not add pricing or quote history here.
- CRM-023 — WhatsApp Inbox 2.0: owns internal selected-conversation navigation representation consumed by this detail dialog.
- CRM-024 — Customers / Products / Lost: owns specialized Customer and Lost screens; Customer manual Legendary administration remains Customer-owned.
- CRM-026 — Final Accessibility & UX Polish: verifies cross-module conformance without weakening criteria above.

## Implementation notes

Use existing React/Vite/TypeScript/Tailwind architecture. Replace current drawer and standalone dense quote form with CRM-018 shared dialog/confirmation/field primitives and feature-specific composed content. Keep route-level ownership of active Opportunity and Pipeline projection; keep drafts local to detail feature; keep typed API calls in existing API modules. Do not add a global store to bridge dialog and Pipeline—use explicit successful mutation/reload reconciliation instead.
