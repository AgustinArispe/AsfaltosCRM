# CRM-051 — WhatsApp Production Media & Opportunity Lifecycle

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-22
Implementation commit: Pending

## Goal

Correct the production image/audio delivery path and enforce the approved rule that a
Customer may retain many historical Opportunities but at most one active Opportunity
at a time, without redesigning WhatsApp.

## Context

Live Meta traffic proved that inbound media metadata persists while image bytes are
not reliably requested and voice notes are absent from the usable Inbox. The deferred
media path currently exposes its authenticated download endpoint only after storage is
already `AVAILABLE`, creating a circular wait for `PENDING` attachments.

CRM-051 supersedes only CRM-050's new-contact-only Opportunity lifecycle. Its private
media, validation, rendering and security contracts remain authoritative.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-008 — WhatsApp Media Storage
- CRM-009 — Meta Cloud API Provider
- CRM-013 — Concurrency Hardening
- CRM-050 — WhatsApp Inquiries, Audio & Inline Media

## Scope

- Expose the authenticated attachment endpoint for `PENDING` media so its first
  authorized read triggers the existing deferred Meta download, validation and durable
  storage path.
- Project explicit `PENDING`, `AVAILABLE` and `FAILED` states; never project provider
  URLs/IDs, storage keys or filesystem paths.
- Preserve authenticated blob fetching and object-URL cleanup, with bounded images,
  accessible inline audio, and truthful loading/failure states.
- Explicitly map Meta voice notes, including `voice=true` and
  `audio/ogg; codecs=opus`, while retaining OGG/Opus signature validation.
- Add safe structured diagnostics using bounded categories and internal IDs, without
  raw payloads, phone numbers, bodies, provider URLs/IDs or credentials.
- For every valid inbound belonging to a uniquely resolved non-deleted Customer,
  reuse/link the sole active Opportunity or create a `NUEVA`, `source=WHATSAPP`
  Opportunity and set its immutable inquiry to that exact message.
- Enforce at most one non-deleted active Opportunity per Customer in the service and
  PostgreSQL. Active means `NUEVA`, `COTIZADA` or `NEGOCIACION`; closed means `GANADA`
  or `PERDIDA`.

## Non-goals

- Redesigning webhook, provider, conversation, polling, auth or storage architecture;
  adding queues, public media, CDN/object storage or Meta URLs.
- Changing identity matching, ambiguity/deleted-customer protections, WEB inquiry
  snapshots, supported image/document validation, or historical closed rows.
- Audio recording/transcoding, video, transcription, waveform generation, automatic
  retry workers, or full production webhook payload logging.
- Inferring/backfilling historical initial inquiries.

## Business rules

- A Customer has at most one active Opportunity across every source. Other creation
  entry points reject a second active row rather than silently reusing it; WhatsApp
  inbound alone uses the create-or-reuse lifecycle defined here.
- Existing Customer/conversation status does not decide creation; active Opportunity
  existence does.
- With an active Opportunity, the message persists and conversation context points to
  it; no Opportunity/inquiry is created. Without one, the exact inbound
  text/image/document/audio creates the Opportunity and immutable inquiry.
- After `GANADA` or `PERDIDA`, a later inbound can create a new historical Opportunity.
  Reopening/regressing a closed row is rejected if another active row exists.
- Same-wamid replay never creates, switches or duplicates any record.

## Data model and migration

- Add a PostgreSQL partial unique index on `opportunities(customer_id)` where
  `deleted_at IS NULL` and status is active.
- Perform no history rewrite. Migration fails visibly on pre-existing active
  duplicates so operators inspect them instead of silently changing commercial data.
- No new media table/inquiry column; historical nullable inquiry references remain
  valid.

## Contracts and state

- `AttachmentResponse` adds typed `storage_status`. `content_url` exists for `PENDING`
  and `AVAILABLE`, not `FAILED`; `is_available` remains true only for `AVAILABLE`.
- An authorized `PENDING` read runs the existing deferred download. Success becomes
  `AVAILABLE`; safe provider/validation/storage failure becomes `FAILED`.
- Responses retain validated Content-Type, private/no-store caching, `nosniff` and
  safe disposition. Browsers receive only local, revoked `blob:` URLs.

## Concurrency and lock order

- Inbound acquires sorted advisory locks, discovers identity, locks `Customer` before
  `WhatsAppConversation`, then creates/links message and Opportunity and revalidates
  after locks.
- The Customer lock serializes the create decision; the partial unique index is the
  independent final guard. Provider/network I/O never occurs under these locks.

## Security and operations

- Preserve signed webhook validation, wamid idempotency, private storage, size/MIME
  allowlists, content signatures and authenticated retrieval.
- `WHATSAPP_MEDIA_STORAGE_ROOT` must exactly equal the writable Railway backend volume
  mount; deployment smoke testing proves content survives a redeploy.
- Diagnostics exclude raw bodies and provider/customer secrets.

## Acceptance criteria

- AC-01: A real-shape inbound image persists `PENDING`; authenticated content read
  downloads/validates/stores it, returns the validated image Content-Type and renders
  inline without exposing provider URLs or paths.
- AC-02: Pending, missing and failed image states are explicit; authenticated blob URLs
  are revoked on cleanup.
- AC-03: A Meta voice-note (`type=audio`, audio id, OGG Opus MIME, `voice=true`) maps,
  persists idempotently, downloads privately and renders an accessible inline player.
- AC-04: MIME/signature/size/provider/storage failures remain safe and image/document
  validation is not weakened.
- AC-05: First inbound for a uniquely resolved Customer without an active Opportunity
  creates one `NUEVA` WhatsApp Opportunity whose inquiry points to that exact message
  for text, image, document and audio.
- AC-06: Further inbound in `NUEVA`/`COTIZADA`/`NEGOCIACION` persists and reuses the
  active context without creating another Opportunity.
- AC-07: After `GANADA` or `PERDIDA`, the next inbound creates a new `NUEVA`; history is
  unchanged.
- AC-08: Concurrent inbound creates at most one active Opportunity; replay creates
  nothing extra.
- AC-09: PostgreSQL rejects a second active row and service entry points fail safely,
  including reopen/regression when another active row exists.
- AC-10: Opportunity Detail renders the triggering persisted inquiry; historical null
  inquiries remain valid and WEB consultation behavior is unchanged.
- AC-11: Focused/full tests, TypeScript, Biome, Ruff, strict mypy, Alembic, build,
  Docker health and Docker-hosted browser tests pass. A post-deploy production smoke
  sequence remains required; automated tests are not production proof.

## Open decisions

None.

## Follow-up / future specs

Background prefetch/retry workers, media retention, object storage/CDN,
recording/transcoding and video require separate specs.

## Implementation notes

Reuse the current provider abstraction, attachment record, policy, filesystem storage,
authenticated endpoint, polling and `useAuthenticatedMedia`. Keep the partial-index
predicate identical in model and migration.
