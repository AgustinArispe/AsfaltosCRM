# CRM-049 — Meta WhatsApp Production Activation

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-19
Implementation commit: N/A

## Goal

Activate the existing Meta Cloud API WhatsApp integration in the FAA production
environment using the real WABA and Phone Number ID, with an explicit, reversible
configuration change and a verified public webhook path.

## Context

CRM-005 through CRM-011 already provide the provider-neutral WhatsApp domain,
conversation and message persistence, media boundary, Meta adapter, webhook mapper,
Inbox, templates, Broadcast processing, and delivery projection. CRM-032 adds the
production-safe `disabled` provider mode. This spec governs production activation and
the small verification/runbook work required to use those completed components with
real credentials; it does not replace their approved contracts.

`docs/BUSINESS_RULES.md` remains authoritative for Customer association, new
WhatsApp-contact Opportunities, the 24-hour customer-service window, templates, and
marketing consent.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API
- CRM-008 — WhatsApp Media Storage
- CRM-009 — Meta Cloud API Provider
- CRM-010 — WhatsApp Inbox Frontend
- CRM-011 — WhatsApp Broadcast Execution
- CRM-032 — Disabled WhatsApp Provider Mode

## Scope

- Configure the production backend explicitly with `WHATSAPP_PROVIDER=meta` and the
  existing validated Meta configuration variables.
- Use the existing public `GET` and `POST` `/api/whatsapp/provider/webhook` route for
  Meta verification and event delivery.
- Verify a real production ingress for one synthetic inbound message and the resulting
  existing Customer/conversation/message association, without creating duplicate
  records on Meta redelivery.
- Verify existing outbound text, approved-template, media, delivery-status, and Inbox
  behaviors against real provider evidence with safely scoped non-production-like test
  data.
- Add an operator runbook/checklist for Railway variables, public HTTPS endpoint,
  Meta dashboard configuration, rollback to `disabled`, and secret rotation.
- Confirm a persistent Railway volume is mounted at the configured
  `WHATSAPP_MEDIA_STORAGE_ROOT` before enabling media traffic.

## Non-goals

- Rebuild the provider, conversation, Inbox, media, Broadcast, or template
  architecture.
- Add Redis, Celery, a resident worker, a generic job queue, WebSockets, or a new
  message-processing service.
- Change Customer/Opportunity association, consent, roles, visibility, or existing
  WhatsApp business rules.
- Persist raw provider webhook bodies, expose provider payloads, or expose secrets in
  APIs, logs, metrics, UI, commits, or documentation.
- Add a template editor, campaign authoring, automatic campaign scheduler, or new
  marketing behavior.

## Business rules

- The frontend continues to communicate only with FastAPI.
- A free-form human reply is allowed only while the provider's 24-hour window decision
  permits it. At or after expiry, the existing composer blocks free-form dispatch and
  requires an approved template.
- Meta remains authoritative for templates, delivery status, policy enforcement, and
  final provider failures.
- Customer resolution, creation of a new-contact Opportunity, duplicate inbound
  handling, unread/waiting projection, and conversation linking continue to use the
  CRM-005 services unchanged.
- Broadcasts retain their existing consent and bounded processing rules.

## Data model

No migration is authorized for activation.

The current schema already supplies the production identifiers and idempotency points:

- `whatsapp_messages.external_message_id` is unique when present and stores Meta
  `wamid` values;
- `whatsapp_message_status_events` deduplicates provider status evidence by external
  message ID, provider state, and provider timestamp;
- `whatsapp_conversations.phone_match_key` is unique and drives the existing
  conservative Customer/conversation resolution; and
- `whatsapp_attachments` retains Meta media IDs separately from durable private media
  storage.

Inbound media stays `PENDING` until the existing media service downloads it through
the provider and stores it under the private configured media root. That provider I/O
does not occur in the webhook request.

## Contracts / API

Existing public contracts remain unchanged.

- `GET /api/whatsapp/provider/webhook` accepts Meta's `hub.mode`,
  `hub.verify_token`, and `hub.challenge`. It returns the challenge as plain text only
  for `subscribe` and a constant-time token match; otherwise it returns `403`.
- `POST /api/whatsapp/provider/webhook` reads the exact raw request bytes, verifies
  `X-Hub-Signature-256` as `sha256=<hex HMAC-SHA256>` with `META_APP_SECRET`, then
  maps supported events. It is unauthenticated by CRM JWT design.
- The mapper accepts inbound `text`, `image`, and `document` messages, and outbound
  status evidence `sent`, `delivered`, `read`, and `failed`, for the configured WABA
  and Phone Number ID only.
- Existing authenticated Inbox and message endpoints remain the only browser-facing
  contract. They already return `can_send_freeform`, `window_expires_at`,
  `template_required`, status timestamps, and safe errors.

## Webhook processing design

The existing request path is retained because it performs only bounded verification,
mapping, and local durable transactions:

1. Railway terminates TLS and forwards the untouched body to the public backend route.
2. FastAPI reads the body once and verifies the Meta signature before JSON parsing or
   application side effects.
3. The typed mapper filters the configured WABA and Phone Number ID and produces
   provider-neutral inbound/status events.
4. The existing webhook coordinator processes events in received order. Each service
   transaction uses the established advisory and row-lock ordering, revalidates state,
   and commits the persisted event before its acknowledgement.
5. The route returns `200` after accepted processing. It never downloads inbound media
   or calls Meta in the webhook request. Media transfer remains a separate existing
   durable-media operation; outbound delivery is initiated only by authenticated CRM
   commands or the existing bounded Broadcast processor.

This keeps acknowledgement small while preserving the CRM-009 contract that a
recognized event is not acknowledged before the existing durable service accepts it.
If production measurements show that the configured 2 MiB event batch cannot meet the
provider acknowledgement budget, a separate approved spec must define a narrow,
durable webhook inbox and its worker/retention model; no in-process background task is
authorized here.

## State transitions

No new state is introduced.

- Inbound events create exactly one message per `wamid`, refresh the existing
  conversation projection, and only apply the existing new-contact behavior on first
  conversation creation.
- `sent`, `delivered`, `read`, and `failed` status events retain their timestamps and
  reconcile monotonically despite duplicate or out-of-order delivery.
- Meta HTTP acceptance remains distinct from delivery. Existing ambiguous acceptance
  remains `UNKNOWN` and is never automatically resent.
- `WHATSAPP_PROVIDER=disabled` still omits all WhatsApp, Broadcast, and provider
  webhook routes. Returning to that value is the immediate production fallback.

## Security & permissions

- All credentials are server-side Railway service variables. Values are never placed
  in source control, frontend variables, build arguments, test fixtures, or operator
  screenshots.
- The App Secret is used only for POST HMAC verification; the verify token is used only
  for the GET challenge; the access token is used only in the adapter's bearer header.
- The production endpoint must use public HTTPS and exact host configuration. The CRM
  JWT does not protect the provider webhook.
- Existing request-size protection remains 2 MiB for the webhook. The platform/reverse
  proxy retains the documented shared, burst-tolerant webhook rate limit.
- The Inbox presents only the existing safe provider status/error projection. It never
  receives raw provider payloads, temporary media URLs, storage keys, tokens, or
  webhook signatures.

## Edge cases

- Retried inbound `wamid` messages and status deliveries do not create a second
  message, conversation, Customer, Opportunity, or status event.
- A status that arrives before an outbound send response is retained and attached by
  the existing reconciliation logic when the message external ID becomes known.
- A status for an unknown outbound message is retained as existing pending evidence;
  it does not create an invented message.
- Invalid/missing signatures are rejected before parsing. Valid unsupported events are
  acknowledged and ignored by the existing mapper.
- A disabled deployment neither loads Meta variables nor exposes the webhook route.
- The Graph API version is a deploy-time configuration value and must be a currently
  supported version verified against Meta documentation before each activation or
  rotation deployment.

## Acceptance criteria

- AC-01: Production starts only with explicit `WHATSAPP_PROVIDER=meta` and all current
  Meta settings validated; `disabled` starts without Meta settings and omits all
  WhatsApp/provider routes.
- AC-02: Meta completes the GET subscription challenge against the public HTTPS URL,
  while an invalid verify token returns `403` and reveals no secret.
- AC-03: A signed real/synthetic inbound text creates or associates only the existing
  Customer, Conversation, Message, and allowed first-contact Opportunity records; a
  repeated delivery of the same `wamid` changes none of their counts.
- AC-04: A signed real/synthetic inbound image or document persists existing attachment
  metadata without downloading provider media in the webhook request; its durable
  content is retrievable only through the existing authorized media boundary after
  storage succeeds.
- AC-05: Signed `sent`, `delivered`, `read`, and `failed` evidence persists in the
  existing status model and appears in the Inbox after its normal polling cycle;
  duplicate and out-of-order deliveries remain monotonic.
- AC-06: The Inbox visibly distinguishes an open customer-service window from a closed
  one, blocks free-form sends outside it, and offers only the existing approved-template
  path in that state.
- AC-07: Real Meta text/media/template sends use the existing adapter, preserve safe
  rate-limit/provider-failure behavior, and never expose a token, raw provider error,
  or temporary media URL.
- AC-08: Railway has a persistent volume mounted at `WHATSAPP_MEDIA_STORAGE_ROOT`; a
  controlled deploy/restart preserves an existing authorized media object.
- AC-09: The deployment runbook verifies startup, endpoint reachability, rate/body
  limits, rollback to `disabled`, secret redaction, and the existing quality gates
  without recording credential values.

## Open decisions

None.

## Follow-up / future specs

- A narrow durable webhook inbox only if measured production acknowledgement latency
  requires it; that future scope must define retention, replay, worker ownership, and
  operational alerting.
- Persistent Meta template catalog or richer template component support.
- Broader production-topology work still tracked by CRM-017.

## Implementation notes

Before implementation, verify the configured Graph API version and Meta dashboard
field subscriptions against the then-current official Meta documentation. Use
synthetic controlled contacts and approved templates for production smoke checks; do
not use arbitrary customer conversations. Tests must cover raw-body signature mutation,
handshake rejection, WABA/Phone Number filtering, `wamid` replay, out-of-order statuses,
window enforcement, disabled-route absence, startup validation, volume persistence,
and safe redaction.
