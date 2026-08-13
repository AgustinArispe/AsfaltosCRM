# CRM-018 — FAA CRM Frontend 2.0 Design System

Status: Approved
Owner: FAA CRM team
Last updated: 2026-08-13
Implementation commit: N/A

## Goal

Define the permanent visual, interaction, accessibility, responsive, and component
foundation for FAA CRM Frontend 2.0. The resulting CRM must support sustained sales
work with a premium, calm, fast, information-dense experience that is unmistakably FAA
without becoming an industrial-themed or marketing-site interface.

## Context

FAA CRM is an internal, desktop-first sales application. The Pipeline is its primary
working surface; Customers, Products, Lost Opportunities, Notifications, WhatsApp,
Broadcasts, and Metrics are operational modules around it. The existing React/Vite/
TypeScript/Tailwind application already has a small internal router, domain API
modules, feature components, an `AppShell`, and initial shared controls. CRM-010 also
establishes a desktop WhatsApp Inbox with cursor polling, stable selection, global
unread semantics, accessible controls, and smaller-laptop context adaptation.

This specification defines the Frontend 2.0 foundation only. It does not change the
business behavior, API ownership, backend route semantics, polling semantics, global
notification read semantics, permissions, or security rules defined by implemented
specs. It owns the smallest shared internal path and typed navigation representation
needed by Frontend 2.0; that client-side composition does not create a backend contract.
In
particular, frontend state must continue to render backend-authoritative business and
provider evidence rather than recreating it.

The production CSP from CRM-016 permits same-origin fonts only. A font CDN must not be
introduced as an implementation shortcut.

## Dependencies

- CRM-010 — WhatsApp Inbox Frontend
- CRM-015 — Quality and Reproducibility Hardening
- CRM-016 — Security Hardening

## Scope

- Semantic visual tokens and their Light, Dark, and System-theme mappings.
- IBM Plex Sans as the distinctive, all-day primary UI font, self-hosted with a safe
  loading and licensing-attribution contract.
- A consistent rounded shape, spacing, elevation, icon, focus, motion, and layering
  language.
- A permanent collapsible sidebar App Shell and responsive working-area rules.
- Shared, accessible primitives for controls, feedback, data presentation, overlays,
  filters, and charts.
- Global keyboard, modal, loading, error, empty, and perceived-performance behavior.
- React/Tailwind component, feature, hook, API-client, state, and route-composition
  boundaries for Frontend 2.0.
- The shared typed navigation model, canonical internal paths, and same-app return
  semantics consumed by CRM-019 through CRM-026.
- The visual and interaction contract required by the CRM-019 through CRM-026 specs.

## Non-goals

- Implementing any screen, component, route, token, font asset, or theme switcher.
- Changing backend contracts, business rules, permissions, notifications semantics,
  state machines, authentication, or polling/reconnect behavior.
- Adding backend endpoints, external services, a new frontend framework, or a global
  state library without measured need.
- A native mobile product, mobile-only navigation, or fixed-resolution-only layouts.
- Marketing-site styling, industrial decoration, a literal Apple UI copy, or broad
  yellow surfaces.
- Replacing the existing manual router, API modules, or feature boundaries merely to
  adopt the design system; no routing dependency is introduced for this contract.

## Design principles

- **Simple by default; detail on demand.** Make the current commercial decision and
  next safe action clear before exposing secondary fields, history, or configuration.
- **Dense but quiet.** Capacity comes from hierarchy, grouping, tabular numerals,
  alignment, and progressive disclosure—not tiny type, visual noise, or color bands.
- **Premium by restraint.** Typography, measured spacing, purposeful elevation,
  responsive feedback, and precise states create quality; decorative effects do not.
- **Desktop-first, space-aware.** Adapt to available CSS pixels, content length, and
  browser zoom instead of assuming a named screen resolution.
- **Keyboard first.** Every operational action has a visible, semantic, keyboard path.
- **State is multimodal.** Business state is communicated with wording, icon/shape,
  and where useful color; color is never its sole signal.
- **One visual language.** Features may specialize a component only when a documented
  operational responsibility requires it; they must not fork its base primitive.

## Visual foundation

### Semantic tokens and themes

Components consume semantic tokens, never raw palette values or feature-specific
component colors. Tailwind utilities and CSS custom properties are both derived from
the same named semantic source so a theme changes mappings rather than component code.
The implementation may add scale tokens behind the semantic layer, but feature code
must not consume those scales directly.

Each Light and Dark mapping defines and independently validates these token families:

| Family | Required semantic tokens and use |
| --- | --- |
| Backgrounds | `canvas`, `subtle`, `surface`, `surface-raised`, `surface-overlay`, and scrim; hierarchy comes from tone and restrained elevation. |
| Text | `text-primary`, `text-secondary`, `text-tertiary`, `text-inverse`, `text-link`, and `text-disabled`; body text must remain readable without depending on placeholder color. |
| Borders | `border-subtle`, `border-default`, `border-strong`, and `border-interactive`; borders clarify structure without making every region boxed. |
| FAA accent | `accent-subtle`, `accent-surface`, `accent-solid`, `on-accent`, and `accent-strong`; warm Caterpillar-like yellow is recognizable identity, focus, and selective important-action emphasis, never a large app surface. |
| Status | `success`, `warning`, `destructive`, and their subtle/surface/solid/on-color pairs. Green, amber, and red are restrained and always paired with text or an icon. |
| Interaction | `focus-ring`, `focus-ring-offset`, `hover`, `pressed`, `selected`, `disabled`, and `loading`; disabled communicates unavailable rather than simply dimming an otherwise ambiguous control. |
| Charts | named categorical series, sequential and divergent ramps, gridline, axis, tooltip, and reference-line tokens. Every series mapping has a non-color identifier in accessible presentation. |

Light uses sophisticated warm-neutral white, charcoal, and gray surfaces; Dark uses
purpose-built charcoal and near-black surfaces with lifted, desaturated semantic
states. Dark is not a simple color inversion. Token pairs must meet WCAG 2.2 AA for
their intended text/icon use in both themes, including borders, focus, disabled,
selected, and modal states. Yellow must use a sufficiently dark foreground or be
reserved for non-text emphasis; it is never assumed to support white text.

### Typography

**IBM Plex Sans** is the FAA CRM primary UI family. It is expressive without being
fashionable-for-fashion's-sake, has strong small-text and Spanish readability, open
counters, tabular figures, and calm numeric rendering for kilograms, counts, dates,
and metrics. Its character supports FAA's premium commercial workspace without
suggesting an industrial aesthetic.

- Use one UI family with optical hierarchy through size, weight, line-height, and
  contrast; do not add a display-font pairing.
- The initial self-hosted payload contains only WOFF2 files for weights **400**
  (body), **500** (labels/controls), and **600** (headings and emphasized data). Weight
  700 is intentionally excluded: 600 supplies the required hierarchy, and a later
  addition requires measured visual need and payload review rather than a speculative
  download.
- Define named text roles for display, page title, section title, body, body-small,
  label, metadata, and numeric data. Body text stays at a readable default and body
  line-height remains comfortable in dense views; text below 12 CSS pixels is not
  permitted for essential information.
- Use `font-variant-numeric: tabular-nums` for quantities, dates, counters, timers,
  and tables where alignment improves scanning. Preserve locale-aware existing
  formatters.
- Provide a metric-compatible system fallback stack (`ui-sans-serif`, system UI,
  `-apple-system`, BlinkMacSystemFont, `Segoe UI`, sans-serif). Avoid synthetic
  bold/italic and reserve space to reduce layout shift.
- Serve the selected weights from the frontend's same origin only, with no Google
  Fonts, CDN, analytics, or other runtime third party. Use `font-display: swap` (or
  `optional` only if its tested fallback metric behavior is acceptable), preload at
  most the critical 400 face, and apply the root `color-scheme`/theme before first
  meaningful paint. Font loading must neither create invisible text nor contribute to
  a theme flash.
- Obtain the unmodified font files from the reviewed upstream IBM Plex release. IBM
  Plex Sans is licensed under the SIL Open Font License 1.1 (OFL-1.1), with `Plex` a
  Reserved Font Name. When the files are added, the repository must include the full
  unmodified upstream license and copyright notice next to the redistributed font
  assets (for example `frontend/public/fonts/IBM-Plex-Sans-OFL-1.1.txt`) and a concise
  provenance notice recording the upstream release/version, source URL, selected
  files/weights, and any subsetting tool. Any modified or subsetted font remains under
  OFL-1.1, must retain the required notice, and must not use the Reserved Font Name
  unless IBM grants written permission. The font files are never sold separately.

### Shape, spacing, elevation, and icons

The product uses smooth, Apple-inspired rounded geometry, not harsh 90-degree boxes
and not an indiscriminate pill treatment. Define one restrained radius scale:

| Role | Shape rule |
| --- | --- |
| Pills / compact badges | fully rounded only when representing a compact status, count, tag, or filter chip. |
| Buttons / inputs / selects | small smooth radius. They remain controls, not pills, unless a compact segmented pattern requires it. |
| Cards / panels | medium radius. Use sparingly to group a coherent responsibility. |
| Modals / floating surfaces | larger, calm radius with a deliberate scrim and consistent elevation. |

Use a shared 4/8-based spacing scale, a small elevation scale, and named z-index
layers (base, sticky, popover, modal, toast). Shadows are low-contrast and functional:
raised or floating surfaces only. Icons are from one accessible SVG icon system with
consistent stroke, sizes, and alignment; no emoji or mixed icon families are structural
UI. Icon-only controls require an accessible name and a practical 44-by-44 CSS-pixel
hit target.

Use SegmentedControl for small, mutually exclusive, closely related views or compact
time/group switches. It is not a replacement for navigation, tabs with deep content,
or arbitrary filter collections.

## App Shell and navigation

The primary navigation is a permanent left sidebar; a top navbar is not the primary
navigation pattern.

- Expanded sidebar contains the approved FAA identity/logo, Pipeline, Dashboard,
  Notifications, WhatsApp, Customers, Products, Lost, and applicable WhatsApp
  Sends/Broadcasts. The account/user area remains anchored at the bottom. Actual route
  availability and role restrictions continue to follow their owning specs and backend
  permissions; an unavailable destination is explained rather than silently invented.
- The expanded state pairs each navigation icon with its text label and provides a
  clear active indicator that uses position/shape/weight as well as color. Hover,
  pressed, keyboard-focus, disabled/unavailable, and badge states use interaction
  tokens consistently.
- The collapsed state remains visible, preserves route orientation through the active
  marker, uses icons only with tooltips and accessible labels, and retains a usable
  sidebar toggle. It maximizes the work area without concealing core navigation.
- NotificationBadge displays an attention count/state only when unseen notifications
  exist. Opening or reading follows existing backend global `read_at` semantics;
  resolution and historical visibility remain backend-authoritative and accessible.
- Main content has a skip link and semantic `main` landmark. Route changes move focus
  to the page/main heading without unexpectedly changing user selection, scroll, or
  in-progress work.

### Shared typed internal navigation

The existing manual router remains the Frontend 2.0 router. It gains one typed,
centralized route parser/serializer and navigation helper; feature modules must not
invent query-string, local-state, or ad-hoc pathname conventions for entity handoffs.
The helper represents only validated positive internal IDs and the following
discriminated route intents:

| Route intent | Canonical path | Owning workspace/detail surface |
| --- | --- | --- |
| Active Opportunity | `/pipeline/opportunities/:id` | Pipeline with CRM-020 centered detail. |
| Lost Opportunity | `/lost/opportunities/:id` | Lost with CRM-020 centered detail. |
| Customer | `/customers/:id` | Customers workspace/detail. |
| Exact WhatsApp conversation | `/whatsapp/conversations/:id` | WhatsApp Inbox with that conversation selected. |
| Broadcast execution | `/whatsapp-sends/:id` | Envíos WhatsApp execution detail. |

The implementation uses a TypeScript discriminated union equivalent to
`workspace`, `opportunity`, `customer`, `conversation`, and `broadcast`; IDs are
numeric internal identifiers, never phone numbers, provider identifiers, or external
URLs. Workspace roots remain `/pipeline`, `/lost`, `/customers`, `/whatsapp`, and
`/whatsapp-sends`.

Normal browser history remains the default return mechanism. When an explicit
cross-workspace handoff benefits from a fallback, the navigation helper may place a
typed, same-app origin/fallback route in `history.state`. It contains only another
validated route intent and may be used for close/back focus restoration. It never
accepts, stores, or follows arbitrary return URLs, external locations, phone numbers,
filter blobs, or temporary feature state. A direct deep link has no origin and falls
back to its owning workspace.

The backend entity remains authoritative after navigation. If a loaded Opportunity is
currently `PERDIDA`, the client replaces an active-Opportunity location with its Lost
canonical location; a Lost location resolving to a non-lost entity returns to its safe
owning context. An unavailable entity preserves the source workspace and gives scoped
feedback. Route-level focus follows the existing heading/main rule, while a detail
dialog restores focus to its typed origin trigger when that trigger is still available.

## Responsive and overflow behavior

Desktop/laptop is the supported primary environment. The minimum supported working
area is a 1024 CSS-pixel-wide viewport at normal browser UI, and all supported layouts
must remain usable at common browser zoom through 200% where applicable. This is a
space contract, not a claim that 1024 is the only breakpoint.

- The sidebar collapses before content is squeezed below usable density. At narrower
  desktop widths it remains accessible as a compact rail; feature content determines
  whether a secondary panel becomes an explicit overlay or returns to a one-primary-
  panel view.
- Grids use `minmax`, container queries where justified, or equivalent available-space
  rules. They collapse from multi-column to fewer columns based on content width, not
  only device labels.
- Main-page width, gutters, and card grids adapt fluidly. Long text wraps at sensible
  boundaries; identifiers and numeric values use deliberate truncation, wrapping, or
  tooltip/expand rules rather than causing page overflow.
- Dialogs use viewport-aware maximum width and height, safe gutters, and internal
  scroll for their body while headers/actions remain reachable. Nested scroll regions
  are limited to bounded workspaces such as message history, tables, and dialog bodies.
- Tables retain semantic table markup. When all essential columns cannot fit, the
  owning feature chooses one documented fallback: priority columns with a detail
  action, a responsive list/card representation, or an explicitly labelled horizontal
  table region. No page-level horizontal overflow is allowed.
- Narrow viewport behavior preserves access to primary work and navigation but does
  not attempt to become a mobile-native CRM. No supported layout disables browser zoom.

## Interaction, keyboard, and overlays

- `Escape` closes only the topmost safe, dismissible dialog/popover/menu. It must not
  discard unsaved edits or cancel an in-flight non-idempotent mutation without an
  explicit confirmation path.
- `Enter` invokes the contextually safe primary action only in a form/control where
  that action is clear. It must not submit multiline text, fire while IME composition
  is active, or confirm destructive actions. Feature-level exceptions such as the
  existing WhatsApp composer (`Enter` send, `Shift+Enter` newline) must stay explicit.
- `Tab` and `Shift+Tab` follow visual/logical order. Modal dialogs trap focus, take
  focus on open, expose an accessible title/description, and return focus to the
  original trigger on close. Popovers and menus close/restore focus predictably.
- Native semantic elements are preferred. Buttons and links activate with their
  native Space/Enter behavior; custom composite widgets define the relevant ARIA
  pattern and keyboard model rather than simulating a button with a `div`.
- Destructive actions use a distinct destructive treatment, explain the outcome, and
  require a deliberate ConfirmationDialog. A loading state prevents duplicate submits
  without removing the recovery/error explanation.

### Modal philosophy

Primary entity detail uses centered, generous dialogs rather than a permanent drawer
unless its owning feature spec demonstrates that a drawer better preserves the work
context. Large detail dialogs support clear hierarchy, optional two zones (primary
content and contextual history/activity), and a single-column fallback when space is
limited. They are read-first with an explicit Edit action; permanent editable fields
are not the default.

Existing implemented behavior remains unchanged until an approved implementation
specification updates it. CRM-010's smaller-laptop WhatsApp context drawer is a
documented responsive workspace adaptation, not a precedent for entity-detail drawers.

## Motion and perceived speed

Motion is restrained, fast, functional, and interruptible. Shared duration/easing
tokens keep micro-interactions around 150–220 ms; overlay entry may use up to 240 ms
and exit is faster. Animate opacity and transforms, not layout properties. Interaction
must remain available while an animation runs.

- Use subtle motion for modal entry/exit, sidebar collapse, hover/press feedback,
  segmented selection, safe state changes, and skeleton/content replacement.
- Dashboard and metrics may add progressive chart reveal, number transition, and
  filter transition when they clarify a changed value. Chart data is readable before
  or without the animation.
- `prefers-reduced-motion: reduce` removes spatial/continuous animation, keeps state
  changes immediate or minimally faded, and never hides information or blocks work.
- Loading appears within 300 ms when an operation will take longer. Use skeletons that
  reserve layout for initial content and short crossfades for replacement; avoid
  full-screen spinners for routine refreshes.

## Component foundation

The shared design-system location is `frontend/src/shared/` (or a deliberately
equivalent shared UI directory established during implementation). It owns generic
tokens, primitives, accessibility helpers, and component contracts; it does not own
feature data fetching or commercial behavior. Feature modules compose these primitives
and may own domain-specific views such as `PipelineColumn`, conversation rows, and
metric cards.

Required reusable primitives/components and their responsibilities are:

| Component | Required variants or semantics |
| --- | --- |
| Button / IconButton | primary, secondary, quiet/ghost, destructive; size, loading, disabled, accessible icon-only naming, and exactly one clear primary action per local surface. |
| Input / Search / Select / Combobox | visible label, description/error linkage, validation, disabled/read-only distinction, autocomplete semantics, and asynchronous results/loading where applicable. |
| Checkbox / Radio | native semantics; Checkbox for independent values, Radio only for a necessary exclusive choice. |
| Pill / Badge / NotificationBadge | status/count/filter semantics; icon/text/shape accompany color; count overflow and accessible label rules. |
| Tooltip / Popover / DropdownMenu | nonessential tooltip content; correctly labelled, focus-managed interactive popovers/menus with escape and outside-dismiss rules. |
| SegmentedControl | compact exclusive switching with selected state and keyboard semantics. |
| Modal / Dialog / ConfirmationDialog | native dialog semantics or equivalent, focus management, compact/large sizing, non-destructive and destructive actions, and safe dismissal rules. |
| Filter controls | compact search, sort, common filters, More filters, active count/state, and clear/reset behavior. |
| Card / Surface | semantic surface/elevation variants; no gratuitous card nesting. |
| Skeleton / EmptyState / ErrorState | scoped initial loading, meaningful empty/no-result guidance, retained-content refresh, error cause/retry, and permission/blocked-action presentation. |
| Toast / inline feedback | mutation acknowledgement/error that does not steal focus; polite live announcement and actionable recovery where appropriate. |
| Avatar | user/customer identity fallback, image alternative text rules, and non-color presence/status treatment when used. |
| Chart surface/container | title, period/filter context, loading/error/empty state, legend, keyboard-accessible exact values, textual summary/table alternative, and token-driven series. |
| Icon system | one SVG family, named exports, consistent sizes/stroke, `aria-hidden` for decorative use, and accessible name supplied by the enclosing control when meaningful. |

Filters are visually secondary to the content they refine: search and common filters
are compact and immediately scannable; sort is clear; secondary options live behind
“More filters”; active selections are visible and resettable. A filter toolbar must
not dominate a working screen or replace a simple default view.

## Loading, errors, empty data, and feedback

- Initial load: use scoped skeletons or a meaningful page-level loading state that
  reflects the expected layout. Preserve dimensions to avoid layout shift.
- Background refresh/polling: retain the last good data, show a subtle refreshing,
  stale, reconnecting, or retry state as needed, and never replace usable content with
  a full-screen spinner. Existing CRM-010 polling and selection-stability rules remain
  authoritative.
- Mutation: show immediate pending feedback on the triggering control; use optimistic
  display only where the operation is safely reversible and reconcile with the
  server-authoritative resource. Failure preserves recoverable inputs where safe.
- Empty dataset, no search results, permission/blocked action, unavailable entity, and
  API error are distinct states with precise explanatory copy and an appropriate next
  action. Do not invent business categories or state transitions to fill an empty view.
- Status/live feedback uses the least disruptive correct live region. Initial content
  does not announce a flood of rows/messages; errors and completed mutations receive
  timely, understandable announcements.

## Accessibility

Frontend 2.0 targets WCAG 2.2 AA where applicable.

- Use semantic HTML, landmark/heading hierarchy, labelled form controls, descriptive
  links, accessible icon names, correct dialog semantics, and ARIA only when native
  semantics cannot express the behavior.
- Maintain contrast in both themes, visible focus indicators with sufficient offset,
  logical reading/focus order, screen-reader meaningful labels, and practical
  44-by-44 CSS-pixel targets for interactive controls where density permits.
- Never convey business status only through color. Add clear text, an icon, label,
  shape, or position; charts also provide a legend and textual/table alternative.
- Validation errors are adjacent to fields, state the cause and recovery, and move
  focus to the first invalid field after a failed submission when appropriate.
- Preserve browser zoom, support text enlargement without clipping essential content,
  provide keyboard alternatives for drag-and-drop, and respect reduced motion.
- Toasts and background updates do not steal focus. Use intentional polite/assertive
  live regions so updates are announced without overwhelming users.

## Theme persistence

The theme choices are Light, Dark, and System. System follows the current OS preference;
an explicit Light or Dark choice overrides System until changed by the user.

Use the simplest client-side preference mechanism unless an existing backend user-
preference contract is already available and demonstrably better. The selected mode is
applied before first meaningful paint where practical (including the root background
and color scheme) to avoid a visible flash. The client preference is presentation-only:
it does not create a new backend contract, role behavior, or cross-device guarantee.

## Performance and frontend architecture

Frontend 2.0 preserves the fast backend experience.

- Avoid blocking route/feature transitions and unnecessary rerenders. Keep query,
  polling, cursor reconciliation, browser-event handling, and mutation ownership in
  feature hooks/services rather than visual components.
- Preserve prior data during refetch/polling; abort obsolete work and debounce only
  high-frequency input such as search. Do not add a global cache/state framework just
  to express local or route state.
- Route-level code splitting and lazy loading are appropriate for heavy, infrequently
  visited areas when measured bundle or interaction evidence supports it. Charts and
  other heavy visualizations must not degrade Pipeline, Inbox, or primary input
  responsiveness; virtualize long lists only when real list volume warrants it.
- Keep animation GPU-friendly, reserve asynchronous layout space, avoid unnecessary
  image/font work, and ensure heavy chart calculations do not run during primary
  interactions.

Architecture remains React, Vite, TypeScript, and Tailwind. The intended one-way
composition is:

1. route-level composition uses the shared typed navigation helper to choose the
   authenticated page/workspace, canonical entity selection, and URL-level state;
2. feature hooks/services own typed API calls, feature-local request/projection state,
   polling, mutations, and error translation;
3. feature views compose shared primitives and receive typed data/callbacks, with no
   direct API or business-rule calculation;
4. `frontend/src/api/` remains the typed owner of backend HTTP contracts and session
   plumbing; it does not own visual state;
5. `frontend/src/shared/` owns generic visual/accessibility behavior only.

State stays as local component, feature-hook, route, or existing auth-context state
according to the smallest owner that needs it. A global state library requires measured
cross-route coordination or performance evidence and a separately approved decision.

## Data model, contracts, state transitions, and security

No data model, persistence, API, route, authentication, authorization, provider,
business-state, or backend change is authorized. Existing security constraints remain:
same-origin API access, session-scoped bearer handling, CSP-compatible same-origin
assets, no untrusted HTML rendering, no external-provider calls from the frontend, and
no secrets/provider URLs/storage keys in visual components or browser state.

## Edge cases

- A collapsed sidebar, 200% browser zoom, long Spanish labels, unavailable routes,
  and dense data cannot produce page-level horizontal overflow or obscure primary
  content/actions.
- Theme changes while an overlay, chart, loading state, or selected navigation item is
  visible preserve semantic contrast and interaction state without a full reload.
- Escape acts only on the highest safe dismissible layer; an unsaved edit or destructive
  confirmation cannot be lost by an accidental keypress or generic Enter handling.
- Network refresh/reconnect cannot remove last-good data, steal focus, or override a
  stable active Inbox selection defined by CRM-010.
- Empty/no-result/blocked/error states do not look identical and do not expose backend
  implementation details, provider data, or secrets.

## Acceptance criteria

- AC-01: A documented semantic token contract covers backgrounds, surfaces, text,
  borders, FAA accent, success, warning, destructive, focus, muted/disabled, and charts;
  no feature component requires raw component colors.
- AC-02: Light, Dark, and System mappings have defined persistence/override behavior,
  independently meet intended WCAG 2.2 AA contrast, and avoid startup theme flash where
  practical.
- AC-03: IBM Plex Sans is self-hosted in WOFF2 weights 400, 500, and 600 only; the
  typography contract defines readable Spanish UI roles, tabular numeric treatment,
  system fallbacks, non-blocking loading, no runtime third party, and OFL-1.1
  attribution/redistribution requirements.
- AC-04: Shared radius, spacing, elevation, icon, and segmentation rules produce
  consistently rounded—but not universally pill-shaped—controls and surfaces.
- AC-05: The App Shell provides an accessible, permanent expanded/collapsed sidebar,
  active/hover/focus/badge states, bottom account area, and primary working area without
  a top navbar as primary navigation.
- AC-06: Supported desktop/laptop layouts adapt to CSS viewport/zoom/content space,
  have no page-level horizontal overflow, and define table, panel, modal, scroll, and
  narrow-viewport fallbacks.
- AC-07: The global keyboard model defines safe Escape/Enter behavior, logical tab
  order, visible focus, native activation, dialog focus trap, and trigger focus return.
- AC-08: Motion tokens keep feedback functional, fast, interruptible, and GPU-friendly;
  reduced-motion users retain immediate readable state changes.
- AC-09: The listed shared primitives/components have documented variants and
  accessibility semantics, and feature modules do not create duplicate one-off base
  controls for equivalent responsibilities.
- AC-10: Entity detail follows the read-first centered-dialog philosophy, while any
  drawer use is explicitly justified by its feature/workspace context.
- AC-11: Filters remain compact and secondary, support search/sort/common and more
  filters, expose active selections, and provide clear/reset behavior.
- AC-12: Initial, refresh, mutation, offline/reconnect, API-error, empty, no-result,
  and blocked states use consistent scoped feedback without routine full-screen spinners
  or loss of last-good content.
- AC-13: The system targets WCAG 2.2 AA through semantic HTML, keyboard operation,
  accessible names, contrast, non-color status evidence, live regions, correct dialogs,
  useful errors, zoom/text resilience, and reduced motion.
- AC-14: Frontend performance guidance preserves data during refresh, avoids unnecessary
  rerenders/blocking transitions, defers heavy features only when beneficial, and keeps
  charts from degrading core CRM work without adding premature global state.
- AC-15: React/Vite/TypeScript/Tailwind architecture keeps shared primitives, feature
  views, hooks/services, API modules, route composition, and state ownership within the
  documented boundaries.
- AC-16: CRM-019 through CRM-026 explicitly depend on and may specialize this contract,
  but may not silently contradict its token, accessibility, interaction, responsive,
  theme, or architecture rules.
- AC-17: One manual-router typed navigation helper serializes/parses the documented
  canonical Pipeline, Lost, Customer, WhatsApp, and Broadcast paths; it validates
  internal IDs, supports only typed same-app `history.state` origin/fallback, rejects
  arbitrary return URLs, and gives direct deep links their owning-workspace fallback.

## Open decisions

None

## Follow-up / future specs

- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-021 — Dashboard & Metrics
- CRM-022 — Notifications
- CRM-023 — WhatsApp Inbox 2.0
- CRM-024 — Customers / Products / Lost
- CRM-025 — WhatsApp Broadcast UI
- CRM-026 — Final Accessibility & UX Polish

Each future specification is a mandatory consumer of CRM-018. It may add feature-
specific detail only when it preserves this foundation; an intentional exception must
be explicit, justified, and approved rather than silently diverging.

## Implementation notes

Implementation follows only after this Draft is approved. Start by inventorying and
migrating the existing `styles.css`, `AppShell`, `shared` controls, and feature-level
visual duplication incrementally; preserve all implemented business/API behaviors and
existing test coverage while doing so. Add the selected self-hosted IBM Plex Sans
assets, OFL-1.1 text, and provenance notice together in the implementation change; do
not make a global state, router, external font, component-library, or dependency
decision as an incidental redesign step.
