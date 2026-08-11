# CRM-013 — Backend Concurrency Hardening

Status: Approved
Owner: FAA CRM team
Last updated: 2026-08-11
Implementation commit: N/A

## Goal

Close the concurrency and idempotency risks found during the Release Candidate audit
without changing approved FAA CRM or WhatsApp business behavior.

## Context

CRM-005, CRM-006, CRM-009, and CRM-011 already define durable WhatsApp Messages,
provider reconciliation, `UNKNOWN` semantics, marketing consent, and PostgreSQL-backed
Broadcast processing. The current implementation has narrower correctness gaps around
absent-row idempotency checks, consent immediately before dispatch, competing recipient
projection updates, and inconsistent row-lock acquisition order. This spec hardens
those boundaries; it does not redefine the approved state machines or API behavior.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API
- CRM-009 — Meta Cloud API Provider
- CRM-011 — WhatsApp Broadcast Execution

## Scope

- Serialize consent append and Broadcast dispatch-start for one Customer and normalized
  phone through one shared transaction-level PostgreSQL advisory lock.
- Make `WhatsAppMessage.dispatch_state: PENDING -> IN_PROGRESS` the exact boundary at
  which a provider dispatch has started.
- Project each `WhatsAppBroadcastRecipient` deterministically from its latest Message
  attempt for current operational state, failure evidence, and retry eligibility.
- Close absent-row races for globally unique consent, Broadcast-create, and outbound
  Message idempotency keys while preserving current replay/conflict contracts.
- Define and apply one lock-order policy to affected WhatsApp, consent, and Broadcast
  mutations.
- Add real PostgreSQL, multi-session concurrency tests for dispatch, claiming,
  idempotency, webhook reconciliation, retries, stale work, and rollback behavior.

## Non-goals

- Changes to approved business rules, recipient eligibility, consent ordering, Message
  or Broadcast states, role visibility, or public API payloads.
- Redis, Celery, a distributed lock service, a new job queue, or a WhatsApp architecture
  redesign.
- Frontend changes, campaign authoring, template policy changes, or provider-specific
  domain behavior.
- Holding a database transaction or lock during provider/network I/O.
- Weakening `UNKNOWN`, automatically retrying ambiguous sends, or treating provider
  acceptance uncertainty as a definitive failure.

## Concurrency invariants

### Consent and dispatch-start

For the exact pair `(customer_id, normalized_phone)`, consent append and Broadcast
dispatch-start acquire the same transaction-level advisory lock. The canonical advisory
identity is namespaced for consent/dispatch and contains both values; it is derived and
acquired through the existing advisory-lock helper so all advisory keys use one stable,
sorted mechanism.

The exact provider dispatch-start boundary is the persisted transition of the attempt's
`WhatsAppMessage.dispatch_state` from `PENDING` to `IN_PROGRESS`. A recipient claim or
`WhatsAppBroadcastRecipient.status=IN_PROGRESS` is work ownership only and does not
mean provider I/O has started.

One short database transaction must:

1. acquire the shared Customer/phone consent-dispatch advisory lock;
2. acquire the required rows according to the global lock order and recheck the claim,
   recipient, latest Message attempt, Customer/phone, and latest effective consent;
3. block the recipient without a provider call when it is no longer eligible;
4. otherwise transition only the current `PENDING` Message to `IN_PROGRESS` and commit.

Only after that commit may provider I/O begin. Consent append acquires the same shared
lock before appending and determining current consent. Therefore, an `OPT_OUT` that
wins the lock commits before dispatch-start and blocks it; a dispatch-start that wins
first has durably crossed the approved boundary before the later opt-out. Provider I/O,
template discovery, media transport, and network waits never occur while a database
transaction is open.

Claiming remains a separate short transaction. It uses stable recipient ordering and
`SELECT FOR UPDATE SKIP LOCKED`, persists the claim, and ensures exactly one initial
`PENDING` Message exists before dispatch-start. A retry reuses its already-authorized
`PENDING` retry Message. Unique constraints remain the final protection against a
second initial Message.

### Latest-attempt Broadcast projection

One deterministic recompute function is the only writer of a recipient's current
operational Message projection. It selects the latest Message attempt for that
recipient by greatest local Message `id`, consistent with the persisted retry chain,
and derives from that attempt only:

- recipient `status`;
- safe failure code and message;
- whether an explicit operational retry is currently eligible.

Retry creation must continue to point to the immediately prior failed attempt. A status
event or provider reconciliation for an older Message updates and preserves that
attempt's own monotonic evidence but cannot replace the projection governed by a newer
Message. Message attempt identity, immutable send inputs, retry linkage, and all
append-only status events remain fully preserved. Recipient timestamps that summarize
historical evidence may remain cumulative, but they cannot govern current status or
retry eligibility.

The same recompute path runs after dispatch changes, provider responses, status
webhooks, retry authorization, and stale-claim recovery. Callers do not assign a
competing recipient status or safe failure projection directly.

### Global idempotency

Before checking or inserting an absent globally unique row, the transaction acquires a
namespaced advisory lock for the normalized key:

- marketing consent `client_event_id`;
- Broadcast `client_generated_id`;
- outbound WhatsApp Message `client_generated_id`.

All outbound Message UUIDs are globally unique under the existing database constraint,
including human and Broadcast attempts. After acquiring the key lock, the service
re-reads the row and applies the existing contract: the same key plus the same fully
normalized request returns the existing effect/resource, while the same key plus a
different normalized request raises the existing domain conflict. Server-generated
timestamps and provider results are not client payload differences.

Existing unique constraints remain the final integrity boundary. A known constraint
race must be rolled back at the smallest safe transaction boundary, re-read, and mapped
to replay or the existing domain conflict as appropriate. Normal concurrent requests
must never expose a raw SQLAlchemy/PostgreSQL `IntegrityError` through a service or API.
Broadcast lifecycle command keys retain their existing per-Broadcast scope and receive
the same concurrent replay/conflict guarantees.

### Global lock order

Affected mutations use this acquisition order, skipping resource classes they do not
need but never acquiring an earlier class after a later one:

1. all transaction-level advisory locks—idempotency, consent/dispatch, and Customer
   identity—deduplicated and sorted by their existing numeric advisory key;
2. `Customer` rows, ascending by ID;
3. `WhatsAppBroadcast` rows, ascending by ID, only when lifecycle state is mutated;
4. `WhatsAppBroadcastRecipient` rows, ascending by ID;
5. `WhatsAppConversation` rows, ascending by ID;
6. `WhatsAppMessage` rows, ascending by ID;
7. dependent attachment, status-event, audit, or other evidence rows.

An unlocked lookup may discover IDs needed to build the lock set, but every relevant
predicate is revalidated after the ordered locks are held. Multi-row operations sort
IDs before locking. Status-webhook and provider-response paths must discover the
Message graph first, then lock the required Broadcast/Recipient/Conversation/Message
rows in this order before reconciliation and projection recompute.

The recipient claim query may use `SKIP LOCKED` without taking a coarse Broadcast row
lock that serializes all workers; lifecycle validation is rechecked transactionally,
and Broadcast completion is a separate ordered transaction. No row or advisory lock is
held across provider I/O.

## Data model

No new entity, business field, state, or schema migration is required. Existing unique
constraints on consent client event ID, Broadcast client-generated ID, outbound Message
client-generated ID, one initial Message per recipient, and one recipient phone per
Broadcast remain mandatory final protections.

Messages and status events retain their existing durable history. The recipient remains
a projection over that history rather than a competing source of truth.

## Contracts / API

No endpoint, request, response, authentication, or status-code contract changes.
Identical concurrent replays return the existing successful resource/effect using the
current created/replayed semantics. Changed key reuse returns the existing domain
conflict and HTTP `409` mapping. Validation failures retain their existing safe
behavior; database exception details are never an API contract.

Internal services use strictly typed inputs, projection results, lock identities, and
domain errors. Routers remain thin and do not catch or interpret database races as
business logic.

## State transitions

All CRM-005 and CRM-011 transitions remain unchanged. This spec clarifies their
transaction boundaries:

```text
claim committed: recipient owns one PENDING Message (provider not started)
dispatch-start committed: Message PENDING -> IN_PROGRESS
provider I/O: outside every DB transaction
reconciliation: IN_PROGRESS -> ACCEPTED | DEFINITIVE_FAILED | UNKNOWN
```

An expired claim with a provably `PENDING` attempt may be reclaimed without a new
Message or provider call. A stale `IN_PROGRESS` attempt is ambiguous, becomes
`UNKNOWN`, and is never automatically resent. Status reconciliation remains monotonic
within each Message attempt; recipient current state is then recomputed from the latest
attempt.

## Real PostgreSQL concurrency tests

Concurrency acceptance tests use the repository's real PostgreSQL engine and at least
two independent `SessionLocal` sessions/connections coordinated by deterministic
barriers or provider test hooks. They do not use SQLite, one shared SQLAlchemy Session,
or process-memory mutexes as a correctness substitute. Test data is committed before
workers start and cleaned through reviewed PostgreSQL transactions.

Required interleavings cover:

- concurrent `OPT_OUT` append versus Broadcast dispatch-start for the same Customer and
  normalized phone, with each lock winner exercised;
- two processors operating on one Broadcast simultaneously, claiming different
  recipients through `SKIP LOCKED` and never double-sending;
- concurrent replay of the same Broadcast create and lifecycle command/idempotency key;
- concurrent replay of the same consent event ID;
- concurrent replay of the same globally unique outbound Message UUID;
- an old-attempt status webhook racing with creation or reconciliation of a newer retry;
- a current-attempt status webhook racing with processor provider-result
  reconciliation;
- safe recovery of stale `PENDING` claims and conservative handling of stale
  `IN_PROGRESS` claims;
- injected failures before commit in claim, dispatch-start, and reconciliation paths.

Tests assert durable rows and recorded provider calls after both sessions finish. They
must prove no duplicate provider calls, no duplicate initial Messages, no lost opt-out,
no stale recipient projection downgrade, no raw `IntegrityError` leak, and complete
transaction rollback without half-applied claim, dispatch, Message, recipient, audit,
or projection state.

## Security & permissions

Authentication, actor attribution, global visibility for `SUPERVISOR` and `VENDEDOR`,
safe provider errors, and secret/redaction rules remain those of CRM-006 and CRM-011.
Advisory lock identities are internal deterministic hashes; raw phone numbers, payloads,
or provider data are not logged or exposed.

## Edge cases

- An `OPT_OUT` waiting on an already-committed dispatch-start does not erase or
  reinterpret that real attempt, but it blocks every later not-yet-started attempt.
- A claimed recipient with no provider-started attempt is recoverable only with the
  same Message and UUID. A second initial Message is never a recovery mechanism.
- An old attempt may receive newer-timestamped provider evidence after a retry exists;
  its own evidence is retained, but Message age is determined by attempt identity, not
  webhook occurrence time.
- Concurrent same-key requests with different normalized payloads deterministically
  produce one effect and one domain conflict, never two effects or a database error.
- A webhook may arrive before provider-response reconciliation or after Broadcast
  completion. Ordered locks and one recompute path preserve both event history and the
  latest-attempt projection.
- A processor crash after dispatch-start is ambiguous even if no response was stored;
  stale recovery preserves `UNKNOWN` and does not infer that the provider was not
  called.

## Acceptance criteria

- AC-01: Consent append and Broadcast `PENDING -> IN_PROGRESS` dispatch-start for one
  Customer/normalized phone serialize on the same transaction advisory lock; both race
  orders prove no lost opt-out and no provider call after an opt-out wins.
- AC-02: Dispatch-start revalidates Customer, phone, consent, claim, recipient, and the
  current `PENDING` Message in one short committed transaction, and provider I/O occurs
  only afterward with no open database transaction or held lock.
- AC-03: One deterministic recompute function derives recipient status, safe failure
  fields, and retry eligibility only from the latest Message ID while preserving every
  attempt and append-only status event.
- AC-04: An old-attempt webhook racing with a newer retry cannot downgrade or otherwise
  overwrite the current recipient projection, regardless of provider event time.
- AC-05: Concurrent identical consent event IDs return one immutable event/effect;
  changed normalized reuse returns the existing domain conflict and neither path leaks
  `IntegrityError`.
- AC-06: Concurrent identical Broadcast create and lifecycle command keys return one
  resource/effect and one audit command effect; changed normalized reuse conflicts
  without a raw database exception.
- AC-07: Concurrent identical globally unique outbound Message UUIDs create and dispatch
  one Message once; changed normalized reuse conflicts without duplicate provider I/O
  or a raw database exception.
- AC-08: Two real-PostgreSQL processors can claim different recipients of one Broadcast
  concurrently via stable `SKIP LOCKED` selection, with exactly one initial Message and
  at most one provider call per recipient.
- AC-09: A status webhook racing with provider-result reconciliation preserves one
  monotonic Message result, one deterministic recipient projection, all status evidence,
  and no duplicate provider call.
- AC-10: Stale `PENDING` work is reclaimed with the same Message/UUID, while stale
  `IN_PROGRESS` work becomes `UNKNOWN` and is never automatically retried or sent
  again.
- AC-11: Multi-session tests exercise the documented advisory and row-lock order across
  Customer, Broadcast, Recipient, Conversation, and Message paths without deadlock or
  lock-order inversion.
- AC-12: Injected failure in claim, dispatch-start, or reconciliation rolls back the
  whole transaction, leaves no half-applied state, and permits only the contractually
  safe replay or recovery behavior.
- AC-13: All concurrency tests use independent sessions against real PostgreSQL and
  prove no duplicate provider calls, duplicate initial Messages, lost opt-out, stale
  projection downgrade, raw `IntegrityError`, or transaction inconsistency.
- AC-14: Strict typing, existing domain errors, existing advisory-lock helpers,
  `SELECT FOR UPDATE`/`SKIP LOCKED`, and all repository quality gates are preserved
  without Redis, Celery, frontend changes, network-held transactions, weakened
  `UNKNOWN`, or automatic retry of ambiguous sends.

## Open decisions

None

## Follow-up / future specs

None

## Implementation notes

Prefer extending the existing advisory-lock helper with stable namespaces and a typed
lock-plan helper over introducing a second locking mechanism. Consolidate recipient
projection writes in `whatsapp_broadcast_projection_service`; Message/status services
should update attempt evidence and invoke recompute rather than assign recipient fields
independently.

Keep claim, dispatch-start, provider I/O, and reconciliation as distinct phases.
Discovery reads used to determine the complete lock set are not authorization or
eligibility decisions; revalidation under the ordered locks is mandatory. Known unique
constraint handling should stay at the smallest service/persistence boundary and map to
the existing typed replay/conflict outcomes.
