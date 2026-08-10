# CRM-009 — Meta Cloud API Provider

Status: Approved
Owner: FAA CRM team
Last updated: 2026-08-10
Implementation commit: N/A

## Goal

Provide a production Meta Cloud API adapter for the existing `WhatsAppProvider`
protocol while keeping the domain, query layer, CRM API, media storage, and frontend
independent from Meta.

## Context

CRM-005 owns the provider protocol, typed message contracts, state reconciliation, and
business behavior. CRM-006 owns authenticated CRM APIs, CRM-007 owns read projections,
and CRM-008 owns durable media storage. CRM-009 defines only Meta transport and mapping
boundaries and must not redefine those modules.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API
- CRM-007 — WhatsApp Query Layer
- CRM-008 — WhatsApp Media Storage

## Scope

- Implement `MetaCloudApiProvider` against the unchanged CRM-005 protocol.
- Add typed Meta HTTP serialization, response decoding, authentication, timeouts,
  bounded retries, safe error mapping, and observability.
- Verify Meta webhook subscriptions and signatures, and map recognized inbound/status
  payloads into existing provider-neutral inputs.
- Upload outbound image/document content, download inbound media, synchronize template
  snapshots, and evaluate the customer-service window.
- Select and validate Meta runtime configuration only when
  `WHATSAPP_PROVIDER=meta`.

## Non-goals

- Frontend or CRM-006 authenticated API contract changes.
- Database tables, migrations, ORM access, or persistent template storage.
- CRM-005 business rules, identity resolution, Customer/Opportunity creation,
  Conversation mutation, query projections, or message state-machine changes.
- CRM-008 storage implementation changes, public media URLs, or provider URLs exposed
  through the CRM API.
- Broadcast execution, marketing consent, campaign creation, or template editing.
- Redis, Celery, WebSockets, SSE, or a general-purpose integration framework.
- WABA/App provisioning, production secrets deployment, token rotation operations, or
  live credential setup.

## Business rules

- Meta remains the source of truth for templates, delivery states, and messaging
  policy; the adapter only translates that evidence into CRM-005 contracts.
- Freeform-window decisions remain backend-owned and cannot be calculated or
  overridden by the frontend.
- Temporary Meta media URLs are transport details. They are never persisted or exposed
  to CRM clients; CRM-008 remains the durable media boundary.
- The adapter does not create or resolve any FAA commercial entity and does not apply
  Customer, Opportunity, unread, waiting, or linking rules.

## Data model

No schema or migration is authorized. The adapter does not import SQLAlchemy or ORM
models.

Template synchronization may maintain one process-local, immutable last-complete
snapshot. It is empty after restart and is not a source of durable truth. Persistent
template/cache fields belong to a future approved spec.

## Contracts / API

`MetaCloudApiProvider` implements the CRM-005 `WhatsAppProvider` methods exactly:

- `send_text(SendTextRequest) -> ProviderSendResult`
- `send_image(SendImageRequest) -> ProviderSendResult`
- `send_document(SendDocumentRequest) -> ProviderSendResult`
- `send_template(SendTemplateRequest) -> ProviderSendResult`
- `download_media(ProviderMediaReference) -> ProviderMediaPayload`
- `list_templates() -> tuple[ProviderTemplateSnapshot, ...]`
- `evaluate_window(WindowEvaluationContext) -> WindowDecision`

No Meta request/response model escapes this adapter. Known JSON structures use strict,
typed boundary DTOs; raw dictionaries are not application contracts. External payloads
may contain unknown fields for forward compatibility, but every consumed field is
validated and mapped explicitly without `Any`, casts, or `type: ignore`.

Provider-specific helpers such as media upload, pagination, webhook verification, and
payload mapping are internal composition, not new `WhatsAppProvider` methods.

The authenticated routes and response schemas in CRM-006 remain unchanged. A separate
provider webhook ingress is available at `GET` and `POST`
`/api/whatsapp/provider/webhook` only in Meta mode. It is not a CRM user endpoint and
does not use JWT authentication.

## Provider architecture

- `MetaCloudApiProvider` owns the existing provider methods and maps their typed inputs
  and outputs.
- A typed Meta Graph client owns base URL/version composition, bearer authentication,
  request execution, streaming, pagination, and bounded retry mechanics.
- `MetaWebhookVerifier` owns GET verification and POST signature verification over the
  exact raw request bytes.
- `MetaWebhookMapper` maps recognized payloads into the existing
  `InboundMessageInput` and `ProviderDeliveryEvent` types, or a typed ignored-event
  result.
- A thin provider-neutral webhook coordinator invokes CRM-005 inbound/status services
  after verification and mapping. The mapper and provider never invoke SQLAlchemy,
  domain services, or FastAPI directly.
- A provider-neutral runtime template snapshot cache atomically accepts only a complete
  successful `list_templates` result. It is not part of the domain or persistence.

Dependencies point inward through typed contracts. Replacing Meta changes provider
assembly and webhook verification/mapping components only.

## Configuration and authentication

Meta mode requires validated backend runtime settings equivalent to:

- `WHATSAPP_PROVIDER=meta`
- `META_GRAPH_API_VERSION`
- `META_ACCESS_TOKEN`
- `META_PHONE_NUMBER_ID`
- `META_WABA_ID`
- `META_WEBHOOK_VERIFY_TOKEN`
- `META_APP_SECRET`
- `META_REQUEST_TIMEOUT_SECONDS`
- `META_RETRY_MAX_ATTEMPTS`
- `META_RETRY_BASE_SECONDS`
- `META_RETRY_MAX_SECONDS`

Names are backend configuration, not public API fields. IDs and API version must be
nonempty and syntactically valid; timeouts/retry values must be positive and bounded.
The Graph origin is fixed to Meta HTTPS infrastructure rather than accepting an
arbitrary runtime URL.

All required Meta settings are validated eagerly at startup only when Meta is selected.
Fake mode starts without Meta variables. Graph requests use the access token in the
`Authorization: Bearer` header over verified TLS. The verify token is used only for the
GET handshake; the App Secret is used only to authenticate POST payload signatures.
Secrets are excluded from representations, exceptions, metrics, and logs.

## Webhook ingress

### GET verification

The ingress accepts Meta's `hub.mode`, `hub.verify_token`, and `hub.challenge` query
values. It returns the challenge verbatim only when mode is `subscribe` and the verify
token matches using constant-time comparison. Missing or invalid verification returns
a safe `403` and never reveals the expected token.

### POST verification and mapping

Before parsing JSON, `MetaWebhookVerifier` validates the official
`X-Hub-Signature-256: sha256=<digest>` header against HMAC-SHA256 of the exact raw body
using `META_APP_SECRET`, with constant-time comparison. Missing, malformed, or invalid
signatures are rejected; CRM JWT credentials are irrelevant.

After signature verification, the mapper:

- maps inbound text, image, and document messages to `InboundMessageInput`, including
  provider message ID, sender/contact identifiers, profile display name when present,
  UTC provider timestamp, caption/body, and typed attachment metadata;
- maps `sent`, `delivered`, `read`, and `failed` evidence to
  `ProviderDeliveryEvent`, including safe failure metadata;
- preserves the order of multiple entries/changes/messages while treating each event
  as independently replayable;
- ignores unsupported message types and unknown event/status kinds with a safe metric;
  it never invents a CRM state;
- rejects malformed recognized structures as mapping failures without exposing or
  retaining the raw payload.

A valid recognized event is acknowledged only after the existing CRM-005 service has
accepted it. Duplicate/redelivered events are expected and rely on CRM-005 durable
idempotency. Valid unknown events are acknowledged and ignored. Transient application
failure returns a retryable `5xx`; invalid signature never reaches application logic.
Raw payloads are not persisted indefinitely.

## Sending and reliability

All send methods post the official `messaging_product=whatsapp` message shape for the
configured Phone Number ID. Recipient, text, media, template name/language, and
parameters are mapped only from existing typed requests. Provider validation rejects a
request that cannot be represented safely by the configured Meta API version.

A successful Meta response must contain a nonempty external message ID. The provider
returns `ProviderSendResult` with that ID and an aware UTC acceptance timestamp. It
does not equate HTTP acceptance with delivery: `initial_state` is `None` unless Meta
explicitly supplies one of CRM-005's supported delivery states.

The CRM `client_generated_id` remains the local idempotency key. Meta does not provide
an equivalent guarantee through this contract, so:

- an optional opaque callback may aid correlation but is never treated as provider
  idempotency;
- explicit Meta error responses may be retried only under the bounded safe policy;
- a timeout/reset after request transmission, an ambiguous success body, or any lost
  acceptance response maps to unknown acceptance and is never automatically retried;
- CRM-005 persists `UNKNOWN`, and explicit resend uses a new local message and UUID.

Delivery ordering is not assumed. Later webhook evidence is mapped independently and
CRM-005 remains responsible for monotonic reconciliation.

## Media

For `send_image` and `send_document`:

1. An existing `provider_media_id` is serialized directly after provider validation.
2. A CRM-008 `storage_key` is resolved through an injected read-only `MediaStorage`
   boundary, never through filesystem paths.
3. The adapter uploads validated bytes to the configured Phone Number ID media
   endpoint, obtains a Meta media ID, and uses it in the message request.

Media upload is an internal helper, not a new provider method. If an upload succeeds
but message dispatch later fails, the Meta media object may expire unused; the existing
protocol does not persist that temporary upload ID. An upload retry may create an
unused duplicate media object but must never duplicate a message send.

`download_media` resolves the provider media ID to a fresh temporary URL and consumes
it immediately with authenticated HTTPS streaming. URLs are never persisted, logged,
returned, or trusted as arbitrary redirect targets. Expired URLs are resolved again by
media ID within the retry policy. Declared length and streamed bytes are bounded by the
CRM-008 configured type limit; provider checksum/metadata is verified when supplied.
The method returns `ProviderMediaPayload`, after which the existing CRM-005 media
service validates and stores content through CRM-008.

## Templates

`list_templates` paginates the configured WABA template endpoint to completion and
maps each item to `ProviderTemplateSnapshot`: external ID, name, language, category,
status, and header type. Language variants are distinct and Meta status values are
preserved safely; only explicitly sendable/approved states may be treated as usable.

Synchronization builds a complete candidate snapshot before atomically replacing the
process-local cache. Entries are upserted by external ID with `(name, language)`
uniqueness. A template missing from a successful complete snapshot is removed from the
runtime cache; missing entries are never inferred from a partial/failed pagination.
Sync failure retains the prior snapshot, reports failure, and never presents stale data
as freshly synchronized. Restart begins with an empty cache.

`send_template` maps only template shapes expressible by CRM-005's existing name,
language, and named text parameters. Templates requiring unsupported header media,
buttons, or component structures fail safely before dispatch. Extending the template
contract requires a future approved spec; this adapter does not redesign it.

## Window evaluation

`evaluate_window` is deterministic and performs no HTTP request. It maps
`last_inbound_at` and aware UTC `now` into the existing `WindowDecision` using Meta's
current customer-service-window policy, maintained as one versioned provider policy
constant rather than frontend or domain logic.

With no inbound timestamp it returns `can_send_freeform=False` and no expiry. Otherwise
it returns the exact UTC expiry and permits freeform strictly before that instant. The
current Meta policy duration cannot be extended by deployment configuration. Meta may
still reject a send, and that response remains authoritative through normal error
mapping.

## Error mapping

No raw Meta error or response body leaves the adapter. Failures map to the existing
`ProviderErrorDetails` contract:

| Meta/transport outcome | Provider mapping |
| --- | --- |
| Valid 2xx with external message ID | `ProviderSendResult` |
| Explicit non-retryable validation/auth/policy failure | `PERMANENT_FAILURE` |
| Explicit rate limit or retryable 5xx after bounded attempts | `RETRYABLE_FAILURE` |
| Connect/DNS failure known to precede transmission | `TIMEOUT_BEFORE_ACCEPTANCE` |
| Read timeout/reset after transmission or ambiguous 2xx | `TIMEOUT_UNKNOWN_ACCEPTANCE` |

Only stable provider codes and sanitized messages populate error details. Authentication
failures are operationally visible but never include token/config values. Media GET,
upload, and template-list failures use permanent/retryable kinds without claiming that
a message was accepted.

## State transitions

The adapter introduces no domain states. Meta send acceptance, delivery webhooks,
inbound messages, and errors are mapped into the CRM-005 dispatch/provider states and
processed by its existing services. Out-of-order or duplicate events never cause the
adapter to synthesize intermediate states.

## Security & permissions

- Meta webhook ingress is authenticated by handshake token or payload signature, not
  by CRM user JWT.
- The signature is checked over raw bytes before parsing or side effects.
- Access token, App Secret, verify token, raw bodies, phone numbers, media URLs, and
  message bodies are never logged or used as metric labels.
- Media retrieval accepts only URLs issued by the Meta media-resolution flow, requires
  HTTPS, validates the expected Meta host policy, and does not follow unvalidated
  redirects.
- CRM-006 user authentication and media authorization remain unchanged.
- The real-provider route table never registers fake development endpoints.

## Edge cases

- One webhook body may contain multiple recognized and unknown changes; one unknown
  item does not discard valid siblings.
- Status events may arrive before the send response, after retries, duplicated, or out
  of order; mapping preserves their external ID and provider timestamp.
- A 2xx response without a usable message ID is acceptance-unknown, not success.
- A successful media upload followed by an unknown message response does not authorize
  automatic resend.
- Temporary media URL expiry triggers ID re-resolution, never persistence of the URL.
- Partial template pagination never removes cached entries.
- New Meta fields/statuses are ignored safely until explicitly mapped; known malformed
  data produces a mapping failure metric.
- Configuration errors stop Meta-mode startup but do not prevent Fake mode startup.

## Performance

Targets apply to healthy Meta/network conditions, configured FAA media limits, and
operations without rate-limit backoff. Retries and throttling are measured separately:

| Adapter operation | Target P95 |
| --- | ---: |
| Message POST (`send_*`, excluding a preceding media upload) | ≤ 3 s |
| Media download (URL resolution plus bounded stream) | ≤ 10 s |
| Media upload (within configured size limit) | ≤ 10 s |
| Complete template sync (up to 500 templates) | ≤ 15 s |

The configured request timeout is finite and cannot be lower than the connect budget
or unbounded above. CI uses deterministic HTTP fixtures; it never requires live Meta
credentials. Production metrics determine operational P95 compliance.

## Observability

The adapter emits through an injected typed metrics boundary, without choosing an
exporter:

- `whatsapp_meta_http_duration_seconds` by safe operation, status class, and outcome;
- `whatsapp_meta_http_requests_total` by operation and status class;
- `whatsapp_meta_retries_total` by operation and safe retry reason;
- `whatsapp_meta_transport_failures_total` by operation and failure kind;
- `whatsapp_meta_mapping_failures_total` by payload kind;
- `whatsapp_meta_rate_limited_total` by operation;
- `whatsapp_meta_webhook_events_total` by supported event kind and outcome;
- `whatsapp_meta_template_sync_total` by outcome.

Structured logs contain only operation, safe outcome/category, attempt count, HTTP
status class, duration, and a local trace correlation value. Metrics and logs never
contain tokens, secrets, raw payloads, message bodies, phone numbers, template
parameters, provider media URLs, storage keys, or customer/message identifiers.

## Acceptance criteria

- AC-01: `MetaCloudApiProvider` satisfies the unchanged CRM-005
  `WhatsAppProvider` Protocol and no Meta type crosses that boundary.
- AC-02: Fake mode starts without Meta settings, while Meta mode fails startup safely
  for each missing/invalid required configuration value.
- AC-03: All Graph requests use the configured version/IDs, verified TLS, bearer
  authentication, finite timeouts, typed payloads, and no secret-bearing error output.
- AC-04: Text, image, document, and supported template requests map to deterministic
  Meta payloads; valid accepted responses return the external ID without fabricating a
  delivery state.
- AC-05: Explicit permanent/retryable failures and before/after-transmission timeouts
  map to the documented `ProviderErrorDetails`; unknown acceptance is never
  automatically retried.
- AC-06: GET webhook verification uses constant-time verify-token comparison and POST
  rejects missing/invalid raw-body signatures before parsing or side effects.
- AC-07: Signed inbound text/image/document payloads map to existing typed CRM-005
  inputs with aware UTC timestamps and never expose temporary media URLs.
- AC-08: Signed `sent`, `delivered`, `read`, and `failed` payloads map to
  `ProviderDeliveryEvent`; duplicate and out-of-order delivery remains safe through
  CRM-005 reconciliation.
- AC-09: Unknown webhook changes/types are acknowledged and measured without state
  invention, while transient application failure permits Meta redelivery.
- AC-10: Outbound media stored by CRM-008 uploads privately before send; inbound media
  download re-resolves expired URLs, enforces bounded streaming, and returns a typed
  payload for CRM-008 persistence.
- AC-11: Template listing consumes all pages, maps language/status/header metadata, and
  atomically replaces the runtime cache only after complete success; failed/partial
  sync does not remove prior entries.
- AC-12: Window evaluation returns the exact current-policy expiry, disallows freeform
  at/after expiry, and makes no provider HTTP request.
- AC-13: The provider, webhook verifier, and mapper import no FastAPI, SQLAlchemy, ORM,
  query-service, Customer, Opportunity, or Conversation behavior.
- AC-14: Provider/webhook logs and metrics cover latency, HTTP status, retries,
  transport/mapping failures, and rate limiting without prohibited sensitive values.
- AC-15: Deterministic fixture benchmarks satisfy the adapter performance budgets and
  all transport branches are testable without real Meta credentials.
- AC-16: Implementation passes strict project gates with no `Any`, casts, or
  `type: ignore`, and introduces no schema, migration, frontend, broadcast, or business
  behavior change.

## Open decisions

None

## Follow-up / future specs

- WhatsApp Broadcast execution, marketing consent, persistent template catalog, and
  richer template component contracts.
- Production Meta deployment and operations: App/WABA/phone provisioning, webhook
  subscription, secret management and rotation, live smoke tests, alerting, and
  runbooks.

## Implementation notes

Implementation must re-check all endpoint fields, signatures, statuses, policy values,
and API-version support against current official Meta documentation before approval
and coding. Tests should use minimal synthetic typed fixtures rather than retained
customer payloads.

The typed HTTP client and metrics boundary should be injected so unit tests can cover
pagination, retries, timeouts, mapping failures, temporary-URL renewal, and redaction
without network access. Provider runtime assembly selects either the existing Fake or
Meta implementation; no domain/router branch may inspect Meta-specific DTOs.
