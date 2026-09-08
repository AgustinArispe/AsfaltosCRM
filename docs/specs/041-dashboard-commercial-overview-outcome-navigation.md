# CRM-041 — Dashboard Commercial Overview and Outcome Navigation

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-08
Implementation commit: N/A

## Goal

Redesign the commercial Dashboard so a supervisor can understand the selected period
in a few seconds: what needs attention now, how the period performed, how many active
Opportunities exist, how many outcomes and kilograms were won or lost, what the two
conversion rates mean, where Opportunities originated, and how to open the matching
Ganadas or Pérdidas workspace directly.

The Dashboard must read as one ordered commercial story, not as a uniform grid of KPI
cards and charts.

## Context and authority

`docs/BUSINESS_RULES.md` is authoritative for active stages, terminal outcomes,
stale notifications, Decimal kilograms, and conversion formulas. CRM-004 supplies the
current metrics family; CRM-038 supplies the resource/request boundaries; CRM-039
supplies the Ganadas route and period-query contract; CRM-040 supplies the stronger
commercial typography direction.

Repository inspection found an important post-CRM-012 mismatch. Current metric
outcomes are projections of an Opportunity's **current** terminal state and
`current_status_entered_at`. Pérdidas, however, has immutable loss events and quote
snapshots, including reopened and repeated-loss episodes. CRM-041 makes selected-period
results event-historical so the Dashboard does not erase a valid loss after reopening
or calculate lost kilograms from a later current quote.

This Draft is the Phase 1 deliverable. It does not authorize implementation until its
status is explicitly changed to `Approved`.

## Dependencies

- CRM-003 — Stale Opportunity Notifications
- CRM-004 — Commercial Metrics
- CRM-007 — WhatsApp Inbox Query Layer
- CRM-012 — CRM Commercial Completion
- CRM-018 — Frontend Design System
- CRM-021 — Dashboard & Metrics
- CRM-022 — Notifications UI
- CRM-023 — WhatsApp Inbox 2.0
- CRM-024 — Customers, Products and Lost UI
- CRM-028 — Visual Clarity & Dashboard Simplification
- CRM-029 — Brand, Dashboard & Interaction Polish
- CRM-038 — Frontend Interaction and Data Synchronization
- CRM-039 — Won Opportunity History and Active Pipeline Retention
- CRM-040 — Pipeline and Opportunity Workspace Hierarchy

## A. Current Dashboard hierarchy diagnosis

### Page hierarchy and displayed sections

`DashboardPage` currently renders, in DOM order:

1. a filter toolbar with `Período`, always-visible `Origen`, a `Filtros` details
   disclosure for `Producto` and `Provincia`, optional custom `Desde`/`Hasta`,
   `Restablecer`, and `Actualizar`;
2. an oversized navy attention block titled `Lo que necesita seguimiento ahora`;
3. five equal KPI cards;
4. a primary two-column area with `Evolución comercial` and the navy
   `Resultados cerrados`/`Distribución vigente` cluster;
5. one tabbed commercial-distribution surface with `Productos`, `Origen`, and
   `Provincias`.

The AppShell owns the visible page identity/navigation; `DashboardPage` itself has no
page-title heading. The current sequence roughly starts with attention but gives
attention, five KPI tiles, conversion/outcome composition, Pipeline, and all dimension
analyses similar surface weight. The user must reconcile repeated values across the
page before understanding the month.

### Current labels, tabs, charts, and behaviors

- Attention labels are `Seguimientos pendientes`, `Notificaciones sin leer`, and
  `Conversaciones esperando`, with `Ver seguimientos`, `Revisar notificaciones`, and
  `Abrir WhatsApp` actions.
- KPI labels are `Oportunidades creadas`, `Resultados cerrados`, `Conversión`,
  `Kg cotizados`, and `Volumen ganado`.
- Timeline heading is `Evolución comercial`, with context `Altas por creación;
  resultados por cierre.` and mutually exclusive tabs `Creadas`, `Ganadas`, and
  `Perdidas`.
- The timeline is a single-series vertical bar chart. For daily buckets, a nonzero bar
  opens a bounded day-detail dialog-like region on click or focus. Monthly bars are not
  drillable. The exact-data disclosure contains Created, Won, Lost, kg won, and kg
  lost simultaneously even though the chart hides two series.
- `Resultados cerrados` repeats won/lost and opportunity conversion in a large donut.
- `Distribución vigente` renders a stacked Pipeline bar and list. Its frontend notion
  of active currently includes `NUEVA`, `COTIZADA`, `NEGOCIACION`, **and `GANADA`**;
  `PERDIDA` is omitted. This conflicts with the operational active-stage definition
  after CRM-039.
- The dimensions control shows exactly one of `Productos por volumen cotizado`,
  `Origen de oportunidades`, or `Provincias por oportunidades creadas`. Products and
  Provinces use ranked horizontal bars; Origin uses a donut. Exact tables are available
  under disclosures. Visual top-N grouping can produce `Otras`, while exact tables
  retain all categories.

### Loading, errors, empty state, refresh, responsive, and theme

- First load replaces all content below filters with one page skeleton. Subsequent
  refresh retains prior values and announces `Actualizando Dashboard.` in an `aria-live`
  region.
- The five period metrics use `Promise.allSettled`; a failed chart retains its last
  successful value and shows a local status error. A missing overview becomes a full
  KPI unavailable state. Pipeline and attention fail independently.
- Empty timeline and dimension states distinguish active filters from general absence.
  Conversion `null` renders `Sin oportunidades cerradas`, not `0 %`.
- The timeline plot may horizontally scroll because its minimum width grows with bucket
  count. Existing page-level browser tests assert no document overflow at desktop,
  tablet-like sizes, 390 × 844, and effective 150% zoom.
- Responsive CSS reduces primary grids and KPI columns progressively; at narrow widths
  semantic DOM order is retained and donut layouts stack. The current five-card grid
  can create awkward wrapping and disproportionate tile weight.
- Dashboard colors are token-based and have Light/Dark browser baselines. CRM-041 must
  preserve token contrast and Dark functionality only for touched surfaces; it is not
  a Dark redesign.

### API/resource dependencies after CRM-038

Initial Dashboard entry currently requests:

- 5 period/dimension metrics: `/metrics/overview`, `/products`, `/sources`,
  `/provinces`, `/timeline`;
- 1 dimension-only current snapshot: `/metrics/pipeline`;
- 1 shared product catalog request: `/products?include_inactive=true`;
- 1 unresolved-notification total request from Dashboard;
- 1 AppShell unread-active notification total, reused as the Dashboard unread value;
- 1 WhatsApp cursor-page request with `waiting_only=true&limit=1`.

A period-only change makes exactly five period metric requests. A source/product/
province change makes those five plus Pipeline. Product catalog, notification evidence,
and WhatsApp evidence are independent and do not refetch for filter changes. Manual
`Actualizar` currently refetches all Dashboard-owned resources, including attention,
but not the AppShell-owned unread total.

### Hierarchy diagnosis

The strongest commercial answer—won/lost count and kilograms—has no dedicated coherent
section. Won appears in the KPI row and again in the donut; lost count appears inside
`Resultados cerrados` twice but lost kilograms only in hidden exact tables. Created,
quoted volume, conversion, and stage composition compete at the same level. Attention
is a large navy module even when every count is zero. Origin, which answers a primary
acquisition question, is hidden behind a tab initially defaulted to Products.

## B. Exact semantics of every current metric

All period contracts require timezone-aware `from` and `to`, convert them to UTC, and
apply a half-open `[from, to)` interval. The Dashboard generates Buenos Aires local
midnight boundaries with the literal `-03:00` offset. Timeline buckets explicitly use
`America/Argentina/Buenos_Aires`. PostgreSQL stores timezone-aware timestamps and the
application persists UTC.

Dimension filters are source, product, and normalized province. Soft-deleted
Opportunities are excluded. A product filter restricts Opportunity counts by existence
of that product but restricts volume sums to that product's line. Province comparison
trims and lowercases. Inactive Products remain valid historical dimensions.

| Current metric | Exact implementation semantics | Business question / assessment |
| --- | --- | --- |
| `opportunities.created` | Count of non-deleted Opportunities whose `created_at` is in the selected period after dimensions. Current status is irrelevant. | “How many Opportunities entered the CRM in this period?” Clear and useful, but not a primary outcome. |
| `opportunities.open` | Count currently in `NUEVA`, `COTIZADA`, or `NEGOCIACION` **and created in the selected period**. | “How many Opportunities created in this period remain open now?” The label is not displayed; it is not the requested all-current active total. |
| `opportunities.won` | Count currently `GANADA` whose current `current_status_entered_at` is in the period. | “How many currently won Opportunities entered GANADA in the period?” Safe because GANADA cannot reopen, but based on mutable Opportunity rows rather than history. |
| `opportunities.lost` | Count currently `PERDIDA` whose latest `current_status_entered_at` is in the period. | “How many currently lost Opportunities entered their latest loss in the period?” It omits reopened prior episodes and cannot represent repeated losses. |
| opportunity conversion | Backend Decimal `won / (won + lost)`, quantized to four places; `null` for zero denominator. | The formula is correct, but current-state outcome inputs make historical reopened losses disappear. Displayed in KPI, result heading, and donut. |
| `volume_kg.quoted` | Sum of current/final `OpportunityProduct.quantity_kg` lines for Opportunities created in the period, regardless of status. With a product filter, only that product's line is summed. | “What current/final quote volume belongs to Opportunities created in the period?” No quote-version history exists. Current label `Kg cotizados` omits this scope and can change after the period. |
| `volume_kg.open` | Sum of current quote lines for Opportunities currently `COTIZADA` or `NEGOCIACION` and created in the period. `NUEVA` has no quote and is excluded. | “How many quoted kg from this cohort remain open?” Not displayed. |
| `volume_kg.won` | Sum of current/final quote lines on currently GANADA Opportunities whose terminal-entry timestamp is in period. | “How many current quote kg were won in the period?” Stable under current terminal rules and displayed prominently. |
| `volume_kg.lost` | Sum of **current** quote lines on currently PERDIDA Opportunities whose latest status-entry timestamp is in period. | It does not use `OpportunityLossEvent.quoted_total_kg`; reopened loss episodes disappear and historical snapshot integrity is lost. Currently visible only in the exact timeline table and dimension payloads. |
| volume conversion | Backend Decimal `kg_won / (kg_won + kg_lost)`, four places; `null` for zero kg denominator. | Formula is authoritative, but the same loss-history defect affects the denominator. Displayed as footer under won volume. |
| Pipeline snapshot | Current count of every Opportunity status at request time, no date period; accepts dimensions. Backend returns all five statuses. | Correct source for “What exists now?” Current UI incorrectly sums GANADA into “Pipeline activo.” |
| Product distribution | Per current Product line: distinct Opportunities and kg whose Opportunity was created in period; current-state won/lost counts and kg by terminal-entry period; conversions from current terminal rows. Ordered by quoted kg. | Current visual uses only kg quoted plus number quoted. Useful secondary demand mix, but “quoted” means current/final quote on period-created Opportunities. |
| Origin distribution | Group by current `Opportunity.source`; Created uses `created_at`, Won/Lost use current terminal state and entry time; source conversion uses won/(won+lost). | Created count directly answers origin. Percentage shown in donut is frontend-created over returned Created counts and is not returned by backend. |
| Province distribution | Group by current `Customer.province`, including `null`; created count/current quote kg use creation period, outcomes use current terminal entry. Soft-deleted Customers' valid Opportunities remain; deleted Opportunities do not. | Current visual uses created count and quotes/conversion as detail. Province is a current Customer field, not an immutable creation snapshot. |
| Timeline Created | Zero-filled count by Buenos Aires day/month of `Opportunity.created_at`. | Valid evolution series. |
| Timeline Won/Lost/kg | Zero-filled current terminal rows by Buenos Aires day/month of `current_status_entered_at`; lost kg uses current quote lines. | Won is valid; Lost and lost kg do not preserve reopened episode history. |
| Stale/follow-up | Total unresolved notifications of the sole type `OPPORTUNITY_STALE`; generation requires a non-deleted Opportunity in the three active stages with `current_status_entered_at <= now - 14 days`. Editing assignee/quote does not resolve it; stage change does. | Exact count of generated unresolved follow-ups. It depends on the notification generation job having run; it is not an on-read stale query. Actionable. |
| Unread notifications | AppShell count requests unresolved and unread notifications. Since the only type is stale, this is a subset of the stale count. | Answers acknowledgement state, not a distinct commercial risk; duplicated in Attention. |
| WhatsApp waiting | Persisted `WhatsAppConversation.waiting_for_response`; current Dashboard only checks whether a page of size 1 has an item. | Answers only “does any waiting conversation exist?”, never the total. Current `Hay` presentation has inappropriate KPI-like weight. |

## C. Duplicate and unclear metrics

- Won/lost counts occur in `Resultados cerrados` KPI and again in the result donut.
- Opportunity conversion occurs as a KPI, a result-cluster context line, and the donut
  proportion.
- Volume conversion is attached to won kg even though its denominator also includes
  lost kg, which is absent beside it.
- Created is a KPI, a timeline series, and the denominator of Origin. These are valid
  only when each representation answers total, change over time, and composition;
  current equal weight obscures that distinction.
- Active stage distribution and the Pipeline board answer related questions; the
  Dashboard needs only a compact snapshot plus explicit board link.
- `Kg cotizados` is ambiguous because it is current/final quote volume for a cohort
  created in the period, not quote events during the period. It must leave the primary
  hierarchy and be renamed when shown.
- `Seguimientos pendientes` and `Notificaciones sin leer` overlap the same notification
  population. CRM-041 removes unread notifications from Dashboard attention and leaves
  acknowledgement evidence in AppShell/Notifications.
- The outcome donut adds no question beyond the exact won/lost counts and conversion;
  it is removed.
- Origin must not be repeated as both donut and bars. It becomes one direct ranked list.

## D. Attention-now redesign

Render a compact section headed `Necesita atención` above the result section. It is a
neutral, low-height list/strip, never a navy hero and never a three-card KPI grid.

1. `X oportunidades sin seguimiento` uses the exact unresolved stale-notification
   total. Supporting text states `14 días o más sin cambio de etapa`. Its explicit
   `Ver seguimientos` link opens `/notifications?view=active`.
2. `X conversaciones pendientes de respuesta` uses the authoritative WhatsApp
   aggregate defined below. If nonzero and an oldest timestamp exists, supporting text
   may say `La más antigua espera …`; this is presentation-relative time derived from
   the server timestamp, not a new SLA. `Abrir pendientes` opens
   `/whatsapp?waiting=true`.

Zero policy is deterministic:

- if both values are successfully zero, collapse the rows into one calm compact state,
  `Sin pendientes urgentes`, with no large colored surface;
- a zero item is hidden when the other item is nonzero;
- a failed resource keeps any last successful value with a local unavailable marker;
- if no prior value exists, show one compact unavailable row without converting `—`
  into zero;
- unread notification count does not appear in Dashboard.

The section must not mark notifications read, resolve notifications, mark conversations
read, or mutate waiting state.

## E. Selected-period result design

`Resultado del período` is the strongest commercial summary immediately after
Attention. Its heading includes a readable applied-period label. One grouped surface,
not five equal cards, presents two outcome columns and a compact conversion region:

- `Ganadas`: count plus `Kg ganados`, with explicit `Ver ganadas` link;
- `Pérdidas`: loss-episode count plus `Kg perdidos`, with explicit `Ver pérdidas` link;
- `Conversión de oportunidades`: `ganadas / (ganadas + pérdidas)`;
- `Conversión de volumen`: `kg ganados / (kg ganados + kg perdidos)`.

The count/kg pairs have the strongest numeric scale. Conversion is visibly secondary
but remains in the same result context. Each conversion exposes its denominator in
visible supporting text or an accessible description. A zero denominator renders
`—` and `Sin resultados cerrados en el período`; it never renders `0 %`. A nonzero
denominator with zero wins correctly renders `0 %`.

Selected-period result semantics are outcome-event historical:

- won count is the number of non-deleted Opportunities whose one terminal GANADA entry
  occurred in `[from, to)`; won kg is the final current quote total for those wins;
- lost count is the number of `OpportunityLossEvent` rows in `[from, to)` belonging to
  non-deleted Opportunities; lost kg is the sum of their immutable
  `quoted_total_kg` snapshots;
- a loss from `NUEVA` legitimately contributes one loss and `0.000 kg`;
- reopening never removes a prior period loss; a later repeated loss is another outcome
  episode and contributes again in its own period;
- dimensions apply to historical loss snapshots: event `source`, normalized
  `customer_province`, and `OpportunityLossProductSnapshot.product_id`. They must not
  be evaluated against later mutable Opportunity/Customer/quote values;
- won dimensions keep CRM-039's current won-history contract because GANADA is terminal
  and its quote cannot be edited.

For precision in UI copy, the loss figure's accessible description says `episodios de
pérdida` when a repeated/reopened case affects interpretation. The visible commercial
label remains `Pérdidas`.

## F. Active Opportunities design

`Oportunidades activas ahora` is a current snapshot, visually and semantically separate
from `Resultado del período`. It uses `/metrics/pipeline` and includes exactly:

- `NUEVA`;
- `COTIZADA`;
- `NEGOCIACION`.

`GANADA` and `PERDIDA` are terminal and excluded. The section shows one total plus the
three stage counts and a compact labelled stacked bar or proportional list. Every stage
has visible text/count; color is supplementary. `Ver Pipeline` opens `/pipeline`.

Date changes do not affect or request this section. Source/product/province dimensions
do affect it, matching CRM-038. The label adds `con los filtros actuales` when a
dimension is applied and exposes the snapshot time as secondary metadata. A zero total
uses the calm text `No hay oportunidades activas ahora`; it does not reserve a large
empty chart.

## G. Evolution design

Replace the Created/Won/Lost tabs and single-series bars with one combined comparison
chart titled `Evolución comercial`. It displays Created, Won, and Lost together for
every bucket. Use three line series with visible point shapes and distinct line styles,
or grouped bars if implementation evidence shows line labels cannot remain legible;
the exact values and series names remain visible in a compact legend/summary and in the
existing disclosure table. Color alone may not distinguish series.

Granularity is deterministic:

- inclusive visible ranges of 1–14 calendar days: `day`;
- 15–120 calendar days, including the default month and Últimos 3 meses: `week`;
- 121 days or more, including Este año: `month`.

Week buckets are anchored to Monday in `America/Argentina/Buenos_Aires`, include every
week intersecting `[from, to)`, and count only events inside the requested half-open
period. The first/last bucket may be partial and its accessible label states its actual
intersection dates. Empty buckets are zero-filled. This requires only a `week`
extension to the existing timeline contract, not a new analytics engine.

Created follows Opportunity creation. Won and Lost follow the event-historical result
semantics from section E; loss kg comes from event snapshots. The exact table keeps
Created/Won/Lost and won/lost kg for all buckets. Day detail remains only for daily
buckets; weekly/monthly chart points are not deceptively clickable. Day-level Lost
detail must use loss-event evidence so reopened loss events remain discoverable.

## H. Origin, Products, and Province design

### Origin

`Origen de oportunidades` follows Evolution and answers `¿De dónde vienen nuestras
oportunidades?` with direct horizontal bars/list, sorted by Created count descending,
then stable source order. Each row shows source, count, and percentage of all
selected-period **created Opportunities after the other applied dimensions**. The
denominator is the sum of returned source Created counts and equals overview Created
under the same filters. Zero denominator renders a compact no-data state. No donut is
used. Percentages may be calculated for display from authoritative integer buckets,
but the denominator and rounding rule must be centralized and tested; commercial counts
and rates remain backend-calculated.

If `source` itself is selected, the single matching origin correctly shows 100% and the
section says it is filtered; it is not mistaken for overall acquisition share.

### Products and Provinces

Products and Provinces are secondary analysis below Origin. Use one compact secondary
surface with a single `Productos`/`Provincias` segmented control, avoiding deeper tab
nesting.

- Products default to ranked `Kg cotizados actuales de oportunidades creadas en el
  período`, with `oportunidades cotizadas` as supporting count. This preserves the
  exact no-quote-history semantics and removes ambiguous `Kg cotizados` from primary
  KPIs. Inactive historical Products remain visible.
- Provinces default to `Oportunidades creadas en el período`, with the current/final
  quote kg only as secondary detail. `Sin provincia` remains a truthful category.
- Both sort by displayed magnitude descending and retain exact-data disclosures for all
  categories if top-N visual grouping is used.
- A genuinely empty selected dimension collapses to a small explanatory row; it never
  consumes a permanent chart-sized panel. One populated category uses one readable row,
  not a decorative full chart.

CRM-041 does not promote Product or Province outcome conversion because current
contracts mix mutable dimensions with terminal history. Correct event-level dimensional
outcome analytics is outside this overview's primary question.

## I. WhatsApp waiting decision

### Verified current semantics

`waiting_for_response=true` is a persisted projection, not a query-time guess. It is
true when at least one inbound message timestamp (`provider_message_at`, falling back
to `created_at`) is later than the last **valid human outbound response**. The valid
outbound timestamp is maximum `accepted_at` where direction is OUTBOUND, origin is
HUMAN, `sent_by_user_id` exists, dispatch state is `ACCEPTED`, and provider state is not
`FAILED`. `waiting_since_at` is the earliest such unanswered inbound timestamp.

- `PENDING`, `IN_PROGRESS`, and `UNKNOWN` human outbounds do not clear waiting.
- `DEFINITIVE_FAILED` does not clear waiting.
- `ACCEPTED` human outbound clears older inbound waiting unless a later provider
  `FAILED` status invalidates it, in which case projection recomputation restores the
  earliest unanswered inbound.
- Broadcast-origin outbounds never count as a human response.
- A late-arriving inbound webhook whose provider timestamp precedes the last valid
  human response does not reopen waiting.
- Inbox order is waiting first, then unread count, then last message time, then ID,
  all descending; cursor ordering preserves that order.
- The current Dashboard request is exactly a cursor page with `waiting_only=true` and
  `limit=1`; the response has no aggregate total, so it proves only a boolean.

### CRM-041 decision

Add a focused authenticated read aggregate:

```text
GET /api/whatsapp/conversations/attention-summary
{
  "waiting_count": <integer>,
  "oldest_waiting_since_at": <aware datetime|null>
}
```

It performs SQL `count(*)` and `min(waiting_since_at)` over persisted
`waiting_for_response=true` conversations. Zero returns `0` and `null`. It neither
loads conversation graphs nor recomputes/mutates projections. This is smaller and
cheaper than adding an always-paid total to every cursor-paginated Inbox response and
does not duplicate an existing aggregate contract.

## J. Backend/API changes required

1. Extend the focused existing metrics projections (`overview`, `products` where
   retained, `sources`, `provinces` where retained, and `timeline`) only as necessary
   so selected-period Lost outcomes use `OpportunityLossEvent` and immutable snapshots.
   Do not expose frontend-computed commercial aggregates.
2. Extend `TimelineGranularity` and `/metrics/timeline` with `week`; retain `day` and
   `month` compatibility and existing bucket limits with an explicit bounded weekly
   maximum.
3. Extend `/metrics/timeline/day-opportunities` Lost series to project loss-event rows
   rather than only currently PERDIDA Opportunities. Its response needs a stable
   `loss_event_id` or typed outcome identifier when required to distinguish repeated
   episodes; Created/Won remain backward compatible.
4. Add the focused WhatsApp attention summary above.
5. Add query-state parsing/serialization to the existing Pérdidas frontend route;
   backend `lost_from`/`lost_to` already exist and are half-open aware filters.
6. Add minimal filter-query parsing to Notifications active view and WhatsApp waiting
   view so Attention actions land on the represented population.

No schema or Alembic migration is required. `OpportunityLossEvent` already stores
`lost_at`, event source, province snapshot, total quoted kg, and a one-to-many Product
snapshot. Won history already has current terminal timestamp and quote totals.

Compatibility requirement: contract fields currently consumed outside Dashboard must
not silently change meaning. If changing existing `overview`/timeline loss fields would
break a documented CRM-004 consumer, add explicitly named outcome fields within those
focused responses and migrate Dashboard to them; do not return two differently defined
values under one name.

## K. Period and navigation contract

Dashboard keeps exactly the established presets:

- `Este mes`: Buenos Aires first day through next-month boundary;
- `Últimos 3 meses`: first day two months before current month through next-month
  boundary;
- `Este año`: January 1 through next-month boundary, matching current convention;
- `Personalizado`: visible inclusive calendar start/end serialized as Buenos Aires
  local midnight and next midnight after the visible end.

Invalid/incomplete custom ranges do not issue a request until both dates form a valid
nonempty interval. The applied period, not an unsubmitted draft, drives content and
outcome links.

Exact outcome links:

- Ganadas: `/won?period=<month|three-months|year|custom>&from=YYYY-MM-DD&to=YYYY-MM-DD`
  with `from`/`to` required for custom and allowed explicitly for deterministic handoff.
  Dashboard `last-three-months` maps to CRM-039's `three-months`.
- Pérdidas: `/lost?period=<month|three-months|year|custom>&from=YYYY-MM-DD&to=YYYY-MM-DD`
  using the same visible inclusive dates. Pérdidas serializes these to aware Buenos
  Aires `lost_from` inclusive and next-local-midnight `lost_to` exclusive; it must stop
  serializing new period links with `Z`.

Safe supported dimensions (`source`, `product`, `province`) are appended only where the
destination already has the equivalent backend filter. Ganadas uses CRM-039 keys.
Pérdidas gains equivalent validated query parsing for those existing filters. No
responsible filter is invented. Unknown/invalid values are ignored and canonically
replaced. The explicit visible links are `Ver ganadas` and `Ver pérdidas`; outcome
surfaces may additionally be clickable only if the explicit link remains keyboard and
screen-reader discoverable.

Pérdidas' existing list continues to show the latest episode for currently PERDIDA
Opportunities; its historical statistics already count all filtered loss events.
CRM-041's period handoff must make the historical summary visibly authoritative for the
linked period and must not imply that a reopened episode will appear in the current-only
list. Redesigning Pérdidas lifecycle/history tables is a non-goal.

## L. CRM-038 request and dependency plan

Resource ownership remains separated:

| Trigger | Required requests | Forbidden collateral work |
| --- | --- | --- |
| Initial Dashboard entry | 5 commercial period resources, 1 Pipeline snapshot, 1 shared Product catalog, 1 unresolved stale total, 1 WhatsApp attention summary; AppShell owns its existing notification request | duplicate Product request, second unread request for Dashboard, broad remount |
| Period-only change | exactly 5 commercial period resources | Pipeline, Product catalog, notifications, WhatsApp |
| Source/product/province change | exactly 5 commercial resources + 1 Pipeline snapshot | Product catalog, notifications, WhatsApp |
| Manual commercial retry | retry only failed commercial resources where practical; a deliberate global Dashboard refresh may refresh Dashboard-owned commercial, Pipeline, stale, and WhatsApp resources once each | AppShell duplicate calls, polling loop |
| AppShell notification refresh | AppShell only; Dashboard consumes shared unread evidence nowhere | metrics, Pipeline, WhatsApp |
| WhatsApp attention retry | 1 attention-summary request | Inbox conversation page or metrics |

The five commercial calls may remain concurrent and settle independently. They are not
a broad every-resource `Promise.all`. Abort/version guards prevent stale responses from
overwriting newer filters. Successful prior values remain mounted during background
revalidation; local `aria-live` status announces refresh without layout shift. Product
catalog has one shared successful request for the mounted Dashboard session.

No aggressive polling is added. WhatsApp attention is fetched on entry, explicit retry/
Dashboard refresh, and optionally existing app recovery signals only if shared without
creating a second polling system.

## M. Typography, responsive, accessibility, and theme strategy

### Hierarchy and visual language

- page title/AppShell identity: 30–34px;
- Result count/kg numbers: 28–36px, with only these receiving display emphasis;
- active total and standard KPI values: 22–28px;
- section titles: 18–20px;
- body, chart values, and labels: 14–16px;
- secondary metadata: at least 13px.

Use tabular numerals, weight, whitespace, alignment, and grouping before color. Neutral
surfaces dominate. Navy is limited to small emphasis or typography, not a hero/result
wall; yellow is an accent, not a panel wash. Remove the large outcome donut and Origin
donut. The specialized UI review reinforced direct ranked bars for categorical
comparison and a combined time-series with visible non-color differentiation; it does
not replace existing FAA tokens or IBM Plex Sans.

### Responsive matrix

- 1440px: Result reads as the widest/strongest block; Attention stays compact; Active
  may align beside a secondary region only without equalizing weight; Evolution has
  full readable width.
- 1280px: no compressed five-KPI strip; outcome pairs and conversions remain grouped;
  chart labels retain at least 14px.
- tablet-like width: sections stack in semantic order; Result may use two outcome
  columns above conversions; secondary distributions become one-column.
- 390 × 844: order remains Attention → Result → Active → Evolution → Origin →
  Products/Provinces; count/kg pairs stack if necessary; explicit links stay visible;
  no horizontal document overflow or KPI carousel. A wide exact table may scroll only
  inside its labelled boundary.
- effective 150% zoom: same semantic order, no clipped controls/actions, no overlap,
  no document overflow, and no chart compressed below readable minimum. Prefer fewer
  x-axis labels over tiny text.

### Accessibility and refresh

- Semantic `h1`/`h2` hierarchy follows section order; grouped metrics use lists or
  description lists with meaningful labels.
- Every chart has visible values/legend, an accessible summary, and an exact data table
  or equivalent; series use line style/shape/text in addition to color.
- Explicit links and controls use visible 2px focus treatment, logical DOM order, and
  minimum 44 × 44px pointer/touch target where interactive.
- Text/token contrast meets WCAG AA in Light and Dark.
- Initial loading has a labelled status and reserved layout. Background refresh retains
  content, exposes `aria-busy`/polite status, and never blanks successful data.
- Partial failures are local and retryable; stale retained data is identified.
- Motion is functional and restrained, respects `prefers-reduced-motion`, and does not
  animate chart geometry merely for decoration.
- Dark mode updates only touched Dashboard surfaces and baselines; no global token or
  Dark redesign is authorized.

## N. Performance and index analysis

Current relevant indexes are:

- partial `opportunities(status, current_status_entered_at)` for non-deleted rows;
- partial `opportunities(source, created_at)` for non-deleted rows;
- `opportunity_loss_events(lost_at, id)`;
- unique loss-event status-history link and unique `(loss_event_id, product_id)`
  snapshot constraint (whose unique index begins with `loss_event_id`);
- WhatsApp Inbox composite index beginning with `waiting_for_response DESC`;
- current OpportunityProduct Opportunity/Product indexes.

Outcome queries must aggregate in PostgreSQL. Do not use `LostOpportunityService`
`statistics()` as currently written for Dashboard because it loads all matching events
and Product snapshots into Python. Build focused SQL count/sum/group projections over
loss events, join Opportunities only to exclude `deleted_at`, and use snapshot EXISTS/
joins for Product dimensions. Timeline must group in SQL and zero-fill only bounded
buckets in application memory.

The existing loss workspace index supports period ordering/ranges. Product-filtered
historical aggregates may require joins through snapshots, but no speculative index is
authorized. Capture representative PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` for unfiltered
period outcomes, Product-filtered outcomes, weekly timeline, and WhatsApp attention at
realistic fixture scale. Add an Alembic index only if measured plans show material
growth and obtain scope approval first; CRM-041 otherwise requires no migration.

For WhatsApp count/min, query only persisted conversation columns. The current Inbox
index can support waiting-first access, but count selectivity must be measured. Do not
load relation summaries. Expected query statement count is one.

## O. Risks and edge cases

- **Historical discontinuity:** loss events were introduced/backfilled by CRM-012.
  Backfilled events and snapshots are the authority; tests must cover their data.
- **Repeated losses:** one Opportunity may contribute multiple loss episodes across or
  within periods. This is intentional historical outcome evidence, not accidental
  duplicate rows.
- **Reopened currently active:** its prior loss remains in Result/Timeline and historical
  Pérdidas statistics while the Opportunity also appears in Active now. Labels must make
  period history vs current snapshot explicit.
- **Deleted Opportunities:** their wins and loss events are excluded consistently even
  if immutable evidence remains persisted. Soft-deleted Customers do not invalidate
  valid non-deleted Opportunity history.
- **Zero-kg loss:** a NUEVA → PERDIDA episode counts but adds zero kg. Opportunity
  conversion can be non-null while volume conversion remains null.
- **Product dimension:** historical losses use the event Product snapshot, not the
  Opportunity's later restored quote. A no-quote loss is excluded by a Product filter.
- **Province/source mutation:** loss events use their immutable snapshots; Created and
  Won retain the relevant current contracts. The UI must not claim all dimensions are
  immutable.
- **Preset year end:** current convention ends at next-month boundary, not next January;
  keep this behavior rather than silently including future months.
- **Weekly partial buckets:** first/last labels and counts honor the requested interval,
  not the full surrounding week.
- **Timezone:** UI date links use Buenos Aires dates; backend datetimes remain aware and
  half-open. No `Z` shortcut may shift local boundaries.
- **Huge values/categories:** Decimal strings never round-trip through float for business
  totals; labels wrap/truncate safely and exact tables retain full values.
- **Partial failure:** Result must not combine new won with stale lost values as though
  one coherent snapshot. The overview response remains atomic; independent sections can
  retain their own last successful data.
- **WhatsApp projection lag/error:** summary reports persisted truth only. `null` oldest
  with positive count violates the model constraint and should be treated as server
  error, not fabricated age.
- **Attention age:** oldest age is informational, has no promised SLA, and updates only
  at normal render/refresh cadence.
- **Direct navigation:** invalid query parameters are canonicalized safely and do not
  reach APIs. Browser Back preserves Dashboard/outcome filter context.

## P. Full scope and non-goals

### Scope

- Replace current Dashboard hierarchy with Attention → Result → Active → Evolution →
  Origin → secondary Products/Provinces.
- Correct selected-period loss count/kg/conversion/timeline to immutable event history.
- Add weekly timeline aggregation and combined comparison.
- Add authoritative WhatsApp waiting count/oldest timestamp and filtered Inbox action.
- Remove Dashboard unread-notification duplication.
- Correct active snapshot to the three open stages.
- Add explicit period-aware navigation to Ganadas and Pérdidas and minimal supporting
  destination query state.
- Preserve CRM-038 request boundaries, resilient refresh, accessibility, responsive,
  Light/Dark token behavior, and deterministic browser evidence.

### Non-goals

- Pipeline redesign.
- Opportunity Detail redesign.
- Ganadas lifecycle/history redesign.
- Pérdidas lifecycle redesign or a new historical event table UI.
- Sidebar redesign.
- Navigation-wide Spanish terminology pass.
- Broadcast visibility change.
- Global icon redesign.
- Full Dark-mode redesign.
- Global design-system rewrite.
- New analytics infrastructure, warehouse, materialized metrics, export, forecasting,
  targets, or custom report builder.
- New frontend state library or chart dependency without separate evidence/approval.
- Seller visibility or role changes.
- Quote version history, pricing, or monetary metrics.
- CRM-042/CRM-043 transversal UI work.

## State transitions

None. CRM-041 reads existing Opportunity, Notification, loss-event, and WhatsApp
projections. Opening a link or rendering/refreshing Dashboard never mutates domain
state.

## Security and permissions

- All metrics, notification, WhatsApp, Ganadas, and Pérdidas routes remain authenticated.
- `SUPERVISOR` and `VENDEDOR` retain current global read visibility; this supervisor-led
  hierarchy introduces no new seller restriction.
- Aggregate responses expose counts/timestamps only and no message content, contact
  data, credentials, or provider evidence.
- Query validation rejects naive/reversed metric ranges and invalid enum/ID filters.
- Existing CSRF/session/token handling, provider isolation, and lock order are unchanged
  because CRM-041 adds no mutation.

## Q. Validation plan and acceptance criteria

### Backend deterministic tests

- **AC-01:** Overview Created retains `created_at` and half-open aware period semantics;
  boundary rows at `from` are included and at `to` excluded.
- **AC-02:** Won count/kg use GANADA terminal-entry time and non-deleted final quote
  totals, with exact Decimal precision.
- **AC-03:** Lost count/kg use loss-event `lost_at` and immutable
  `quoted_total_kg`; reopening does not remove the episode and repeated loss creates a
  second contribution.
- **AC-04:** Opportunity conversion is won/(won+loss episodes), volume conversion is
  won kg/(won kg+lost snapshot kg), each four-place Decimal and `null` only on zero
  denominator.
- **AC-05:** A lost-from-NUEVA event contributes count zero kg; only-won, only-lost,
  and no-outcome periods produce deterministic rates.
- **AC-06:** Source/province/Product filters apply to immutable loss-event/snapshot
  fields and exclude soft-deleted Opportunities without excluding soft-deleted
  Customers' valid Opportunity history.
- **AC-07:** Pipeline returns all statuses compatibly; Dashboard active projection sums
  only NUEVA/COTIZADA/NEGOCIACION and excludes GANADA/PERDIDA.
- **AC-08:** Origin Created buckets sum to the overview Created denominator under the
  same filters, including zero and single-source cases.
- **AC-09:** Timeline day/week/month uses Buenos Aires buckets, zero-fills, handles
  partial Monday-anchored weeks, preserves half-open boundaries, and uses event loss
  semantics.
- **AC-10:** Lost daily detail can identify repeated/reopened loss episodes without
  conflating them with current status.
- **AC-11:** WhatsApp attention summary returns exact count and minimum
  `waiting_since_at`; zero returns null oldest.
- **AC-12:** WhatsApp waiting projection tests cover PENDING, IN_PROGRESS, UNKNOWN,
  DEFINITIVE_FAILED, ACCEPTED, later FAILED, broadcast exclusion, late inbound ordering,
  and earliest unanswered inbound.
- **AC-13:** Aggregate query statement counts remain bounded; realistic PostgreSQL plans
  show SQL aggregation and no full-history Python loading. No speculative index or
  migration is added.

### Frontend component/integration tests

- **AC-14:** Full-data month renders the exact hierarchy and one nonduplicated instance
  of each primary result; lost kg is as prominent as won kg.
- **AC-15:** Zero-activity month, only won, only lost, no active Opportunities, and
  zero-volume outcomes render honest null/zero states.
- **AC-16:** Attention zero/nonzero/partial-failure combinations follow hide/calm-state
  rules; unread notifications are absent.
- **AC-17:** WhatsApp waiting zero/nonzero renders authoritative count and optional
  oldest age, never `Hay` as a pseudo-count.
- **AC-18:** Combined Evolution shows all three series simultaneously; day/week/month
  selection follows the deterministic thresholds and exact table values agree.
- **AC-19:** Origin one/many/zero datasets show correct count and percentage denominator;
  Products/Provinces populated and empty states do not reserve oversized charts.
- **AC-20:** Period change issues exactly five commercial requests, preserves current
  content while revalidating, and does not request Pipeline/catalog/notifications/
  WhatsApp.
- **AC-21:** Dimension change issues five commercial requests plus one Pipeline request;
  catalog remains one successful request.
- **AC-22:** Partial API failure is local, retryable, and preserves prior successful
  values without combining incoherent overview fields.
- **AC-23:** `Ver ganadas` creates the validated CRM-039 period/dimension URL and the
  destination requests equivalent aware boundaries.
- **AC-24:** `Ver pérdidas` creates the equivalent Pérdidas URL; destination historical
  statistics use Buenos Aires aware half-open boundaries and explain the current-only
  list limitation where relevant.
- **AC-25:** `Ver seguimientos` and `Abrir pendientes` land on active Notifications and
  waiting-only Inbox respectively without mutating state.
- **AC-26:** Browser Back returns to the applied Dashboard state or preserves destination
  origin/query context according to existing router conventions.

### Browser, responsive, accessibility, and visual tests

- **AC-27:** Deterministic browser fixtures cover full month, zero activity, only won,
  only lost, no active, attention zero/nonzero, WhatsApp zero/nonzero, Origin one/many,
  and empty/populated secondary dimensions.
- **AC-28:** At 1440px, 1280px, tablet-like width, 390 × 844, and effective 150% zoom,
  semantic order is preserved, no document overflow occurs, links remain visible, and
  charts/KPIs stay legible without carousels.
- **AC-29:** Keyboard traversal follows visual order; focus-visible is clear; all
  actions and chart data are available without pointer hover.
- **AC-30:** Axe passes in Light and Dark; chart meaning is not color-only, headings are
  semantic, loading/refresh announcements are appropriate, and reduced motion is
  honored.
- **AC-31:** Updated deterministic Dashboard desktop and Dark visual baselines prove
  Result dominance, compact Attention, direct Origin comparison, no large decorative
  donut, and no giant navy/yellow block.
- **AC-32:** Existing Ruff check/format, mypy strict, backend tests/coverage/compileall,
  Alembic check/current, frontend check/tests/build/coverage, npm audit, Docker Compose
  build/health, and CI thresholds remain passing without weakening gates.

Browser fixtures must use fixed timestamps/timezone and explicit loss/reopen/message
evidence. Tests must not depend on the wall clock, provider network, random ordering, or
shared mutable run order.

## R. Expected files/modules likely to change during implementation

### Frontend

- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/DashboardPage.test.tsx`
- `frontend/src/metrics/DashboardFilters.tsx`
- `frontend/src/metrics/DashboardVisuals.tsx`
- `frontend/src/metrics/DashboardVisuals.test.ts`
- `frontend/src/metrics/filters.ts`
- `frontend/src/metrics/filters.test.ts`
- `frontend/src/metrics/types.ts`
- `frontend/src/metrics/useDashboardMetrics.ts`
- `frontend/src/metrics/useTimelineDayDetail.ts`
- `frontend/src/api/metrics.ts`
- `frontend/src/api/whatsapp.ts`
- `frontend/src/whatsapp/types.ts`
- `frontend/src/pages/LostPage.tsx`
- `frontend/src/pages/LostPage.test.tsx`
- `frontend/src/api/lost.ts`
- `frontend/src/lost/types.ts`
- `frontend/src/pages/WonPage.tsx` and tests only if explicit period handoff exposes a
  compatibility gap
- `frontend/src/pages/WhatsAppInboxPage.tsx` and Inbox-state tests for `waiting=true`
- `frontend/src/pages/NotificationsPage.tsx` and tests for `view=active`
- `frontend/src/routing/router.tsx` / route-query helpers and tests only as required by
  canonical query preservation
- `frontend/src/styles.css`

### Backend

- `backend/app/services/metrics_service.py`
- `backend/app/schemas/metrics.py`
- `backend/app/api/routers/metrics.py`
- `backend/tests/test_metrics_service.py`
- `backend/tests/test_metrics_api.py`
- `backend/app/services/whatsapp_query_service.py` or a narrowly named aggregate
  service/projection beside it
- `backend/app/services/whatsapp_query_projections.py`
- `backend/app/schemas/whatsapp.py`
- `backend/app/api/routers/whatsapp.py`
- `backend/tests/test_whatsapp_query_service.py`
- `backend/tests/test_whatsapp_api.py`

### Deterministic browser evidence

- `backend/app/scripts/seed_visual_qa.py`
- `backend/tests/test_visual_qa_seed.py`
- `backend/quality/browser/test_10_product_semantics.py`
- `backend/quality/browser/test_20_responsive_accessibility.py`
- `backend/quality/browser/test_30_states.py`
- `backend/quality/browser/test_40_visual_regression.py`
- Dashboard visual baseline assets under `backend/quality/browser/baselines/`

No Alembic file is expected. Exact implementation files may be fewer after reuse is
confirmed; this list does not authorize unrelated refactors.

## Open decisions

None

## Follow-up / future specs

- CRM-042 and CRM-043 own later transversal UI work.

## Implementation notes

Prefer extending current focused contracts and components. Keep API/domain calculation
outside visual components, Decimal strings intact until formatting, and query-state
serialization in typed helpers shared by Dashboard and destination workspaces where a
real common responsibility exists. Do not introduce a chart package solely for this
scope; the existing SVG/DOM approach can render three bounded series, subject to the
readability tests above.
