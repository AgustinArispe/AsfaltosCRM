# CRM-021 — Dashboard & Metrics

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-14
Implementation commit: 3edf94ba4f93587b33b3488e753b5a32e223666a

## Goal

Create FAA CRM's most polished analytical workspace: a premium, useful Dashboard that answers what needs attention now and how the commercial operation is performing. It combines immediate operational evidence with authoritative commercial metrics, charts, and provincial insight without becoming a decorative BI wall.

## Context

CRM-004 already supplies authenticated, backend-calculated overview, product, source, province, timeline, and current Pipeline-snapshot aggregates. Its typed Decimal values, period semantics, and conversion formulas are authoritative; the frontend only formats and visualizes them. Active global notifications have exact pagination totals, while the cursor-based WhatsApp conversation list intentionally has no aggregate total.

The current React/Vite/TypeScript/Tailwind frontend has no metrics client, Dashboard page, or chart dependency. App.tsx composes routes and pages, frontend/src/api owns typed HTTP calls, and feature pages currently own request state locally. CRM-018 is the mandatory FAA visual, interaction, theme, accessibility, responsive, component, and architecture foundation. This spec specializes it and must not contradict it.

docs/BUSINESS_RULES.md remains authoritative for commercial states, global stale notifications, visibility, products, kilogram precision, and the rule that metrics are calculated on the backend. Both existing roles see the same opportunities and metrics; this Dashboard adds no seller-based visibility.

## Dependencies

- CRM-003 — Stale Opportunity Notifications
- CRM-004 — Commercial Metrics
- CRM-006 — WhatsApp Internal API
- CRM-007 — WhatsApp Inbox Query Layer
- CRM-010 — WhatsApp Inbox Frontend
- CRM-018 — Frontend Design System

## Scope

- Define /dashboard as the App Shell analytical workspace and its compact hierarchy: identity and filters, operational attention, KPIs, evolution, conversion/Pipeline, product/source performance, and geographic insight.
- Define the Dashboard's use of existing metrics, notification, opportunity, and WhatsApp read contracts without changing their business semantics or adding backend endpoints.
- Define chart visual/accessibility behavior, Light/Dark treatment, responsive layout, loading/refresh/empty/error states, useful interaction, and bounded functional motion.
- Define Dashboard feature/API/component ownership within the existing frontend
  architecture and its focused custom SVG/DOM chart approach.

## Non-goals

- New commercial metric definitions, frontend aggregation of Opportunity-level data, forecasting, AI, campaign ROI, report export, or a general BI/query builder.
- Seller/user filters, changed role visibility, pricing, monetary measures, or fields that are not supplied by the current CRM domain.
- Metrics-backend redesign, new API endpoints, mobile-native Dashboard design, an external map API, or inferred customer geography.
- Making filters the visual focus, reproducing the full Pipeline Kanban, or adding a global state library without measured evidence.
- Implementing this page, installing a chart library, or approving this spec.

## Dashboard workspace

### Information hierarchy and layout

The Dashboard starts with page identity, short period context, and compact global filters. Its content follows this priority, using adaptive CSS grids rather than a fixed screen mockup:

1. operational attention;
2. KPI summary;
3. commercial evolution;
4. conversion and current Pipeline distribution;
5. Products and sources; and
6. provincial distribution.

Every surface has a specific commercial or operational question to answer. At normal desktop widths, the evolution chart receives the largest analytical span; conversion and Pipeline sit alongside it when their minimum readable widths fit. Products/sources and province insights use smaller paired or stacked surfaces. At no width does a decorative chart displace actionable attention or KPI context.

The App Shell's permanent FAA sidebar owns navigation. Dashboard does not introduce a top navigation bar, second side rail, or marketing-style hero. Its heading and content retain CRM-018's semantic landmarks, skip-link behavior, tokens, IBM Plex Sans roles, restrained rounded surfaces, and Light/Dark/System themes.

### Operational attention

The top attention block is short, evidence-based, and operationally prior to analytics. It contains compact actionable summaries only when current backend contracts can prove their state:

| Evidence | Presentation and truthful limit |
| --- | --- |
| Active stale Opportunity notifications | Seguimientos pendientes uses the exact active total from GET /notifications. The only implemented notification type is OPPORTUNITY_STALE, so this is an exact stale-follow-up count. |
| Unread active notifications | Notificaciones sin leer uses the exact total from GET /notifications?unread_only=true. It is not treated as a second business definition of stale state. |
| WhatsApp waiting for response | Conversaciones esperando respuesta is shown only when a bounded GET /whatsapp/conversations?waiting_only=true&limit=1 result proves at least one item. It says that work exists; it never displays a fictional global count. |
| Newly created Opportunities | When useful, Oportunidades creadas en el período reuses the overview created value and links only to the existing Pipeline workspace, without pretending Pipeline has a date-filter deep link. |

An attention item is a link or button only when the target route can preserve its meaning. The existing /pipeline and /whatsapp workspaces may be opened, but the current routes do not own a Dashboard query/deep-link contract for stale, unread, or waiting filters. CRM-022 and CRM-023 may later define that handoff; until then those items remain clear summaries rather than deceptive clickable controls. Dashboard never marks a notification read, resolves it, or mutates a conversation merely by rendering or opening its summary.

Operational attention uses label, count/state, and an appropriate icon or shape in addition to colour. It has distinct no-attention, loading, and unavailable states and does not expand into a long notification feed.

## Metrics, filters, and API contracts

### Authoritative metric semantics

Dashboard must preserve CRM-004 exactly:

- created/open Opportunity counts and quoted kg use Opportunity.created_at;
- won/lost counts, terminal kg, and both conversion denominators use current_status_entered_at for the current terminal state;
- opportunity conversion is won / (won + lost) and volume conversion is kg_won / (kg_won + kg_lost);
- a zero denominator is null, never zero percent;
- kg is Decimal with three decimal places and ratios are Decimal with four decimal places;
- period queries are timezone-aware, half-open [from, to), and timeline buckets use America/Argentina/Buenos_Aires; and
- Pipeline is a current snapshot, not a period metric, and includes every OpportunityStatus, including PERDIDA.

The visual layer may format returned values for Spanish reading but does not recompute, round through JavaScript floating point, infer a ratio, or silently combine incompatible timestamp populations. Kilograms retain exact Decimal-oriented formatting with the kg unit and up to the API's three fractional places. Conversion cards format a non-null returned Decimal as a percentage with explicit numerator/denominator context. A null ratio says Sin oportunidades cerradas en el período, not 0%.

### Global filters and query application

The filter strip is compact and visually secondary: date period is always visible; source is visible when space permits; Product and province live under Más filtros; active selections have a clear count/context; and one Restablecer action returns the documented default. There is no seller/user filter.

| Filter | Contract and behavior |
| --- | --- |
| Period | Default: Este mes, from Buenos Aires local midnight on the first calendar day through the next month boundary. Presets are Este mes, Últimos 3 meses (from the first day two months before the current month through next-month boundary), and Este año. Personalizado selects inclusive calendar dates which the client serializes as [start 00:00, day-after-end 00:00) in America/Argentina/Buenos_Aires. The UI sends timezone-aware from and to values only. |
| Source | Uses the existing LeadSource values and is passed as source to all metrics endpoints. |
| Product | Uses existing Products, including inactive Products for historical analysis, and passes the positive product_id to all metrics endpoints. A Product with no matching period data is a truthful empty result. |
| Province | Offers normalized non-null province values returned by the current province aggregate for the other selected dimensions and passes the existing nonblank province query. Sin provincia remains an explicitly labelled chart row but is not an invented selectable filter because the current contract cannot request a null province. |

The same date/dimension selection is sent to /metrics/overview, /products, /sources, /provinces, and /timeline. /metrics/pipeline receives only shared source/product/province dimensions; it never receives from/to. Its container is labelled Pipeline actual with returned snapshot_at and No se filtra por período, so a date change does not imply it changed the snapshot. Dimension changes do refresh it.

Filter changes replace a single typed feature-filter object and cancel obsolete requests. The URL may own a shareable, validated representation of period and dimensions only if route implementation can do so without duplicating feature state; URL state is not a backend contract. Dashboard sends no raw search text or client-computed aggregation to metrics APIs.

### Existing endpoint use

| Existing endpoint | Dashboard use |
| --- | --- |
| GET /metrics/overview | KPI values and optional new-Opportunity attention summary. |
| GET /metrics/timeline | Commercial-evolution buckets at day or month granularity. The UI chooses day only within CRM-004's 366-bucket limit and otherwise requests month; a typed oversized-period error offers the supported coarser view rather than silently changing a custom range. |
| GET /metrics/pipeline | Current status distribution, with dimensions but no period. |
| GET /metrics/products | Product ranking and exact opportunity/kg/conversion evidence. |
| GET /metrics/sources | Source performance and conversion evidence. |
| GET /metrics/provinces | Ranked provincial activity plus kg and conversion context. |
| GET /notifications and GET /whatsapp/conversations | Bounded operational-attention evidence only; neither endpoint derives commercial metrics. |

## Visualizations and KPI hierarchy

### KPI proposal

The default has five high-value KPI surfaces, not a wall of interchangeable numbers:

1. Oportunidades creadas — overview opportunities.created, explicitly Creadas en el período.
2. Resultados cerrados — a compact paired Ganadas and Perdidas presentation, explicitly Cerradas en el período.
3. Conversión de oportunidades — returned opportunity conversion plus won/lost counts, or the explicit null state.
4. Kg cotizados — overview volume_kg.quoted, explicitly attributed to Opportunities created in the period.
5. Volumen ganado — returned volume_kg.won with secondary volume-conversion evidence and explicit null state where no terminal volume exists.

Cards use strong numeric hierarchy, concise labels, one meaningful supporting line, tabular figures, and no unsupported prior-period delta. Ganadas, Perdidas, and conversion use text and icon/label evidence in addition to restrained semantic green/red; FAA yellow is reserved for selected/current emphasis rather than every KPI.

### Commercial evolution

Evolución comercial is the primary visual. A compact SegmentedControl selects one clear measure group rather than overlaying unrelated measures:

- Oportunidades (default) is an accessible SVG line/area chart for Leads creados, Ganadas, and Perdidas. Its title and legend state that the created series uses creation date while terminal series use terminal-status entry date.
- Volumen renders only Kg ganados and Kg perdidos; the existing timeline has no quoted-kg series, so Dashboard does not invent one.

The chosen group may use a restrained primary area/line and semantic terminal lines; it never becomes a rainbow. Hover and keyboard focus reveal an exact bucket tooltip. The chart has a compact legend, readable labels at the selected granularity, and an adjacent or collapsible semantic table with the same dates and values. The table is the assistive-technology and narrow-layout equivalent, not a lesser data set.

### Conversion and Pipeline

Conversión uses a restrained ring only when won + lost is nonzero. Its centre and nearby text show the returned percentage plus absolute won/lost values; segment labels and a list make it understandable without colour. With no closed Opportunities it shows the clear null state and no misleading filled circle. Volume conversion is supporting KPI evidence, not a competing second donut.

Pipeline actual uses one compact labelled horizontal segmented bar or stage-block row, not a miniature Kanban. It includes the API's NUEVA, COTIZADA, NEGOCIACION, GANADA, and PERDIDA counts. Labels, order, counts, and an accessible list communicate status independently of colour; GANADA may use success and PERDIDA restrained destructive evidence. It does not imply that Lost belongs in the CRM-019 main Kanban or that selected date period applies.

### Products, sources, and provinces

- Productos is a ranked horizontal-bar list by backend-returned kg_quoted, with readable Product labels and each row's exact quoted kg plus quoted-Opportunity count. The API already orders this dimension by quoted kg and product ID. It may show won-kg/conversion as secondary row detail, but does not add a noisy measure toggle or pie chart for many Products.
- Origen uses compact bars for created Opportunities and a text conversion label where the returned denominator exists. It uses source names, values, and markers in addition to categorical colour; a donut is not required merely because current category count is small.
- Actividad por provincia is initially a ranked horizontal-bar/list visualization, ordered by Opportunities created with clear values and secondary won/kg/conversion context. It includes a clearly named Sin provincia group when returned. This answers which provinces generate activity without pretending data has geographic coordinates.

An Argentina map is deliberately not part of the initial Dashboard. A map may be proposed in a later approved change only with a maintained Argentina-only boundary asset, token-compliant interaction, province mapping demonstrably exact, no external runtime map service, and the same ranked list/table alternative. A donut alone is never sufficient for provincial insight.

### Chart visual system and interaction

All charts consume CRM-018 chart tokens: semantic gridline, axis, tooltip, reference-line, categorical, sequential, divergent, selected, and muted mappings. FAA yellow is the selective primary-highlight/current-selection colour; semantic green/red and restrained neutral series are secondary. Light and Dark mappings independently preserve intended contrast. Gridlines are quiet, labels remain legible, tooltips include title/value/unit/period, and selected/focused data is identifiable by more than colour.

Interactive data points are keyboard reachable only when they offer meaningful detail or action; Tab order follows chart reading order, arrow-key movement follows a documented SVG/composite-widget pattern, and Escape returns from an open tooltip/popover when safe. If a chart offers a meaningful filter suggestion, selecting it applies the documented global filter with visible active state and reset; it never introduces a hidden drilldown or unsupported backend query. Ordinary hover never traps focus or becomes the only way to learn a value.

## Loading, refresh, motion, responsiveness, and accessibility

### States and perceived speed

Initial load uses a Dashboard skeleton whose KPI, attention, and chart surfaces reserve final geometry; no giant page spinner replaces the workspace. Requests are bounded and can run in parallel by independent concern: overview/timeline/dimensions, current Pipeline, and operational attention. A failure in one chart remains local with concise cause/retry and does not blank last-good Dashboard data.

During filter/background refresh, current values remain visible with a subtle updating state. New results replace the relevant surface only after they are coherent with active filters; aborted or stale responses cannot overwrite newer selections. Routine notification/polling work does not reanimate every chart or reorder the page. Mutation is not a Dashboard responsibility.

Every surface distinguishes no data in period, filter-produced no match, null denominator, endpoint failure, and unavailable operational evidence. Empty lists use concise explanatory copy and reset/retry where useful, never fake zeros, decorative illustrations, or fabricated forecasts.

### Motion

Dashboard may be richer than operational CRM screens while retaining CRM-018's fast, functional motion: 150–220 ms micro-feedback, and at most 240 ms for chart entry. KPI values may transition once from previous authoritative values; charts may reveal selected series progressively; filters may crossfade unchanged geometry; and hover/focus may emphasize focused datum. Motion uses opacity/transforms or GPU-friendly SVG presentation, never layout thrashing, bouncing, loops, or delay before values are readable.

prefers-reduced-motion: reduce makes KPI and chart data immediately available, removes spatial/path-drawing transitions, and retains only minimal non-blocking state-change feedback. No chart animation restarts merely because routine polling refreshed an unrelated operational summary.

### Responsive and zoom behavior

Dashboard is desktop/laptop first and follows CRM-018's 1024 CSS-pixel supported working area and common browser-zoom contract. It responds to actual main-content container after expanded/collapsed sidebar space, not fixed device labels:

- KPI cards flow from five compact surfaces to fewer columns and then a logical stack; type never becomes unreadably small.
- The primary evolution chart keeps a practical minimum inline size; conversion and Pipeline move below it before labels collide. Product/source and province pairs become one column.
- Chart legends move above/below data or reduce to labelled rows; long Product/province labels wrap/truncate with a full accessible name. The semantic list/table alternative remains reachable.
- The page has no horizontal overflow. Any genuinely wide exact-data table lives in a labelled, locally scrollable region with sticky/readable headers; page scrolling stays vertical. Filters wrap in reading order and Más filtros remains accessible.

This is not a mobile-native product redesign. At constrained widths, stacking and table/list alternatives preserve analytical answers rather than shrinking charts into unreadability.

### Accessibility

Dashboard targets CRM-018 and WCAG 2.2 AA where applicable. It uses landmark and heading hierarchy, semantic buttons/links/forms, visible focus, contrast in each theme, accessible names for icon controls, logical focus order, practical pointer targets, and status/error text that is never colour-only. A skip link reaches Dashboard main content.

Every KPI has a screen-reader name/value/unit/context. Every chart surface includes a title, selected-filter/period context, textual conclusion or summary, legend/list, and exact table/list alternative. Canvas-only core data is prohibited; an SVG/chart-library implementation still must expose meaningful equivalent HTML. Tooltips, updates, and errors use appropriate live regions without announcing whole chart datasets on initial render. Reduced motion, browser zoom, text enlargement, and keyboard-only data access are mandatory.

## Chart technology decision

Dashboard uses focused custom SVG/DOM charts. Simple ranked bars, Pipeline stage
blocks, legends, and exact values use semantic HTML/CSS where that is clearer; the
timeline and conversion ring use limited feature-owned SVG compositions. CRM-018 owns
the shared chart surface, token, loading, error, legend, and exact text/table-alternative
contract, not a generic chart builder.

Do not install `@visx`, Recharts, or another chart library for Frontend 2.0. The
Dashboard chart set is deliberately narrow, and its required accessible summaries,
keyboard behavior, and exact table/list alternatives remain FAA-owned regardless of a
rendering library. Reconsider this decision only if measured implementation complexity,
accessibility evidence, or route-chunk/bundle evidence shows that the limited custom
approach cannot meet this spec without greater maintenance or user cost. Any such later
change requires a separately approved amendment; no mixed chart stacks, canvas-first
runtime, external chart/map API, or incidental dependency is permitted.

## Frontend architecture, security, and performance

- Route-level composition adds Dashboard route/page within the existing App.tsx routing model and App Shell. A Dashboard feature hook owns filter state, request cancellation, last-good projections, and error translation; visual components receive typed data/callbacks and never call APIs or calculate commercial definitions.
- frontend/src/api/metrics.ts is typed owner of metrics contracts; notification and WhatsApp API modules remain their own typed owners. Shared primitives and chart containers live under frontend/src/shared; Dashboard-specific compositions stay in a Dashboard feature directory. No global store is introduced.
- Use existing aggregated endpoints only. Never download Opportunities, quotes, or conversations merely to construct a Dashboard chart, issue per-card requests, or perform N+1 frontend enrichment.
- Abort obsolete filter requests, preserve prior data during refetch, avoid full-page rerenders for one chart error, and profile before adding memoization, virtualization, code splitting, or a chart dependency. Lazy-load selected chart code only when bundle analysis justifies it; charts must not degrade Pipeline, Inbox, or primary input responsiveness.
- Existing authentication/session handling, same-origin API use, role permissions, CSP, and no-secret browser policy remain unchanged. Dashboard creates no persistence, API, provider, authentication, authorization, or business-state contract.

## Edge cases

- A custom range always serializes an aware Buenos Aires half-open period; invalid, reversed, unsupported, or oversized timeline ranges surface typed backend error and keep last good result until corrected.
- Date changes do not make current Pipeline snapshot appear historical. Dimension filters affect it only as existing API allows.
- Null province remains visible in provincial results but cannot become a false province=null filter. Inactive Products remain available for historical analysis.
- A failed attention query never changes metric values, and a successful refresh never marks notifications or conversations read/resolved.
- A chart with no data, null conversion denominator, and failed request are visually/textually distinct. Long Spanish labels, 200% zoom, theme changes, and reduced motion cannot obscure values or cause page-level horizontal overflow.
- Filter response/version that produced chart, tooltip, table, and active-filter label stays consistent; stale responses and routine polls do not steal focus.

## Acceptance criteria

- AC-01: /dashboard follows the documented attention-first hierarchy and CRM-018 App Shell/theme/component rules without becoming a decorative BI wall.
- AC-02: Operational attention uses only existing notification/WhatsApp/overview evidence, shows exact totals only where API provides them, and never creates a false deep link, read, resolution, or conversation mutation.
- AC-03: Five compact KPI surfaces present created, won/lost, opportunity conversion, quoted kg, and won-volume/conversion context with correct Decimal/null treatment and no vanity delta.
- AC-04: Period, source, Product, and supported province filters use compact/resettable CRM-018 controls, date presets serialize aware Buenos Aires half-open periods, and no seller filter exists.
- AC-05: All period metrics receive same documented filters; Pipeline receives only dimensions and is visibly identified as an unfiltered-by-date current snapshot.
- AC-06: Commercial evolution uses only timeline measures at valid day/month granularity, exposes exact data/legend/table equivalents, and clearly states different timestamp semantics of created and terminal series.
- AC-07: Conversion displays absolute won/lost evidence plus percentage without a misleading ring or zero when its denominator is null.
- AC-08: Pipeline visualization represents every authoritative current status without recreating Kanban or implying PERDIDA is a main Pipeline column.
- AC-09: Product, source, and province surfaces use documented ranked/bar models, preserve inactive/null-province history appropriately, and do not use decorative pie charts or inferred geography.
- AC-10: Geographic insight is an accessible ranked provincial list/bar with no map or external runtime geographic dependency in this scope.
- AC-11: Charts use CRM-018 semantic chart tokens in Light and Dark, FAA yellow only selectively, and non-colour labels/legends/selected evidence.
- AC-12: Dashboard motion is short, functional, non-looping, non-blocking, and fully reduced-motion safe; routine refresh does not replay unrelated chart animation.
- AC-13: Initial, independent refresh, no-data, no-match, null-denominator, API-error, and unavailable-attention states are scoped, distinct, preserve last-good content during refresh, and avoid routine full-page spinners.
- AC-14: Available-space grids, chart/table fallbacks, sidebar interaction, and 200% zoom preserve readable data with no page-level horizontal overflow.
- AC-15: KPI/chart data and controls meet documented keyboard, focus, textual equivalent, semantic HTML, contrast, live-region, and WCAG 2.2 AA requirements.
- AC-16: Frontend consumes only aggregated typed APIs, bounds/cancels concurrent work, avoids N+1 data loading/unnecessary chart rerenders, and keeps core CRM work responsive.
- AC-17: Dashboard remains within React/Vite/TypeScript/Tailwind shared/feature/API/route ownership boundaries and introduces no global state library.
- AC-18: Dashboard uses the documented focused custom SVG/DOM approach; no chart
  library, unmeasured heavy/mixed chart stack, canvas-first runtime, or external chart/
  map API is introduced unless later measured evidence and an approved amendment require it.

## Open decisions

None

## Follow-up / future specs

- CRM-022 — Notifications: owns any Dashboard-to-Notifications filter/deep-link contract and notification workspace implementation.
- CRM-023 — WhatsApp Inbox 2.0: may own a Dashboard-to-Inbox waiting/unread selection handoff without changing cursor/list contract.
- CRM-026 — Final Accessibility & UX Polish: verifies cross-workspace chart and Dashboard accessibility conformance without weakening CRM-018.

## Implementation notes

Implement only after this Draft is approved. Start with typed API-contract tests based on
CRM-004 responses and isolated Dashboard component/feature-hook tests for filters, null
values, stale requests, summaries, and accessible custom SVG/DOM data alternatives.
Preserve existing frontend architecture and backend-authoritative metric definitions; do
not make a dependency, state-management, map, or backend-contract change incidental to
visual work.
