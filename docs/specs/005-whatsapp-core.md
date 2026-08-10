# CRM-005 — WhatsApp Core

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-10
Implementation commit: `8de68bf`

## Goal

Provide the persistence and domain core for one-to-one WhatsApp conversations using a strict provider boundary and deterministic fakes, so the module can be developed and tested before Meta credentials exist.

## Context

This spec captures migration `0005_whatsapp_core` and the implemented fake-provider backend. It does not claim that Meta, webhooks, HTTP routers, or an Inbox UI exist.

## Scope

Permanent phone-keyed conversations, inbound/outbound messages, provider status events, historical opportunity links, attachment metadata and media storage boundary, shared customer identity resolution, fake provider behavior, local idempotency, concurrency, unread and waiting projections, and window evaluation.

## Non-goals

Meta HTTP integration, real webhooks, WhatsApp API routers, Inbox frontend, broadcasts, marketing consent, persistent template synchronization, Redis/Celery, and real object storage are not implemented.

## Business rules

- One permanent conversation exists per normalized external phone number; it is not split into open/closed sessions.
- A conversation may be `RESOLVED` or `NEEDS_REVIEW`; an unresolved conversation has no customer.
- Unknown first inbound contact atomically creates Customer, `Opportunity(NUEVA, WHATSAPP)`, an automatic opportunity link, conversation, and message.
- Existing customers do not automatically receive a new opportunity. Open opportunities are suggestions; linking is explicit and historical terminal links are retained.
- Identity matching is exact and conservative by normalized phone/email signals; ambiguous or soft-deleted matches require review. New customer fallback is `Contacto WhatsApp ••••1234` when display name is absent/invalid.
- Inbound messages are `RECEIVED`; outbound dispatch is `PENDING -> IN_PROGRESS -> ACCEPTED` or `DEFINITIVE_FAILED`/`UNKNOWN`. Provider delivery is independently `SENT`, `DELIVERED`, `READ`, or `FAILED`.
- `waiting_for_response` is true when inbound messages exist after the last valid human outbound response. Pending, in-progress, unknown, failed, and broadcast messages do not resolve it.
- Unread count is global for the team; marking a conversation read clears its current count.

## Data model

- `whatsapp_conversations`: customer FK nullable only for `NEEDS_REVIEW`, external phone, normalized phone key (unique), provider contact/display name, last inbound/outbound/message timestamps, unread count, waiting flag/since, window expiry, and timestamps.
- `whatsapp_messages`: conversation FK, nullable external provider ID, nullable UUID `client_generated_id`, direction/type/body, sending user, retry-of self-FK, dispatch and provider states, safe provider error fields, provider/accepted/delivery timestamps. Partial unique indexes enforce inbound external-ID dedupe and outbound idempotency.
- `whatsapp_message_status_events`: external message ID, optional message FK, provider state, occurred/received timestamps, safe errors, unique `(external_id,state,occurred_at)`.
- `whatsapp_conversation_opportunities`: conversation/opportunity/user FKs, linked/unlinked timestamps, source; at most one active link per conversation via partial unique index.
- `whatsapp_attachments`: one attachment per message, image/document type, provider media ID, MIME/name/size metadata, stable storage key/status/error. Temporary provider URLs are never persisted. All FKs use `RESTRICT`.

## Contracts / API

The internal `WhatsAppProvider` Protocol exposes typed operations: `send_text`, `send_image`, `send_document`, `send_template`, `download_media`, `list_templates`, and `evaluate_window`. DTOs cover send requests/results, media references/payloads, template snapshots, window decisions, delivery events, and safe provider errors.

`MediaStorage` is an internal typed protocol; Phase 2 provides `FakeMediaStorage` only. There are no implemented HTTP WhatsApp endpoints.

## State transitions

Inbound processing deduplicates by external ID, reuses/creates the permanent conversation, resolves identity, records `RECEIVED`, updates projections, and creates attachment metadata. Outbound processing validates/locks the conversation, checks client idempotency, commits `PENDING`, calls the provider outside the DB transaction, and reconciles success, definitive failure, or unknown acceptance. Explicit resend of `UNKNOWN` creates a new message with `retry_of_message_id`; unknown messages are never auto-retried.

Provider delivery events are persisted before/after message acceptance as necessary and reconciled monotonically: late or duplicate events do not downgrade a stronger effective state. Accepted human outbound resolves waiting; a failed outbound leaves it waiting.

## Security & permissions

Domain services require an active CRM user for human outbound and manual linking. Provider credentials are not part of the fake implementation and are intended to remain backend configuration. Error metadata is provider-safe; message bodies and future media URLs are not emitted unnecessarily in logs.

## Edge cases

- Same external inbound ID is a replay; same outbound client ID with a different payload is a domain conflict.
- Two inbound deliveries for one phone are serialized by identity/external-ID locks.
- The provider may timeout before acceptance or with unknown acceptance; these outcomes remain distinct and durable.
- Status events may arrive before the provider response or out of order; unmatched events are retained for reconciliation.
- An active opportunity link can be replaced only by closing the prior link; terminal historical links remain.
- Attachment download/storage failure is represented by `FAILED` metadata rather than a temporary URL or lost message.

## Acceptance criteria

- AC-01: Repeated inbound delivery for one external message ID creates one message and reuses one phone-keyed conversation.
- AC-02: A new unknown contact is created atomically with fallback/display Customer, `WHATSAPP` opportunity, history/link, conversation, and message.
- AC-03: Existing, ambiguous, and soft-deleted customer matches follow exact resolution/review rules without guessing.
- AC-04: Existing-customer inbound messages do not auto-create opportunities; suggestions and manual historical links behave as specified.
- AC-05: Outbound client-generated IDs are idempotent; a payload conflict is rejected and explicit retry creates a linked new message.
- AC-06: Fake provider success, permanent failure, retryable failure, both timeout outcomes, deterministic IDs, duplicate events, and out-of-order events are testable.
- AC-07: Dispatch and provider delivery states reconcile monotonically and retain compact status events, including events received before acceptance.
- AC-08: Waiting becomes true after inbound and resolves only after accepted human outbound; failed/unknown outbound does not resolve it.
- AC-09: Global unread count increments for inbound and is cleared by the conversation read operation.
- AC-10: Image/document attachments persist typed metadata and transition through fake media download/storage success or failure without temporary URLs.
- AC-11: Freeform sending is allowed only when the provider window decision permits it; the window expiry is exposed by the domain result.
- AC-12: Concurrent duplicate inbound and outbound attempts do not create duplicate messages, active links, or inconsistent projections.

## Open decisions

The approved future WhatsApp roadmap still requires a Meta provider/webhook boundary, production media storage, template synchronization, broadcasts/consent, and HTTP/UI surfaces. Those are explicitly outside this implemented core and must be specified before implementation.

## Implementation notes

`WhatsAppInboundService`, `WhatsAppMessageService`, conversation/link services, status and media services keep responsibilities separate. PostgreSQL unique constraints, transaction locks, and advisory locks provide the durable idempotency/concurrency boundary; no Redis or Celery is required.
