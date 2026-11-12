# CRM-057 — Prequote stage and customer transition notes

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-11-12
Implementation commit: `eb410cb0deb15eceed63e777eb4f04b1bde39f1a`

## Goal and authorization

The user's explicit request on 2026-11-11 authorizes Nueva → Para cotizar →
Cotizada → Ganada, quote validation upon entering Cotizada, and mandatory notes
for manual stage changes, visible from each Customer. This supersedes the conflicting
stage/quote/action requirements in CRM-001, CRM-012, CRM-040 and CRM-041, not their
unrelated requirements. Existing local documentation edits must be preserved.

## Scope and business rules

- Add PARA_COTIZAR before COTIZADA. NUEVA → PARA_COTIZAR needs no quote;
  PARA_COTIZAR → COTIZADA atomically saves positive product quantities.
- COTIZADA → GANADA; regressions GANADA → COTIZADA and COTIZADA → PARA_COTIZAR.
  PARA_COTIZAR cannot regress to NUEVA. Retain existing quotes on regression.
- Loss is allowed from every open stage. Reopening requires a retained quote and
  returns to COTIZADA. Preserve existing loss/consent/role/locking rules.
- Every authenticated manual stage mutation requires a trimmed nonblank note,
  maximum 4000 characters, including loss, regression and reopening. No separate
  note request: mutation and note commit or fail together.
- Automatic initial NUEVA events from intake/Web/WhatsApp remain unchanged; no
  fabricated author, note or retrospective notes. Initial creation is not a change
  between stages and is outside the mandatory transition-note gate.
- Notes are immutable transition evidence, available in opportunity history and a
  paginated Customer activity section across their opportunities. Existing free-form
  opportunity notes and revision history are not moved, deleted or changed.

## Migration and data model

- Add PARA_COTIZAR to the PostgreSQL enum; keep NEGOCIACION readable as legacy
  history, labelled Negociación (histórico), never a selectable current destination.
- Existing current NEGOCIACION becomes COTIZADA. Existing COTIZADA remains COTIZADA.
  Preserve products, IDs, original history, timestamps, loss snapshots and notes.
- Add nullable note text to status history: old records stay null. Constrain stored
  non-null notes to 1–4000 trimmed characters. Update active WhatsApp uniqueness
  index to include PARA_COTIZAR and retain legacy protection.
- Document rollback limitations; never silently discard a new stage or new notes.

## Contracts / API

- Add POST /opportunities/{id}/prepare-quote with mandatory note.
- Quote, win, regress, lose and reopen requests include mandatory note; old clients
  without it receive 422, with no partial writes. No bypass via the retired
  move-to-negotiation endpoint.
- Expose nullable note on status-history responses.
- Add authenticated GET /customers/{id}/stage-notes with page/page_size; return
  note, opportunity ID, from/to status, actor and timestamp, newest first.
- Keep JWT, roles, resource visibility and existing pagination limits unchanged.

## Non-goals

No deployment to production, external messages, dependency upgrades, new roles,
quote-version system, note backfill, mandatory notes on automatic intake, or
renaming historical facts. Preserve the ongoing timeline visual improvements.

## Acceptance criteria

- AC-01: Pipeline, detail, filters and Dashboard show the new ordered stages.
- AC-02: New → Para cotizar succeeds without products; skipping it is rejected.
- AC-03: Entering Cotizada needs positive product quantities and a nonblank note;
  failures leave stage, quote, history and notifications unchanged.
- AC-04: Every manual transition rejects absent/blank/overlong notes in the API;
  valid notes retain exact normalized body, author and timestamp atomically.
- AC-05: Regression, loss and reopening obey the new targets and existing guards.
- AC-06: Notes appear in opportunity history and only the associated Customer's
  paginated stage notes, across opportunities, with no duplication on reopen replay.
- AC-07: Migration preserves old quotes/history and keeps active WhatsApp uniqueness.
- AC-08: UI requires notes for button and drag actions; cancellation does not mutate;
  pending/error states preserve input and prevent duplicate submits.
- AC-09: Automated initial intake remains operational without human notes.
- AC-10: Existing backend/frontend quality gates and health checks are exercised;
  report existing dependency-audit blockers without weakening gates or publishing.

## Open decisions

None.

## Verification / implementation notes

Use existing domain services, DTOs and modal patterns. Validate on a disposable test
database and back up the local preview DB before migration. No production writes.

Local verification on 2026-11-11:

- Backed up the preview database before applying migration 0019. Migration tests
  verify preserved quotes, timestamps and history, active WhatsApp uniqueness,
  note constraints and the guarded downgrade. No production database was changed.
- Backend: 512 tests passed, 93.19% coverage; Ruff, strict mypy (172 files),
  compileall and Alembic check/current passed.
- Frontend: 280 tests passed with coverage thresholds met; TypeScript and Vite
  production build passed. Biome has existing CSS specificity warnings.
- Browser verification on localhost: a dedicated synthetic customer completed
  Nueva → Para cotizar → Cotizada → Ganada. Empty notes disabled confirmation;
  quoting required products and kg. All three notes persisted in opportunity
  activity and the customer sheet with actor, timestamp and stage transition.
- All three preview Compose services are healthy. The original local database
  volume remains preserved separately from this preview.
- Full npm audit retains six existing development dependency alerts (three
  moderate, three high); production-only audit reports zero. This required gate
  remains a publishing blocker. No commit, push or deployment was performed;
  spec status stays Approved pending the verified implementation commit.

Release requires a database backup and coordinated backend/frontend deployment:
old clients without transition notes receive 422 and must reload. Migration 0019
intentionally refuses an automatic downgrade that could discard stage notes;
rollback requires a reviewed restore plan.

## Publication preparation — 2026-11-12

The user explicitly authorized publishing all pending changes to main. Commit
`eb410cb` implements CRM-057/058/059; `db17793` fixes the period selector's accessible
name and stores the four reviewed Chromium baselines for the intended UI changes.
Local verification passes 529 backend tests (93.26% coverage), 294 frontend tests,
build, typing, formatting, migration checks and healthy Compose services. Updated
development dependency locks pass both full npm and Python vulnerability audits
without exceptions. GitHub validation runs on a temporary branch before main is
updated. The earlier audit/publishing limitations above describe the prior session.
