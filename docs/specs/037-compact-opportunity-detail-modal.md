# CRM-037 — Compact Opportunity Detail Modal

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-07
Implementation commit: `9961635`

## Goal

Redesign the centered Opportunity Detail modal as a compact, cohesive commercial
record that helps a salesperson identify the customer, scan the opportunity, act, and
review its consultation, quote, activity, and notes without excessive whitespace or
competing visual regions.

## Context

CRM-020 introduced the centered, read-first Opportunity Detail experience. CRM-036
later added the original web consultation to its primary content. The current modal
now distributes a relatively small amount of information across a generic modal
heading, a separate Pipeline-return row, a second identity header, a wide summary, a
separate Customer-information section, and an Activity/Notes column with a minimum
width of 19rem. At the existing 72rem modal width, these layers make related commercial
facts feel scattered and leave large areas of unused white space.

This specification refines only the centered Opportunity Detail modal. It follows the
compact visual language established by CRM-018, CRM-027, CRM-028, and CRM-031 and does
not change domain behavior, data, API contracts, or the Opportunity context drawer
used by WhatsApp Inbox.

CRM-020 excluded the internal Opportunity ID from its identity header. The explicit
requirement for this redesign supersedes that single presentation restriction for the
centered detail modal: the existing human-readable `Oportunidad #<id>` reference
remains visible. It does not authorize exposure of integration identifiers.

## Dependencies

- CRM-018 — Frontend Design System
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-027 — Visual Design & Product Polish
- CRM-028 — Visual Clarity & Dashboard Simplification
- CRM-031 — Visual Consistency & Product Polish
- CRM-036 — Web Consultation in Opportunity Detail

## Scope

- Replace the modal's stacked generic heading, standalone Pipeline-return row, and
  inner identity header with one compact Opportunity identity header.
- Keep the close control and the existing return-to-origin navigation behavior.
- Consolidate Opportunity and Customer facts into one semantic two-column summary.
- Present status-aware commercial actions in a compact, consistent action rail.
- Recompose the main body as a wider commercial-content column and a narrower,
  content-sized Activity/Notes sidebar.
- Keep `Consulta del cliente` before `Cotización` for `WEB` Opportunities.
- Preserve all existing displayed information, truthful missing-value states, quote
  rendering, Activity history, Notes loading/composition, feedback, and commercial
  actions.
- Reduce the centered modal's maximum width and Opportunity-specific spacing without
  changing the default presentation of other modal consumers.
- Add focused component tests and responsive browser/visual coverage for the revised
  modal composition.

## Non-goals

- Any backend, persistence, Alembic, schema, query, domain, permissions, or API change.
- Changing CRM-002 intake, WordPress/Avada, HMAC, idempotency, or CRM-036 data behavior.
- Adding, inferring, or backfilling province, responsible user, consultation, quote,
  or any other missing value.
- Exposing `external_submission_id`, LeadIntake identifiers, or other internal intake
  metadata.
- Copying the web consultation into Notes or Activity.
- Removing or changing quote, stage-transition, WhatsApp, lost, reopen, Activity, or
  Notes behavior.
- Redesigning the quote, loss, confirmation, or WhatsApp context dialogs.
- Redesigning the Opportunity context drawer embedded in WhatsApp Inbox.
- Adding a UI library, new visual system, decorative motion, or decorative
  border-left/border-top treatments.

## Information architecture and visual contract

### Modal shell

- The centered Opportunity Detail modal uses a maximum width of `64rem` while still
  respecting the existing viewport inset and bounded vertical scroll behavior.
- The shared Modal primitive remains the accessible dialog, focus trap, close
  boundary, and overlay. If it needs a typed composition option for an integrated
  header or Opportunity-specific size, its existing defaults and other consumers must
  remain visually and behaviorally unchanged.
- Only one visible identity header is rendered. `Detalle de oportunidad` is not shown
  as a second generic heading above the record.
- The separate row containing `Volver al Pipeline` is removed. Its navigation remains
  available as a compact return affordance within the unified header and retains the
  correct origin label/route for Pipeline or Lost Opportunities.
- The shell must not introduce a second nested full-record outline or a large empty
  minimum height. Content determines height up to the existing viewport maximum.

### Header

- The unified header contains, in scan order: the compact return affordance,
  `Oportunidad #<id>`, company name or Customer name as the accessible dialog title,
  contact-person name when a separate company exists, Legendary badge when applicable,
  status badge, and close button.
- Identity is visually dominant but restrained: the company/Customer name uses the
  existing title scale and navy text; the Opportunity number and contact are supporting
  text. Status remains text-labelled and is not communicated by color alone.
- The shared close target remains accessible and keyboard-operable. The header keeps
  its established compact overlay height rather than adding another padded identity
  band beneath it.

### Compact summary

- One semantic definition list replaces the current split between the four-field
  summary and the separate `Información del cliente` section.
- On wide layouts it is a two-column grid with this row-major order:
  1. Origen / Responsable
  2. Creada / Tiempo en etapa
  3. Email / Teléfono
  4. Provincia
- Email and phone retain their actionable `mailto:` and `tel:` links. Missing values
  retain the current truthful labels, including `Sin responsable`, `No informado`, and
  `No informada` as applicable.
- The summary is one cohesive, neutral information region. Individual facts do not
  become cards. It uses existing surfaces, typography, dividers, and a 4/8px-derived
  spacing rhythm; it does not use pale yellow or decorative top/left accents.
- A lost Opportunity's reason remains visible as a compact semantic destructive
  notice associated with the summary, without becoming a large banner.

### Actions

- Existing status and permission logic remains unchanged.
- Available actions retain the commercial priority defined by CRM-020 and CRM-028:
  the principal state-advancing or quoting action first, WhatsApp/secondary actions
  next, and the destructive `Marcar perdida` action last.
- Opportunity actions use the existing `Button` compact size (`2.25rem` / 36px visible
  control height), consistent labels, icon sizing, and gaps. Only one action is styled
  as primary at a time; WhatsApp keeps its restrained communication treatment and the
  loss action keeps its destructive treatment.
- The action rail sits directly after the summary and before the main content. It
  wraps without overlap and does not occupy a full-height or oversized call-to-action
  panel. Accessible touch targets remain consistent with CRM-031.

### Main content

- On wide layouts the body uses two columns: `minmax(0, 1fr)` for commercial content
  and a context sidebar constrained to `clamp(15rem, 27%, 17rem)`, separated by a
  `1rem` gap.
- The main column renders `Consulta del cliente` for `WEB` Opportunities and then
  `Cotización`. Non-`WEB` Opportunities start with `Cotización` and do not reserve an
  empty consultation region.
- Consultation behavior from CRM-036 is unchanged: stored text is plain text,
  preserves line breaks, wraps long tokens safely, and uses the approved empty text
  `No hay un mensaje del formulario web disponible.` when unavailable.
- Quote contents, inactive-product indication, quantities, total, and the truthful
  `Aún no se registró una cotización.` state remain unchanged.
- Consultation and quote read as sections of one commercial record. They use concise
  headings and compact internal spacing, with a structural full-width divider or
  spacing only where separation is needed. They must not be rendered as a stack of
  large disconnected administrative cards or one-pixel grid bands.
- Empty states are inline supporting text with no fixed height and no oversized empty
  container.

### Activity and Notes sidebar

- The existing `Contexto` region, `Actividad`/`Notas` segmented control, chronological
  Activity, lazy Notes loading, retry state, note list, note composer, keyboard
  shortcut, validation, saving feedback, and permissions are preserved.
- The sidebar aligns to the top, sizes to its content, and does not stretch to match a
  taller main column or consume half of the modal.
- Its 15–17rem desktop width is intentionally secondary to the commercial-content
  column while remaining sufficient for the existing note composer. Text and controls
  wrap without horizontal overflow.
- Empty Activity/Notes states remain concise and do not create artificial vertical
  space.

## Responsive behavior

- At an available dialog-content width of at least `52rem`, the main content and
  context sidebar use the specified asymmetric two-column layout.
- Below `52rem`, the body becomes one column in semantic order: consultation when
  applicable, quote, then Contexto. The sidebar becomes full width and keeps its
  content-sized height.
- The summary remains two columns while at least `40rem` is available and becomes one
  column below that threshold, preserving the same DOM and reading order.
- Actions wrap into additional rows as needed. On narrow or touch-oriented layouts,
  controls may use the existing standard height where necessary to maintain touch
  accessibility; actions never overflow horizontally.
- At narrow viewports the dialog keeps the existing viewport inset, bounded vertical
  scroll, focus trap, Escape/backdrop policy, and focus restoration. Quote tables keep
  their contained horizontal-overflow behavior.
- At 150% browser zoom on a 1280×720 viewport, all information and actions remain
  reachable without page-level horizontal scrolling, clipped controls, or obscured
  focus indicators.

## Data model

No change. All displayed values continue using the existing `OpportunityDetail`
projection and related frontend types. `lead_intakes.message` remains the single source
of truth for the WEB consultation under CRM-036.

## Contracts / API

No change. The frontend must not add requests, request fields, response fields, or
integration metadata for this redesign.

## State transitions

No change. The redesign does not alter allowed Opportunity transitions, validation,
confirmation, side effects, or refresh/navigation behavior.

## Security & permissions

- Existing authentication, authorization, and global Opportunity visibility remain
  unchanged.
- Existing action visibility/availability and Note permissions remain unchanged.
- The web consultation remains safe plain text and no integration identifier becomes
  visible.

## Edge cases

- Very long company names, contact names, email addresses, phone numbers, province
  names, and consultation tokens wrap without colliding with the status or close
  controls.
- Missing company uses Customer name as the title without duplicating a contact row.
- Missing optional facts retain truthful missing-value labels and do not leave blank
  grid cells that imply unavailable content exists.
- A non-`WEB` Opportunity does not reserve consultation space.
- A `WEB` Opportunity with no message shows only the approved concise empty text.
- A long quote table stays within the main column and scrolls locally in the horizontal
  axis when needed.
- Long Activity or Notes content increases the local dialog scroll normally; the
  sidebar does not force the main column to an artificial height.
- Loading, not-found, request-error, action-error, WhatsApp-feedback, and mutation
  states remain reachable and readable within the same modal shell.
- Opening nested quote, loss, or confirmation dialogs continues preserving focus and
  returning it to the appropriate Opportunity control.

## Acceptance criteria

- AC-01: Opportunity Detail presents one visible identity header containing the return
  affordance, Opportunity number, company/Customer, conditional contact, status,
  conditional Legendary badge, and close control; it does not also render the generic
  `Detalle de oportunidad` heading or a standalone return row.
- AC-02: The centered modal is capped at `64rem`, has no artificial content minimum
  height, and uses a single bounded dialog scroll without changing other Modal
  consumers.
- AC-03: Origin, responsible, creation time, time in stage, email, phone, and province
  appear in one semantic two-column summary at wide widths, in the specified row-major
  order, with current links and truthful missing-value labels preserved.
- AC-04: Existing status/permission-dependent actions behave exactly as before and use
  the shared compact button size in their existing commercial priority order, with no
  more than one primary action.
- AC-05: At widths of at least `52rem`, the main body renders a flexible commercial
  column and a top-aligned `15rem`–`17rem` Contexto sidebar; the sidebar does not stretch
  to the main column's height.
- AC-06: For `WEB` Opportunities, `Consulta del cliente` remains before `Cotización`,
  preserves safe multiline wrapping, and uses the CRM-036 approved empty text when
  absent; non-`WEB` Opportunities show neither the section nor reserved space.
- AC-07: Quote data and empty state, Activity history, lazy Notes loading and retry,
  note creation, keyboard shortcut, feedback, and all current commercial actions
  remain present and functional.
- AC-08: Below `52rem`, commercial content precedes Contexto in a single column; below
  `40rem`, the summary also becomes one column. Neither transition causes horizontal
  page overflow or inaccessible controls.
- AC-09: Missing data is not inferred or invented, and no intake/internal integration
  metadata is displayed.
- AC-10: The modal uses existing FAA tokens and primitives: Manrope, saturated yellow
  primary, navy structure, neutral surfaces, existing radii and shadows, and no pale
  yellow or decorative top/left borders.
- AC-11: Keyboard focus trapping, close behavior, return navigation, focus restoration,
  visible focus states, heading hierarchy, labelled status, and nested-dialog focus
  behavior pass existing and focused accessibility tests.
- AC-12: Focused component tests cover structure, content preservation, responsive
  class/contracts, WEB/non-WEB consultation states, action sizing, and Notes/Activity;
  browser visual checks cover the modal at supported desktop, constrained, and 150%
  zoom conditions without unintended changes to the WhatsApp Opportunity drawer.
- AC-13: Frontend TypeScript, lint/format, unit/coverage, build, audit, and applicable
  Docker/browser quality gates pass; backend/API files and contracts remain unchanged.

## Open decisions

None

## Follow-up / future specs

None

## Implementation notes

Keep `OpportunityDetailContent` reusable, but apply this composition only to its
centered/page layout. Preserve the compact drawer layout and current behavior in
WhatsApp Inbox. Prefer a small typed extension to the shared Modal primitive if needed
to compose the integrated accessible header; do not fork dialog focus/close behavior
or change Modal defaults. Use the existing `Button`, `Badge`, `SegmentedControl`,
`LegendaryBadge`, feedback/state components, typography, spacing, surface, border,
radius, and shadow tokens.
