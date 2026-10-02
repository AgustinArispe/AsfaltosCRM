# CRM-056 — Manual WhatsApp response handling

Status: Approved
Owner: FAA CRM team
Last updated: 2026-10-02
Implementation commit: N/A

## Goal

Let an authenticated CRM user mark the current customer request in a WhatsApp conversation as handled without sending a message.

## Context

CRM-005 currently derives waiting exclusively from inbound messages after the last accepted human outbound. A final courtesy reply therefore remains in the waiting queue. This explicit user request extends that rule; `RESOLVED` continues to describe customer identity only.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API
- CRM-023 — WhatsApp Inbox 2.0

## Scope

Persist a manual handled marker for the currently observed inbound messages, expose an authenticated command, recompute waiting projections, and update the Inbox immediately. A later persisted inbound reactivates waiting.

## Non-goals

No message sending, read-state change, opportunity/customer mutation, provider-window change, or deletion. No new notification category.

## Business rules

The manual marker suppresses waiting only for inbound messages already persisted when the user marks the conversation handled. A later inbound resumes normal waiting behavior. Accepted human outbound still resolves waiting; failed, unknown, and Broadcast outbound do not. The team-wide unread count is independent.

## Data model

Add nullable `handled_at`, `handled_by_user_id`, and `handled_through_message_id` to `whatsapp_conversations`. The message ID is the durable cutoff for inbound evidence. Retain the latest handling audit fields when later messages arrive.

## Contracts / API

`POST /api/whatsapp/conversations/{id}/handled` requires an active user and returns the updated conversation summary. Existing list/detail/change and attention-summary contracts retain their fields and derive their waiting values from the updated projection.

## State transitions

Waiting → handled clears `waiting_for_response` and `waiting_since_at`. Repeated handling is idempotent. A new inbound after the cutoff restores waiting; a replay of an existing inbound does not. The marker is not a permanent conversation closure.

## Security & permissions

Both current CRM roles may handle a visible conversation. The user ID is server-derived. Hidden conversations are unavailable to the command.

## Edge cases

Conversation row locks serialize handling with inbound persistence. A later inbound is identified by its database message ID rather than provider timestamps, which can arrive out of order. Existing message, unread, window, deletion, and commercial evidence remain intact.

## Acceptance criteria

- AC-01: An inbound message makes the conversation waiting; handling removes it from waiting filters and counters without removing messages.
- AC-02: Reload and polling preserve the handled state; the action is available only while waiting.
- AC-03: A newly persisted inbound after handling makes the conversation waiting again, while replay does not.
- AC-04: Unread/read, Meta window, Opportunity, Customer, and hidden-conversation behavior remain independent.
- AC-05: Backend, frontend, browser, audit, migration, and project quality gates pass.

## Open decisions

None.

## Follow-up / future specs

None.
