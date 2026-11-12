# CRM-059 — Shared period filters

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-11-12
Implementation commit: `eb410cb0deb15eceed63e777eb4f04b1bde39f1a`

## Authorization and scope

The user requests the supplied period filter design throughout the CRM, including
a missing 15-day range. Use one reusable component in Dashboard, Ganadas and
Pérdidas, the existing surfaces with date filters. Preserve other filter dimensions,
roles, date meanings, navigation and draft/Apply behavior.

- Quick options: Todo, Hoy, Últimos 7 días, Últimos 15 días, Este mes. Keep existing
  three-month/year/custom options under Más períodos. Always show Desde/Hasta.
- Quick rolling ranges include today plus 6/14 earlier Buenos Aires calendar days.
  Month means the full current calendar month. Three months starts two calendar
  months earlier; year starts January, ending with the current calendar month.
- Manual dates select Personalizado and have inclusive visible endpoints. Reject
  inverted/incomplete custom ranges without issuing invalid metric requests.
- Todo removes date constraints in lists. Dashboard gets true all-history support
  using actual stored event bounds, never an invented earliest date.
- Keep day/month timeline limits, use monthly buckets for Todo, and preserve
  dimensions and selected dates when navigating to outcomes or drilldowns.
- Match the reference's hierarchy, quick selector and paired dates using existing
  light/dark design tokens, accessible labels, keyboard focus and responsive layout.

## Contract

Metrics date endpoints optionally accept `all_history=true` instead of `from`/`to`.
Reject mixing modes; existing bounded requests and missing-date validation remain
unchanged. Auth, dimensional filters and aggregation rules stay intact. Responses
include the computed period. No schema migration or new dependency.

## Acceptance criteria

- AC-01: All three date-filter surfaces use the shared component with 15 days.
- AC-02: Rolling ranges work at Buenos Aires midnight, month/year and leap-day
  boundaries; visible end dates serialize to the next exclusive midnight.
- AC-03: Todo includes stored history in Dashboard, Ganadas and Pérdidas, with no
  arbitrary date cutoff and no invalid empty timestamps or all-history drilldowns.
- AC-04: Presets/manual dates survive supported URLs, preserve dimensions and
  existing Apply/reset semantics; invalid custom dates do not trigger requests.
- AC-05: Desktop/mobile and light/dark render without horizontal page overflow.
- AC-06: Relevant tests, build and quality gates run; existing npm audit failures
  remain a publishing blocker. No commit/push/deployment through failed gates.

## Non-goals

No new date filters for screens that never had them, no change to pipeline snapshot
semantics, business metrics, access rules, external integrations or production.

## Open decisions

None.

## Local verification — 2026-11-11

- Shared PeriodFilter is used in Dashboard, Ganadas and Pérdidas. Rolling presets
  use Buenos Aires calendar dates; manual drafts do not issue requests until both
  dates are valid. Ganadas/Pérdidas keep their existing explicit Apply action.
- Backend: 529 tests passed, 93.26% coverage. Ruff, strict mypy (173 files),
  compileall and Alembic check/current passed; no migration was required.
- Frontend: 294 tests passed with coverage thresholds met. TypeScript and Vite
  build passed; Biome reports the existing 24 CSS specificity warnings.
- Tests cover Argentina midnight, leap-day/year boundaries, inclusive 15-day
  serialization, invalid manual drafts, list/statistic filtering, URL restoration,
  Dashboard all-history drilldowns, true stored history bounds before 1970, future
  fixture events, empty history, and rejecting mixed/missing API period modes.
- Read-only authenticated requests against the local Compose backend returned 200
  for 15-day overview, exactly 15 daily timeline buckets, all-history overview and
  monthly timeline, and the corresponding Ganadas/Pérdidas list ranges. Frontend
  returned 200 and all three Compose services are healthy.
- Live visual verification (desktop/mobile and light/dark) remains unverified:
  CUA reports local browser use disabled in Work settings. No alternative browser
  automation bypass or screenshot claim was made.
- Full npm audit retains six existing development dependency alerts (3 moderate,
  3 high); production-only audit reports zero. No commit, push or deployment;
  status remains Approved pending a verified implementation commit.

## Publication preparation — 2026-11-12

The user authorized publishing all pending changes to main. The implementation
commit is recorded above; follow-up `db17793` makes Más períodos explicitly
accessible and refreshes four reviewed visual baselines from GitHub Chromium
artifacts. Desktop light/dark screenshots confirm the requested shared period
layout and 15-day option. The first remote run passed 43 browser cases and
identified two selector lookups plus four expected baseline changes; validation is
rerun after the correction without weakening comparison thresholds or tests.

The full local suite passes 529 backend and 294 frontend tests, coverage, build,
typing, format and migration checks; Compose services are healthy. npm and Python
audits now report no known vulnerabilities. Earlier browser/audit/publishing
limitations above describe the prior local-only session. All changes are validated
on a temporary Git branch before updating main.
