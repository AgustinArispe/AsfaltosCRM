# CRM-002 — Web Lead Intake

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-10
Implementation commit: `05b8adf`

## Goal

Accept trusted website submissions and turn each valid submission into an auditable customer snapshot and a `WEB` opportunity without duplicate leads.

## Context

The endpoint is intended for server-to-server WordPress/CF7 integration. It is separate from user-authenticated CRM routes and follows the identity rules in `docs/BUSINESS_RULES.md`.

## Dependencies

- CRM-001 — Core CRM

## Scope

Input normalization, exact customer identity resolution, enrichment, idempotency, atomic opportunity creation, immutable intake snapshots, HMAC authentication, and concurrency handling.

## Non-goals

The implementation does not replace the existing CF7 email, implement fuzzy matching, or create a campaign/workflow editor.

## Business rules

- A valid submission creates one `Opportunity` in `NUEVA`, source `WEB`, with no assigned user.
- An existing customer is matched conservatively by exact normalized email and/or phone.
- Existing nonempty customer fields are never overwritten; only empty fields are enriched.
- No fuzzy matching or country-code assumptions are made.
- The original submission remains an immutable snapshot, including message and submitted fields.

## Data model

`lead_intakes` stores `source`, external submission ID, submitted name/company/email/phone/province, message, the created opportunity FK, and `received_at`. A unique `(source, external_submission_id)` prevents duplicate processing; `opportunity_id` is also unique. The opportunity FK is `RESTRICT`.

## Contracts / API

`POST /api/intake/web` accepts a strict JSON payload containing external submission ID, name, optional company/email/phone/province, and optional message. The source is not client-selectable; the route sets `WEB`. A new submission returns `201` with customer/opportunity/intake identifiers; an identical replay returns `200` with `created=false`. A changed replay is rejected as an idempotency conflict.

The request uses `X-Intake-Timestamp` and `X-Intake-Signature`. The signature is HMAC-SHA256 over `{timestamp}\nPOST\n/api/intake/web\n{raw body}` and must be within 300 seconds of current UTC time.

## State transitions

One accepted submission atomically resolves or creates Customer, enriches only missing fields when matched, creates `Opportunity(NUEVA, WEB)`, and persists its intake snapshot. Any failure rolls back all of these writes.

## Security & permissions

This route does not require a CRM JWT. It requires the configured backend signing secret, timestamp freshness, and constant-time signature comparison. Generic authentication errors avoid exposing verification details; the signing secret is backend-only.

## Edge cases

- Email is trimmed/lowercased; optional text is trimmed; message line endings normalize to LF; phone matching removes whitespace, hyphens, and parentheses while preserving `+`.
- Phones with fewer than seven ASCII digits are not matchable.
- Concurrent requests use PostgreSQL advisory locks for external ID and identity keys.
- A replay with the same normalized snapshot is safe; a changed snapshot conflicts.
- An identity conflict is rejected rather than guessing a customer.

## Acceptance criteria

- AC-01: A valid signed request creates exactly one customer (when needed), one `WEB` opportunity in `NUEVA`, and one immutable intake snapshot.
- AC-02: Replaying the same source/external ID and normalized payload returns the original result without new rows.
- AC-03: Reusing the ID with a different normalized payload returns an idempotency conflict.
- AC-04: Exact normalized email/phone matching reuses an active customer and enriches only empty fields.
- AC-05: Phone normalization preserves `+`, removes separators, and does not infer a country code or use fuzzy matching.
- AC-06: Missing, malformed, expired, or mismatched HMAC headers are rejected without creating data.
- AC-07: Extra fields, client-provided source, and payloads over documented limits are rejected.
- AC-08: Concurrent identical submissions produce one intake/opportunity; distinct identities remain independent.
- AC-09: A transaction failure leaves no partial customer, opportunity, or intake rows.

## Open decisions

None

## Follow-up / future specs

- The later WordPress/CF7 server-to-server delivery arrangement remains integration work outside this implemented endpoint.

## Implementation notes

`CustomerIdentityResolver` is shared with WhatsApp identity resolution. Intake locks are transaction-scoped and `LeadIntakeService` owns the atomic unit of work.
