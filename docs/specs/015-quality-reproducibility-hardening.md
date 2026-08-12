# CRM-015 — Quality and Reproducibility Hardening

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-12
Implementation commit: aa8b23f

## Goal

Make FAA CRM builds, CI, dependencies, and quality gates deterministic and
reproducible before backend freeze.

## Context

CRM-001 through CRM-014 define the implemented product, backend correctness,
PostgreSQL concurrency/performance behavior, and current quality expectations. The
repository already has a reproducible npm graph through `package-lock.json` and
`npm ci`, but backend runtime requirements are version ranges and therefore resolve a
potentially different transitive graph on a later build of the same commit.

The existing GitHub Actions workflow runs Ruff, mypy strict, PostgreSQL-backed pytest
with 93% backend coverage, compileall, Alembic checks, Vitest, TypeScript/Vite build,
and `npm audit`. It does not yet audit Python vulnerabilities, lint or format frontend
source, enforce frontend coverage, or prove the declared Docker Compose path in CI.
External Actions are referenced by mutable major-version tags.

This spec closes those release-engineering gaps without changing application behavior,
schema, architecture, or UX.

## Dependencies

- CRM-001 through CRM-014 — all implemented business, API, concurrency, and
  performance behavior must remain unchanged.

## Scope

- Introduce committed, exact, hash-checked backend runtime and development lock
  artifacts while retaining clear top-level dependency declarations.
- Make backend Docker and CI installs consume only those locked artifacts.
- Add a maintained Python dependency vulnerability gate over the locked graph.
- Add one React/TypeScript-aware frontend lint and formatting tool.
- Record the measured Vitest coverage baseline and enforce conservative regression
  floors.
- Add a Docker Compose smoke job covering service health, HTTP, proxying, and migration
  state without repeating the full test suites.
- Pin third-party GitHub Actions to immutable commits and retain minimal workflow
  permissions.
- Align fast local pre-commit checks with CI where practical.
- Define forward-looking CRM spec/acceptance-test traceability.
- Preserve every current quality invariant.

## Non-goals

- Business behavior, public API behavior, authentication, authorization, or FAA rules.
- Database schema or migration changes.
- Application architecture refactors or new product features.
- Frontend UX, visual design, navigation, or interaction changes.
- Dependency upgrades merely because newer versions exist.
- Replacing npm, Vitest, TypeScript, Ruff, mypy, pytest, Alembic, Docker Compose, or
  GitHub Actions with a large build/CI platform.
- Making expensive PostgreSQL suites part of pre-commit.
- Retrofitting every historical test with a spec reference or enforcing one test per
  acceptance criterion.

## Python dependency reproducibility

### Source declarations and locks

The backend uses a pip-tools lock workflow because it fits the current pip requirements
layout without turning the application into a package or changing application
libraries:

- `backend/requirements.in` is the human-edited runtime source and retains the current
  direct dependency ranges and explanatory comments.
- `backend/requirements-dev.in` is the human-edited development/quality source. It
  constrains runtime packages to `requirements.lock` and declares only direct quality
  tools, including the exact lock compiler and vulnerability scanner.
- `backend/requirements.lock` contains the complete exact runtime graph.
- `backend/requirements-dev.lock` contains the complete exact development/quality
  graph compatible with the runtime lock.

Both lock files are committed pip-compile output with exact versions, hashes, dependency
origins, and a stable generation command. They contain no unconstrained direct or
transitive dependency. Runtime and development installs use pip hash-checking mode.
Development/CI environments install both locks; an application runtime image installs
the runtime lock only unless a clearly named quality/development target requires both.

The canonical resolver environment is the repository's pinned Linux Python 3.13
toolchain. Python patch versions, pip-tools, and relevant container image manifest
digests are explicit so a lock is not regenerated under an accidental interpreter or
resolver change. Platform markers are evaluated for that supported runtime. No global
Python tool is required: the existing locked development environment or a disposable
pinned container performs lock generation.

The first lock generation captures a working graph allowed by the current declarations.
It must not deliberately upgrade direct application libraries. If resolution requires
a direct-library change, that change is isolated and justified in review rather than
hidden inside the locking conversion.

### Install and update workflow

CI verifies lock freshness by regenerating both artifacts in the canonical environment
and comparing them byte-for-byte with the committed files. Docker and CI install with
equivalent hash-enforcing commands and never install the range-based `.in` files.
Dependency caches key from the committed locks, not the input declarations.

The documented update workflow is:

1. change one top-level declaration only when needed;
2. run the canonical containerized lock command without a blanket upgrade, or name the
   exact package being intentionally upgraded;
3. review direct and transitive lock diffs, hashes, licenses where relevant, and audit
   findings;
4. run locked installs and every normal quality gate;
5. commit the declaration and lock changes together.

A resolver, Python patch, base-image digest, or lock-tool update is also an explicit
reviewed toolchain change. Generated locks must never be edited by hand. Normal builds
need no private package index, credentials, or host-installed dependency manager.

Docker base images and the PostgreSQL service image are pinned to immutable manifest
digests while retaining their human-readable Python 3.13, Node 22, and PostgreSQL 17
tags/comments. Updating a digest is an explicit reviewed maintenance change and does
not implicitly authorize a major/minor runtime upgrade.

## Backend vulnerability auditing

Use the PyPA-maintained `pip-audit` scanner, pinned in the development lock. It audits
the complete hash-checked runtime and development locks with dependency resolution
disabled, so the scanned graph is the graph installed by CI rather than a fresh range
resolution. CI never invokes automatic vulnerability fixes.

The default policy fails on every applicable known vulnerability, which necessarily
includes all relevant high and critical findings and avoids depending on incomplete or
inconsistent severity metadata. Human-readable output remains in the job log and a
machine-readable JSON result is retained as a short-lived CI artifact even when the
gate fails. The audit uses public ecosystem advisory data and needs no secret or
authenticated package feed.

An advisory may be excepted only through a reviewed repository file that identifies the
advisory alias, exact package/version, applicability analysis, compensating controls,
tracking issue, owner, approval date, and expiry/review date. The audit wrapper reports
every active exception and fails closed for expired, malformed, or package/version-
mismatched entries. False positives and upstream-only fixes therefore remain visible;
`--ignore-vuln`, shell exit suppression, or a CI allow-failure flag may not be added
silently.

## Frontend lint and formatting

Adopt Biome as the single new frontend lint/format solution. One exact
`@biomejs/biome` development dependency and the npm lock supply the executable; no
global installation is required. Biome is preferred over a combined ESLint/Prettier
stack because it provides one maintained configuration and one deterministic check for
the current Vite, React, and TypeScript source.

The configuration covers application source, tests, and checked-in frontend config,
while excluding dependencies, build output, and coverage artifacts. It preserves the
existing source conventions where practical and enables:

- deterministic formatting;
- stable recommended correctness rules;
- React hooks top-level and exhaustive-dependency correctness;
- unused/dead imports and variables where they can be identified safely;
- stable JSX accessibility rules appropriate to the current components.

TypeScript remains the type checker and is not replaced by lint. CI runs one read-only
Biome check that includes lint and formatting; local npm scripts provide the same check
and an explicit write-format command. Unsafe fixes are never applied in CI. Any rule
exception is narrow, local, explained, and may not disable an entire correctness or
accessibility category merely to adopt the tool.

No second formatter or overlapping frontend linter is added.

## Frontend coverage baseline and gate

The pre-spec baseline was measured from the current commit with Node 22.23.2,
Vitest 4.1.10, the matching V8 coverage provider, and all 79 existing frontend tests.
Coverage includes `src/**/*.{ts,tsx}` and excludes test files, test setup, type-only
declarations, generated output, and dependencies.

| Metric | Measured baseline | Initial CI floor |
| --- | ---: | ---: |
| Statements | 86.10% (1,587 / 1,843) | 85% |
| Branches | 75.95% (1,071 / 1,410) | 75% |
| Functions | 87.25% (445 / 510) | 86% |
| Lines | 89.24% (1,460 / 1,636) | 88% |

The floors are global, explicit Vitest thresholds. They are intentionally rounded
below the measured baseline to absorb non-semantic instrumentation noise while still
failing meaningful regression. A threshold reduction requires new measured evidence
and an approved spec change; normal improvements do not automatically ratchet the
numbers or force low-value tests.

Auth/session behavior, routing/protected navigation, Pipeline transitions and forms,
Customer/Product actions, and WhatsApp Inbox reconciliation/polling are already
represented in the current suite. The notable critical-area baseline gap is
`useWhatsAppInbox.ts` at 76.05% statements, 57.50% branches, 69.04% functions, and
80.80% lines; the thin `WhatsAppInboxPage.tsx` wrapper is also only 50% statements and
42.85% functions. These are documented gaps, not a reason to manufacture coverage-only
tests. A future behavioral change in those paths must add focused tests for the changed
polling, reconnect, race, or action behavior.

Add the exact `@vitest/coverage-v8` version matching Vitest, a local coverage script,
text and JSON summary output, and an HTML/LCOV artifact on pull requests or failures.
Artifact upload uses a pinned Action and runs even when the threshold gate fails, with
short retention and no repository write permission.

## Docker Compose CI smoke test

A separate integration job exercises the declared repository entry point instead of a
parallel server setup:

1. provide synthetic CI-only environment values and an isolated Compose project;
2. run `docker compose build` and `docker compose up -d --wait`;
3. require PostgreSQL, backend, and frontend health checks to become healthy within a
   bounded timeout;
4. verify backend `/health` returns the expected database-backed success;
5. verify the frontend root returns a successful HTTP response;
6. request `/api/auth/me` through the frontend Vite proxy and require the expected
   unauthenticated `401` JSON response, proving frontend-to-backend routing rather than
   accepting a static frontend response;
7. verify the running backend is at the single Alembic head;
8. on failure, print bounded service status/log diagnostics, then always run
   `docker compose down -v --remove-orphans`.

The job uses the repository Dockerfiles and Compose file. It does not invoke pytest,
Vitest, Ruff, mypy, frontend build, or audit commands again. It is a required push/PR
smoke gate, not a production deployment and not a live Meta or WordPress test.

## GitHub Actions supply-chain hardening

Every external `uses:` reference, including GitHub-authored checkout, setup, and
artifact Actions, is pinned to a verified full-length commit SHA. A trailing comment
retains the reviewed human-readable release such as `# v7`; dependency update reviews
verify that a replacement SHA belongs to the upstream repository and tag.

Workflow-level `permissions: contents: read` remains the maximum token grant for jobs
that check out the repository. Jobs that do not need repository contents use empty
permissions. No `write`, `id-token`, package, deployment, issue, pull-request, or
security-event permission is granted by this scope. Actions and container images are
updated only through reviewed diffs, never a floating branch or major tag.

## Pre-commit alignment

Pre-commit continues using repository-local commands from the locked Python virtual
environment and frontend `node_modules`; it installs no global tools. Fast hooks cover
the same Ruff lint/format, mypy strict, and Biome read-only check used by CI. Hooks use
path filters so frontend checks run only for relevant frontend changes and Python
checks retain their current scope.

Canonical lock regeneration/freshness, vulnerability network access, PostgreSQL tests,
coverage, npm audit, Docker builds, and Compose smoke remain CI or explicit developer
commands because they are slow, networked, or stateful. The README documents one
locked bootstrap and the exact pre-commit/full-quality commands so local and CI names
do not drift.

## SDD and test traceability

For new specs, important acceptance tests should reference the owning `CRM-NNN AC-NN`
in a test docstring, adjacent comment, or clearly documented test group where practical.
One integration test may cover several criteria and one criterion may require several
tests. Small implementation-detail tests need no artificial reference.

No historical test is retrofitted solely for traceability, and no automation counts
tests per criterion or fails because an AC string is absent. Reviewers use the
references as navigation evidence, not as a substitute for verifying behavior.

## Quality invariants

CRM-015 adds gates; it does not weaken existing ones:

- `mypy --strict backend/app backend/tests` and the zero-`Any`/zero-unjustified-ignore
  culture remain mandatory for new and modified Python;
- Ruff lint and format remain the only backend lint/format gates;
- backend coverage remains at least 93%, from the approved measured 93.56% baseline,
  unless a future approved spec records new measured evidence;
- backend tests continue using PostgreSQL, with concurrency/performance suites retaining
  their existing opt-in boundaries;
- TypeScript strict, Vitest, Vite build, and npm audit at high severity remain required;
- compileall, Alembic check/current, Docker health checks, and Docker Compose startup
  expectations remain required;
- no gate may be skipped, marked allow-failure, or duplicated with a conflicting tool
  merely to make CI green.

## Data model

No database schema, migration, persisted product data, or application model changes.
Locks, scanner exceptions, lint configuration, coverage output configuration, and CI
metadata are repository quality artifacts only.

## Contracts / API

No public backend or frontend contract changes. The expected unauthenticated
`/api/auth/me` response is used only as an existing proxy smoke assertion.

Developer-facing contracts are the documented lock update command, locked install
commands, npm lint/format/coverage scripts, pre-commit command, vulnerability audit,
and Docker Compose smoke procedure.

## Security and failure behavior

- Lock hashes protect artifact integrity but do not replace vulnerability review.
- Scanner results and exception metadata contain package/advisory identifiers only;
  they contain no application secrets or customer data.
- CI uses synthetic credentials and Fake WhatsApp/storage modes. It never requires
  Meta, WordPress, production database, registry, or package-index credentials.
- A missing/stale lock, vulnerability, lint/format error, coverage regression,
  unhealthy Compose service, mutable Action reference, or quality-gate regression
  fails the responsible job with reviewable output.
- Failure diagnostics redact environment values and never publish `.env`, database
  credentials, JWT secrets, intake signing secrets, provider payloads, or customer data.

## Edge cases

- A top-level dependency range may remain unchanged while a new transitive release is
  published; the committed lock keeps the installed graph unchanged.
- A lock generated under a different Python/platform/resolver is rejected by the
  canonical freshness check rather than normalized silently.
- An advisory without a fix still fails unless its explicit, unexpired applicability
  exception is reviewed; lack of an upstream release is not a silent waiver.
- A coverage failure still uploads its report, while a test-process crash must not be
  misreported as a coverage-only regression.
- The proxy smoke expects `401`, not `200`; success means the request reached the
  existing authenticated backend route and was rejected correctly.
- Compose teardown runs after startup, assertion, or migration failure and removes its
  isolated volumes without touching a developer or production project.
- A new important acceptance test may reference multiple ACs; traceability never
  prescribes test granularity.

## Acceptance criteria

- AC-01: The canonical Python 3.13 resolver produces committed exact, hash-checked
  runtime and development locks whose package/version graph and bytes are identical
  for an unchanged commit and toolchain.
- AC-02: Backend CI and Docker runtime/quality targets install only the appropriate
  committed locks with hash checking, and the documented containerized update workflow
  makes every dependency/toolchain upgrade an explicit reviewed diff without global
  tools.
- AC-03: Pinned `pip-audit` scans the locked runtime and development graphs, fails on
  every unwaived known vulnerability including relevant high/critical findings, retains
  reviewable output, and accepts only explicit expiring reviewed exceptions.
- AC-04: One pinned Biome configuration and local npm scripts deterministically check
  React/TypeScript formatting, hooks, practical unused code, and JSX accessibility in
  CI without adding an overlapping frontend formatter/linter.
- AC-05: Vitest reports statements, branches, functions, and lines for the documented
  source set, enforces the measured 85/75/86/88 floors, and retains useful coverage
  artifacts without adding percentage-only tests for documented critical-area gaps.
- AC-06: A required CI smoke job builds and starts the repository with Docker Compose,
  waits for healthy services, verifies backend health, frontend HTTP, frontend proxy
  authentication behavior, and Alembic head, and always performs clean teardown without
  rerunning full suites.
- AC-07: Every third-party GitHub Action uses a verified immutable full commit SHA with
  its readable release comment, container/toolchain references are immutable, and no
  workflow receives more than read-only contents permission.
- AC-08: Fast pre-commit hooks use the same locked Ruff, mypy, and Biome checks as CI,
  while network audits, coverage, Docker, and PostgreSQL suites remain documented
  explicit/CI gates rather than slow local hooks.
- AC-09: New important acceptance tests reference their owning `CRM-NNN AC-NN` where
  practical, with no historical retrofit or brittle one-test-per-AC enforcement.
- AC-10: All pre-existing backend/frontend tests, 93% backend coverage, mypy strict,
  Ruff, PostgreSQL, compileall, TypeScript strict, Vite build, npm audit, Alembic,
  performance boundaries, and Docker health gates remain enabled and green with no
  business, API, schema, architecture, authentication, or UX change.

## Open decisions

None

## Follow-up / future specs

- Dependency upgrades that change application behavior or require migration belong to
  the owning feature/security spec rather than this quality baseline.
- A higher frontend coverage floor may be proposed only after meaningful behavior tests
  raise the measured baseline sustainably.

## Implementation notes

Prefer small checked-in scripts with explicit inputs and exit codes for lock freshness,
audit exception validation, and Compose assertions. Shell glue must fail closed and
must not suppress scanner or service failures. Keep generated reports out of source
control and use short-lived CI artifacts.

Adopt the quality tooling and formatting in reviewable mechanical commits if needed,
but do not mix dependency upgrades, application refactors, test rewrites, or product
changes into CRM-015.
