# CRM-035 — Canonical Production CORS Origin

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-06
Implementation commit: N/A

## Goal

Allow the canonical FAA CRM frontend at `https://crm.scroll.com.ar` to call the
separately deployed API, while retaining the existing narrow, fail-closed production
CORS policy.

## Context

CRM-033 introduced CORS for the temporary Railway frontend origin. Production topology
now uses `https://crm.scroll.com.ar` for the frontend and
`https://becrm.scroll.com.ar` for the backend. The former Railway frontend origin is
temporary and must no longer be the required production origin. This does not alter
FAA commercial behavior in `docs/BUSINESS_RULES.md`.

## Dependencies

- CRM-033 — Production CORS for Separate Frontend Deployment

## Scope

- Replace the single canonical required production CORS origin with
  `https://crm.scroll.com.ar`.
- Retain exact-one-origin production validation and the existing narrow CORS middleware
  configuration.
- Update focused validation tests and operator documentation.

## Non-goals

- Allow the temporary Railway frontend, preview deployments, localhost, HTTP, ports,
  paths, wildcards, arbitrary origins, cookies, credentials, or additional origins.
- Change API routes, authentication, authorization, `ALLOWED_HOSTS`, backend topology,
  data model, migrations, or FAA business rules.

## Business rules

No FAA commercial rule changes. Bearer JWT authentication remains unchanged.

## Data model

None.

## Contracts / API

In production, `CORS_ALLOWED_ORIGINS` must contain exactly:

```text
CORS_ALLOWED_ORIGINS=https://crm.scroll.com.ar
```

The configured origin remains an exact HTTPS origin with no port, path, query,
fragment, user information, duplicate, or wildcard. The existing allowlisted methods
and request headers remain unchanged.

## State transitions

None.

## Security & permissions

The policy remains fail-closed and does not permit credentialed browser requests. The
old Railway origin is not authorized merely because it was previously required.

## Edge cases

- The exact canonical origin starts production successfully and receives CORS headers.
- The old Railway origin, a wildcard, HTTP origin, or multiple origins fails production
  startup or receives no CORS authorization, as applicable.
- Requests without `Origin` retain their existing behavior.

## Acceptance criteria

- AC-01: Production startup succeeds when `CORS_ALLOWED_ORIGINS` is exactly
  `https://crm.scroll.com.ar`.
- AC-02: An allowed preflight and actual API request from the canonical origin receive
  the existing narrow CORS response; authentication behavior remains unchanged.
- AC-03: Production startup rejects the former Railway origin, wildcards, malformed or
  non-HTTPS origins, duplicates, multiple origins, and missing CORS configuration.
- AC-04: Documentation gives the exact canonical Railway backend variable value.
- AC-05: Focused tests and the complete backend quality gate pass against an isolated
  PostgreSQL database.

## Open decisions

None.

## Follow-up / future specs

Adding another frontend origin or altering CORS credentials requires a separate
approved security specification.

## Implementation notes

The change is limited to the required-origin configuration constant, focused tests,
and deployment documentation. No dependency or migration is needed.
