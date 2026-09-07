# CRM-036 — Web Consultation in Opportunity Detail

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-07
Implementation commit: N/A

## Goal

Make the customer's original web-form consultation clearly available in Opportunity
Detail so the commercial team can understand a `WEB` lead without consulting the
WordPress submission or creating duplicate internal records.

## Context

CRM-002 already persists each accepted web submission as an immutable `LeadIntake`,
including its normalized optional `message`, and links it one-to-one to the created
Opportunity. CRM-020's authenticated Opportunity Detail response and UI currently
expose Customer, quote, status history, and internal Notes, but do not project the
linked intake. As a result, the persisted customer consultation is absent from the
detail even though intake creation succeeded.

`docs/BUSINESS_RULES.md` remains authoritative: the intake snapshot is immutable,
existing Customer data is not overwritten, and all users may see all Opportunities.

## Dependencies

- CRM-002 — Web Lead Intake
- CRM-020 — Opportunity Detail & Quote Flow

## Scope

- Extend the authenticated Opportunity Detail read projection with the message from
  the Opportunity's linked `LeadIntake`, when one exists.
- Show a dedicated `Consulta del cliente` section in the primary information zone for
  `WEB` Opportunities, after Customer information and before Cotización.
- Render the consultation as plain text, preserving intentional line breaks and
  wrapping long content within the existing bounded detail scroll.
- Represent truthfully the case where a `WEB` Opportunity has no linked intake or its
  accepted intake contained no message.
- Add backend contract/query tests and frontend rendering tests for the new projection
  and its empty/non-`WEB` states.

## Non-goals

- Changing CRM-002 intake creation, normalization, identity resolution, atomicity,
  idempotency, HMAC authentication, request/response contract, or lock behavior.
- Modifying the WordPress/Avada bridge or its payload/signature contract.
- Copying the intake message into Opportunity Notes, status history, or a new activity
  entity.
- Editing or deleting the immutable intake snapshot from Opportunity Detail.
- Displaying or inventing province, responsible user, quote, or other missing data.
- Exposing the intake's internal ID, external submission ID, submitted contact
  snapshot, or other integration-oriented audit metadata in the UI.

## Business rules

- For a `WEB` Opportunity backed by a `LeadIntake`, the displayed consultation is the
  immutable normalized `LeadIntake.message`; it is not a mutable Opportunity Note.
- A missing intake or `NULL` message is represented as unavailable and is never
  synthesized from Customer data, Notes, WordPress, or another channel.
- The consultation section is specific to source `WEB`; it does not reinterpret
  WhatsApp messages or internal Notes as an original web consultation.
- Existing global Opportunity visibility applies. This feature introduces no role or
  assignee-based visibility rule.

## Data model

No persistence or Alembic change is required. Continue using the existing optional
one-to-one `Opportunity.lead_intake` relationship and `lead_intakes.message` column as
the single source of truth.

The message remains optional, immutable, bounded, and normalized according to CRM-002.
No duplicated message column or automatic Note is added.

## Contracts / API

`GET /api/opportunities/{opportunity_id}` adds an optional, source-specific
`web_intake` projection to `OpportunityDetail`:

```json
{
  "web_intake": {
    "message": "Necesito asesoramiento para una obra vial."
  }
}
```

`web_intake` is `null` when the Opportunity has no linked intake. Its `message` is
`null` when the accepted intake did not contain a nonblank message. The projection
does not expose intake IDs, `external_submission_id`, the submitted contact snapshot,
or `received_at`; Opportunity Detail already exposes the commercially useful current
Customer data and Opportunity creation time.

Because existing Opportunity mutation endpoints return `OpportunityDetail`, they keep
the same expanded response shape when applicable. The CRM-002 public intake response
and request remain unchanged.

## State transitions

None. Reading or displaying the original consultation does not mutate the Opportunity,
Customer, LeadIntake, Notes, history, or pipeline state.

## Security & permissions

- The projection is available only through the existing authenticated Opportunity
  Detail routes and inherits their authorization and global Opportunity visibility.
- The public HMAC-protected intake boundary is unchanged.
- The message is rendered as plain text; submitted HTML is never interpreted or
  executed.
- No integration identifiers or additional intake snapshot fields are exposed to the
  frontend.

## Edge cases

- A manually created `WEB` Opportunity may have no `LeadIntake`; detail shows the
  dedicated section with a concise unavailable-message state.
- An accepted intake may validly have `message=NULL`; detail shows the same truthful
  unavailable-message state.
- A non-`WEB` Opportunity does not show the web consultation section, even if invalid
  legacy data were to contain an unexpected relation.
- Multiline, Unicode, and long messages remain plain text, preserve line breaks, wrap
  without horizontal overflow, and use the existing detail body's vertical scroll.
- Replaying a CRM-002 submission continues comparing the normalized message and does
  not create a second Opportunity, intake, Note, or activity record.

## Acceptance criteria

- AC-01: An authenticated detail request for a CRM-002-created `WEB` Opportunity
  returns `web_intake.message` exactly as stored after CRM-002 normalization.
- AC-02: Opportunity Detail shows a clearly titled `Consulta del cliente` section for
  a `WEB` Opportunity and renders its message as safe multiline plain text before the
  quote section.
- AC-03: A `WEB` Opportunity without a linked intake or without a stored message shows
  a concise unavailable-message state and does not invent content.
- AC-04: A non-`WEB` Opportunity does not show the web consultation section.
- AC-05: The detail projection does not expose intake IDs, external submission IDs,
  submitted contact snapshot fields, or other bridge metadata.
- AC-06: No migration, duplicated persistence, automatic Opportunity Note, or status
  history/activity entry is created for the intake message.
- AC-07: Existing CRM-002 normalization, HMAC behavior, atomicity, replay response,
  changed-payload conflict, and concurrent idempotency tests continue to pass without
  contract changes.
- AC-08: Multiline and long unbroken consultation text remains readable without HTML
  execution or horizontal overflow in supported desktop and responsive layouts.

## Open decisions

None

## Follow-up / future specs

None

## Implementation notes

Load `Opportunity.lead_intake` in the existing detail query only; do not add it to
Pipeline summary queries. Add a small typed Pydantic projection for the source-specific
message and the matching TypeScript type. Compose the new semantic section in the
existing reusable Opportunity detail content rather than adding a new request, global
state, or general activity abstraction.
