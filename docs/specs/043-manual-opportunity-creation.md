# CRM-043 — Manual Opportunity Creation

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-10
Implementation commit: 2304dbd

## Goal

Allow authenticated FAA users to register an Opportunity received outside the
automated Web or WhatsApp intake flows, especially referrals and word of mouth,
without leaving the Pipeline workspace or creating inconsistent Customer data.

## Context

CRM-001 currently exposes authenticated Customer and Opportunity creation contracts,
but the Pipeline has no composed creation workflow. The generic Opportunity contract
requires an existing `customer_id`; creating a new Customer and then an Opportunity
through two independent requests can leave a Customer without the intended
Opportunity if the second request fails.

The persisted `LeadSource` domain currently contains only `WEB` and `WHATSAPP` and is
stored in the shared PostgreSQL enum `lead_source_enum`, used by `opportunities`,
immutable `lead_intakes`, and historical `opportunity_loss_events`. Web intake is
server-controlled and idempotent under CRM-002. WhatsApp intake is
provider/conversation-controlled under CRM-005 through CRM-010. Manual entry must not
weaken or replace either ingestion boundary.

The Pipeline state introduced by CRM-038 already supports authoritative Opportunity
upserts without remounting the workspace. Dashboard, Pipeline, Won, Lost, Customer
detail, Opportunity detail, metrics, filters, and drilldowns all consume the shared
source value and therefore must recognize any approved new source consistently.

## Dependencies

- CRM-001 — Core CRM
- CRM-002 — Web Lead Intake
- CRM-005 — WhatsApp Core
- CRM-012 — CRM Commercial Completion
- CRM-038 — Frontend Interaction and Data Synchronization
- CRM-041 — Dashboard Commercial Overview and Outcome Navigation
- CRM-042 — Dashboard Visibility and Per-user Notifications

## Scope

- Add a primary `Nueva oportunidad` action to the Oportunidades/Pipeline toolbar.
- Add one compact, responsive, centered creation modal using the current CRM modal,
  form, feedback, focus, and motion conventions.
- Let the user select one active existing Customer or enter a new Customer profile.
- Create the new Customer, when needed, and its Opportunity atomically.
- Add `REFERIDO` as the referral/word-of-mouth source in the typed domain,
  persistence, filters, metrics, and all source labels.
- Fix the manual creation source to backend-owned `REFERIDO`; according to existing
  role permissions, allow responsible-user selection where authorized.
- Always create the Opportunity in `NUEVA`; status is backend-owned and is not an
  accepted request field.
- Record the authenticated actor in the existing creation history and produce the
  existing new-lead notification side effect.
- Upsert the authoritative response into the mounted Pipeline state without a board
  reload, preserving the mounted workspace, filters, selection, and scroll.
- Add bounded, targeted backend and frontend coverage for this contract.

## Non-goals

- Changing the Opportunity lifecycle, quote rules, loss/reopen behavior, Legendary
  qualification, Customer visibility, or assignee visibility semantics.
- Adding products, quantities, a quote, a consultation message, notes, campaign data,
  or a user-selectable status during creation.
- Fuzzy Customer matching, country-code inference, automatic merging, or automatic
  overwriting/enrichment of an existing Customer selected by the user.
- Replacing, routing through, or changing the Web intake and WhatsApp intake flows.
- Creating a generic lead-source administration UI or allowing arbitrary source text.
- Persisting Pipeline filters, scroll, or draft form contents beyond the mounted
  authenticated workspace.

## Business rules

### Opportunity creation

- Every successful manual command creates exactly one Opportunity belonging to one
  active Customer.
- The backend always sets `status=NUEVA`, `loss_reason=NULL`, `created_at`,
  `updated_at`, and `current_status_entered_at`. The client cannot supply or override
  any of these fields.
- The Opportunity initially has no quoted products. It follows all existing quote,
  transition, assignment, loss, reopen, notification, and retention rules immediately
  after creation.
- Multiple Opportunities for the same Customer are valid. Customer reuse is not, by
  itself, an Opportunity duplicate and must not be blocked.

### Source semantics

- `manual` describes how a CRM user entered the record; it is not an acquisition
  source and must not be persisted as `MANUAL`.
- The persisted domain value is `REFERIDO`, with the user-facing label
  `Referido / boca a boca`.
- Every Opportunity created through the manual endpoint has backend-owned
  `source=REFERIDO`. The client cannot submit or override `source`.
- `WEB` and `WHATSAPP` remain server-controlled by their existing intake flows and are
  not offered as manual creation choices. Manual creation never creates a
  `lead_intakes` row, WhatsApp conversation, message, or link.
- Existing `WEB` and `WHATSAPP` data and semantics remain unchanged. No historical
  row is reclassified or backfilled.

### Existing Customer

- Existing-Customer mode searches the current authenticated, paginated Customer
  contract and exposes only active Customers.
- Search is bounded and uses the existing name/company/email/phone matching behavior.
  The user must explicitly select one result; free text is not interpreted as a
  Customer identifier.
- The selected Customer is revalidated as present and active inside the creation
  transaction.
- Creation does not update, enrich, merge, or clear any field on the selected Customer.
  Customer edits remain in the existing Customer workflow.

### New Customer

- New-Customer mode accepts only current Customer domain fields: required `name` and
  optional `company`, `phone`, `email`, and `province`.
- The modal and request cannot set either Legendary flag or deletion/audit fields.
- Values use the current Customer normalization and validation: surrounding whitespace
  is removed, blank optional values become `NULL`, provided email must be valid, and
  phone remains a stored contact value without inferred country code.
- Name remains the only required contact field, consistent with the current Customer
  contract. A phone with fewer than seven ASCII digits may be stored but is not a
  matchable identity signal under the existing conservative resolver.
- Exact normalized email and comparable phone are checked with the existing
  `CustomerIdentityResolver` under transaction-scoped advisory and Customer row locks.
- One exact active match does not silently convert `new` mode to `existing` mode. The
  command returns a typed conflict with the safe matching Customer summary so the user
  can deliberately select that Customer and resubmit.
- Multiple active matches, identity signals pointing to different Customers, or any
  deleted identity match return a typed conflict and create neither Customer nor
  Opportunity. The service never guesses or revives a deleted Customer.
- With no matchable email or phone, no fuzzy or name/company match is attempted and a
  new Customer may be created.

### Duplicate command handling

- The modal generates one UUID `command_id` when a submission begins and reuses it for
  transport retries of that unchanged normalized request.
- The first command atomically stores its normalized request fingerprint and resulting
  Opportunity reference. An identical replay by the same authenticated actor returns
  the original result with `created=false` and creates no new rows or notifications.
- Reusing a `command_id` with different normalized input or a different actor returns
  an idempotency conflict. Starting a deliberate second Opportunity uses a new UUID.
- While a request is pending, the frontend disables repeat submission without changing
  the form dimensions. A transport failure does not automatically invent a new UUID.

### Responsible user

- Existing CRM-001 permissions remain authoritative: a Supervisor may select any
  active user or leave the Opportunity unassigned; a Vendedor cannot assign an
  Opportunity during creation.
- The Supervisor selector uses the existing Supervisor-only user listing and includes
  only active users as selectable values. The backend still revalidates active state.
- For a Vendedor, `assigned_user_id` is omitted or `NULL`, the modal communicates
  `Sin responsable`, and any non-null assignment is rejected with `403`.
- Creating the Opportunity does not imply self-assignment and does not change global
  Opportunity visibility.

### Audit, notifications, and downstream behavior

- The existing `OpportunityStatusHistory` creation event is appended with
  `from_status=NULL`, `to_status=NUEVA`, `transition_kind=CREATED`, the backend
  timestamp, and `changed_by_user_id` set from the authenticated token.
- No actor identifier is accepted from the request.
- The existing per-user `NEW_LEAD` notification is created for all active users in the
  same transaction, including the creator under current CRM-042 behavior.
- Legendary recomputation and all subsequent Opportunity behavior use the existing
  `OpportunityService.create_opportunity_in_transaction` boundary.
- A manual Opportunity participates in Pipeline queries, Customer Opportunity history,
  stale follow-up eligibility, Dashboard overview/timeline/source/province metrics,
  Won/Lost workspaces, origin filters, and drilldowns exactly like an Opportunity from
  another source.
- `REFERIDO` must be supported by every exhaustive backend/frontend source enum,
  serializer, source filter, label map, metric projection, URL parser, and fixture.

## Data model

### Source migration

- Add `REFERIDO` to Python `LeadSource`, frontend `LeadSource`, and PostgreSQL
  `lead_source_enum` through a new Alembic revision after
  `0010_notification_recipients`.
- The PostgreSQL enum is shared by `opportunities.source`, `lead_intakes.source`, and
  `opportunity_loss_events.source`. The added database value is therefore structurally
  valid for each column, but the Web intake route remains fixed to `WEB`, WhatsApp
  remains fixed to `WHATSAPP`, and only the manual Opportunity endpoint sets
  `REFERIDO`. No manual command writes `lead_intakes`.
- No existing Opportunity, intake, loss event, or metric evidence is backfilled.
- Downgrade must not discard or rewrite commercial history. It may rebuild the enum
  only when no persisted `REFERIDO` value is referenced; otherwise it must fail with a
  clear operator-facing message.

### Manual command persistence

Add `manual_opportunity_creation_commands` with:

- `command_id UUID` primary key;
- `request_fingerprint TEXT NOT NULL`;
- `opportunity_id BIGINT NOT NULL UNIQUE`, FK to `opportunities.id` with `RESTRICT`;
- `created_by_user_id BIGINT NOT NULL`, FK to `users.id` with `RESTRICT`;
- `created_at TIMESTAMPTZ NOT NULL` with the standard UTC server default.

This is an idempotency record, not a second Opportunity audit timeline. It contains no
contact snapshot beyond the deterministic fingerprint. The creation history remains
the human-readable domain audit. The command row and all Customer, Opportunity,
history, notification-recipient, and Legendary writes share one transaction.

The mutation follows the permanent PostgreSQL lock order: sorted transaction advisory
locks for command and normalized Customer identities, then matching Customer rows,
then downstream Opportunity-related evidence. No transaction or lock is held during
network I/O.

## Contracts / API

### Create manual Opportunity

`POST /api/opportunities/manual`

Authentication: active CRM bearer user.

Strict request, represented as a discriminated union:

```json
{
  "command_id": "b504fc7b-838f-45b8-92a3-f70e71551ac0",
  "assigned_user_id": 7,
  "customer": {
    "kind": "existing",
    "customer_id": 42
  }
}
```

or:

```json
{
  "command_id": "b504fc7b-838f-45b8-92a3-f70e71551ac0",
  "assigned_user_id": null,
  "customer": {
    "kind": "new",
    "name": "Esteban Ríos",
    "company": "Vial Patagonia",
    "phone": "+54 9 11 5555-0101",
    "email": "esteban@example.com",
    "province": "Buenos Aires"
  }
}
```

`source`, `status`, timestamps, Legendary values, products, consultation text, actor
IDs, and unknown fields are rejected. The endpoint sets `source=REFERIDO` and
`status=NUEVA`. Positive-ID and current Customer field validators apply.

Response for first execution: `201 Created`.

Response for identical replay: `200 OK`.

```json
{
  "created": true,
  "opportunity": {
    "id": 123,
    "status": "NUEVA"
  }
}
```

`opportunity` is the complete existing `OpportunityDetail` representation, not a
creation-specific partial model. The replay response changes only `created` to
`false`.

Expected errors:

- `401` inactive/missing authentication;
- `403` Vendedor supplies a non-null assignee;
- `404` selected Customer or assigned user does not exist;
- `409 MANUAL_CUSTOMER_MATCH_EXISTS` with one safe `CustomerSummary` when `new` mode
  exactly matches one active Customer;
- `409 MANUAL_CUSTOMER_IDENTITY_AMBIGUOUS` when active identity signals are ambiguous;
- `409 MANUAL_CUSTOMER_IDENTITY_DELETED` when a deleted identity is detected;
- `409 MANUAL_OPPORTUNITY_COMMAND_CONFLICT` for changed/cross-actor command replay;
- `409` selected Customer is deleted or selected responsible user is inactive;
- `422` malformed UUID, invalid email/IDs, blank required name, invalid union, a
  client-provided source/status, or other extra fields.

Typed `409` details use a stable object with `code` and only the safe fields required
by the modal. Existing string-only error responses remain backward compatible.

### Existing supporting contracts

- Existing-Customer search reuses bounded `GET /api/customers?search=&page=&page_size=`;
  it does not load the entire Customer catalog.
- Supervisor responsible-user options reuse `GET /api/users`; no new user visibility
  endpoint is introduced.
- Existing `POST /api/opportunities` remains backward compatible for current callers.
  The Pipeline creation UI uses only the composed manual endpoint.
- Pipeline refresh/list and all metrics APIs keep their current shapes; their typed
  filter parameter accepts `REFERIDO` after the enum migration. Existing intake
  endpoints continue to own and fix their respective source values.

## State transitions

- The only creation transition is the existing virtual start to `NUEVA`:
  `NULL -> NUEVA` with transition kind `CREATED`.
- No role, Customer mode, or frontend state may choose another initial status or
  override the endpoint-owned `REFERIDO` source.
- Once returned, the entity enters the existing CRM-001/CRM-012 lifecycle without a
  manual-entry variant or special terminal behavior.

## Frontend modal UX

- `Nueva oportunidad` is the Pipeline toolbar's primary action and does not displace
  existing search, sort, origin, product, stage-age, reset, or refresh behavior.
- Activating it opens one centered modal with the shared backdrop, header, close
  button, focus trap, Escape/backdrop conventions, internal scroll, and trigger-focus
  restoration used by current CRM dialogs.
- The modal begins with a compact segmented choice: `Cliente existente` or
  `Cliente nuevo`. Switching mode does not submit or mutate data.
- Existing mode provides a debounced bounded search, explicit result selection, and a
  compact selected-Customer summary. It has clear loading, no-results, error, and
  replace-selection states.
- New mode shows only name, company, phone, email, and province. Fields use accessible
  labels, inline validation, autocomplete/input modes where appropriate, and no large
  form sections.
- The modal shows the non-editable origin `Referido / boca a boca`; it contains no
  source selector. Responsible is selectable only for Supervisors; Vendedores see the
  fixed unassigned outcome without an enabled administrative control.
- Primary action is `Crear oportunidad`; secondary action closes the modal. Pending,
  error, identity-conflict, success, keyboard, and reduced-motion states follow shared
  CRM conventions.
- On an exact active-customer conflict, the modal preserves entered data and offers a
  deliberate `Usar cliente existente` action using the returned Customer. Ambiguous or
  deleted conflicts do not guess a Customer and direct the user to refine/search or
  resolve the Customer record.
- On success, the creation modal closes, returns focus to the toolbar trigger, announces
  the result through an accessible live region, and the Opportunity is available for
  the normal card click, drag, detail, quote, assignment, loss, and lifecycle actions.

## Pipeline synchronization

- The frontend sends one creation command and upserts only the returned authoritative
  `OpportunityDetail` into `OpportunityWorkspaceState`; it does not refetch four
  stages, remount the page, reset filters, replace browser history, or reset scroll.
- The new entity is inserted by ID into the `NUEVA` projection and sorted according to
  the current Pipeline sort. Its detail may be cached from the same response.
- Request generation/protection must prevent an older in-flight stage response from
  removing the newly created entity, using the same protected authoritative mutation
  mechanism as CRM-038.
- Source, search, and product filters keep their current semantics. If the authoritative
  upsert does not match any current filter, the card remains correctly excluded and a
  compact notice says `Oportunidad creada. Los filtros actuales la están ocultando.`
  with an explicit `Ver en Nueva` action.
- Only activating `Ver en Nueva` may remove the incompatible source, search, or
  product filters. It keeps the Pipeline mounted, retains its remaining compatible
  state, reveals the new card in `NUEVA`, and does not trigger a full-page refresh.

## Dashboard and origin implications

- A `REFERIDO` Opportunity contributes to Created metrics at `created_at`, to current
  Pipeline status counts, and later to Won/Lost metrics at the existing authoritative
  event timestamps.
- It participates in province and product metrics under existing rules; immediately
  after creation it has no quoted Product and therefore contributes to no product
  dimension until quoted.
- Origin distribution and origin drilldowns include `REFERIDO` as a distinct row and
  filter. Percentages and conversion retain existing denominators and calculations.
- Dashboard, Pipeline, Ganadas, Pérdidas, Customer detail, Opportunity detail, URL
  query parsing/serialization, and modal cards display the approved label and never
  fall through to an incorrect Web/WhatsApp label.
- Historical loss snapshots retain the Opportunity source at loss time exactly as
  CRM-012/CRM-041 require.

## Security & permissions

- Both current roles may open and submit the manual creation modal. All created
  Customers and Opportunities follow the existing globally visible CRM model.
- Only Supervisors can assign a responsible user. Existing Customer creation permission
  remains available to both roles, but neither role can set Legendary state here.
- The backend derives the actor exclusively from the authenticated session, revalidates
  selected Customer and assignee state in the transaction, and rejects extra fields.
- Identity conflicts may return one active Customer summary because current business
  rules allow every authenticated user to view all Customers. Deleted/ambiguous
  conflicts expose stable codes without unnecessary contact records.
- Idempotency fingerprints, validation logs, and error responses must not expose
  secrets, tokens, SQL details, or unrelated Customer contact data.

## Edge cases

- The selected Customer is deleted, the selected assignee is deactivated, or the
  identity resolution changes between search and submit: reject atomically and keep
  the modal recoverable.
- Email and phone resolve to different active Customers: report ambiguity and create
  nothing.
- An active and deleted record share an identity: report the deleted/ambiguous conflict
  and require explicit Customer cleanup; do not silently choose the active row.
- Name-only Customer creation is allowed and receives no fuzzy duplicate check.
- Two concurrent commands with the same normalized new identity serialize on sorted
  advisory keys. At most one can create a new Customer; the other receives the exact
  match conflict unless it is an identical replay of the same command.
- Concurrent identical `command_id` submissions create one Customer, one Opportunity,
  one creation history entry, one logical notification with its recipients, and one
  command row.
- A timeout after commit is recoverable by replaying the same command UUID and payload.
- Closing/reopening the modal before submit starts a new command UUID. Closing during a
  pending request does not cause a second background submission.
- Optional blank strings normalize to `NULL`; accented Customer/province display text
  remains intact.
- A source-filter, product-filter, or search-filter mismatch keeps the filters and
  truthful projection intact, exposes the approved hidden-result notice, and changes
  incompatible filters only after the user activates `Ver en Nueva`.

## Tests

### Backend targeted coverage

- Domain/application tests for existing and new Customer modes, atomic rollback,
  forced `NUEVA`, active/deleted/missing entities, role-aware assignment, actor history,
  notification recipients, and Legendary recomputation.
- Identity/concurrency tests for exact email/phone reuse conflicts, ambiguity, deleted
  identities, name-only creation, sorted locks, and two concurrent commands.
- API tests for strict union validation, absence of user-set status/actor/Legendary
  fields, first/replay/conflicting command responses, permissions, and response detail.
- Enum/migration and focused metrics/query tests proving `REFERIDO` is accepted,
  filtered, grouped, serialized, and retained in loss evidence without changing Web or
  WhatsApp intake behavior.

### Frontend targeted coverage

- Toolbar action/modal accessibility, existing-Customer search/selection, new-Customer
  validation, fixed visible `REFERIDO` origin, rejection of client-provided source,
  and role-specific responsible control.
- Exact-match conflict recovery, pending double-submit prevention, retry with stable
  command UUID, error preservation, close/Escape/focus restoration, and responsive
  modal behavior.
- Successful authoritative upsert into `NUEVA`, no four-stage reload, stale-list
  protection, preserved filters/scroll/workspace, the exact hidden-result notice, and
  explicit `Ver en Nueva` filter removal.
- `REFERIDO` labels/options and filters across Pipeline, Dashboard, Ganadas, Pérdidas,
  Customer/Opportunity detail, metrics drilldowns, and URL parsing.

Before implementation is considered complete, run the repository gates required by
`AGENTS.md`; targeted tests above do not waive the final quality requirements.

## Acceptance criteria

- AC-01: An authenticated user can open `Nueva oportunidad` from the mounted Pipeline
  and create an Opportunity for an explicitly selected active existing Customer.
- AC-02: An authenticated user can create a new Customer with only supported Customer
  fields and its Opportunity in one transaction; a failure leaves neither partial row.
- AC-03: Every manual Opportunity is backend-created in `NUEVA` with no quote/loss,
  regardless of request manipulation, and status/actor fields are rejected inputs.
- AC-04: Creation appends exactly one `CREATED` history event with the authenticated
  actor and produces the existing per-user new-lead notification atomically.
- AC-05: Supervisors may choose an active responsible user or no responsible;
  Vendedores always create unassigned and a spoofed assignment receives `403`.
- AC-06: Exact active, ambiguous, and deleted Customer identity conflicts are
  deterministic, typed, conservative, and create no Customer or Opportunity; name-only
  entry uses no fuzzy match.
- AC-07: An identical command replay returns the original Opportunity without duplicate
  Customer, Opportunity, history, command, or notification rows; changed/cross-actor
  replay conflicts.
- AC-08: The authoritative response is upserted immediately into mounted Pipeline state
  without a full page/stage reload or loss of filters, scroll, current sort, or detail
  workspace state. If filters hide it, the exact approved notice and explicit
  `Ver en Nueva` action are shown; filters change only after that action.
- AC-09: The resulting card supports the same click, detail, drag, quote, transition,
  assignment, loss, notification, stale-follow-up, and reconciliation behavior as any
  other `NUEVA` Opportunity.
- AC-10: `REFERIDO` is persisted and displayed as `Referido / boca a boca` consistently
  in every backend/frontend source contract, filter, metric, drilldown, URL, and
  historical loss snapshot. The manual endpoint always sets it server-side, rejects a
  client source, and existing Web/WhatsApp ingestion remains unchanged.
- AC-11: Existing-Customer search and user selection stay bounded and role-protected;
  no full Customer or user catalog is exposed to an unauthorized client.
- AC-12: The Alembic upgrade preserves all current rows, adds the approved enum value
  and command persistence, and downgrade never discards `REFERIDO` commercial history.
- AC-13: The modal is keyboard accessible, traps focus, closes through established
  conventions, restores trigger focus, exposes inline errors, and remains usable on
  mobile without horizontal document overflow.

## Open decisions

None.

## Follow-up / future specs

- Additional acquisition sources beyond `REFERIDO`, bulk manual Opportunity creation,
  automatic Customer merging, or campaign attribution require a separate approved
  specification.

## Implementation notes

- Introduce a focused application service for the composed manual command; reuse
  `CustomerIdentityResolver`, `create_customer_from_profile`, and
  `OpportunityService.create_opportunity_in_transaction` rather than duplicating
  identity, notification, Legendary, or history logic.
- Use typed Pydantic request/response variants and typed domain conflict DTOs. Do not
  use magic dictionaries or `Any` for the known request and error structures.
- Extend existing source label/config collections rather than adding per-page source
  branches. In particular, replace binary fallbacks that currently treat every
  non-`WEB` value as WhatsApp.
- Reuse the generic Pipeline column/state components and shared Modal/form primitives;
  do not create source-specific columns or a parallel Opportunity workspace.
- Preserve the old authenticated Opportunity creation endpoint for current WhatsApp
  conversation behavior and keep external intake endpoints source-controlled.
