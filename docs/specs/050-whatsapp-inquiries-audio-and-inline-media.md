# CRM-050 — WhatsApp Inquiries, Audio & Inline Media

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-22
Implementation commit: N/A

## Goal

Close three production gaps in the existing Meta WhatsApp integration: retain the
first inbound inquiry on the Opportunity it creates, receive and play audio safely,
and render private image attachments inline in the CRM conversation.

## Context

CRM-036 exposes the immutable original WEB inquiry in Opportunity Detail. A new
unknown WhatsApp contact already creates a Customer, Conversation, Opportunity and
first inbound message atomically, but the Opportunity does not reference that message.
The present WhatsApp type, webhook mapper, media policy, provider contract, upload
contract and UI cover only `TEXT`, `IMAGE` and `DOCUMENT`.

`docs/BUSINESS_RULES.md` remains authoritative except for the explicit user-approved
addition of WhatsApp audio in this spec. The existing private media design remains
authoritative: frontend code never communicates with Meta and never receives Meta
temporary URLs.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-008 — WhatsApp Media Storage
- CRM-009 — Meta Cloud API Provider
- CRM-036 — Web Consultation in Opportunity Detail
- CRM-049 — Meta WhatsApp Production Activation

## Scope

- Persist a nullable, immutable reference from an Opportunity created for a new
  WhatsApp contact to the exact first inbound `WhatsAppMessage` that caused its
  creation; never copy its body into a business snapshot.
- Return and render that reference in Opportunity Detail as the existing customer
  consultation section, labelled as WhatsApp. Text displays its persisted body;
  image, document, and audio display a truthful media-inquiry representation and
  link only through the existing authenticated CRM media endpoint.
- Accept Meta `audio` inbound webhook events and persist their wamid, metadata and
  attachment idempotently through the same deferred provider-download/storage flow
  as images and documents.
- Add `AUDIO` to the typed domain/API/frontend contracts and support the configured
  WhatsApp audio allowlist, including `audio/ogg; codecs=opus`/the normalized OGG
  Opus representation. Audio bytes are signature-validated, stored privately on
  the persistent media volume, and served only by the authenticated CRM endpoint.
- Extend the provider abstraction and Meta implementation to send a safely uploaded
  audio attachment. The existing composer may select an allowed audio file; recording,
  transcoding, and conversion are out of scope.
- Render available image attachments inline with a bounded, aspect-ratio-preserving
  preview. Use the existing authenticated fetch and object URL; keep open/download
  as secondary actions. Render available audio with a native inline, non-autoplaying
  audio player. Both media types have clear pending, unavailable and fetch-failure
  states and work in Light and Dark themes.

## Non-goals

- Redesigning WhatsApp conversations, Opportunity Detail, storage architecture,
  authentication, polling, templates, broadcasts, or provider selection.
- Video, stickers, locations, contacts, transcription, waveform generation,
  media editing, image processing, audio recording, or audio transcoding.
- Public URLs, provider URLs, filesystem paths, CDN/object-storage migration,
  antivirus scanning, or changes to document/image allowlists or their limits.
- Backfilling historical WhatsApp Opportunities with an inferred inquiry.

## Business rules

- The initial WhatsApp inquiry belongs only to an Opportunity atomically created for
  a new commercial contact. An existing customer/conversation or later inbound
  message does not set or replace it.
- The reference is immutable once set. Web intake behavior and its immutable
  `lead_intakes.message` snapshot are unchanged.
- Historical WhatsApp Opportunities may have no initial inquiry and remain valid;
  Detail shows no invented content for them.
- Wamid replay must return the original message/opportunity/inquiry reference and
  must not create or relink any entity.
- Audio is a supported WhatsApp message type. It follows the existing conversation
  window, human outbound authorization, status, retry and audit semantics; it has no
  caption. Meta's supported format and size rules are further restricted by the
  configured FAA allowlist and size limit.

## Data model

- Add `Opportunity.initial_whatsapp_message_id`, nullable, unique, and `SET NULL`
  foreign-keyed to `whatsapp_messages.id`. It is populated only when the atomic
  new-contact inbound flow creates that Opportunity; historical rows remain `NULL`.
- Add `AUDIO` to `whatsapp_message_type_enum` through Alembic. `WhatsAppAttachment`
  remains the sole attachment metadata/storage record; no audio body or duplicate
  inquiry table is introduced.
- The migration must enforce that the referenced message is inbound and belongs to
  the Opportunity's auto-created WhatsApp conversation in application logic under
  the established lock order. The foreign key and unique reference prevent dangling
  or shared inquiry references.

## Contracts / API

- `OpportunityDetail` adds a nullable typed WhatsApp initial-inquiry projection with
  message identity/type/body/timestamp and, where present, the existing safe
  attachment projection. It never includes provider IDs, raw storage keys,
  filesystem paths, or provider URLs.
- Existing Opportunity Detail response fields and WEB `web_intake` are compatible.
- WhatsApp message, attachment, media-upload metadata, outbound message request,
  provider request and frontend discriminated unions accept `AUDIO`.
- Media retrieval remains `GET /api/whatsapp/attachments/{id}/content` (and the
  existing private uploaded-media route), authenticated for active CRM users. It
  returns the validated stored MIME type, `Cache-Control: private, no-store`,
  `X-Content-Type-Options: nosniff`, and `Content-Disposition: inline` for image and
  audio; documents retain attachment disposition.
- Add only the necessary audio limit and comma-separated MIME allowlist configuration
  to settings and `.env.example`, with safe defaults documented and validated at
  startup. No provider token enters a browser response or log.

## State transitions

- Inbound audio attachment: `PENDING` on persistence, then `AVAILABLE` after deferred
  validated private storage or `FAILED` with a safe error. It uses the existing
  attachment state machine and retry behavior.
- The Opportunity inquiry reference is write-once and has no transition after the
  creation transaction commits.

## Security & permissions

- Preserve signed Meta webhook validation, wamid idempotency, transaction lock order,
  private persistent storage, size limits, MIME allowlists, byte-signature/content
  validation, authenticated retrieval, safe error messages, and no provider secrets
  in frontend/logs.
- Validate declared audio MIME against a narrow configured list and detect the
  container/signature before storage. OGG is accepted only when its headers prove an
  Opus stream; a generic OGG container is rejected. Browser-provided MIME strings are
  never trusted as sufficient validation.
- Frontend media is fetched with the existing bearer-authenticated endpoint, converted
  to an object URL, and revoked on replacement/unmount. CSP continues to allow only
  same-origin media plus `blob:`; no third-party media origin is added.
- Native audio controls are keyboard operable and non-autoplaying. Meaningful images
  have text alternatives; open/download controls have accessible names and loading or
  error feedback is announced without relying only on color.

## Edge cases

- A first inbound image/document/audio becomes a media inquiry even if its download
  later fails; Detail shows truthful unavailable media, never fabricated text.
- A repeated webhook with the same wamid and different content remains an idempotency
  conflict; it cannot mutate the initial inquiry.
- The media endpoint revalidates stored content before response. Missing storage,
  mismatched MIME, oversized content, malformed OGG/Opus, unauthorized access and
  expired/dead Meta URLs produce safe failure states without leaking internals.
- Image/audio object-URL fetch failures preserve the message and show retry-safe
  unavailable feedback. The UI must not render a Meta URL even transiently.
- Outbound audio requires a stored, validated `AUDIO` upload and an in-window human
  send. Unsupported/malformed audio is rejected before provider dispatch; provider
  rejection follows existing definitive/unknown-send behavior.

## Acceptance criteria

- AC-01: A first text inbound from an unknown contact creates exactly one Customer,
  Conversation, `WHATSAPP` Opportunity, message and immutable initial-inquiry
  reference; authenticated Opportunity Detail shows it as a WhatsApp consultation.
- AC-02: A first inbound image, document, or audio creates the same reference and
  Detail truthfully identifies the attachment/media inquiry without inventing body
  text or copying media metadata into Opportunity records.
- AC-03: Existing matched customers/conversations and later inbound messages never
  create, replace, or infer an Opportunity initial inquiry; historical Opportunities
  with no reference remain readable.
- AC-04: Same-wamid replay creates no duplicate message, Opportunity or inquiry link;
  conflicting replay is safely rejected.
- AC-05: Valid Meta inbound audio maps to `AUDIO`, persists attachment metadata and
  wamid idempotently, downloads deferred, validates/stores privately, and can be
  retrieved only by an authenticated CRM user with the validated audio Content-Type.
- AC-06: Oversize, disallowed MIME, generic/non-Opus OGG, malformed signature,
  content-type mismatch, missing file, and storage/provider failure reject or mark
  audio safely without a public/provider URL or filesystem path.
- AC-07: An allowed uploaded audio can be sent through the typed provider abstraction
  and Meta media/message requests, preserving current window, idempotency, status,
  retry and audit behavior. No recording or transcoding UI is added.
- AC-08: Available inbound/outbound audio renders an accessible, non-autoplaying
  inline player with pending, unavailable and error states in both themes; it uses an
  authenticated blob URL and revokes it on cleanup.
- AC-09: Available inbound/outbound images render a bounded inline preview with
  aspect ratio preserved and keyboard-accessible open/download secondary action;
  pending, missing and failed states are explicit and expose no Meta URL.
- AC-10: Focused backend/media/Opportunity tests, frontend Inbox/Opportunity tests,
  full backend/frontend suites, TypeScript, Biome, Ruff, mypy strict, build, Docker
  health checks and browser suite pass before the implementation commit.

## Open decisions

None.

## Follow-up / future specs

Audio recording, transcoding, transcripts, video, media retention/deletion policy,
image processing and a public/CDN media delivery strategy each require a separate
approved spec.

## Implementation notes

Reuse the current provider-agnostic attachment, deferred download, message projection,
authenticated endpoint and `useAuthenticatedMedia` lifecycle. Extend their typed
discriminated contracts rather than introducing a second media path. Use the current
Opportunity Detail consultation composition with a small typed inquiry projection;
do not query provider media from Detail. Add a focused audio signature detector and
tests instead of relying on a filename or declared MIME. Keep per-type size and MIME
configuration in the existing typed runtime policy.
