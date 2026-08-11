# CRM-011 — WhatsApp Broadcast Execution

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-11
Implementation commit: `e48f9e176873710cd5904d3f3004252a44de2fd6`

## Goal

Execute and track safe WhatsApp broadcasts for marketing content already prepared and
approved outside the CRM, without turning the CRM into a campaign or content-authoring
tool.

## Context

`docs/BUSINESS_RULES.md` permits the CRM to select externally prepared WhatsApp
content/templates, send it to valid recipients, and track delivery while requiring
marketing opt-in and opt-out. CRM-005 through CRM-009 already provide permanent
phone-keyed conversations, real Message dispatch/delivery state, durable media, a
provider boundary, and Meta template discovery. CRM-011 adds consent and batch
execution without redefining those foundations.

The CRM does not create, design, edit, review, or approve a marketing campaign. Meta
and the selected approved template remain the source of truth for template content,
approval status, supported components, and provider policy. A Broadcast is only the
auditable execution record for content prepared by marketing elsewhere.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API
- CRM-008 — WhatsApp Media Storage
- CRM-009 — Meta Cloud API Provider

## Scope

- Persist append-only, phone-specific marketing opt-in and opt-out events.
- Create, inspect, confirm, start, process, and summarize WhatsApp Broadcasts.
- Select explicit Customer recipients and snapshot their normalized phone numbers.
- Deduplicate each Broadcast by normalized phone before confirmation.
- Select a currently approved Meta/provider marketing template by immutable identity.
- Supply one immutable broadcast-level set of named text parameter values when the
  selected external template requires them; no per-recipient interpolation is added.
- Optionally attach one supported image or PDF/document header through CRM-008 when
  the selected approved template accepts or requires dynamic header media.
- Validate consent, recipient identity, template status/components, parameters, media,
  and immutable execution inputs before confirmation and again before dispatch.
- Dispatch in bounded PostgreSQL-backed batches and track every actual attempt through
  one real `WhatsAppMessage`.
- Reconcile accepted, sent, delivered, read, failed, and unknown outcomes into
  recipient and aggregate Broadcast projections.
- Permit explicit retries of eligible failed attempts, preserving the complete Message
  chain.
- Preserve actor, timestamp, validation, selection, dispatch, retry, and outcome
  evidence for audit.

## Non-goals

- Campaign builder, campaign approval workflow, copywriting, content generation, or
  creative editing.
- Segmentation, saved audiences, inferred recipients, contact scoring, or automatic
  recipient selection.
- Meta App, WABA, phone-number, webhook, token, template, or business-verification
  setup.
- Persistent template catalog or template editor.
- Changes to the WhatsApp Inbox or a Broadcast frontend.
- Email or SMS campaigns.
- Analytics dashboard UI, attribution, conversion analysis, or marketing ROI.
- Redis, Celery, a general job queue, or a new realtime transport.
- Native mobile or mobile-specific UI.
- Per-recipient template values, URL/button construction, coupon codes, carousels, or
  template component shapes not represented by the provider-neutral contract.
- Automated parsing of inbound opt-out keywords or bulk external consent imports.

## Business rules

- Marketing prepares and approves the campaign/content outside the CRM. A Broadcast
  references that external work and may not author, edit, or approve it.
- A send is eligible only when the exact Customer and normalized destination phone
  have a latest effective `OPT_IN` event and no later effective `OPT_OUT` event.
- Consent belongs to the normalized phone, not implicitly to every past or future
  phone of a Customer. A Customer phone change does not transfer consent.
- Valid consent originates either directly in FAA CRM (`FAA_CRM`) or in an external
  FAA-controlled source (`EXTERNAL_FAA`) with traceable evidence.
- Consent does not expire automatically. It remains valid until an explicit effective
  `OPT_OUT` or revocation event becomes the latest event for that Customer and phone.
- An opt-out becomes effective immediately when recorded and blocks every future
  Broadcast attempt to that phone, including confirmed or processing Broadcasts.
- Recipient selection is explicit. CRM queries, filters, metrics, Opportunities, and
  inferred segments never add recipients automatically.
- At most one recipient row exists for a normalized phone in one Broadcast. Repeating
  the same phone cannot cause a second initial send.
- Only a currently provider-approved, sendable `MARKETING` template may be confirmed or
  dispatched. Template identity, language, component signature, and approval evidence
  come from the provider; the CRM never marks a template approved.
- One broadcast-level parameter set and optional header media apply identically to all
  recipients. The values are immutable execution inputs supplied from the externally
  prepared content, not CRM-authored copy.
- Confirmation is an explicit user action after validation. Confirmation freezes the
  template, parameters, header media, external reference, label, and recipient set.
- A confirmed or started Broadcast cannot be edited. Operational state, delivery
  evidence, and explicit retries remain appendable. Changed content or recipients
  require a new Broadcast.
- Every actual initial send or explicit retry creates one outbound
  `WhatsAppMessage`; aggregate-only or synthetic send records are prohibited.
- Broadcast Messages are not human replies and never clear or satisfy
  `waiting_for_response`, regardless of acceptance or delivery state.
- `UNKNOWN` means provider acceptance is uncertain. It is never automatically or
  explicitly retried by this feature because a second send could duplicate delivery.
- Processor-level retries never create a second Message silently. Meta/provider
  bounded transport retries inside one existing dispatch attempt remain governed by
  CRM-009.
- Both current roles use the same global Broadcast visibility. This spec adds no
  seller-based or role-based visibility restriction.

## Data model

All timestamps are timezone-aware and persisted in UTC. Schema changes require one or
more Alembic migrations.

### `WhatsAppMarketingConsentEvent`

An append-only event is the authority for consent history:

- `id`;
- `customer_id`, required in this scope;
- `normalized_phone`, the exact destination identity affected by the event;
- `decision`: `OPT_IN` or `OPT_OUT`;
- `source`: `FAA_CRM` or `EXTERNAL_FAA`;
- nullable bounded `evidence_reference`, required for `EXTERNAL_FAA` and containing a
  traceable safe reference rather than raw provider payload or sensitive evidence;
- `occurred_at`, when the represented customer action occurred;
- `effective_at`, supplied for imported external consent and assigned to the append
  time for direct CRM consent;
- `recorded_at` and `recorded_by_user_id`.

Rows cannot be updated or deleted through application services. Current consent for a
Customer and phone is the latest non-future effective event ordered by
`(effective_at, id)`. `FAA_CRM` is auditable through its authenticated actor and
timestamps; `EXTERNAL_FAA` is valid only with its required source evidence. Consent has
no expiry field or time-based invalidation. A direct CRM opt-out uses the append time
as its effective time and therefore blocks future sends immediately. Backdated
`occurred_at` never rewrites effective ordering, and imported `effective_at` cannot be
in the future. Corrections append a new event. Indexes support current-state lookup by
`(customer_id, normalized_phone, effective_at, id)` and history by Customer. The
Customer FK uses `RESTRICT`; consent history is never cascade-deleted.

### `WhatsAppBroadcast`

The execution header contains:

- `id`, immutable internal `label`, and nullable bounded
  `external_campaign_reference` supplied by marketing;
- `status`: `DRAFT`, `CONFIRMED`, `PROCESSING`, or `COMPLETED`;
- optimistic `version` for draft mutations and confirmation;
- template external ID, name, language, category, provider status, header type,
  header-media requirement, and component-signature/hash captured from a complete
  provider snapshot;
- optional CRM-008 `header_media_ref` plus private storage identity and safe immutable
  MIME, filename, size, and checksum evidence; storage keys are never API fields;
- created/confirmed/started/first-completed/last-completed timestamps and corresponding
  actor IDs where applicable;
- immutable confirmation validation timestamp and summary counts;
- standard created/updated timestamps.

Template parameter values are stored in typed child rows equivalent to
`WhatsAppBroadcastTemplateParameter(broadcast_id, position, name, value)`, unique by
`(broadcast_id, name)`. They are returned only to authenticated CRM users and are
never logged or used as metric labels. A persistent cross-Broadcast template catalog
is not created.

### `WhatsAppBroadcastRecipient`

Each explicitly selected destination contains:

- `id`, `broadcast_id`, and selected `customer_id`;
- immutable-at-confirmation Customer display and normalized-phone snapshots;
- the consent event validated at confirmation;
- `status`: `DRAFT`, `READY`, `IN_PROGRESS`, `ACCEPTED`, `SENT`, `DELIVERED`, `READ`,
  `FAILED`, `UNKNOWN`, or `BLOCKED`;
- nullable typed block/failure reason and safe failure code/message;
- nullable `conversation_id` resolved or created only when dispatch is about to occur;
- claim token/worker identity, `claimed_at`, and bounded lease metadata used by the
  PostgreSQL processor;
- selected/confirmed/first-attempt/latest-attempt and delivery timestamps;
- standard created/updated timestamps.

A unique constraint on `(broadcast_id, normalized_phone)` is the durable deduplication
boundary. Selection of the same Customer/phone is idempotent. If multiple selected
Customers normalize to one phone, the ordered explicit request retains the first and
returns the later entries as duplicates; it never creates another row or another send.

`BLOCKED` represents a recipient for whom no new provider call was made, such as an
opt-out recorded after confirmation, a changed/deleted Customer phone, or a template
that ceased to be sendable. The typed reason distinguishes these cases from `FAILED`,
which always refers to a real Message attempt.

### Message and audit linkage

`WhatsAppMessage` gains a typed origin distinguishing at least `HUMAN` and
`BROADCAST`, plus nullable `broadcast_recipient_id`, template identity/language fields,
and the constraints needed to represent a template attempt without pretending that
the CRM authored its body. Existing rows are backfilled as `HUMAN`.

Every actual initial or retry attempt has `origin=BROADCAST` and belongs to exactly one
recipient. A partial unique constraint permits only one non-retry initial Message per
recipient. An explicit retry has a new `client_generated_id`, the same
`broadcast_recipient_id`, and `retry_of_message_id` pointing to the immediately prior
failed attempt. Its dispatch/provider states and timestamps remain those from CRM-005.

For image/PDF template headers, each attempt may have its own
`WhatsAppAttachment` metadata row referencing the same immutable CRM-008 stored object;
bytes are not duplicated. Message type remains `TEXT`, `IMAGE`, or `DOCUMENT` according
to the provider-neutral template/header representation. Broadcast origin, rather than
message type or sender, prevents waiting-state resolution.

An append-only `WhatsAppBroadcastAuditEvent` records lifecycle commands and material
processor decisions: creation, recipient replacement, validation/confirmation, start,
retry authorization, stale-claim recovery, completion, and block reason. It stores the
Broadcast, optional recipient/Message link, typed event/reason, actor when user-driven,
UTC timestamp, and safe scalar counts/identifiers. It does not store secrets, template
parameter values, phone numbers, message content, provider payloads, or generic raw
JSON.

## Contracts / API

All CRM endpoints are under `/api/whatsapp`, require an active CRM user, use strict
Pydantic request models with `extra="forbid"`, and return safe typed resources. List
pagination uses opaque keyset cursors. Provider errors use only curated codes/messages;
raw payloads, credentials, storage keys, and temporary media URLs are never returned.

### Consent

- `POST /marketing-consent-events` appends one event. The strict body contains a UUID
  `client_event_id`, `customer_id`, `decision`, `source`, `occurred_at`, optional
  `effective_at`, and optional `evidence_reference`; normalized phone and actor come
  from the backend. `FAA_CRM` rejects a client-supplied effective time and uses the
  append time. `EXTERNAL_FAA` requires a non-future effective time and a nonblank
  evidence reference. Replaying the same UUID and normalized payload returns the
  existing event; changed reuse is a conflict. It returns the event and effective
  current consent.
- `GET /marketing-consent-events?customer_id=...&limit=...&cursor=...` returns
  chronological append-only history, including phone snapshots and current status.
  This scope does not expose bulk import or mutation/deletion endpoints.

### Template selection

- `GET /broadcast-templates` obtains a fresh complete provider snapshot and returns
  only approved/sendable marketing variants with external ID, name, language, named
  parameter declarations, header type, and whether dynamic header media is accepted or
  required. It persists no catalog.
- A partial/failed provider listing returns a safe unavailable result and cannot be
  used to confirm a Broadcast. Cached data may aid display but is never presented as a
  fresh approval decision.

The provider-neutral `ProviderTemplateSnapshot` and `SendTemplateRequest` may be
extended with typed component declarations and an optional
`ProviderMediaReference`; no Meta DTO crosses the provider boundary. Unsupported
buttons/components or mismatched parameters/media fail before dispatch.

### Broadcast lifecycle and recipients

- `POST /broadcasts` creates a `DRAFT` from a strict UUID `client_generated_id`,
  label/external-reference, provider template identity, broadcast-level named
  parameters, and optional existing CRM-008 `header_media_ref`. Identical UUID replay
  returns the existing Draft; changed reuse is a conflict.
- `GET /broadcasts?status=...&limit=...&cursor=...` lists safe execution summaries;
  `GET /broadcasts/{broadcast_id}` returns immutable inputs, validation evidence,
  recipient page links/counts, lifecycle timestamps, and current delivery counts.
- `PUT /broadcasts/{broadcast_id}/recipients` accepts strict UUID `command_id`,
  `customer_ids: list[PositiveInt]`, and `expected_version`, and atomically replaces
  the explicit recipient set while `DRAFT`. The result reports selected, duplicate,
  invalid/deleted, missing-phone, and missing-consent candidates without silently
  selecting anyone else.
- `POST /broadcasts/{broadcast_id}/validate` accepts `expected_version`, performs full
  pre-send validation without changing lifecycle state, and returns exact safe counts,
  reasons, an input digest, and a short-lived opaque `validation_token` bound to the
  Draft version and immutable candidate inputs.
- `POST /broadcasts/{broadcast_id}/confirm` accepts UUID `command_id`,
  `expected_version`, and `validation_token`, revalidates atomically, and freezes the
  Broadcast only when the token/input digest still matches. Any invalid recipient or
  template/media/parameter input prevents confirmation; confirmation is not partial.
- `POST /broadcasts/{broadcast_id}/start` accepts UUID `command_id`, transitions
  `CONFIRMED` to `PROCESSING`, records the actor, and makes `READY` recipients
  claimable. An idempotent replay returns the same resource and never sends directly a
  second time.
- `POST /broadcasts/{broadcast_id}/process` asks the application processor to execute
  at most one configured bounded batch. The authenticated request includes UUID
  `command_id` and returns claimed/completed/remaining counts. The same typed
  application service is callable by a reviewed CLI or scheduler; a scheduler
  processes already-started Broadcasts and does not invent a user.
- `POST /broadcasts/{broadcast_id}/retries` accepts UUID `command_id` and a nonempty
  explicit list of failed recipient IDs. For each still-eligible latest `FAILED`
  attempt it creates exactly one new `PENDING` Message with a new UUID and
  `retry_of_message_id`, then makes that recipient processable. Ineligible,
  already-retried, blocked, or `UNKNOWN` recipients are reported without a provider
  call.
- `GET /broadcasts/{broadcast_id}/delivery-summary` returns recipient counts by current
  state, total Message attempts, failure/block reason counts, accepted/sent/delivered/
  read/failed timestamps, and completion timestamps. It contains no provider payload.

Draft create/recipient requests support safe idempotent HTTP replay through the
Broadcast version and stable resource ID. Confirm, start, process, and retry commands
are transactionally idempotent and append at most one matching audit event/effect per
command key.

## Pre-send validation

Confirmation succeeds only when all of the following are true:

1. The Broadcast is `DRAFT`, its expected version matches, and at least one recipient
   exists.
2. Each Customer exists, is not soft-deleted, has the snapshotted valid phone, and no
   other selected Customer occupies that normalized phone.
3. The exact Customer and phone have a latest effective opt-in; consent never expires
   automatically, while a later effective opt-out makes the recipient ineligible.
4. A fresh complete provider lookup identifies the selected `MARKETING` template
   variant as approved/sendable.
5. Named parameters exactly match the provider declaration; unsupported or unexpected
   components are absent.
6. Header media presence/type matches the approved template, is an available CRM-008
   object, and passes the configured IMAGE or PDF/DOCUMENT validation and limits.
7. The validation response contains exact counts and safe reasons plus a token bound to
   those inputs, allowing a separate deliberate confirm action rather than dispatching
   from a draft edit.

Immediately before each batch and each retry dispatch, the processor rechecks template
sendability, media availability, Customer/phone consistency, and the latest consent.
A changed condition blocks the affected send and records why. It never relies only on
the confirmation snapshot and never calls the provider after an opt-out.

## State transitions

Broadcast lifecycle:

```text
DRAFT -> CONFIRMED -> PROCESSING -> COMPLETED
                                  ^          |
                                  | retry    |
                                  +----------+
```

Only a successful full validation permits `DRAFT -> CONFIRMED`. `PROCESSING` reaches
`COMPLETED` when no recipient is `READY` or `IN_PROGRESS`; failed, unknown, and blocked
recipients are terminal for that processing pass. Explicit eligible retry may reopen a
completed Broadcast operationally without changing immutable inputs. `first_completed_at`
is retained and `last_completed_at` advances.

Recipient lifecycle for one attempt is:

```text
DRAFT -> READY -> IN_PROGRESS -> ACCEPTED -> SENT -> DELIVERED -> READ
                    |               |          |
                    +-------------> FAILED <---+
                    +-------------> UNKNOWN
READY ----------------------------> BLOCKED
FAILED -- explicit eligible retry -> READY
```

Provider delivery evidence reconciles monotonically through CRM-005; duplicate or
out-of-order status events cannot downgrade `READ` to `DELIVERED` or create another
Message. A later provider `FAILED` event is retained even after acceptance/sent as
defined by the existing provider state rules. Broadcast aggregate counts are derived
from current recipient state and the complete Message attempt history, not manually
incremented counters.

## Batch processing, idempotency, and concurrency

- Configured batch size, claim lease, provider concurrency, and pacing are positive,
  bounded backend settings. API callers cannot request an unbounded batch.
- Workers claim `READY` recipients with a short transaction using `FOR UPDATE SKIP
  LOCKED` (or an existing PostgreSQL equivalent), stable ID ordering, and a persisted
  claim token. Provider I/O never holds a database transaction or row lock.
- The initial Message and UUID are committed once before provider dispatch. Concurrent
  processors observe the same recipient/Message and cannot create another initial
  attempt.
- Before the provider call, dispatch becomes `IN_PROGRESS`. A crash with a stale
  `IN_PROGRESS` attempt is conservatively reconciled to `UNKNOWN`; it is never sent
  again automatically. A stale claim that provably has no started provider attempt may
  be safely reclaimed using the same Message and UUID.
- Provider result reconciliation locks and rechecks both recipient and Message. A late
  webhook or process response is idempotent and monotonic.
- `POST /process`, concurrent scheduler invocations, process restarts, HTTP retries,
  and duplicate status webhooks cannot produce two initial Messages or two provider
  calls for one claim.
- No Redis, Celery, distributed mutex, or in-memory queue is part of correctness. A
  CLI/scheduler may repeatedly invoke the same database-backed processor until no work
  remains.

## Security & permissions

- All active `SUPERVISOR` and `VENDEDOR` users may view Broadcasts and use the consent
  and Broadcast commands in this spec. No new role restriction is introduced.
- Authentication supplies every user actor; clients cannot choose creator, confirmer,
  starter, retrying user, sender, or consent recorder IDs.
- Confirmation and start are separate deliberate commands. A request that edits a
  confirmed Broadcast returns `409 Conflict` and performs no mutation or send.
- Sending without currently valid consent fails closed. Provider/template/media
  unavailability also fails closed before new dispatch.
- Strict typed request models reject extra or unknown fields. Phone normalization,
  Customer availability, template compatibility, and media validation are backend
  responsibilities.
- API responses and audit logs exclude access tokens, App Secret, verify token, raw
  provider/template payloads, internal storage keys/paths, temporary provider URLs,
  unsafe errors, and generic evidence bodies.
- Parameter values, phone numbers, Customer identity, and media filenames are not logs
  or metric labels. Authenticated detail returns only the business data needed to audit
  that Broadcast.
- Consent, Broadcast, recipient, audit, Message, attachment, and status history cannot
  be hard-deleted through this feature.

## Edge cases

- No consent history, invalid external evidence, or a latest opt-out is ineligible;
  absence is never interpreted as opt-in and elapsed time never expires consent.
- Selecting the same phone through repeated or different Customer IDs yields one
  recipient row and an explicit duplicate result, never two sends.
- A Customer phone change after selection invalidates confirmation; after confirmation
  it blocks the pending send rather than redirecting it to the new or stale number.
- An opt-out recorded after confirmation or while a different recipient is being sent
  blocks every not-yet-started attempt to that phone. A provider call already in
  progress retains its real outcome and audit evidence.
- Template deletion, paused/rejected status, changed component signature, incomplete
  template pagination, parameter mismatch, or unavailable header media prevents a new
  provider call.
- A duplicate confirm/start/process/retry request returns the existing effect. Reusing
  an idempotency key for different recipients or inputs is a conflict.
- A definitive provider failure is a real failed Message. It is not erased or mutated
  when retried; the new Message links to it.
- `UNKNOWN` remains visibly uncertain even if the Broadcast otherwise completes. Only
  a later provider status event may reconcile it; user retry is rejected.
- A delivery webhook may arrive after Broadcast completion or after a failed retry. It
  updates the correct Message/recipient monotonically and refreshes the summary without
  changing immutable execution inputs.
- An image/PDF object shared by many attempt attachment rows remains one private stored
  object; a partial provider media upload cannot expose a URL or make another recipient
  look sent.

## Acceptance criteria

- AC-01: Consent updates append authenticated, immutable, phone-specific `OPT_IN` or
  `OPT_OUT` events; current eligibility is derived deterministically, absence fails
  closed, and an opt-out blocks every later Broadcast attempt.
- AC-02: A Draft stores one provider-approved marketing-template selection, one typed
  broadcast-level parameter set, and optional compatible image/PDF header media without
  creating, editing, or approving campaign content.
- AC-03: Recipient selection is explicit and atomically deduplicates normalized phones;
  the database permits one initial recipient/send per phone per Broadcast.
- AC-04: Validation returns an input-bound confirmation token, and confirmation
  requires its matching Draft version, at least one recipient, fresh full template
  approval, valid parameters/media, consistent Customers/phones, and current opt-ins;
  any failure prevents partial confirmation or dispatch.
- AC-05: Confirmed content and recipients are immutable, start is separately explicit,
  and duplicate confirm/start requests create neither another transition nor a send.
- AC-06: Every actual initial send creates exactly one real origin-`BROADCAST`
  `WhatsAppMessage`; broadcast acceptance/delivery never resolves
  `waiting_for_response` or creates an Opportunity.
- AC-07: Recipient and summary projections expose accepted, sent, delivered, read,
  failed, unknown, and blocked evidence from real Messages/status events without
  provider payloads or manually drifting aggregate counters.
- AC-08: An explicit eligible failed retry creates one new Message/UUID linked to the
  immediately prior failed Message; retries are consent/template revalidated and
  `UNKNOWN` is never retried.
- AC-09: Stable command/version keys, Message UUIDs, unique constraints, and monotonic
  reconciliation make HTTP replay, process restart, and duplicate/out-of-order webhook
  handling idempotent.
- AC-10: Concurrent processors use bounded PostgreSQL claiming with `SKIP LOCKED` or an
  equivalent existing pattern, perform provider I/O outside transactions, and cannot
  claim or dispatch the same attempt twice.
- AC-11: Stale work is reclaimed only when no provider attempt could have started;
  ambiguous in-progress work becomes `UNKNOWN` and is never automatically resent.
- AC-12: Both active roles can view and operate the authenticated contracts with global
  visibility; no seller filter, new role, frontend-to-Meta call, secret, raw payload,
  storage key, or unsafe error is introduced.
- AC-13: Append-only consent and Broadcast audit events plus immutable recipient,
  Message, attachment, actor, timestamp, validation, retry, and status links reconstruct
  who authorized and executed each attempted or blocked send.
- AC-14: Bounded database-backed processing can be invoked through the authenticated
  API or the same CLI/scheduler-compatible application service without Redis, Celery,
  or correctness depending on process memory.

## Open decisions

None

## Follow-up / future specs

- Broadcast frontend for creation, explicit recipient selection, confirmation,
  execution progress, retries, and delivery results.
- Persistent provider template catalog only if runtime discovery proves insufficient.
- Production scheduling and operations: cadence, throughput/rate-limit tuning,
  alerting, runbooks, stuck-work monitoring, and deployment ownership.

## Implementation notes

Keep consent policy, Broadcast commands, recipient validation, batch claiming,
dispatch, delivery projection, and audit serialization in separate strictly typed
services. Routers and CLI commands call the same application services; neither embeds
business rules.

Reuse CRM-005 dispatch/provider reconciliation, CRM-008 storage, CRM-009 template and
Meta boundaries, phone normalization, and existing UTC helpers. Extend those contracts
only where Broadcast origin, template components, or header media require it. Do not
fork a parallel message/status state machine or persist a raw provider/template
payload.
