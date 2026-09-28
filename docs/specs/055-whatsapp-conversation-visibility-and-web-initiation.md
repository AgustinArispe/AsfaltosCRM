# CRM-055 — WhatsApp Conversation Visibility & Web Initiation

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-28
Implementation commit: `994489c63956a941a5fc4f865564f1413605c8cf`

## Goal

Let authenticated commercial users hide a WhatsApp conversation from the Inbox without
removing its commercial evidence, and let them explicitly open or begin a WhatsApp
conversation from an Opportunity contact with a usable phone number.

## Context

CRM-052 continues to enforce Meta's service window. This feature does not send a
message merely by opening an Opportunity. It exposes the existing template path when
the window is closed. The explicit requirement approved on 2026-09-28 also updates
CRM-052: the configured FAA pair `retomar_consulta_vencida` / `es_AR` is valid when
Meta reports category `MARKETING`; `hello_world` and other arbitrary marketing
templates stay hidden from the human Inbox selector.

## Dependencies

- CRM-023 — WhatsApp Inbox 2
- CRM-052 — WhatsApp Service Window & Recontact Template
- CRM-053 — Opportunity Detail Soft Delete
- CRM-054 — Global Notification Soft Delete

## Scope

- Add nullable timezone-aware `WhatsAppConversation.deleted_at` through Alembic.
- Add authenticated, idempotent conversation hiding. Inbox lists, detail, attention,
  change feeds, message reads and normal mutations exclude hidden conversations.
- A later valid inbound message restores the same hidden conversation before it is
  projected, preserving its phone key, provider IDs, messages, attachments, Customer,
  Opportunity links and audit evidence.
- Add the Inbox destructive confirmation flow and immediate local selection/list
  reconciliation.
- Add an Opportunity Detail `Iniciar WhatsApp` action for a usable customer phone.
  It reuses an existing visible or hidden conversation for that customer/phone, or
  creates a resolved local conversation and links it to the Opportunity. Navigation
  opens the Inbox selection only after explicit action.
- For a new conversation, no free-form dispatch is created. The existing closed-window
  template UI remains the only allowed first outbound path; a later inbound response
  remains the only way to reopen free-form sending.
- Configure `retomar_consulta_vencida` / `es_AR`, hide `hello_world`, and preserve
  legitimate future non-marketing templates in the generic selector.

## Non-goals

- Physical deletion or restoration UI, bulk hiding, changing Customer/Opportunity
  visibility, deletion of messages/media/audit data, template creation, automatic
  dispatch, Railway configuration, production migration execution, deployment, or
  real Meta traffic.

## Business rules

- Hiding is an Inbox visibility state only. A valid inbound provider message restores
  the existing conversation atomically and keeps provider `wamid` idempotency.
- Both current authenticated commercial roles may hide a conversation they can access.
  Unknown, hidden, or unauthorized references return the existing safe not-found
  behavior and reveal no evidence.
- Phone normalization uses the existing WhatsApp customer identity convention. A
  missing or unusable phone disables initiation with clear Spanish feedback.
- A configured recontact template is selected by exact name and language, must remain
  provider-approved and supported, and may be `MARKETING` only for the approved FAA
  pair. `hello_world` is never exposed as a human commercial template.

## Data model

- `whatsapp_conversations.deleted_at` is nullable, timezone-aware and preserves every
  existing foreign key and unique phone key.
- An Inbox index supports normal non-deleted conversation ordering. No message,
  attachment, Customer, Opportunity or link is deleted or altered by hiding.

## Contracts / API

- `DELETE /whatsapp/conversations/{conversation_id}` returns `204 No Content` for an
  accessible visible or already hidden conversation; it is idempotent.
- `POST /opportunities/{opportunity_id}/whatsapp-conversation` returns the selected
  conversation detail. It never sends a provider message.
- Existing list/detail/template/message contracts retain their shapes. Hidden rows are
  absent from normal Inbox and polling projections.

## State transitions

- `visible -> hidden`: set `deleted_at` once and remove from Inbox projections.
- `hidden -> hidden`: successful no-op for a known accessible conversation.
- `hidden -> visible`: a new valid inbound message clears `deleted_at` under the
  existing conversation lock, then updates the ordinary inbound projection.
- `new web-contact conversation -> visible`: explicit Opportunity action creates a
  resolved conversation with the existing normalized contact identity and link; it has
  no inbound timestamp and therefore cannot authorize free-form messaging.

## Security & permissions

- Existing authenticated CRM access is required for every new command. The frontend
  never receives provider credentials or template IDs and never calls Meta.
- Service operations acquire locks in the repository's required order. No lock spans
  provider I/O.

## Edge cases

- The unique phone key means a hidden conversation is restored and reused, never
  duplicated. An active conversation for the customer with a different number may be
  reused only when it matches the customer's normalized phone.
- A concurrent hide and inbound delivery is resolved under the conversation lock;
  the later inbound makes the conversation visible.
- Failure or cancellation in either confirmation/action keeps the current view intact
  and offers retryable Spanish feedback.

## Acceptance criteria

- AC-01: An authenticated user can hide an accessible conversation through a centered
  destructive confirmation; cancellation and failure preserve the view.
- AC-02: Hidden conversations disappear immediately from Inbox, detail, attention and
  normal polling/list projections, while all message, attachment, Customer,
  Opportunity and audit rows remain stored.
- AC-03: Repeated hide is idempotent; inaccessible callers cannot infer a conversation;
  a new valid inbound message restores the same conversation and its existing IDs.
- AC-04: A WEB Opportunity with a valid phone opens an existing matching conversation
  or creates and links one without duplicates or automatic dispatch. A missing/invalid
  phone has an accessible disabled/error state.
- AC-05: New conversation initiation does not bypass the 24-hour rule. Template send
  records the normal outbound evidence; only a later inbound changes free-form
  availability.
- AC-06: `hello_world` is absent from human approved-template selection;
  `retomar_consulta_vencida` / `es_AR` is available when fresh, approved and supported
  even as `MARKETING`; other marketing templates remain unavailable.
- AC-07: Backend/frontend/browser coverage, migration checks, lint/typecheck, build,
  and the repository quality gates pass.

## Open decisions

None.

## Follow-up / future specs

Personal conversation archival, bulk Inbox controls, template administration and
marketing-consent changes require separate approval.

## Implementation notes

Use the existing `ConfirmationDialog`, typed WhatsApp API module, Inbox hook and
provider-neutral services. Railway must later set
`WHATSAPP_RECONTACT_TEMPLATE_NAME=retomar_consulta_vencida` and
`WHATSAPP_RECONTACT_TEMPLATE_LANGUAGE=es_AR`; this feature does not change Railway.
