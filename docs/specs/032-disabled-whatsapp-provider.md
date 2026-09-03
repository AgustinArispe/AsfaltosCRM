# CRM-032 — Disabled WhatsApp Provider Mode

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-03
Implementation commit: N/A

## Goal

Allow a production CRM deployment to run safely before Meta credentials are available by
explicitly disabling the WhatsApp integration, without weakening production validation
or non-WhatsApp CRM operations.

## Context

`CRM-009`, `CRM-011`, and `CRM-016` establish the provider boundary, Meta integration,
and fail-closed production configuration. Production currently permits only Meta, so a
deployment cannot start while the approved Meta configuration is intentionally absent.
`docs/BUSINESS_RULES.md` permits a provider abstraction and limits Fake provider use to
development and tests.

## Dependencies

- CRM-009 — Meta Cloud API Provider
- CRM-011 — WhatsApp Broadcast Execution
- CRM-016 — Application Security Hardening

## Scope

- Add `disabled` as an explicit WhatsApp provider mode.
- Permit `disabled` and valid `meta` configuration in production; continue rejecting
  `fake`.
- Construct a no-network disabled runtime that does not load Meta configuration or
  instantiate Meta or Fake providers.
- Omit WhatsApp, Broadcast, development simulation, and provider-webhook routes when
  the provider is disabled.
- Reject the bounded broadcast processor before it can claim recipients or send.
- Cover production disabled, production Fake rejection, Meta validation, disabled route
  absence, and processor rejection with focused tests.

## Non-goals

- Add Meta credentials, modify Railway variables, call Meta, or change provider
  credentials/configuration semantics.
- Change WhatsApp persistence, consent, broadcast state transitions, user roles, or
  FAA commercial rules.
- Remove stored WhatsApp history or add a new disabled-mode API payload.
- Change non-WhatsApp routes, Docker startup commands, or dependencies.

## Business rules

The existing WhatsApp provider and marketing-consent rules in `docs/BUSINESS_RULES.md`
remain unchanged. Disabled mode makes no delivery attempt and introduces no provider
state transition.

## Data model

None.

## Contracts / API

When disabled, all `/api/whatsapp` routes are absent and therefore return the normal
FastAPI `404` response. Non-WhatsApp API contracts are unchanged. The broadcast CLI
terminates before database processing with a safe disabled-provider error.

## State transitions

None. Disabled mode neither claims broadcast recipients nor creates outbound message
attempts.

## Security & permissions

- Production still requires filesystem media storage, disabled development routes,
  trusted hosts, distinct valid secrets, and a Psycopg PostgreSQL URL.
- `meta` continues to require validated Meta configuration.
- `fake` remains rejected in production.
- Disabled mode has no Meta transport, webhook, Fake provider, or Fake media storage.

## Edge cases

- Explicit SQLAlchemy provider drivers and database settings are unaffected.
- Existing stored WhatsApp records remain persisted but are not exposed through omitted
  WhatsApp routes while disabled.
- Invoking the broadcast CLI while disabled does not acquire database work or perform
  provider I/O.

## Acceptance criteria

- AC-01: Production startup accepts `WHATSAPP_PROVIDER=disabled` without any Meta
  environment variables while retaining all other production guards.
- AC-02: Production startup rejects `WHATSAPP_PROVIDER=fake`.
- AC-03: Production Meta startup still fails when required Meta configuration is absent
  or invalid.
- AC-04: Disabled runtime has no Meta webhook, Meta provider, or Fake provider, and
  `/api/whatsapp` routes are unavailable.
- AC-05: The broadcast processor exits before recipient claims or outbound dispatch
  when disabled.
- AC-06: Non-WhatsApp application routes remain registered in disabled production mode.

## Open decisions

None.

## Follow-up / future specs

- A read-only disabled-mode WhatsApp history UX, if operationally needed.
- Meta credential installation and provider activation runbook.

## Implementation notes

The user explicitly approved this limited production-safe feature. Any future
read-only WhatsApp-history UX while disabled requires a separate specification.
