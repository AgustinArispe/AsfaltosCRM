# CRM-004 — Commercial Metrics

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-10
Implementation commit: `97a21a6`

## Goal

Expose consistent backend-calculated commercial KPIs for the CRM frontend and other authenticated consumers.

## Context

Metrics are calculated by `MetricsService`; the frontend only visualizes returned values. Definitions follow `docs/BUSINESS_RULES.md`.

## Dependencies

- CRM-001 — Core CRM

## Scope

Overview, product, source, province, timeline, and current pipeline snapshot metrics, shared filters, period validation, timezone bucketing, Decimal quantities, and conversion formulas.

## Non-goals

No client-side aggregation, forecasting, custom dashboard builder, or historical analytics tables are implemented.

## Business rules

- Opportunity conversion is `won / (won + lost)`.
- Volume conversion is `kg_won / (kg_won + kg_lost)`.
- A zero denominator returns `null`; nonzero ratios are quantized to four Decimal places.
- Created/open counts and quoted volume use opportunity creation time.
- Won/lost counts, terminal volume, and conversion denominators use entry into the terminal state (`current_status_entered_at`).
- Period filters are timezone-aware and half-open: `[from, to)`.
- Timeline buckets use `America/Argentina/Buenos_Aires` and include empty day/month buckets.
- Pipeline is a current snapshot, not a period metric, and includes every opportunity status.

## Data model

Metrics read existing Customers, Products, Opportunities, and quote lines; no metrics tables or schema changes are introduced. Soft-deleted opportunities are excluded.

## Contracts / API

Authenticated GET endpoints:

- `/api/metrics/overview`
- `/api/metrics/products`
- `/api/metrics/sources`
- `/api/metrics/provinces`
- `/api/metrics/timeline` with `granularity=day|month`
- `/api/metrics/pipeline` (no period parameters)

Period endpoints accept timezone-aware `from`/`to` plus optional `source`, positive `product_id`, and normalized `province`. Responses use typed Decimal fields. Timeline returns the applied period, granularity, timezone, and zero-filled buckets; pipeline returns a timezone-aware `snapshot_at`.

## State transitions

None. Metrics are read-only aggregate projections over persisted CRM state; terminal attribution follows the stored status-entry timestamp.

## Security & permissions

All metrics routes require an active authenticated user. No additional seller-specific visibility is applied by the metrics service.

## Edge cases

- Naive datetimes, reversed/empty periods, unsupported granularity, unknown source, and invalid product IDs are rejected.
- Province matching trims and compares case-insensitively; null province is retained as its own grouping.
- Inactive products remain visible in historical product metrics.
- Empty aggregates return zero quantities/counts and null conversion where applicable.

## Acceptance criteria

- AC-01: Overview returns created, won, lost, open, quoted, won, lost, and open values using the documented timestamp semantics.
- AC-02: Opportunity and volume conversion use independent denominators and return null for zero denominators.
- AC-03: Ratios and kg values preserve Decimal precision (`0.0000` ratios and three-decimal kg values).
- AC-04: Source, product, and province dimensions honor shared filters without including soft-deleted opportunities.
- AC-05: Product metrics include inactive products with historical quote lines and order by quoted kg then product ID.
- AC-06: Province metrics retain null-province history and group province values case-insensitively after trimming filters.
- AC-07: Timeline uses the Buenos Aires calendar, supports day/month buckets, and zero-fills empty buckets.
- AC-08: Pipeline returns a current count for every `OpportunityStatus`, excludes deleted opportunities, and has no period requirement.
- AC-09: All metric endpoints reject unauthenticated access and invalid query periods/filters.

## Open decisions

None

## Follow-up / future specs

None

## Implementation notes

PostgreSQL aggregate queries perform calculations in the backend. The API converts aware input datetimes to UTC while retaining the Buenos Aires timezone for timeline calendar bucketing.
