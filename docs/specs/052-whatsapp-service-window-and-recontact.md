# CRM-052 — WhatsApp Service Window & Recontact Template

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-23
Implementation commit: e3c0923

## Goal

Make Meta's 24-hour customer-service window clear and actionable in the WhatsApp
Inbox, while allowing a human to re-contact a customer only through a specifically
configured, currently approved service template after that window has closed.

## Context

CRM-023 already calculates the provider window from the last inbound message, blocks
free-form sends after expiry, polls the Inbox, and supports provider-approved human
templates. This feature makes that existing enforcement visible and gives the closed
state a focused, production-safe recovery path. `docs/BUSINESS_RULES.md` remains
authoritative: Meta is the source of truth for templates, approval and policy.

## Dependencies

- CRM-023 — WhatsApp Inbox 2
- CRM-009 — Meta Cloud API Provider
- CRM-049 — Meta WhatsApp Production Activation

## Scope

- Show one compact per-conversation service-window status in the active Inbox chat:
  open, closing soon, or closed. Show a human-readable remaining time when there is a
  known expiry.
- Treat a remaining time of two hours or less as closing soon. This is visual guidance
  only; it neither prevents work nor produces notifications.
- When closed, keep free-form text and attachment sending disabled, explain the Meta
  restriction in Spanish, and surface the primary CTA `Usar plantilla para retomar
  contacto` at the composer.
- Add an optional non-secret runtime setting holding the configured *name* of FAA's
  recontact template. The CRM resolves that name against the fresh provider catalog;
  it exposes a template as recontact only if Meta currently reports it as approved,
  supported and non-marketing. Its language and all sendable details remain the
  provider's values. No Meta template ID is hardcoded or exposed.
- Reuse the current approved-template send endpoint, provider abstraction,
  idempotency key, message status/delivery model, and polling. The recontact selector
  shows only the catalog entries identified as recontact; absence is explicit and has
  no generic fallback.
- Keep the existing all-approved human-template selector available for its current
  use cases.
- Update the active conversation from its existing polling stream so a new inbound
  message automatically restores the open window and composer without a page reload.

## Non-goals

- Bypassing, extending, or attempting to reopen Meta's 24-hour window with a template.
- Creating, editing, approving, or persisting a Meta template catalog; changing Meta
  template names/languages/statuses from the CRM; adding a template editor.
- Adding periodic notifications, browser push notifications, SSE/WebSockets, Redis,
  Celery, or changes to marketing broadcasts, consent, opportunity lifecycle,
  customer linking, private media, authentication, or delivery states.

## Business rules

- Free-form sending is authorized only by the existing provider window decision from
  the last inbound customer message. A template send never changes `last_inbound_at`
  and therefore never reopens free-form sending.
- A later valid inbound customer message updates `last_inbound_at`; the existing
  provider calculation then reopens the window automatically.
- The recontact template is available only when the configured name matches a fresh,
  currently approved and supported, non-marketing provider template. Pending,
  rejected, paused, missing, unsupported, or marketing entries are unavailable.
- The suggested copy submitted for Meta approval is: `Hola {{1}}, somos de FAA. Te
  escribimos para continuar con tu consulta. Cuando puedas, respondé este mensaje y
  seguimos por acá.` The CRM neither stores nor assumes that copy; the Meta catalog is
  authoritative.

## Data model

No persistence or schema changes. The configured template name is runtime
configuration, not a database catalog and not a Meta ID.

## Contracts / API

- The existing human-template catalog response adds a typed nullable purpose marker:
  `RECONTACT` only for a current configured catalog match; all existing template data
  remains compatible.
- The existing template-send endpoint continues to validate the selected name,
  language, approval, sendability, parameters and header media against a fresh
  provider snapshot before dispatch.
- Existing conversation/free-form fields remain the server authority. The frontend
  derives display status from `can_send_freeform` and `window_expires_at`; it does not
  authorize sends locally.

## State transitions

- `OPEN` when the existing provider decision permits free-form sending and more than
  two hours remain; `CLOSING_SOON` when it permits sending with two hours or less;
  `CLOSED` when it does not. A missing expiry while sending is permitted renders as
  open without a countdown.
- A template send keeps the state `CLOSED`. A new inbound message transitions from
  `CLOSED` to `OPEN` or `CLOSING_SOON` according to the recalculated expiry.

## Security & permissions

- All catalog and send operations require existing authenticated CRM access. The
  frontend never calls Meta and never receives template IDs, access tokens, raw
  provider payloads, storage keys or private-media URLs.
- The backend revalidates provider approval/sendability at send time; client purpose
  markers cannot authorize a template.

## Edge cases

- If no configured match exists, the CTA opens an explicit unavailable state rather
  than selecting any approved template. If a previously visible template changes
  status before confirmation, the existing send validation rejects it without a
  provider send.
- Countdown refreshes locally only in the active chat (minute precision and precise
  threshold/expiry wakeups); it creates no minute-by-minute API traffic or
  notifications.
- A delayed or out-of-order polling change is merged through the existing freshness
  rules. A new inbound update changes the selected detail and composer in place.
- Template provider success/failure retains the existing sent/delivered/read/failed
  evidence and error behavior. A successful template response cannot flip
  `can_send_freeform` to true.

## Acceptance criteria

- AC-01: An open conversation shows a compact open status and remaining time where
  available; a conversation with at most two hours remaining shows a non-blocking
  amber warning; an expired conversation shows closed status.
- AC-02: The closed composer disables free-form text/attachments, explains why in
  Spanish, and exposes `Usar plantilla para retomar contacto` without searching the
  generic template UI.
- AC-03: The catalog marks only the configured, fresh Meta-approved, supported,
  non-marketing template as `RECONTACT`; a missing, pending, rejected or marketing
  match produces no recontact option and no fallback.
- AC-04: Recontact template selection and sending use the existing provider pathway,
  idempotency and delivery states; send success or failure preserves closed free-form
  state.
- AC-05: A new inbound reply updates the active Inbox via polling and enables the
  composer without a full page reload.
- AC-06: Focused WhatsApp backend/frontend tests cover open/closing/closed statuses,
  blocked free-form, recontact availability/unavailability, send success/failure,
  no reopening on template send, inbound reopening, countdown updates and in-place
  polling; all repository quality gates and Docker browser suite pass.

## Open decisions

None.

## Follow-up / future specs

Template catalog administration, template lifecycle operations, multiple named
recontact purposes, notification policies, and real-time transport each require a
separate approved spec.

## Implementation notes

Use the existing provider catalog service rather than a local catalog. `WHATSAPP_RECONTACT_TEMPLATE_NAME`
is deliberately an optional template-name selector, not a credential or an external
ID; production setup must first create and approve the template in Meta, then set the
matching name. Keep UI status logic in a typed presentation component and use native
disabled controls, accessible status text and the existing accessible modal.
