# CRM-058 — Optional province when quoting or winning

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-11-12
Implementation commit: `eb410cb0deb15eceed63e777eb4f04b1bde39f1a`

## Authorization and scope

The user explicitly requests a recommended, optional province prompt when a lead
advances to Cotizada or Ganada and its customer has no province. Extend CRM-057's
forward transition confirmations without changing its stages or mandatory notes.

- On Para cotizar → Cotizada and Cotizada → Ganada, show an optional province field
  in the existing confirmation when the customer's province is absent or blank.
- Explain that completing it is recommended and that the user may continue if it
  is unknown. An empty field must never block the transition.
- Save a supplied province on the customer in the same transaction as the quote or
  win. Never overwrite a province already present, including concurrent updates.
- Hide the prompt for customers with a province. Preserve input on errors, reset
  it when closing, and prevent changes while submitting.
- Cover both opportunity detail actions and pipeline drag confirmations.

## Contracts and data

Quote and win accept optional `province` (trimmed text, blank/null/omitted means
skip). Existing requests remain compatible. Reuse Customer.province; no migration.
Lock Customer before Opportunity when filling the missing customer field.

## Non-goals

No mandatory location, guessing, external lookup, province catalog, changes to
loss/reopening/regression, dependency upgrades, or production deployment.

## Acceptance criteria

- AC-01: Missing province prompts on both forward transitions and both UI paths.
- AC-02: Blank province permits submission with the existing note/product rules.
- AC-03: Supplied province persists on Customer; the win prompt then disappears.
- AC-04: Skipping at Cotizada prompts again at Ganada.
- AC-05: Existing/concurrently supplied province is preserved. Invalid transitions
  and failed quotes do not partially save province, history or state.
- AC-06: Errors preserve the draft, cancel causes no write, reopening resets it.
- AC-07: Relevant tests/build/quality checks run; report the existing npm audit
  blocker without committing, pushing or deploying through a failing gate.

## Open decisions

None.

## Local verification — 2026-11-11

- Backend: 523 tests passed, 93.19% coverage; Ruff, strict mypy (173 files),
  compileall and Alembic check/current passed. No schema change was needed.
- Frontend: 284 tests passed with coverage thresholds met; TypeScript, Vite build
  and Biome passed (24 existing CSS specificity warnings).
- Tests cover blank/null/omitted province compatibility, saving at quote or win,
  preserving an existing province despite a stale identity-map snapshot, and
  rollback of customer/quote/history after failure. UI tests cover detail and
  pipeline prompts, optional input, error retries and hiding the filled field.
- Browser: a dedicated synthetic local lead advanced to Cotizada with no province;
  the optional prompt appeared again at Ganada. Completing Córdoba saved it on the
  customer and displayed it on the opportunity after the transition.
- All three local Compose services are healthy. Full npm audit still reports six
  existing development dependency alerts (3 moderate, 3 high), while production
  dependencies report zero. No commit, push or production deployment; the spec
  remains Approved pending a verified implementation commit.

## Publication preparation — 2026-11-12

The user authorized publishing all pending work to main. The implementation is
recorded above in a separate documentation commit. The complete local suite now
passes 529 backend and 294 frontend tests, build/typing/format/migration checks and
Compose health checks. Both full dependency audits pass after the quality lock
refresh. GitHub validation runs on a temporary branch before main is updated; the
earlier blocker notes describe the state before this publication preparation.
