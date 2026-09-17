# CRM-047 — Instagram Reporting Source

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-17
Implementation commit: `ae34a18`

## Goal

Recognize Instagram as a typed commercial source so Reportes can filter and display
Instagram Opportunities consistently with every existing source.

## Context

Commercial reports derive their source filter, labels, and aggregates from the shared
`LeadSource` domain. Adding only a visual option would create a filter that the API and
PostgreSQL cannot represent.

## Dependencies

- CRM-004 — Commercial Metrics
- CRM-021 — Dashboard Metrics
- CRM-043 — Manual Opportunity Creation

## Scope

- Add `INSTAGRAM` to the typed backend, frontend, and PostgreSQL lead-source domain.
- Show `Instagram` in the shared source selector used by Reportes.
- Accept `INSTAGRAM` in metric filters and aggregate persisted Instagram Opportunities.
- Keep source labels and URL parsing consistent across existing CRM surfaces.
- Add targeted backend, frontend, and migration coverage.

## Non-goals

- Building an Instagram/Meta ingestion integration.
- Changing manual Opportunity creation, which remains backend-owned `REFERIDO`.
- Reclassifying or backfilling existing Opportunities or historical evidence.
- Adding campaign, advertising, messaging, or social-media analytics.

## Business rules

- `INSTAGRAM` is a commercial acquisition source with the user-facing label
  `Instagram`.
- Report metrics use the existing source aggregation and filtering semantics without
  special treatment for Instagram.
- Existing `WEB`, `WHATSAPP`, and `REFERIDO` data and behavior remain unchanged.

## Data model

Add `INSTAGRAM` to `lead_source_enum` through an Alembic revision after
`0012_other_loss_reason_detail`. No rows are backfilled. Downgrade must refuse to
remove the value while any supported commercial-history table references it.

## Contracts / API

Existing source-bearing responses may return `INSTAGRAM`. Existing metric endpoints
accept `source=INSTAGRAM`; unknown source values remain rejected.

## Security & permissions

Existing authentication, global visibility, and metric permissions remain unchanged.

## Acceptance criteria

- AC-01: Reportes offers an accessible `Instagram` option in its Origen selector.
- AC-02: Metric endpoints accept `source=INSTAGRAM` and return only matching data.
- AC-03: Source aggregates serialize Instagram rows as `INSTAGRAM`.
- AC-04: Shared frontend source parsing and labels recognize `INSTAGRAM`.
- AC-05: PostgreSQL is upgraded through Alembic without modifying existing rows.
- AC-06: Unknown source values remain invalid and existing sources remain unchanged.

## Open decisions

None

## Follow-up / future specs

An Instagram ingestion or manual source-selection workflow requires a separate,
explicitly approved specification.
