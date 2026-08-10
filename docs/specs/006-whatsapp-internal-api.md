# CRM-006 — WhatsApp Internal API

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-10
Implementation commit: c940617

## Goal

Expose the implemented WhatsApp core through authenticated FastAPI contracts so a
future Inbox can be developed entirely with `FakeWhatsAppProvider` before Meta
credentials exist.

## Context

CRM-005 owns WhatsApp persistence, identity resolution, message dispatch, status
reconciliation, attachments, unread state, waiting state, and provider abstractions.
CRM-006 adds HTTP/query boundaries without redefining those rules.

## Dependencies

- CRM-005 — WhatsApp Core

## Scope

Authenticated APIs for conversation discovery/detail, incremental polling, message
history and sending, global read state, opportunity links, stored media, provider window
decisions, and fake-only development simulation.

## Non-goals

- `MetaCloudApiProvider` and real Meta webhooks.
- Broadcasts, marketing consent, or persistent template synchronization.
- WhatsApp Inbox frontend or mobile-specific UI.
- Redis, Celery, WebSocket, or SSE infrastructure.
- Real object storage.
- New WhatsApp tables or changes to CRM-005 state machines.

## Business rules

- Every endpoint in this spec requires an active CRM user. Unread state remains global
  for the team.
- The API delegates identity, opportunity association, waiting, dispatch, delivery,
  retry, and window decisions to CRM-005 services.
- Existing customers do not receive an automatically created Opportunity. A link is
  explicit; replacing or removing it closes the active historical link rather than
  deleting it.
- A freeform send is rejected when the backend provider decision requires an approved
  template. The frontend never calculates WhatsApp policy.
- Message content types are `TEXT`, `IMAGE`, and `DOCUMENT`. Binary content is never
  embedded as base64 in JSON, and temporary provider URLs are never returned.
- Provider payloads, credentials, internal storage keys, and unsafe errors are not API
  fields.

## Data model

No schema or migration is required. APIs read and mutate the five CRM-005 tables and
use the existing `MediaStorage` and `WhatsAppProvider` boundaries. Polling and page
cursors are opaque API tokens and are not persisted.

An API resource change timestamp is derived from the relevant persisted timestamps:
conversation/customer/opportunity-link/opportunity data for a conversation summary,
and message/attachment data for a message summary. This lets related summary changes
participate in polling without adding an event table.

## Contracts / API

All paths are under `/api/whatsapp`.

### Conversations

- `GET /conversations` performs the initial inbox load. Query fields are `limit`,
  optional `page_cursor`, `waiting_only`, `unread_only`, and `search`. Filters combine
  with AND. Search trims its value, normalizes phone separators, and otherwise matches
  display name, Customer name, or company case-insensitively.
- Default ordering is `waiting_for_response DESC`, `unread_count DESC`,
  `last_message_at DESC NULLS LAST`, `id DESC`. Page cursors preserve this keyset and
  the snapshot boundary, so later updates do not reshuffle an in-progress page walk.
- The response contains `items`, `next_page_cursor`, and `sync_cursor`.
- `GET /conversations/changes?cursor=...&limit=...` returns full conversation summaries
  changed after the cursor, ordered by `(resource_updated_at ASC, id ASC)`, plus
  `next_cursor` and `has_more`. It is unfiltered so a client can observe an item leaving
  `waiting_only` or `unread_only` and reapply its current view.
- `GET /conversations/{conversation_id}` returns the same summary plus historical
  opportunity links and current suggestions.

A conversation summary contains identity/display fields, `resolution_status`, a
nullable Customer summary, active opportunity link, open-opportunity suggestions,
last-message timestamps, `unread_count`, `waiting_for_response`, `waiting_since_at`,
and the window decision. Customer summaries expose only CRM fields needed by the Inbox;
soft-deleted historical customers are marked unavailable and cannot be used for send or
link operations.

### Messages

- `GET /conversations/{conversation_id}/messages?limit=...&before_cursor=...` returns
  the newest snapshot page when no cursor is supplied and older pages otherwise. Items
  are returned chronologically by `(message_at ASC, id ASC)`; `next_before_cursor` and a
  `sync_cursor` are included.
- `GET /conversations/{conversation_id}/messages/changes?cursor=...&limit=...` returns
  created or updated message resources ordered by `(resource_updated_at ASC, id ASC)`.
  Attachment storage changes and provider-status reconciliation must be observable.
- `POST /conversations/{conversation_id}/messages` accepts a strict discriminated
  request for `TEXT`, `IMAGE`, or `DOCUMENT`. Every request includes UUID
  `client_generated_id` and optional `retry_of_message_id`; text includes `body`, while
  media includes `media_ref` and optional `caption`. `sent_by_user_id` is always taken
  from the authenticated user, never from the request.

Message responses contain local and external IDs, direction/type/body, sender summary,
`client_generated_id`, chronological `message_at`, retry metadata, attachment metadata,
and a curated status object: dispatch state, provider state, accepted/sent/delivered/
read/failed timestamps, and nullable safe error code/message. Compact internal status
events and raw provider payloads are not returned.

An identical `client_generated_id` replay returns the existing message without a second
provider call. Reuse with different normalized content, attachment, sender, conversation,
or retry target is a conflict. `UNKNOWN` is never auto-retried; explicit resend uses a
new UUID and `retry_of_message_id` as defined by CRM-005.

### Read state and opportunity association

- `POST /conversations/{conversation_id}/read` has no request body, atomically sets the
  global unread count to zero, and returns the updated conversation summary. Repeating
  it is safe.
- `PUT /conversations/{conversation_id}/opportunity-link` accepts strict JSON
  `{"opportunity_id": <positive id>}`. Linking the current Opportunity is idempotent;
  linking another valid Opportunity closes the prior active link at the same operation
  timestamp and creates one new active link.
- `DELETE /conversations/{conversation_id}/opportunity-link` closes the current link,
  preserves all history, and returns the updated detail. With no active link it is
  idempotent.

Links require a resolved, available Customer and a non-deleted Opportunity belonging to
that Customer. Terminal Opportunities may remain in link history. Suggestions contain
only open, non-deleted Opportunities and never create or link one automatically.

### Attachments

- `POST /media` accepts `multipart/form-data` with one binary file and a strict metadata
  part containing `media_type` (`IMAGE` or `DOCUMENT`). The backend validates configured
  size and MIME allowlists, stores bytes through `MediaStorage`, and returns an opaque
  `media_ref`, MIME type, sanitized filename, media type, and size. At minimum, the V1
  contract supports common image content and `application/pdf`.
- `GET /media/{media_ref}/content` provides authenticated preview of an uploaded but not
  yet sent item. The reference is opaque and never exposes a storage key or object URL.
- `GET /attachments/{attachment_id}/content` retrieves persisted message content. For a
  pending inbound attachment it first invokes the CRM-005 media service; available bytes
  are then streamed from `MediaStorage` with safe `Content-Type`, `Content-Disposition`,
  and private cache headers.
- Media send requests resolve `media_ref` server-side and persist the resulting attachment
  metadata with the outbound Message. Missing, failed, mismatched, or oversized media is
  rejected before provider dispatch.

### Window and templates

Conversation list/detail and send responses expose:

- `can_send_freeform`;
- `window_expires_at`;
- `template_required`;
- `reason`, which is null when freeform is allowed and
  `APPROVED_TEMPLATE_REQUIRED` when it is not.

These fields come from a fresh backend `evaluate_window` decision. CRM-006 defines no
template-send or template-list endpoint: CRM-005 has no persisted template identity on a
Message, and Fake Provider can exercise this API with an open configured window.

### Fake-only development API

The `/api/whatsapp/dev` router is constructed and registered only when the configured
provider is the concrete fake provider. Runtime authorization checks alone are
insufficient; the routes must not exist in the real-provider route table.

- `POST /dev/inbound` injects strict text/image/document input through
  `WhatsAppInboundService`. Media metadata may reference content previously uploaded by
  `media_ref`; no base64 is accepted.
- `POST /dev/messages/{message_id}/statuses` accepts an ordered nonempty list of
  `SENT`, `DELIVERED`, `READ`, or `FAILED`, optional safe failure metadata, timestamps,
  and a duplicate flag. It emits Fake Provider events and reconciles each through
  `WhatsAppStatusService`.
- `PUT /dev/provider-behaviors/{client_generated_id}` configures one of
  `PERMANENT_FAILURE`, `RETRYABLE_FAILURE`, `TIMEOUT_BEFORE_ACCEPTANCE`, or
  `TIMEOUT_UNKNOWN_ACCEPTANCE` with optional safe code/message before the send request.

### Polling and cursor semantics

Cursors are versioned, opaque, URL-safe tokens. Clients must not construct or compare
them. Malformed or unsupported cursor versions return `422`.

1. Initial Inbox load uses `GET /conversations`; its `sync_cursor` is the high-water mark
   captured at the snapshot boundary.
2. The client polls `/conversations/changes` with that cursor, upserts full summaries,
   follows `has_more` immediately, and then waits for the next polling interval.
3. Opening a conversation loads its newest message page and stores that response's
   message `sync_cursor`; older history uses `before_cursor`, while new/status/attachment
   changes use `/messages/changes`.
4. On reconnect, the client resumes from its last acknowledged cursors. Cursors do not
   expire in this phase because persisted resources are the source of truth. If a cursor
   becomes unsupported, the client discards that local projection and performs the
   corresponding initial load again.
5. Changing search/filter parameters starts a new initial inbox snapshot. Change feeds
   remain unfiltered so state transitions cannot disappear silently.

## State transitions

HTTP handlers do not introduce states. Send, retry, delivery reconciliation, read,
waiting, resolution checks, and link replacement use CRM-005 transitions and locks.
Unlinking sets `unlinked_at` and updates the conversation change timestamp; it never
deletes a link row.

## Security & permissions

- `SUPERVISOR` and `VENDEDOR` may use the authenticated Inbox APIs; visibility remains
  global as defined by FAA business rules.
- Requests use strict Pydantic schemas with `extra="forbid"`; multipart metadata is
  parsed into the same strict models.
- Provider secrets, raw payloads, temporary URLs, internal storage keys, and unsafe
  errors are never serialized or logged.
- Media reads and uploads require authentication and stream content without logging
  bodies. Filenames are sanitized before response headers.
- Fake development routes require active authentication and are absent unless
  `WHATSAPP_PROVIDER=fake` selects `FakeWhatsAppProvider` during application assembly.

## Edge cases

- Missing resources return not found without disclosing unrelated customer data.
- `NEEDS_REVIEW`, deleted Customer, wrong-customer Opportunity, invalid retry target,
  reply already in progress, and closed freeform window fail before a provider call.
- Late/out-of-order delivery evidence remains represented by CRM-005 effective state and
  timestamps; API polling may return the same resource more than once and clients upsert
  by local ID.
- Concurrent reads, links, sends, and idempotent replays use CRM-005 row/unique-locking
  guarantees. Same UUID plus different content never dispatches twice.
- Empty result pages retain the supplied sync cursor. Stable ID tie-breakers prevent
  duplicate or skipped rows with equal timestamps.

Domain-to-HTTP mapping uses the existing `{"detail": "..."}` error shape:

| Condition | HTTP behavior |
| --- | --- |
| Missing conversation/message/attachment/opportunity | `404 Not Found` |
| Identity needs review or Customer unavailable | `409 Conflict` |
| Invalid opportunity association or active-reply/state conflict | `409 Conflict` |
| Same idempotency key with different payload | `409 Conflict` |
| Freeform window closed | `409 Conflict` with template-required detail |
| Invalid request or attachment | `422 Unprocessable Content` |
| Provider definitive failure | `200 OK` with persisted `DEFINITIVE_FAILED` message and safe error; not a retryable transport error |
| Provider acceptance unknown | `202 Accepted` with persisted `UNKNOWN` message; never auto-retry |

A newly accepted outbound resource returns `201 Created`; an identical replay returns
`200 OK`. No new machine-readable error-code envelope is introduced.

## Acceptance criteria

- AC-01: Every WhatsApp and fake-development endpoint rejects missing, invalid, or inactive-user authentication and returns no provider secrets.
- AC-02: Conversation initial load applies waiting/unread/search filters and stable inbox ordering while returning customer, opportunity, unread, waiting, and window summaries.
- AC-03: Conversation snapshot and change cursors support lossless upsert polling, pagination, reconnect, filter exits, and deterministic timestamp ties.
- AC-04: Message history pages older records without duplication and its change feed returns new messages plus later status or attachment updates.
- AC-05: Authenticated text sends use the current user and Fake Provider; identical UUID replay does not dispatch twice and changed reuse returns `409`.
- AC-06: Image and PDF/document uploads and sends use `MediaStorage`/Fake Provider without base64, storage keys, or temporary URLs in API payloads.
- AC-07: Marking a conversation read globally sets `unread_count=0`, is idempotent, and does not alter waiting state.
- AC-08: Responses expose the fresh backend window decision, and a closed freeform window prevents dispatch with template-required detail.
- AC-09: Linking, replacing, and unlinking an Opportunity preserve historical rows, enforce Customer ownership, and never auto-create an Opportunity for an existing Customer.
- AC-10: Attachment upload, preview, and message-content endpoints require authentication, validate type/size, and stream only available stored content with safe headers.
- AC-11: Message responses expose CRM-005 dispatch/delivery/retry evidence and safe errors without raw provider events or payloads.
- AC-12: Definitive failure and unknown acceptance produce the documented durable API outcomes; `UNKNOWN` requires explicit resend with a new UUID.
- AC-13: Fake development routes inject inbound media/text, simulate ordered/duplicate statuses, and configure all fake failure/timeout modes through domain services.
- AC-14: The fake development router is absent—not merely forbidden—when any non-fake provider is configured.
- AC-15: Domain failures use the documented HTTP statuses and existing `{"detail": "..."}` shape; strict requests reject extra fields.

## Open decisions

None

## Follow-up / future specs

- Meta provider adapter and real webhook verification/processing.
- WhatsApp Inbox frontend.
- Broadcasts, marketing consent, and persistent template synchronization/sending.
- Production media storage and production upload/retention limits.

## Implementation notes

Keep routers thin. Add typed query/serialization services for cursor pagination and API
projections; continue using CRM-005 command services for mutations. Cursor encoding,
media references, and fake-router registration belong at infrastructure boundaries and
must remain provider-agnostic outside the fake-only router.
