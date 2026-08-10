# CRM-010 — WhatsApp Inbox Frontend

Status: Draft
Owner: FAA CRM team
Last updated: 2026-08-10
Implementation commit: N/A

## Goal

Provide a desktop-first WhatsApp Inbox inside the existing CRM so FAA users can find
conversations needing attention, read and reply quickly, exchange supported media, and
connect the chat to useful Customer and Opportunity context without leaving FastAPI as
the sole backend boundary.

## Context

CRM-005 owns WhatsApp business behavior and persisted state. CRM-006 exposes the
authenticated client contracts and polling protocol, CRM-007 builds their projections,
CRM-008 stores media, and CRM-009 supplies the real provider boundary. This spec owns
only the Inbox frontend and does not redefine those modules.

The current frontend uses React, TypeScript, Tailwind CSS, the existing `AppShell` and
navigation, a small internal router, typed API modules, and shared buttons, badges,
loading, feedback, modal, and drawer components. CRM-010 extends that system rather
than introducing a second visual or navigation framework.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API
- CRM-007 — WhatsApp Query Layer
- CRM-008 — WhatsApp Media Storage
- CRM-009 — Meta Cloud API Provider

## Scope

- Add a `WhatsApp` entry to the authenticated CRM sidebar for both current roles.
- Add a desktop Inbox workspace with three operational panels: conversation list,
  active chat, and compact CRM context.
- Support conversation search plus waiting and unread filters while preserving the
  deterministic priority supplied by CRM-006.
- Implement initial loads, cursor-based incremental polling, reconnect/focus resync,
  keyset history paging, and stable local upserts.
- Read text, image, and document messages and send text, supported images, and PDF
  documents through CRM-006.
- Present unread, waiting, dispatch, delivery, read, failure, retry, and backend window
  evidence without inventing frontend states.
- Mark the active conversation read using the global team read endpoint.
- Show useful Customer and linked/suggested Opportunity context, allow link/replace/
  unlink actions, and provide navigation to existing CRM detail pages.
- Provide complete loading, empty, offline, stale, recoverable-error, keyboard, focus,
  and screen-reader behavior for the Inbox.
- Keep the workspace usable on smaller desktop/laptop screens without defining a
  separate mobile product.

## Non-goals

- Meta/WABA setup, provider configuration, webhooks, or any backend change.
- New persistence, API routes, query behavior, state transitions, or business rules.
- Broadcasts, marketing consent, campaigns, segmentation, or campaign UI.
- Persistent template management, template editor, or template-send UI before an
  approved CRM API contract exists.
- WebSocket, SSE, Redis, Celery, or a frontend event-sourcing/cache framework.
- Audio, video, stickers, location, contacts, or other unsupported message types.
- A native mobile app or mobile-specific navigation and interaction design.
- Reproducing full Customer or Opportunity detail pages inside the Inbox.
- Cloning WhatsApp Web branding, layout details, or decorative behavior unnecessarily.

## Business rules

- All Inbox data and actions use authenticated CRM APIs. The frontend never calls Meta
  or a media provider directly and never evaluates WhatsApp policy itself.
- The team shares one global unread state. Opening and successfully displaying a
  conversation marks it read for everyone; it does not change waiting state.
- Conversations waiting for a valid human response remain the highest operational
  priority. Failed, pending, in-progress, or unknown outbound attempts do not hide that
  state unless CRM-005/006 report otherwise.
- Existing Customers do not receive new Opportunities automatically from this UI.
  Linking is explicit, replacement preserves history, and unlinking does not delete
  historical links.
- When `can_send_freeform=false`, the composer is disabled and explains that an
  approved template is required. CRM-010 does not offer template sending because
  CRM-006 has no such endpoint.
- Media is limited to `IMAGE` and `DOCUMENT`; the V1 outbound document UX accepts PDF.
  Provider URLs, storage keys, and base64 message payloads are never client contracts.

## Data model

No backend schema, migration, or browser persistence is introduced.

Frontend models are strict TypeScript representations of CRM-006 resources:

- conversation summary/detail, Customer summary, Opportunity summary/link;
- message, attachment, sender, dispatch status, and delivery status;
- conversation/message page and change-feed cursors;
- outbound text/image/document requests and media upload responses.

The Inbox keeps an in-memory projection keyed by local conversation/message ID, plus
the last acknowledged opaque cursors, active filters, selected conversation ID,
history-page cursor, and transient composer/upload state. Provider payloads and ORM
shapes are not represented. A full page reload performs a fresh initial load; durable
offline storage is outside this scope.

## Contracts / API

CRM-010 consumes the existing CRM-006 endpoints without changing their payloads:

- `GET /api/whatsapp/conversations` for initial/filter snapshots and older list pages;
- `GET /api/whatsapp/conversations/changes` for incremental summary upserts;
- `GET /api/whatsapp/conversations/{id}` for selected detail and links;
- `GET /api/whatsapp/conversations/{id}/messages` for newest/older history;
- `GET /api/whatsapp/conversations/{id}/messages/changes` for message/status/media
  upserts;
- `POST /api/whatsapp/conversations/{id}/messages` for typed outbound sends;
- `POST /api/whatsapp/conversations/{id}/read` for global read state;
- `PUT` and `DELETE /api/whatsapp/conversations/{id}/opportunity-link` for explicit
  association changes;
- `POST /api/whatsapp/media` plus authenticated media/attachment content endpoints.

The context panel may use the existing core CRM Customer and Opportunity detail
endpoints by the IDs returned from CRM-006. Customer detail supplies email; active
Opportunity detail supplies quoted products and kilograms. This enrichment is bounded
to the selected conversation and must not trigger per-row calls from the conversation
list.

### Inbox layout and conversation list

On wide desktop screens the workspace occupies the available AppShell content height:

1. a bounded-width conversation list with search/filter controls;
2. a flexible chat panel with header, message history, and composer;
3. a compact CRM context panel.

On smaller laptop widths the context panel becomes an explicit accessible toggle/
drawer while list and chat remain the primary workspace. At widths where both primary
panels cannot fit safely, the selected panel may occupy the workspace with an obvious
back action. This is responsive protection, not a separate mobile product design.

Conversation rows show only scannable evidence: display/Customer name, phone when
needed, latest activity preview/time, unread count, waiting emphasis, and identity/
window exceptions. Backend order is preserved:
`waiting_for_response`, unread, latest message, stable ID. Polling may reorder rows but
must never change the active conversation automatically.

Search is debounced and uses the CRM-006 search contract. Waiting and unread filters
combine with AND. Changing search/filter starts a fresh snapshot and cursor. Additional
conversation pages use the supplied page cursor through an explicit, accessible load
more action; page walking does not use offsets.

### Polling and selection stability

1. Initial load fetches the first conversation snapshot, stores its `sync_cursor`, and
   selects the first prioritized item only when no valid selection exists.
2. While the document is visible and online, conversation and selected-message change
   feeds poll on one shared configurable cadence, initially five seconds. Requests do
   not overlap; `has_more` pages drain immediately before the next interval.
3. Full resource summaries/messages are upserted by local ID. Conversation rows are
   re-sorted with the CRM-006 order and active filters; messages are sorted by
   `(message_at, id)`.
4. Selecting a conversation aborts obsolete detail/message work, loads detail and the
   newest message page, records that message `sync_cursor`, then marks the successfully
   displayed conversation read. Repeated read calls are harmless.
5. Polling, row movement, unread clearing, waiting changes, and status updates do not
   steal focus or replace the selected conversation. If the selected row leaves the
   current filter, its chat may remain open until the user selects another result or
   the resource becomes unavailable.
6. Older messages load with `before_cursor` while preserving the visible scroll anchor.
   Initial activation scrolls to the newest message. New messages auto-scroll only when
   the user is already near the end; otherwise a visible new-message affordance is
   shown.
7. Offline/background state pauses interval polling. Browser focus, visibility regain,
   and online reconnect trigger an immediate cursor resync. A rejected/unsupported
   cursor discards only the affected local projection and repeats that initial load.

### Message presentation and composer

- Inbound and outbound messages are visually distinguishable without relying on color
  alone. Text preserves intentional line breaks; timestamps use existing formatters.
- Images render from authenticated attachment content fetched as a blob. Documents show
  sanitized filename/type/size and an authenticated open/download action. Temporary
  object URLs are revoked when replaced or unmounted.
- Outbound state is expressed with compact accessible labels/tooltips: local submitting,
  accepted/sent, delivered, read, failed, or acceptance unknown. Provider and dispatch
  evidence from CRM-006 is authoritative; the UI never synthesizes delivery.
- The text composer supports multiline input. `Enter` sends, `Shift+Enter` inserts a
  newline, and IME composition never triggers a send. Sending is disabled for empty
  content, an active request, unresolved/unavailable identity, or a closed freeform
  window, with an adjacent explanation rather than a disabled control alone.
- One outbound attachment may be staged at a time. The UI validates obvious type/size
  hints, uploads multipart bytes, receives an opaque `media_ref`, and sends that
  reference with optional caption. Backend validation remains authoritative. No base64
  or provider URL enters message JSON.
- A `client_generated_id` is created once per send intent. A transport retry reuses that
  UUID; explicit resend of a durable failed/unknown message uses a new UUID and the
  reported `retry_of_message_id` contract. An optimistic local row may show submission
  progress but is replaced only by a server resource with the same send intent.

### CRM context panel

The context panel contains only operationally useful information:

- Customer name, company, phone, email, and province when available;
- active or suggested Opportunity, its status, source, and availability;
- quoted products and kilograms for the active linked Opportunity;
- link, replace, and unlink actions permitted by CRM-006;
- quick links to the existing Customer and Opportunity detail pages.

Suggestions are never auto-linked. Replacing or unlinking an active link requires a
clear confirmation that history is preserved. `NEEDS_REVIEW`, unavailable Customer,
deleted Opportunity, and invalid ownership outcomes are shown as non-actionable safe
states. Historical link lists and full CRM editing stay on existing detail surfaces.

## State transitions

CRM-010 introduces no domain transition. It renders CRM-005/006 evidence and invokes
their commands.

Frontend-only request states are bounded and replaceable:

- initial load: `idle -> loading -> ready | error`;
- polling: `idle -> refreshing -> idle`, retaining the last good projection on error;
- send/upload: `idle -> submitting -> reconciled | recoverable error`;
- connection: `online -> offline/stale -> resyncing -> online`.

A send response or message poll upserts the authoritative server state. `UNKNOWN` stays
visibly uncertain and is never presented as failed or automatically resent. `FAILED`
does not become delivered/read unless a later CRM-005 projection says so.

## Security & permissions

- Both `SUPERVISOR` and `VENDEDOR` use the same globally visible Inbox; no seller-based
  filtering is added.
- Every CRM/media request uses the existing authenticated API session and global `401`
  handling. Media blobs are not loaded from unauthenticated public URLs.
- The frontend contains no Meta access token, App Secret, verify token, WABA/phone
  configuration, provider media URL, raw webhook body, raw provider response, storage
  key, filesystem path, or unsafe provider error.
- Render message/customer text as text, not HTML. Filenames and response content types
  remain backend-sanitized; the frontend does not infer trust from extensions.
- Composer drafts and downloaded media are not persisted in local/session storage in
  this scope. Object URLs and aborted requests are cleaned up.

## Edge cases

- An empty Inbox, empty filter/search result, no selected conversation, and a selected
  conversation with no available messages each have distinct useful empty states.
- Initial-load failure provides retry; polling failure keeps the last good data with a
  non-blocking stale/reconnect indication and bounded retry cadence.
- A conversation deleted/unavailable between list and detail returns to a safe
  unselected state without selecting another conversation unexpectedly.
- Rapid selection changes cannot allow stale responses from a prior conversation to
  overwrite the active chat or context.
- Duplicate change-feed resources and identical send replays upsert by stable local ID
  and never create duplicate bubbles.
- If a message arrives while older history is loading, both cursors continue serving
  their separate purposes and the scroll anchor is retained.
- Read success with a concurrent new inbound must accept the next polling summary as
  authoritative rather than forcing the local count to zero.
- Attachment upload success followed by send failure retains the opaque upload for the
  same explicit retry intent; it does not silently send again.
- Context enrichment failure does not block chat use. It shows a scoped retry while the
  CRM-006 summary remains visible.
- A closed window, `NEEDS_REVIEW`, unavailable Customer, active reply conflict,
  definitive provider failure, and unknown acceptance use CRM-006 safe error/detail
  semantics and do not reveal provider internals.

## Acceptance criteria

- AC-01: An authenticated user can open the `WhatsApp` sidebar entry and receive a
  three-panel desktop Inbox or its documented smaller-laptop adaptation, with useful
  loading, empty, and initial-error states.
- AC-02: The conversation list preserves CRM-006 waiting/unread/activity priority,
  exposes waiting and unread evidence clearly, and never changes the active
  conversation because polling reorders rows.
- AC-03: Debounced search plus waiting/unread filters start fresh snapshots, combine
  correctly, page with opaque cursors, and show distinct no-result feedback.
- AC-04: Conversation polling drains `has_more`, upserts duplicate/full resources by
  local ID, reapplies the current view, and performs no full Inbox download on each
  normal interval.
- AC-05: Selection loads detail/newest messages once, remains stable across upserts,
  aborts stale selection work, and preserves message scroll position when older pages
  or new messages arrive.
- AC-06: Message history and change polling render chronological text, image, and
  document resources without duplicate bubbles or raw provider/storage fields.
- AC-07: A valid text send uses one stable `client_generated_id`, reconciles the server
  response/poll result into the chat, and does not duplicate dispatch after a transport
  retry.
- AC-08: An authenticated user can stage, upload, preview/remove, and send a supported
  image or PDF/document with optional caption through `media_ref`, without base64 or a
  provider URL in JSON.
- AC-09: Successfully displaying a conversation invokes the idempotent global read
  endpoint, clears the reported unread count without clearing waiting, and accepts a
  concurrent later inbound count as authoritative.
- AC-10: Outbound accepted/sent/delivered/read/failed/unknown evidence is visible and
  understandable without color alone; duplicate or out-of-order updates never produce
  a frontend downgrade contrary to the server projection.
- AC-11: When the backend reports `template_required`, the freeform composer is disabled
  with its reason and expiry context; no template-send control or frontend policy
  override is offered.
- AC-12: The context panel shows bounded Customer and active/suggested Opportunity data,
  enriches only the selected context for email/products/kg, and links to existing full
  detail pages.
- AC-13: Link, replace, and unlink actions call CRM-006, preserve historical semantics,
  update the selected projection, never auto-create an Opportunity, and surface safe
  conflict/not-found outcomes.
- AC-14: The conversation selector, filters, message log, composer, attachment controls,
  context toggle, confirmations, and status/error feedback are fully keyboard usable,
  have programmatic labels/focus behavior, and do not announce the initial history as
  a flood of new messages.
- AC-15: Offline, focus, visibility, and reconnect handling pauses overlapping polling,
  resumes from acknowledged cursors, resets only rejected projections, retains last
  good data, and offers scoped retry feedback.
- AC-16: Frontend source, rendered output, tests, and network contracts contain no Meta
  or storage secrets, raw provider/webhook payloads, temporary provider URLs, or direct
  provider requests.

## Open decisions

None

## Follow-up / future specs

- Template selection and sending UX after an approved persistent/read/send API contract.
- WhatsApp Broadcast execution UI together with consent and template catalog specs.
- Alternate realtime transport (SSE/WebSocket) only if measured polling UX requires it.

## Implementation notes

Keep WhatsApp API access, cursor reconciliation, polling ownership, and projection
types outside visual components. Reuse `AppShell`, routing, authentication, buttons,
badges, feedback, loading, modal/drawer, formatters, and existing Customer/Opportunity
detail routes where they fit; introduce shared components only for real Inbox
responsibilities.

Implementation should use the installed UI/UX, accessibility, and motion skills for
review and validation. Motion, if any, must clarify panel/context changes or message
appearance, remain subtle, and respect `prefers-reduced-motion`.
