# CRM-040 — Pipeline and Opportunity Workspace Hierarchy

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-08
Implementation commit: `a0c6306`

## Goal

Strengthen the Pipeline and centered Opportunity Detail as one coherent commercial
workspace: cards must remain dense but clearly separated and have unambiguous
interaction states; detail must give customer identity, commercial status, actions,
original consultation, and quote the hierarchy and readable scale required for daily
sales work without returning to the old oversized generic modal.

## Context

CRM-037 successfully removed duplicate headings, consolidated Customer and Opportunity
facts, reduced empty space, and created one bounded centered detail with a secondary
Activity/Notes region. CRM-038 then kept the Pipeline mounted and synchronized while
route-driven detail is open, and CRM-039 added the active `GANADA` retention projection
and historical Ganadas detail surface. Those behaviors remain authoritative.

Current implementation and deterministic visual-baseline inspection show two related
hierarchy problems. Pipeline cards use a white raised surface at rest, but hover fills
their button with `--surface-hover`, visually approaching the column's
`--surface-secondary`; focus-visible reuses that same fill; selected is mostly a
two-pixel border; dragging reduces the source to 40% opacity and renders a generic
overlay; and pending only disables the button. In centered detail, CRM-037's `64rem`
cap and compact spacing now undershoot the commercial content: 24px status and
Legendary pills, a broad flat summary, 14px section headings, and a 15–17rem Contexto
sidebar make quote and original consultation feel secondary despite their commercial
importance.

This Draft is a frontend visual/information-hierarchy change only. It does not
authorize application-code implementation until explicitly approved.

## Dependencies

- CRM-018 — Frontend Design System
- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-036 — Web Consultation in Opportunity Detail
- CRM-037 — Compact Opportunity Detail Modal
- CRM-038 — Frontend Interaction and Data Synchronization
- CRM-039 — Won Opportunity History and Active Pipeline Retention

## Current-state audit

### Pipeline card DOM, semantics, and density

- Each card is an `article` containing one full-card native `button`. The article owns
  `aria-busy`, `data-opportunity-id`, surface/radius, selection, and drag-source
  opacity. The button owns the accessible name, `aria-current`, disabled state,
  click, drag ref, cursor, focus, padding, and all visible content.
- Visible content is one 16px/650 single-line primary identity, an optional 13px
  single-line contact, then a 13px source plus the shared 24px Legendary pill. Optional
  stage age is a separate 12px line. Product/quote context, responsible user, status,
  and Opportunity reference are absent from cards; status is inferred solely from the
  containing column.
- Card padding is approximately 10–11px and inter-card gap 8px. The resulting density
  is appropriate for the four-column board, but information below identity is small
  and the single meta row gives source and Legendary similar weight.
- Columns use a `15rem` minimum, four-column grid with `63rem` minimum total width,
  local horizontal board scroll, and local vertical card-list scroll. At narrow
  viewports the Kanban intentionally remains horizontally navigable; the document
  itself must not overflow.
- The full card is the detail click target. Draggable non-terminal cards use grab/
  grabbing cursors and a six-pixel pointer activation threshold; `GANADA` uses pointer
  and cannot drag. Keyboard drag uses Space, arrows, Enter/Space/Tab, and Escape.
- The board and card are semantically navigable, but the card accessible name is long
  and does not identify current status except indirectly through the section. Busy is
  exposed by `aria-busy` on the article and disabled on the button, with no persistent
  visible progress label or indicator.

### Pipeline visual-state collapse

| Before | After | Why |
| --- | --- | --- |
| Default: raised surface with only an inset 1px subtle border | Raised neutral surface, visible 1px border and subtle resting shadow | The card remains distinct from its gray column before interaction |
| Hover: button fill becomes `--surface-hover`, near the column background | Preserve/clarify card surface; strengthen border and subtle shadow/elevation | Hover must increase tactile separation, not wash the card into the column |
| Focus-visible: same hover fill plus inset 2px ring | Strong external 2px focus ring with offset, plus selected-capable border | Keyboard focus must be stronger than hover and must not consume card content area |
| Selected/opened: selection fill and inset 2px navy border | Persistent selection surface/marker and strong border, independent of hover/focus | The route-selected card remains identifiable while its detail is open |
| Dragging source: selected/default card at 40% opacity | Muted source placeholder plus compact, card-faithful elevated drag overlay | Drag state stays legible and spatially stable without looking disabled or disappearing |
| Busy: disabled button with browser/default disabled behavior | Content remains mounted; visible compact progress cue, restrained busy surface, `aria-busy` | Pending work becomes trustworthy without flicker or card replacement |
| Terminal `GANADA`: pointer only, otherwise visually like draggable cards | Same core card hierarchy with explicit labelled stage context and non-drag affordance | Terminal/read-only state is understandable without creating a separate application |

Default, hover, focus, selected, dragging, and busy currently overlap because they
reuse the same surface/ring vocabulary or depend almost entirely on opacity. Disabled
is applicable only while a mutation is pending; a terminal card remains an interactive
detail trigger and must not be styled as disabled.

### Opportunity Detail implementation audit

- The native shared `dialog` is capped at `64rem` and `calc(100dvh - 2rem)`. One inner
  wrapper owns the only vertical `overflow-y-auto`; the shell uses the overlay radius,
  border, surface, scrim, and overlay shadow. This is the correct single-scroll model.
- The shared modal header contains an Opportunity-specific rendered header plus the
  shared 44px close button. The custom header places return affordance and
  `Oportunidad #<id>` at 12px, company/Customer at 20px, optional contact at 14px,
  optional Legendary, and status at the far edge.
- Both status and Legendary use the shared `Badge`: fixed 24px height, 13px text,
  pill radius, and compact padding. Their sizes are acceptable for dense list metadata
  but too small for primary workspace status. Legendary is attached inline to the
  title and reads as a tiny floating pill rather than a deliberate secondary signal.
- Centered layout renders a 1–2-column neutral summary with Origin, Responsible,
  Created, Time in stage, Email, Phone, and Province. Labels are 12px and values 14px.
  All facts share the same cell treatment, so Relationship, Time, and Contact are not
  visually grouped.
- Actions immediately follow the summary and preserve the lifecycle-dependent order,
  but all use compact 36px controls. The primary action exists, yet the rail appears
  appended under metadata instead of associated with the commercial identity and
  current decision.
- The body uses `minmax(0, 1fr)` plus `clamp(15rem, 27%, 17rem)` above 52rem. The main
  region is one white surface where Consultation and Quote are separated by a divider;
  both headings are 14px. Consultation text is safe multiline 14px/24px. Quote is a
  14px table with 12px header; total is visually stronger but the section as a whole
  does not read as central commercial evidence.
- Contexto is a gray secondary surface with 14px heading, Activity/Notes segmented
  control, 12–14px chronology, lazy Notes loading, composer, errors, and save state.
  The sidebar concept is appropriate at wider widths, but 15–17rem becomes cramped for
  long notes while taking width from already compact commercial content.
- Below 52rem, Consultation and Quote precede Contexto in one column; below 40rem the
  summary stacks and the header stacks status beneath identity. The semantic order is
  sound. The quote table alone may scroll horizontally inside its own boundary.
- CRM-037 improved duplicate-header removal, return-to-origin navigation, content-sized
  height, one dialog scroll, truthful missing states, and main/context separation. It
  remains weak in readable commercial scale, explicit grouping, action association,
  status/Legendary prominence, consultation/quote emphasis, and width balance.
- The same centered component is opened from Pipeline, Pérdidas, and Ganadas. Surface
  differences are limited to the return label/route and existing lifecycle actions.
  `GANADA` remains terminal/read-only for lifecycle and quote mutations; `PERDIDA` may
  expose only the already-authorized reopen behavior.
- The shared Modal uses native `showModal`, labelled title IDs, Escape cancellation,
  backdrop close, a custom Tab wrap, initial-focus hook, and focus restoration. It has
  no typed 68–72rem Opportunity size and its scrolling wrapper/header cannot currently
  express an Opportunity-specific sticky identity/action zone without a small opt-in
  composition capability.

## Scope

### Pipeline card hierarchy

- Preserve one semantic `article` and one full-card native detail button. Keep the drag
  ref, six-pixel activation constraint, keyboard sensor, accessible drag instructions,
  `aria-current`, and `aria-busy` behavior, refining labels only where clarity requires.
- Preserve existing card density and four-column `PipelineColumn` configuration. A
  normal card should generally remain within roughly 88–112px depending on optional
  contact and stage age; do not add every available Opportunity field.
- Establish this scan order:
  1. company when present, otherwise Customer name, as primary identity;
  2. Customer/contact name when distinct, plus a clear textual commercial-stage cue;
  3. responsible or concise quote context only when already available and useful;
  4. source and optional stage age as tertiary metadata;
  5. Legendary as an intentional but secondary customer signal.
- The containing column still provides primary stage grouping. Any card-level status
  cue must be compact text/semantic context, not another competing pill on every card.
- Use 15–16px identity, 13–14px commercial/supporting content, and 12–13px tertiary
  content. Avoid using 12px for all metadata and avoid enlarging every line.
- Preserve truncation for dense single-line identity where necessary, with the full
  visible value available through the existing title/accessibility context. Critical
  detail content must wrap in the workspace rather than inherit card truncation.

### Explicit Pipeline card states

- **Default:** opaque raised card surface, visible border against the column, and the
  subtle elevation token. It must not depend on hover for separation.
- **Hover:** on fine pointers only, keep an opaque raised/primary surface while moving
  to an interactive border and the next restrained shadow level. A transform is
  optional and, if used, is limited to `translateY(-1px)`; no scaling or large lift.
  Pointer/grab cursor remains appropriate to the current interaction.
- **Focus-visible:** render a WCAG-visible 2px external ring plus at least 2px offset,
  not only an inset shadow. It must be visually stronger than hover, remain unclipped,
  and coexist with selected state. Keyboard-initiated drag must not add decorative
  motion.
- **Selected/opened:** keep a persistent selection surface and strong navy/selection
  border or marker after pointer exit. It remains recognizable under focus and when
  the modal scrim lowers background contrast. `aria-current="true"` remains.
- **Dragging:** retain a stable, visibly muted source footprint and use a compact drag
  overlay with the card's radius, border, identity hierarchy, and floating shadow.
  Elevation may be stronger than hover but remains bounded; no bounce, rotation, large
  scale, or disappearance.
- **Pending/busy:** never replace or remove the card. Keep identity and current
  optimistic stage visible; add a compact spinner/progress cue and textual accessible
  pending description, apply `aria-busy`, and disable conflicting click/drag. Avoid an
  opacity treatment that can be confused with dragging/disabled and avoid layout
  shift when the request settles.
- **Disabled/non-interactive:** there is no persistent disabled card state. A terminal
  `GANADA` card remains an enabled detail button but is not draggable. Temporary busy
  is the only disabled interaction state and is labelled as pending, not read-only.
- State precedence is: busy overrides drag initiation; dragging overrides hover;
  focus-visible remains externally visible over selected; selected persists beneath
  hover/focus; default is the fallback. Drop-target styling remains on the column and
  must not compete with the drag overlay.

### Opportunity Detail workspace layout

- Replace the Opportunity-specific 64rem cap with `70rem` (`1120px`), within the
  requested 68–72rem range and still `min(..., calc(100% - 2rem))`. The dialog keeps a
  maximum height of `calc(100dvh - 2rem)` and exactly one intentional vertical scroll.
  It must not restore the former generic 72rem/large-modal composition, nested record
  outlines, artificial minimum height, or duplicate headings.
- Use one integrated commercial header/overview zone. In scan order it contains the
  return affordance and Opportunity reference, company/Customer identity, optional
  contact context, prominent textual status, intentional Legendary signal, close
  control, grouped summary, and lifecycle actions. Identity, status, and the current
  primary action should be understandable in the first visible viewport.
- On wide layouts, use a main commercial column and secondary Contexto column with a
  target split near `minmax(0, 1fr) minmax(17rem, 19rem)` and a 20–24px gap. The exact
  CSS may use a bounded `clamp`, but quote and consultation must retain the clearly
  wider column. Contexto aligns to the top and does not stretch artificially.
- Use one modest neutral overview surface or structured band, not a card for every
  fact. Within it, group a semantic definition list into:
  - Relationship: Origin, Responsible;
  - Time: Created, Time in current stage;
  - Contact: Phone, Email, Province.
- Group labels and separators may be visual headings while the underlying `dl` keeps
  coherent reading order. Email/phone remain `mailto:`/`tel:` links and missing values
  remain truthful. A Pérdidas reason stays an associated destructive notice, not a
  giant banner.
- Preserve one semantic `h2` dialog title and ordered `h3` section headings. Do not
  duplicate `Detalle de oportunidad`, Customer identity, or Opportunity reference.

### Status and Legendary

- Opportunity status in centered detail must use an Opportunity-specific status
  treatment at 14–15px, weight 650–700, 32px minimum visible height, 12–14px horizontal
  padding, and the existing semantic status tone. It remains text-labelled, is
  associated with the identity group, and must not rely on color alone.
- Do not globally enlarge `Badge`; dense tables and unrelated dialogs retain current
  defaults. Add a typed badge size/variant only if it is reusable without changing
  defaults, otherwise compose an Opportunity-specific status class.
- Legendary in detail uses 13–14px, 28–32px height, readable padding, the existing
  star from the current icon language, and `Legendario` text. It sits near customer
  identity but below status in visual weight. It is not a tiny detached pill and does
  not compete with the primary action.
- Render Legendary from the effective server-provided qualification
  (`customer.is_legendary`, with the existing historical override compatibility where
  needed), consistent with Pipeline and Customer surfaces. Do not alter qualification
  rules, persistence, or recomputation.
- In Pipeline cards, Legendary may remain more compact than in detail, but uses at
  least 13px readable text and belongs with customer context, not as punctuation after
  origin.

### Typography and spacing contract

- Continue using Manrope and the existing semantic token palette. Prefer existing type,
  radius, surface, border, shadow, easing, and 4/8px-derived spacing tokens over new
  arbitrary values.
- Centered header identity: 22–24px, 650–700, approximately 28–32px line height.
- Contact identity: 14–15px, regular/medium, 20–22px line height.
- Opportunity reference/return metadata: 12–13px, 600 where interactive.
- Status: 14–15px, 650–700. Detail Legendary: 13–14px, 650.
- Section headings (`Consulta del cliente`, `Cotización`, `Contexto`): 16–17px,
  650–700, 22–24px line height. Do not use 14px for all commercial headings.
- Summary group headings/labels: 12–13px, 600; values: 14–15px, 20–22px line height.
- Consultation body: 15–16px, 24px line height, natural multiline wrapping and
  `overflow-wrap:anywhere` for hostile tokens. Keep a readable text measure rather
  than stretching prose edge to edge.
- Quote product and quantity rows: 14–15px; Product names at 550–650; quantities and
  total use tabular figures. `kg` remains explicit. Quote total is 15–16px and stronger
  than individual lines.
- Activity/Notes: 13–14px metadata and 14px body; the note textarea remains at least
  16px on narrow/touch layouts to avoid browser zoom.
- Use 24px primary section separation, 16–20px section padding, 12–16px group gaps,
  8px row/control gaps, and 4px tight label/value gaps. Do not create giant empty
  regions or compact core commercial content below these ranges.

### Actions

- Preserve all current lifecycle, permission, request, confirmation, synchronization,
  error, optimistic update, and navigation rules.
- Exactly one primary action appears when the lifecycle offers a next commercial step:
  - `NUEVA`: `Cotizar`;
  - `COTIZADA`: `Pasar a negociación`;
  - `NEGOCIACION`: `Marcar ganada`;
  - eligible `PERDIDA`: `Reabrir`;
  - `GANADA` and non-reopenable `PERDIDA`: no primary lifecycle action.
- `Editar cotización` is secondary in `COTIZADA`/`NEGOCIACION`; `Abrir WhatsApp` is a
  secondary communication action in every currently supported state; `Marcar perdida`
  is destructive/terminal and visually separated after ordinary actions.
- Place actions in or immediately adjacent to the commercial overview so their
  relationship to identity/status is clear. On desktop they may form a right-aligned
  decision row; on narrower widths they wrap or become a full-width ordered stack.
- Primary/secondary action targets are at least 40px high on desktop and 44px on
  touch/narrow layouts. Icon-only controls remain 44px. Pending actions keep their
  width/content stable where practical, show spinner plus verb (`Cotizando…`,
  `Actualizando…`, `Buscando conversación…`, `Reabriendo…` as applicable), set
  `aria-busy`, disable duplicate submission, and leave unrelated safe actions usable
  unless current mutation rules already disable them.
- Terminal/read-only status is conveyed by the explicit status and absence of invalid
  lifecycle actions, not by disabling a row of controls or inventing a read-only mode.

### Consultation, quote, Activity, and Notes

- For `WEB`, Consultation remains before Quote and uses only CRM-036's immutable plain
  text projection. A present message receives a subtle distinct content surface or
  typographic inset, 15–16px readable text, preserved line breaks, and safe wrapping
  so it is immediately noticeable. No quote, note, HTML, or Customer data is inferred.
- The approved empty text remains exact and truthful. When absent, use an inline muted
  empty state with no large container or decorative emphasis, so absence does not
  overpower identity or Quote. Non-`WEB` Opportunities render no Consultation section
  or reserved gap.
- Quote is the primary commercial evidence section. Its heading area explicitly shows
  whether a quote exists, an optional concise Product-line count/total kilograms from
  already-loaded data, and the allowed create/edit action only if that action is not
  already represented as the workspace primary/secondary action. Do not duplicate the
  same command in two places.
- Existing Product names, inactive indication, per-line Decimal quantities, and total
  kilograms remain. No price, money, budget, version history, or new quote rule is
  introduced. Many Products remain within the workspace scroll; only the bounded table
  region may scroll horizontally where unavoidable.
- A missing quote uses the exact truthful empty text and makes the allowed `Cotizar`
  primary action easy to associate with the absence. Terminal states never expose
  quote creation/editing.
- Contexto remains one secondary integrated region with existing Activity/Notes tabs,
  chronological history, lazy Notes request, retries, composer, shortcut, feedback,
  and permissions. It uses quieter surface/heading contrast than Consultation/Quote
  but the same radius, separators, typography family, and spacing rhythm.
- Keep the desktop sidebar at widths where it can be at least 17rem without cramping
  the primary column. Below that evidence-based threshold, place Contexto full width
  after Quote. Long Activity/Notes participates in the one workspace scroll; do not
  add a second vertical sidebar scroll.

### Responsive behavior

- Validate at 1440px, 1280px, a tablet-like 768–960px width, and 390×844, plus effective
  browser zoom conditions. Desktop/laptop remains primary.
- At approximately 56rem available dialog width or more, show the asymmetric two-column
  commercial/context layout. Below it, use a single column. Final threshold may be
  tuned from browser evidence but must not leave either column cramped.
- Summary groups may use three groups on large widths, two columns at intermediate
  widths, and one column on narrow widths while preserving DOM/reading order.
- Narrow semantic order is fixed: identity/status, actions, Consultation when
  applicable, Quote, then Activity/Notes. Relationship/Time/Contact remain within the
  identity/overview region and may stack before actions without changing this content
  priority.
- At 390×844, the dialog uses a safe 8–16px viewport inset, bounded `dvh` height, one
  vertical scroll, no page-level horizontal overflow, readable status/Legendary, and
  reachable 44px controls. Header identity/status may stack; close remains visible and
  does not overlap long names.
- Pipeline retains its intentional internal horizontal Kanban scroll on tablet/mobile,
  with columns/cards readable at their current useful minimum. No document-level
  horizontal overflow is allowed, and focus rings must not be clipped by card/column
  overflow.
- At 150% zoom on 1280×720 and 200% effective zoom where covered by the existing suite,
  all detail content and actions remain reachable and keyboard focus remains visible.

### Accessibility and motion

- Keep native buttons, links, headings, definition lists, tables, ordered lists, and
  native dialog semantics. Every interactive control has a meaningful accessible name;
  the full-card name includes identity and enough stage/drag context without becoming
  redundant.
- Status, Legendary, pending, selected, terminal, and error states include visible
  text/semantics and are never communicated by color alone. Busy uses `aria-busy` and
  a polite status/announcement already compatible with CRM-038.
- Focus-visible uses at least a 2px high-contrast ring and clear offset in Light and
  Dark. It must survive selected, modal scrim, internal scrolling, and 200% zoom. Do
  not remove native focus without a stronger replacement.
- Retain keyboard card activation, keyboard drag, Escape cancellation, dialog focus
  containment, return-to-trigger/fallback focus, return affordance, close control,
  backdrop policy, and nested quote/loss/confirmation focus behavior.
- Detail and narrow-layout controls meet 44×44px targets; desktop text controls should
  be at least 40px where this spec enlarges the current compact rail. Adjacent targets
  retain at least 8px practical separation.
- Verify normal text at 4.5:1 and large/structural graphical indicators at 3:1 against
  adjacent surfaces in both current themes. CRM-040 does not redesign Dark theme, but
  every new token pairing/state must remain distinguishable there.
- Use CSS transitions limited to relevant properties. Hover/selection/border/shadow
  feedback uses `--motion-fast` or `--motion-standard` (120–180ms) and `--ease-ui`.
  The optional card lift is at most 1px. Drag feedback tracks the interaction directly.
- Do not introduce bounce, large transforms, stagger, decorative entrance, or a motion
  dependency. Preserve the native dialog's current entry behavior unless a pre-existing
  shared transition is used. Under `prefers-reduced-motion: reduce`, remove positional
  transforms and reduce transition duration while keeping immediate non-motion state
  changes visible.

## Non-goals

- Backend, database, Alembic, persistence, API, or request-contract changes.
- Opportunity lifecycle, quote-domain, permission, terminal-state, Legendary
  qualification, CRM-039 retention/history, or Pérdidas reopen-rule changes.
- CRM-002/Web intake persistence, normalization, idempotency, security, or projection
  changes; copying Consultation into Notes or Activity.
- Dashboard redesign, sidebar/navigation redesign, global terminology pass, hiding
  Broadcasts, global icon redesign, full Dark-theme redesign, or global design-system
  rewrite.
- Redesigning the WhatsApp Inbox Opportunity context drawer. Shared content behavior
  may remain compatible, but the 70rem workspace hierarchy applies only to centered
  Opportunity Detail.
- Redesigning Quote, Loss, Confirmation, Customer, Products, Ganadas list, or Pérdidas
  list surfaces beyond the visual integration point that opens centered detail.
- New frontend state/data-fetching library, UI component library, animation library,
  new global state, or broad modal rewrite.
- Prices, money, commercial budget generation, stock, Product categories, or quote
  version history.

## Business rules

- `docs/BUSINESS_RULES.md` and CRM-020/036/038/039 remain authoritative. CRM-040 changes
  presentation hierarchy only.
- The Pipeline remains `NUEVA` → `COTIZADA` → `NEGOCIACION` → `GANADA`; `PERDIDA` and
  `GANADA` remain terminal under existing rules, with only the existing eligible
  Pérdidas reopen command.
- Quote content remains Products plus positive Decimal kilograms only. Terminal quotes
  remain immutable.
- The original web consultation remains the immutable CRM-036 projection, displayed
  only for `WEB`; missing content is never invented.
- Both existing roles retain global Opportunity visibility and current action
  permissions.
- Active-board `GANADA` retention and Ganadas historical access remain exactly as
  CRM-039 defines them.

## Data model

No change. CRM-040 consumes the current typed `OpportunitySummary` and
`OpportunityDetail` projections. It adds no field, table, migration, derived persisted
state, status, or duplicated consultation/quote data.

## Contracts / API

No change. Existing Pipeline stage requests, detail request, mutation responses,
Notes requests, WhatsApp lookup, Ganadas filters, Pérdidas behavior, and CRM-038
authoritative reconciliation remain byte-for-byte compatible in purpose and topology.
Frontend visual-state props/classes may be refined as typed internal component
contracts, but no network call or payload is added.

## State transitions

No domain transition change. Visual state is a presentation projection only:

```text
default -> hover | focus-visible | selected
selected + hover/focus-visible -> selected remains persistent; transient cue layers above
default/selected -> dragging -> settled default/selected or pending optimistic state
default/selected -> pending -> authoritative success or rollback/error
GANADA -> enabled detail trigger, not draggable, no lifecycle mutation
```

CRM-038 request generations, optimistic replacement, rollback, scoped stage refresh,
cached detail, mounted workspace, filters, and scroll preservation are unchanged.

## Security & permissions

- Existing authenticated routes, global visibility, roles, and server-side command
  validation remain unchanged.
- No secret, integration identifier, intake metadata, private backend state, or new
  Customer field is exposed.
- Consultation remains escaped React plain text. Long content cannot inject markup or
  escape its bounded layout.
- Visual absence or disabled styling never substitutes for backend authorization.

## Edge cases

- Long company/Customer/contact names wrap in detail without colliding with status,
  Legendary, close, or actions; dense cards truncate predictably without widening a
  column.
- Long email, phone, province, unbroken consultation token, multiline consultation,
  many Products, large kilogram values, inactive Products, long history, and long Notes
  remain readable within the single dialog scroll and without document overflow.
- Company absent uses Customer name once; distinct company/contact identity remains
  understandable. Missing contact facts retain exact truthful labels.
- Automatic and manual-effective Legendary Customers receive the same visual signal;
  regular Customers do not reserve badge space.
- A `WEB` Opportunity with missing intake/message shows the approved concise empty
  state; non-`WEB` renders no Consultation region.
- Quote present/absent and lifecycle permission combinations never duplicate a command
  or expose an invalid action.
- Busy card/action, mutation success, rollback/error, background Pipeline refresh, won
  retention expiry, and selected-detail synchronization do not flicker, remount the
  card, lose selection, or erase last successful content.
- Focus remains visible when a selected card sits beneath the dialog scrim and is
  restored after closing. Nested dialogs restore focus to the invoking control.
- Opening centered detail from Pipeline, direct Pipeline URL, Ganadas history, and
  Pérdidas produces the same hierarchy with truthful return affordance and only the
  lifecycle actions allowed on that entity.
- Dark theme may keep its current overall design, but new border/shadow/status/busy
  distinctions cannot collapse into adjacent surfaces.

## Risks

- The current card article clips overflow. An external focus ring or elevated hover
  can be cut by the card or column scroller unless spacing/overflow is adjusted without
  widening the board or creating document overflow.
- A full-card control owns both click and drag. Added progress elements or metadata
  must remain non-interactive descendants and must not create nested controls, change
  the six-pixel activation threshold, or make ordinary clicks start a drag.
- A wider 70rem shell can recreate the old oversized feeling if content is stretched
  uniformly. The asymmetric columns, readable text measure, content-sized height, and
  absence of artificial minimum height are therefore acceptance requirements, not
  optional polish.
- Making the integrated overview or actions sticky could create a second perceived
  scroll region, hide focused content, or collide with nested dialogs. A sticky
  boundary is permitted only after viewport/zoom evidence and must remain within the
  one existing scroll container.
- Shared `Badge`, `Modal`, and `LegendaryBadge` have unrelated consumers. Any shared
  extension must be opt-in and snapshot-tested so default dialogs, table badges, and
  the WhatsApp drawer do not change.
- The current centered detail renders Legendary only from the manual override even
  though Pipeline and the backend expose effective qualification. Correcting the
  visual condition must use existing response truth and compatibility fallback; it
  must not invent client-side Legendary calculation.
- The full requested state/fixture matrix is combinatorial. Use representative stable
  scenario baselines plus semantic assertions for the remaining combinations; do not
  produce dozens of redundant full-page snapshots or mask meaningful regions.
- User-owned concurrent frontend changes can invalidate unrelated visual baselines.
  CRM-040 baseline approval must distinguish its intended diffs from pre-existing
  failures and must not update unrelated images opportunistically.

## Visual regression and browser test plan

Visual acceptance is required in addition to component/unit tests. Use only the
canonical Docker Compose application, deterministic QA seed/clock, bundled Chromium,
ready local fonts, fixed locale/timezone, clean console/network logging, and the
existing baseline comparator. Do not weaken pixel/mean-delta thresholds to pass.

### Pipeline matrix

- Add intentional 1440×900 and 1280×800 baselines containing cards in `NUEVA`,
  `COTIZADA`, `NEGOCIACION`, and active-board `GANADA`, including company/contact,
  no-company identity, regular and Legendary Customers, and stage-age on/off where
  hierarchy differs.
- Capture stable element/surface clips for default, fine-pointer hover, keyboard
  focus-visible, route-selected/opened, selected+focus, pointer dragging with source
  and overlay, keyboard dragging if deterministically capturable, pending/busy, and
  terminal enabled/non-draggable `GANADA`.
- For busy state, intercept/delay the existing mutation response rather than introduce
  a test-only app state; assert the card remains mounted, `aria-busy=true`, conflicting
  controls are disabled, accessible pending feedback exists, and completion/rollback
  causes no layout jump.
- Assert keyboard drag and pointer drag still issue exactly the current permitted
  request, optimistic movement remains visible, failure rolls back, and CRM-038 stale
  responses cannot overwrite the authoritative result. Visual coverage supplements,
  rather than replaces, existing mutation journeys.

### Opportunity Detail fixture matrix

- Baseline a `WEB` lead with a real multiline consultation and one without a stored
  consultation; assert exact CRM-036 visibility/empty truth.
- Baseline quote-present and quote-absent states, including many Products, inactive
  retained Product, large kg values, and lifecycle-permitted create/edit action.
- Cover regular and effective Legendary Customers; long company/Customer/contact name;
  long email; missing phone/email/province/responsible; and loss reason.
- Cover `NUEVA`, `COTIZADA`, `NEGOCIACION`, terminal `GANADA`, and `PERDIDA`, asserting
  the one-primary-action matrix, secondary/destructive ordering, terminal absence, and
  pending action labels/states.
- Open `GANADA` from current Pipeline and from `/won/opportunities/<id>` historical
  Ganadas context; open `PERDIDA` from Pérdidas. Assert shared hierarchy, correct
  accessible dialog name, correct return label/route/query preservation, and no list/
  board remount.
- Cover Activity with long history and Notes with loading, error/retry, empty, long
  content, multiline composer, pending save, and successful save. Assert Contexto
  remains secondary and uses the single dialog scroll.

### Viewports, zoom, themes, and accessibility

- Test at 1440×900, 1280×800, tablet-like 768×1024 or 960×720, and 390×844. Include
  effective 150% at 1280×720 and existing 200% coverage; retain zoom capability.
- At every narrow/effective-zoom target assert no document-level horizontal overflow,
  bounded dialog geometry, one vertical workspace scroller, visible close/back,
  reachable actions, correct semantic order, and locally contained quote overflow.
- Run Light and Dark focused baselines for cards and detail status/Legendary/busy/focus
  pairings. This is regression coverage, not CRM-043's redesign.
- Run Axe on open detail and Pipeline, semantic role/name tests, sequential heading and
  reading-order checks, Tab/Shift+Tab containment, Escape/backdrop policy, focus
  restoration, card Enter/Space behavior, keyboard drag/cancel, and non-color state
  assertions.
- Run with `prefers-reduced-motion: reduce`; assert transforms are removed/reduced and
  no action waits for animation. With normal motion, assert only the specified
  120–180ms properties and bounded one-pixel lift.
- Browser baselines are updated only after deliberate human review of the final
  hierarchy. Do not accept threshold changes, broad masks, timing sleeps, or hidden
  content as regression fixes.

## Acceptance criteria

- AC-01: Pipeline cards retain one semantic full-card detail button, existing click/
  drag/keyboard behavior, dense useful height, and a scan order of identity,
  commercial context, supporting metadata, then tertiary source/age.
- AC-02: Default, hover, focus-visible, selected/opened, dragging, pending/busy, and
  terminal enabled/non-draggable states are visually and semantically distinct under
  the precedence defined by this spec in Light and Dark.
- AC-03: Default cards remain visibly separated from columns; fine-pointer hover
  increases border/shadow/elevation without washing into the column; focus-visible is
  stronger than hover and remains unclipped; selected persists without hover.
- AC-04: Dragging uses a stable muted source and card-faithful bounded overlay; busy
  keeps the card mounted with visible/accessibly announced progress and no flicker,
  disappearance, or layout shift.
- AC-05: Pipeline cards modestly increase commercial readability using the specified
  15–16px, 13–14px, and 12–13px hierarchy without enlarging every line or materially
  reducing board density.
- AC-06: Centered Opportunity Detail is capped at `70rem`, viewport bounded, content
  sized, and uses exactly one vertical workspace scroll; it does not return to the old
  generic 72rem composition or retain CRM-037's undersized 64rem cap.
- AC-07: One integrated header/overview visibly prioritizes Opportunity reference,
  company/Customer, distinct contact, labelled commercial status, intentional
  Legendary signal, grouped summary, actions, and close/back controls without
  duplicated identity headings.
- AC-08: Status is 14–15px and at least 32px high with strong weight and textual label;
  detail Legendary is 13–14px and 28–32px high, uses the consistent star/text signal,
  and is visually secondary to identity/status. Effective automatic/manual Legendary
  truth is preserved.
- AC-09: Existing facts are grouped as Relationship (Origin/Responsible), Time
  (Created/Time in stage), and Contact (Phone/Email/Province) using semantic structure,
  alignment, whitespace, and subtle separators rather than per-datum cards.
- AC-10: Each lifecycle state shows at most one primary action exactly as defined;
  secondary communication/edit actions and destructive/terminal actions have clear
  order, association, target sizes, pending feedback, and unchanged domain behavior.
- AC-11: A present CRM-036 Consultation is prominent, 15–16px, safe multiline plain
  text; its approved missing state is truthful and subdued; non-`WEB` Opportunities
  reserve no consultation space.
- AC-12: Quote is primary commercial evidence and clearly represents existence or
  absence, Products, inactive labels, per-line and total Decimal kilograms, and the
  single permitted create/edit command without prices, monetary budgets, duplication,
  or rule changes.
- AC-13: Activity/Notes remain an integrated secondary Contexto region with all current
  loading, retry, compose, shortcut, pending, history, permission, and save behavior;
  it moves after Quote when a readable 17rem sidebar cannot be maintained.
- AC-14: At 1440px, 1280px, tablet-like width, 390×844, 150% zoom, and applicable 200%
  zoom, the required semantic order and readable sizes hold, actions remain reachable,
  and neither page nor dialog causes unintended horizontal overflow.
- AC-15: Detail opened from active Pipeline, historical Ganadas, and Pérdidas shares
  one hierarchy while preserving return origin/query, CRM-038 mounted-state/
  synchronization, CRM-039 retention, and all terminal/reopen rules.
- AC-16: Native dialog role/name, focus trap/containment, Escape/backdrop policy, initial
  and restored focus, nested-dialog focus, keyboard card activation/drag, meaningful
  action names, live busy/error feedback, 44px narrow targets, contrast, and non-color
  state cues pass focused accessibility/browser checks.
- AC-17: Motion is limited to useful 120–180ms state feedback and direct drag response,
  uses existing easing/tokens, has no bounce/decorative sequence/large transform, and
  removes positional motion under reduced-motion.
- AC-18: Deterministic browser baselines cover the complete Pipeline state matrix and
  Detail fixture/lifecycle/origin/responsive matrix in this spec; thresholds are not
  weakened and expected images receive explicit human review.
- AC-19: No backend/API/domain files, Dashboard/sidebar/global terminology/Broadcast
  visibility, global icon system, global theme, global design system, or frontend state
  library changes are introduced.
- AC-20: Frontend typecheck, lint/format, unit/coverage, build, npm audit, applicable
  Docker health checks, focused browser semantics/Axe/motion/visual tests, and existing
  CRM-038/039 regression tests pass before implementation is considered complete.

## Open decisions

None

## Follow-up / future specs

- CRM-043 owns the full Light/Dark and global design-system cleanup. CRM-040 only
  prevents regressions in the touched states and surfaces.

## Implementation notes

- Expected primary modules are `OpportunityCard`, `PipelineColumn`, `PipelineBoard`,
  `OpportunityDetailContent`, `OpportunityDetailPage`, `OpportunityContextPanel`,
  `LegendaryBadge`, `Badge`, `Modal`, and their focused tests/styles.
- Prefer state modifiers/data attributes on the existing card and a small typed visual
  presentation contract. Do not introduce a second card component per stage or a
  separate won/lost detail application.
- A minimal opt-in shared primitive extension is allowed: an Opportunity workspace
  modal size near 70rem, an optional sticky/integrated header boundary if browser
  evidence requires it, and/or a typed Badge size. Existing Modal/Badge defaults and
  unrelated consumers must remain unchanged. Do not fork focus management.
- Reuse `--shadow-subtle`, `--shadow-raised`, `--shadow-floating`, surface/border/focus,
  radius, type, easing, and duration tokens where they express the required state.
  Add a narrowly semantic token only when the existing set cannot keep state parity in
  both themes; avoid a global token migration.
- Preserve `OpportunityDetailContent` drawer behavior for WhatsApp Inbox. Centered
  workspace classes/composition must stay layout-specific.
- The current centered header checks only `legendary_historical_override`, while
  Pipeline consumes effective `is_legendary`. The implementation should use the
  effective projection consistently as a visual truth fix without altering Legendary
  domain behavior.
- Preserve all CRM-038/039 request generation, busy ID, optimistic rollback, cached
  detail, route, expiry, and narrow-refresh logic. Visual progress derives from current
  state; it must not create new requests or remount boundaries.

## Expected files/modules likely to change

- `frontend/src/pipeline/OpportunityCard.tsx`
- `frontend/src/pipeline/PipelineColumn.tsx`
- `frontend/src/pipeline/PipelineBoard.tsx`
- `frontend/src/pipeline/OpportunityDetailContent.tsx`
- `frontend/src/pipeline/OpportunityContextPanel.tsx`
- `frontend/src/pages/OpportunityDetailPage.tsx`
- `frontend/src/customers/LegendaryBadge.tsx`
- `frontend/src/shared/Badge.tsx` only if an opt-in size is cleaner than a local class
- `frontend/src/shared/Modal.tsx` only for a minimal opt-in Opportunity capability
- `frontend/src/styles.css`
- focused tests beside the touched Pipeline/detail/shared components and pages
- `backend/quality/browser/test_20_responsive_accessibility.py`
- `backend/quality/browser/test_30_states.py`
- `backend/quality/browser/test_40_visual_regression.py`
- `backend/quality/browser/test_90_mutating_journeys.py` only where existing mutation
  journeys need visual-state assertions
- deliberate CRM-040 PNG baselines under `backend/quality/browser/baselines/`

No backend application, schema, migration, API contract, or business-rule file is
expected to change.
