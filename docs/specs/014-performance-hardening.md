# CRM-014 — Backend Performance Hardening

Status: Approved
Owner: FAA CRM team
Last updated: 2026-08-12
Implementation commit: —

## Goal

Resolve the Release Candidate performance findings with bounded SQL and operational
work, reproducible PostgreSQL evidence, and no premature architecture change.

## Context

CRM-004 calculates commercial metrics directly in PostgreSQL. CRM-007 derives
WhatsApp Inbox and polling projections from current persisted rows. CRM-011 and
CRM-013 provide consent-safe, PostgreSQL-backed Broadcast processing, while CRM-012
exposes `Opportunity.reopen_count` from immutable reopen events.

The current implementation has four evidence gaps:

- Broadcast recipient selection and full validation look up each Customer and latest
  consent separately, so SQL statement count grows with recipient count.
- Broadcast provider dispatch is sequential, but the configured batch size is only
  required to be positive and its current default can keep an API request open for a
  long time.
- the timeline zero-fills one Python item per requested day or month without a maximum
  period;
- existing query timing coverage uses a small unit-test fixture and does not provide
  release-scale PostgreSQL plans or repeatable benchmark artifacts.

This spec hardens those boundaries without changing FAA business rules, public
resource semantics, or the existing PostgreSQL/SQLAlchemy architecture.

## Dependencies

- CRM-004 — Commercial Metrics
- CRM-006 — WhatsApp Internal API
- CRM-007 — WhatsApp Query Layer
- CRM-011 — WhatsApp Broadcast Execution
- CRM-012 — CRM Commercial Completion
- CRM-013 — Backend Concurrency Hardening

## Scope

- Batch Broadcast Customer and latest-consent reads so validation statement count is
  independent of recipient count.
- Bound one Broadcast processor call to a small sequential operational batch.
- Add granularity-specific maximum periods to the metrics timeline.
- Add deterministic, opt-in PostgreSQL scale benchmarks and release profiles.
- Add reproducible `EXPLAIN (ANALYZE, BUFFERS)` tooling and an operator runbook for
  the critical queries in this spec.
- Measure polling change-key queries and the Opportunity `reopen_count` projection
  before changing their query shapes.
- Permit only measured, behavior-preserving query improvements within the existing
  architecture.

## Non-goals

- Redis, Celery, caching infrastructure, materialized views, a new job queue, or a
  general analytics/read-model framework.
- New polling tables, materialized change timestamps, WebSockets, or SSE.
- Parallel Broadcast provider dispatch or an unmeasured Meta concurrency level.
- `pg_trgm`, fuzzy search, or a Customer/Conversation search redesign.
- New frontend behavior, business-rule changes, role/visibility changes, or provider
  policy changes.
- A new database engine, ORM, metrics definition, cursor format, or pagination model.
- Making the large performance profile mandatory on every CI push.

## Performance invariants

### Broadcast validation query count

Recipient selection, `validate`, and `confirm` must preserve CRM-011 eligibility and
result semantics while replacing per-recipient reads with bounded set-based queries:

1. load the relevant recipients explicitly in stable recipient/selection order;
2. load all referenced Customers in one bounded query keyed by sorted unique ID;
3. load at most one current consent event for every requested
   `(customer_id, normalized_phone)` pair in one bounded query;
4. select current consent only from events with `effective_at <= now`, ordered latest
   by `(effective_at DESC, id DESC)` within each exact Customer/phone pair;
5. map the results into typed in-memory lookups and produce issues, consent IDs, input
   digests, duplicate outcomes, and invalid/missing lists in their existing
   deterministic order.

The implementation may use a PostgreSQL window function, `DISTINCT ON`, or an
equivalent SQLAlchemy 2.x statement, provided ties are resolved exactly by
`(effective_at, id)` and no event from another Customer or phone can participate.
Absent consent continues to fail closed. Backdated events, future-effective events,
later opt-outs, Customer deletion, phone changes, and duplicate normalized phones keep
their CRM-011 behavior.

Validation mapping must use explicit columns/typed DTOs or relationships protected by
`raiseload`; it must not trigger ORM lazy loading. Query-count tests compare the same
operation with 1, 10, and at least 100 recipients and require one fixed upper bound,
excluding the intentionally external provider template lookup and media-storage
boundary. The exact fixed statement count may differ between validation phases, but it
must not increase with recipient count.

CRM-013 dispatch-start consent revalidation remains per claimed recipient under the
shared consent/dispatch advisory lock and global row-lock order. It is bounded by the
processor batch size and must not be combined in a way that weakens the opt-out race
guarantee.

### Broadcast processor pacing

One call to the shared Broadcast processor claims and attempts at most 10 recipients.
The backend default and hard maximum are both 10; startup/configuration rejects zero,
negative, or larger values. The authenticated API accepts no batch-size, loop-count,
concurrency, or duration override, so callers cannot request unbounded work.

Provider dispatch remains sequential with concurrency exactly 1. Each recipient keeps
the CRM-013 phases of short claim/dispatch-start transactions, provider I/O with no
open database transaction or held lock, and short reconciliation transactions. One
provider response or rate-limit backoff therefore cannot hold database locks for the
rest of the batch.

The existing CLI and an external scheduler are the preferred repeated-processing
path. One CLI invocation processes one bounded batch and reports remaining work; the
scheduler invokes it again according to deployment cadence. The API also processes
only one batch per request and never loops until a Broadcast is empty.

No artificial parallelism or fixed request-rate claim is introduced. Existing
provider retry/backoff and rate-limit evidence remain authoritative. Raising the batch
cap, adding concurrent dispatch, or adding a rate-based pacing algorithm requires
measured Meta latency/rate-limit evidence and a separately approved spec change.

### Metrics timeline limits

Only `/api/metrics/timeline` gains granularity-specific period limits. Existing
overview, product, source, province, and pipeline behavior is unchanged.

Limits are measured as the number of zero-filled Buenos Aires calendar buckets that
the existing half-open `[from, to)` period would return:

| Granularity | Maximum buckets | Intent |
| --- | ---: | --- |
| `DAY` | 366 | bounded operational daily analysis |
| `MONTH` | 1,200 | up to 100 years of FAA historical analysis |

Exactly the maximum is valid; one additional bucket is rejected before aggregate SQL
or bucket materialization. Offset changes and partial first/last buckets continue to
use `America/Argentina/Buenos_Aires` and the existing half-open period semantics.

The service and request boundary share a typed period-limit contract. An oversized
request returns `422` through a narrow typed validation result with stable code
`METRICS_TIMELINE_PERIOD_TOO_LARGE` and the requested granularity, requested bucket
count, and maximum bucket count. This does not create a general error-envelope
redesign. Unsupported granularity, naive timestamps, and reversed/empty periods retain
their existing validation behavior.

### Scale benchmark profiles

Performance measurement runs against real PostgreSQL in a dedicated non-production
database with fixed synthetic data, a fixed random seed, UTC timestamps, and realistic
FAA distributions for Customers, Opportunities, links, attachments, consent, message
directions/states, and status events. Seed generation is deterministic and refuses to
truncate or seed a database that is not explicitly identified as a performance
database.

Required profiles are:

| Profile | Conversations | Messages/status events | Use |
| --- | ---: | ---: | --- |
| `baseline` | approximately 1,000 | approximately 10,000 | normal release benchmark |
| `large` | approximately 10,000 | approximately 100,000 | optional release/capacity profile |

The larger count may be split between Messages and status events, but it must retain
enough events to exercise the correlated message change key. Each artifact records the
exact generated row counts, seed, profile, PostgreSQL version, migration revision,
commit, command arguments, warm-up count, sample count, and host/container context.

The benchmark runner measures at least:

- conversation list, including representative waiting/unread and search filters;
- conversation detail;
- newest/older message history;
- conversation changes polling;
- message changes polling;
- critical overview, product, province, and day/month timeline metric queries with
  representative filters;
- Broadcast recipient validation and confirmation revalidation.

Each operation has warm-ups and repeated samples and emits machine-readable JSON plus
a concise table containing rows returned, SQL statement count, median, P95, and max.
Correctness, deterministic order, bounded page sizes, and query-count invariants are
hard failures. Wall-clock results are release evidence and are evaluated against the
existing CRM-007 targets on a documented environment; they are not added as
timing-sensitive assertions to the normal unit-test suite.

The `baseline` profile is required for Release Candidate verification. The `large`
profile is manual/optional unless its measured runtime later proves acceptable for a
scheduled release job. Normal push CI retains fast correctness and query-count tests
and does not seed either scale profile by default.

### PostgreSQL EXPLAIN tooling and runbook

A reviewed command/script and `docs/runbooks/backend-performance.md` must reproduce
`EXPLAIN (ANALYZE, BUFFERS)` for the actual SQLAlchemy query shapes against either
benchmark profile. The workflow seeds or verifies the selected profile, runs
PostgreSQL `ANALYZE`, uses representative fixed parameters/cursors, wraps lock-taking
read plans safely, and writes text/JSON plan artifacts without production data or
secrets.

The runbook covers:

- conversation changes polling;
- message changes polling;
- overview/product/province/timeline metrics with source, Product, and province
  filters where applicable;
- Broadcast recipient claiming;
- latest marketing consent lookup, including the batched validation form;
- Opportunity list/detail queries that include `reopen_count`.

Each captured plan records estimated versus actual rows, loops, scan/join strategy,
sorts or spills, buffer hits/reads, planning time, and execution time. A sequential
scan alone is not evidence of a defect. A query or index change requires a reproducible
bad plan or benchmark regression plus before/after plans showing material improvement
without changing result semantics.

No index is pre-authorized by this spec. If measurement identifies a necessary index,
the exact index and before/after evidence must be added to this spec before its
implementation; every PostgreSQL schema change then uses Alembic. No index may be
added only because a predicate or ordering appears likely to need one.

### Polling, search, and `reopen_count`

Conversation and message polling retain CRM-006/007 cursor contents, strict
`(resource_updated_at, resource_id)` ordering, stable tie handling, unfiltered
incremental upserts, `has_more`, empty-page cursor retention, and observation of the
same related-resource changes.

The first response to a slow polling plan is measurement and the smallest
behavior-preserving SQL/query/index improvement. This scope does not materialize a
change table or new timestamp. If plans prove that existing derived change keys cannot
meet the approved targets, the evidence must be recorded and a spec amendment must
explicitly approve any new persisted projection before implementation.

Customer/Conversation contains-search remains on the existing conservative semantics.
`pg_trgm` is documented only as a future option if real search cardinality, frequency,
and plans warrant it; it is not installed, migrated, or required by this scope.

`Opportunity.reopen_count` remains the count of immutable
`OpportunityReopenEvent` rows and `is_reopened` remains `reopen_count > 0`. The
benchmark and EXPLAIN tooling audit the current correlated `column_property` in list
and detail queries. It changes only if measured subplan loops or runtime justify a
refactor; an allowed refactor uses an explicit aggregate/batched query or another
existing-SQLAlchemy shape, preserves every public response, and does not store or cache
a mutable count.

## Data model

No schema change is planned. Benchmark data and artifacts are development/release
tools, not application persistence. No cache table, materialized view, change table,
denormalized timestamp, stored `reopen_count`, or PostgreSQL extension is introduced.

Any later evidence-backed index requires the spec update and Alembic process described
above; it is not implicitly authorized by this spec.

## Contracts / API

- Existing WhatsApp query, polling, Broadcast, consent, metric response, and
  Opportunity response payloads remain compatible.
- `POST /api/whatsapp/broadcasts/{id}/process` continues accepting only its command ID
  and performs no more than 10 sequential attempts.
- `/api/metrics/timeline` adds only the documented typed oversized-period `422` result.
- Benchmark and EXPLAIN commands are operator/developer contracts, not authenticated
  public HTTP endpoints.

## State transitions and concurrency

No CRM, Message, recipient, Broadcast, consent, or Opportunity state transition
changes. CRM-013 advisory/row-lock order, latest-attempt projection, idempotency,
dispatch-start boundary, stale-work handling, and `UNKNOWN` behavior remain mandatory.
Provider I/O, benchmark orchestration, and EXPLAIN artifact writing never occur while
application database locks are held.

## Security and operations

- Performance datasets are synthetic and contain no FAA Customer identity, message
  body, consent evidence, provider payload, media, token, or secret.
- Commands redact database credentials and refuse destructive setup against an
  unguarded database.
- Artifacts use operation/profile identifiers, aggregate counts, and plans only; they
  do not become API responses or logs with high-cardinality customer/message labels.
- Both current roles retain their existing global visibility and permissions.

## Edge cases

- Consent events with equal `effective_at` use greatest `id`; a future-effective event
  is ignored until effective, and a later effective opt-out wins exactly as before.
- Missing/deleted Customers, changed phones, duplicate phones, and absent consent keep
  the existing ordered recipient outcome and fail-closed behavior.
- A tenth processor recipient is allowed and an eleventh remains `READY` for a later
  invocation; duplicate/replayed processor commands remain idempotent.
- Timeline periods crossing daylight-saving/offset boundaries are counted by Buenos
  Aires calendar bucket, not elapsed UTC hours. Empty but valid periods still return
  zero-filled buckets.
- Equal polling timestamps and late related-resource updates preserve current cursor
  behavior even if the SQL shape is optimized.
- An expensive `reopen_count` plan may be left unchanged when measured FAA-scale cost
  is acceptable; a correlated expression is not itself proof of a performance bug.

## Acceptance criteria

- AC-01: Broadcast recipient selection, validation, and confirmation use bounded batch
  Customer/latest-consent queries with no ORM lazy loading, and statement-count tests
  prove the count does not grow from 1 to at least 100 recipients.
- AC-02: Batched consent lookup preserves exact Customer/phone matching, future-event
  exclusion, deterministic `(effective_at, id)` latest ordering, opt-in/opt-out
  correctness, validation digest, and ordered recipient outcomes.
- AC-03: One API/CLI processor invocation attempts at most 10 recipients sequentially,
  accepts no caller work-size override, keeps provider I/O outside DB transactions,
  and preserves CRM-013 idempotency, lock order, opt-out, and `UNKNOWN` behavior.
- AC-04: Timeline accepts at most 366 `DAY` or 1,200 `MONTH` Buenos Aires buckets,
  accepts exact boundaries, rejects one bucket over with the typed oversized-period
  `422`, and preserves all CRM-004 metric formulas, filters, precision, bucketing, and
  zero filling.
- AC-05: A deterministic opt-in PostgreSQL benchmark command seeds the documented
  baseline profile, measures every required query/validation operation with warm-ups
  and repeated samples, and emits reproducible machine-readable evidence; the larger
  profile is available without becoming a normal push-CI requirement.
- AC-06: A documented command reproduces `EXPLAIN (ANALYZE, BUFFERS)` after `ANALYZE`
  for polling, filtered metrics, recipient claiming, latest consent, and Opportunity
  `reopen_count` queries using production-like synthetic data and safe parameters.
- AC-07: No index, change table/timestamp, denormalized count, materialized view,
  cache, or PostgreSQL extension is added without the documented measured evidence and
  required spec/Alembic approval; `pg_trgm` remains future-only.
- AC-08: Polling regression tests preserve cursor semantics, deterministic ordering,
  incremental related-resource changes, pagination, and query-layer public behavior;
  metrics and Opportunity responses remain behaviorally compatible.

## Open decisions

None

## Follow-up / future specs

- `pg_trgm` or another search optimization only if real Customer/Conversation search
  volume and measured PostgreSQL plans justify it.
- Persisted polling projections or alternate realtime transport only if the baseline
  query improvements cannot meet measured requirements and a separately approved spec
  defines the persistence and client behavior.
- Higher Broadcast throughput, parallel provider dispatch, or rate-based pacing only
  after production Meta latency/rate-limit evidence establishes a safe operating
  envelope.

## Implementation notes

Prefer small operation-specific typed query helpers over a repository abstraction.
Reuse the existing statement counter, query projection DTOs, strict metrics types,
advisory/row-lock helpers, Docker PostgreSQL service, and CLI conventions. Keep seed,
benchmark, and plan-capture responsibilities separate so unit tests can verify their
deterministic contracts without running release-scale timing workloads.
