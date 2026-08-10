# CRM-007 — WhatsApp Query Layer

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-10
Implementation commit: `375b8cd`

## Goal

Define the read-side architecture that builds stable, UI-ready WhatsApp Inbox
projections for the future API and frontend.

## Context

CRM-005 owns WhatsApp persistence and command behavior. CRM-006 owns the authenticated
internal API contracts and external cursor protocol. CRM-007 owns only the query layer
between those boundaries and SQLAlchemy persistence.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API

## Scope

Typed query services and projections for conversation summaries/details, message history,
and changed-resource reads. The scope includes deterministic keyset pagination, search,
filtering, eager loading, polling read support, and query metrics.

## Non-goals

- New domain rules, provider behavior, HTTP endpoints, polling transport, dispatch, or
  state transitions.
- ORM entities exposed to routers or frontend serializers.
- Repository pattern, CQRS framework, caching layer, Redis, WebSockets, event sourcing,
  new tables, schema changes, or migrations.
- Provider-specific logic or provider calls from query services.

## Business rules

No business rules are introduced. Query results must reflect the CRM-005 persisted
state and the CRM-006 read contracts, including global unread state, waiting state,
identity review, historical opportunity links, and terminal message evidence.

## Data model

The query layer reads the existing CRM-005 tables:
`whatsapp_conversations`, `whatsapp_messages`, `whatsapp_message_status_events`,
`whatsapp_conversation_opportunities`, and `whatsapp_attachments`, together with the
existing Customer, Opportunity, User, and related timestamp data.

No query-side tables, denormalized projections, database views, schema changes, or
migrations are allowed. Cursors are typed in memory and encoded by the CRM-006 API
boundary; they are never persisted.

## Query architecture

The layers have one-way responsibilities:

1. CRM-005 command services perform mutations, provider dispatch, locking, and
   projection-maintaining side effects.
2. Query services issue read-only SQLAlchemy 2.x statements and map rows into typed
   projection DTOs. They never call command services or providers.
3. CRM-006 API routers authenticate requests, decode/encode its public cursor protocol,
   invoke query/command services, and serialize DTOs. Routers never serialize ORM
   entities directly.
4. SQLAlchemy persistence remains the source of read data. Query services may use
   explicit joins, subqueries, aggregates, and loader options, but not a repository
   abstraction.

All new Python is fully typed for `mypy --strict`: no `Any`, casts, or `type: ignore`.
Known structures use dataclasses, Pydantic models, `Protocol`, or explicit typed
collections rather than untyped dictionaries.

## Projection model

Projections are immutable, UI-ready DTOs with no SQLAlchemy relationships or sessions.
They contain only fields needed to render or update the Inbox:

- `CustomerSummaryProjection`: customer ID, name, company, phone, province, and an
  availability/deleted indicator. It is nullable for `NEEDS_REVIEW` conversations.
- `OpportunitySummaryProjection`: opportunity ID, status, source, created timestamp,
  link timestamp when applicable, and terminal/open indicator.
- `ConversationSummaryProjection`: local ID, phone/display data, resolution status,
  customer summary, active opportunity summary, open-opportunity suggestions, last
  message/inbound/outbound timestamps, unread count, waiting flag/since, stored window
  expiry, and `updated_at`.
- `ConversationDetailProjection`: the summary plus ordered historical opportunity-link
  projections and detail metadata needed by CRM-006. It does not contain the complete
  message history; that is a separate message query.
- `AttachmentProjection`: attachment ID, image/document type, MIME type, sanitized
  filename, known size, storage availability, and an API-resolvable content reference.
  Provider media IDs, storage keys, and temporary URLs are excluded.
- `MessageStatusProjection`: dispatch state, provider delivery state, accepted/sent/
  delivered/read/failed timestamps, and safe provider error metadata.
- `MessageProjection`: local/external IDs, conversation ID, direction/type, body,
  sender summary, client-generated ID, retry metadata, chronological `message_at`,
  attachment projection, and status projection.

`can_send_freeform`, template requirements, and provider policy reasons are not computed
by this layer. CRM-006 composes those fields from its backend window decision; the query
projection supplies only the persisted `window_expires_at`.

## Query services

### ConversationQueryService

Responsibilities:

- List conversation summaries using CRM-006 filters: `waiting_only`, `unread_only`,
  trimmed search, and typed page limits/cursors.
- Apply the CRM-006 deterministic inbox order:
  `waiting_for_response DESC`, `unread_count DESC`, `last_message_at DESC NULLS LAST`,
  `id DESC`.
- Build one conversation detail projection with customer summary, active link,
  historical links, and suggestions without loading all messages.
- Return nullable customer data and `NEEDS_REVIEW` faithfully; never infer identity or
  create an opportunity.

### MessageQueryService

Responsibilities:

- Read a bounded newest/older message page in chronological `(message_at, id)` order.
- Map persisted dispatch/delivery evidence, retry metadata, and attachment availability
  into `MessageProjection` values.
- Read message changes after a typed resource cursor, including status reconciliation and
  attachment-storage updates.
- Never return raw status-event rows, provider payloads, temporary URLs, or ORM entities.

### PollingQueryService

Responsibilities:

- Read conversation resources whose derived change key is after a supplied high-water
  cursor, ordered by `(resource_updated_at ASC, resource_id ASC)`.
- Read message resources with the same monotonic change-key rule, including related
  attachment changes.
- Return a typed next cursor and `has_more` result to the CRM-006 adapter.
- Use the persisted timestamps maintained by CRM-005 rather than inventing an event log.

It does not define polling intervals, HTTP routes, cursor serialization, reconnect
behavior, or frontend reconciliation; those remain CRM-006 concerns.

## Pagination and consistency

Pagination is keyset-based, never offset-based. A typed page cursor contains the snapshot
watermark and the final ordering tuple for that page. Conversation cursors use the
CRM-006 inbox sort tuple; message history cursors use `(message_at, id)`. Equal
timestamps always use the local ID as a tie-breaker.

Changed-resource cursors contain `(resource_updated_at, resource_id)`. A query includes
rows strictly after that tuple and returns the last emitted tuple as the next cursor.
The change key is derived from conversation/customer/opportunity-link/opportunity
timestamps for conversation projections and message/attachment/status timestamps for
message projections. This lets updates to status, unread/waiting fields, links, or
stored media be observed without a new table.

Each page executes in one read transaction/snapshot. Empty pages return the supplied
high-water cursor unchanged. Query services do not recompute waiting, unread, identity,
or effective provider state; they read the persisted CRM-005 projections and evidence.

## SQLAlchemy and loading strategy

- Use SQLAlchemy 2.x `select()` statements with explicit typed columns and return types.
- Use `joinedload`/explicit joins for one-to-one or many-to-one Customer and summary
  relationships, and `selectinload` or batched subqueries for bounded collections such
  as links and attachments.
- Load only fields required by each projection; never lazy-load during DTO mapping.
- Fetch suggestions and historical links in batches for the complete page, not once per
  conversation. Fetch message attachments in the same bounded message query.
- Avoid loading complete message histories for conversation lists/details.
- Tests must assert query counts or equivalent evidence so a page cannot introduce N+1
  SQL statements.

## Contracts / API

This spec defines internal typed service contracts and projection DTOs only. It does not
define or implement HTTP routes, request schemas, authentication dependencies, public
cursor encoding, or polling transport. CRM-006 is the sole API contract; its routers
adapt these projections to the already-approved responses.

The service methods accept typed filter/page/cursor objects and return typed page or
change-feed results. No method returns `Customer`, `WhatsAppConversation`,
`WhatsAppMessage`, or another ORM entity to a caller outside the persistence boundary.

## State transitions

None. Query services are read-only. They observe command-side state transitions and must
not mutate rows, resolve identities, mark conversations read, link opportunities, send
messages, or call providers.

## Security & permissions

Authentication and authorization are enforced by CRM-006 before query invocation. The
query layer applies the existing global team visibility and must not add seller-specific
filters. Projection mapping excludes secrets, provider payloads, storage keys, temporary
URLs, and unnecessary message content from metrics or diagnostics.

## Edge cases

- `NEEDS_REVIEW` conversations may have no usable customer projection; they remain
  visible with their resolution status.
- Soft-deleted customers/opportunities remain represented only as permitted historical
  summaries and are not presented as actionable suggestions.
- Terminal opportunity links remain in detail history while only the active link is
  marked actionable.
- Equal timestamps, empty pages, missing optional fields, and late message timestamps
  must have deterministic DTO output.
- A malformed cursor is rejected by CRM-006 before query execution; the query service
  receives only validated typed cursors.
- Related customer/opportunity changes may make a conversation appear in the change
  feed even when no WhatsApp message was added.

## Performance expectations

Targets are measured at the query-service/database boundary, excluding HTTP network,
provider calls, media streaming, and frontend rendering, with bounded page sizes from
CRM-006:

| Query | Target P95 |
| --- | ---: |
| Conversation list (up to 50 summaries) | ≤ 250 ms |
| Conversation detail (without message history) | ≤ 250 ms |
| Message history page (up to 100 messages) | ≤ 250 ms |
| Changed-resource polling page (up to 500 resources) | ≤ 200 ms |

The targets assume indexed PostgreSQL queries and a production-like FAA dataset. A
query exceeding a target is investigated through metrics and SQL/query-count evidence;
adding a cache or new infrastructure is outside this spec.

## Observability

Define metrics only; implementation and exporter choice are outside this spec:

- `whatsapp_query_duration_seconds`, histogram by safe operation (`conversation_list`,
  `conversation_detail`, `message_history`, `polling`) and outcome.
- `whatsapp_query_rows_returned`, histogram by operation.
- `whatsapp_query_db_statements_total`, counter by operation, to detect N+1 regressions.
- `whatsapp_query_cursor_rejections_total`, counter by cursor kind and safe reason.
- `whatsapp_query_errors_total`, counter by operation and stable error category.
- `whatsapp_query_projection_mapping_errors_total`, counter by projection type.

Metrics must not label or record phone numbers, customer IDs, message bodies, provider
payloads, storage keys, tokens, or secrets.

## Acceptance criteria

- AC-01: Query services return immutable typed projections and never expose SQLAlchemy ORM entities.
- AC-02: Conversation summaries support CRM-006 waiting/unread/search filters, customer/link/suggestion summaries, and the documented deterministic order.
- AC-03: Conversation detail returns UI-ready customer, active-link, historical-link, suggestion, unread/waiting, and timestamp data without loading message history.
- AC-04: Message history returns bounded chronological pages with typed status, retry, and attachment projections, including null/terminal edge cases.
- AC-05: Conversation and message keyset cursors are deterministic, use stable ID tie-breakers, and return correct next cursors for empty/equal-timestamp pages.
- AC-06: PollingQueryService returns only resources whose derived change key is after the supplied cursor and includes status, attachment, customer, link, or opportunity summary changes.
- AC-07: Query results reflect CRM-005 persisted waiting, unread, identity, link, dispatch, and provider-state projections without recomputing or mutating them.
- AC-08: SQLAlchemy 2.x typed queries load bounded relations eagerly or in batches and pass an explicit no-N+1 query-count test.
- AC-09: The implementation passes `mypy --strict` with no `Any`, casts, or `type: ignore`, and uses no repository/CQRS/cache abstraction.
- AC-10: No table, schema, migration, provider call, command-side mutation, or HTTP endpoint is introduced by the query layer.
- AC-11: Query operations meet the documented P95 targets under the bounded page-size benchmark fixture.
- AC-12: The defined observability metrics are emitted with safe labels only and never contain customer/message/provider secrets.

## Open decisions

None

## Follow-up / future specs

### Future Specs

- CRM-006 implementation will adapt these projections to its approved FastAPI contracts.
- Any future inbox search semantics, caching, alternate transport, or analytical read
  model requires a separate approved spec; none is part of CRM-007.

## Implementation notes

Keep query services small and operation-oriented. Prefer explicit SQLAlchemy statements
and projection constructors over generic mappers. The API boundary owns serialization;
command services remain the only owners of WhatsApp business mutations.
