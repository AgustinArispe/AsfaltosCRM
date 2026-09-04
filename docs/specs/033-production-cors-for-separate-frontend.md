# CRM-033 — Production CORS for Separate Frontend Deployment

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-04
Implementation commit: b2763dd16e0904ddd75672cf3025a5de3e3291f0

## Goal

Permit the explicitly deployed Railway frontend to call the FAA CRM API from its
separate HTTPS origin, while retaining a narrow, fail-closed Bearer-token CORS policy.

## Context

CRM-016 deliberately established same-origin-only operation and omitted CORS. The
current Railway deployment serves the frontend at
`https://robust-creativity-production-f6de.up.railway.app` and the API at
`https://becrm.scroll.com.ar`; browser JSON and Bearer-header requests therefore
preflight and currently receive FastAPI's normal `405` because no CORS middleware
handles `OPTIONS`.

This explicit production deployment requirement supersedes CRM-016's same-origin
assumption only to the narrow extent defined here. `docs/BUSINESS_RULES.md` remains
unchanged: this feature does not alter FAA CRM business behavior.

## Dependencies

- CRM-016 — Application Security Hardening

## Scope

- Add one typed runtime setting, `CORS_ALLOWED_ORIGINS`.
- Register narrowly configured FastAPI/Starlette CORS middleware when that setting
  contains one or more valid origins.
- Require exactly one valid origin in production:
  `https://robust-creativity-production-f6de.up.railway.app`.
- Permit only the exact configured origins; no wildcard origin, regex origin, reflected
  arbitrary origin, or origin inferred from `Host` is allowed.
- Permit preflight and actual API requests only for the frontend methods and request
  headers already used by the shipped frontend.
- Preserve development Compose's `/api` Vite proxy behavior when the setting is unset.
- Add focused configuration and HTTP middleware tests.

## Non-goals

- Change authentication, JWT claims, sessions, cookies, CSRF protection, roles,
  permissions, business rules, API routes, request/response schemas, or frontend code.
- Allow third-party, preview, localhost, wildcard, arbitrary Railway, HTTP, or
  dynamically discovered production origins.
- Add CORS credentials, cookies, `SameSite` changes, refresh tokens, or an OAuth/SSO
  flow.
- Change `ALLOWED_HOSTS`, trusted-proxy handling, deployment domains, Railway service
  configuration other than the new environment variable, database schema, or Alembic.

## Business rules

No FAA commercial rule changes. Authentication remains Bearer JWT in the
`Authorization` request header; browsers do not receive credentialed cookie support.

## Data model

None.

## Contracts / API

`CORS_ALLOWED_ORIGINS` is a comma-separated collection of canonical origins, with no
paths, query strings, fragments, user information, or trailing slash. Every item is
trimmed before validation. A valid production item is an exact HTTPS origin with a
nonempty public DNS host and no wildcard. Ports are not allowed in production. Duplicate
items are rejected rather than silently normalized.

The required initial production value is exactly:

```text
CORS_ALLOWED_ORIGINS=https://robust-creativity-production-f6de.up.railway.app
```

An unset or blank value means CORS middleware is not enabled in development or test,
preserving same-origin `/api` operation. In production, the value must be exactly the
single origin above. An unset, blank, multiple-origin, malformed, duplicate,
wildcard-containing, non-HTTPS, local/test/Compose-only, path-bearing, or otherwise
untrusted value stops startup.

For a request whose `Origin` exactly matches an allowed origin, middleware permits only
these methods:

- `GET`
- `POST`
- `PUT`
- `PATCH`
- `DELETE`

`OPTIONS` is handled only as the CORS preflight mechanism, not as an application route.
The only allowed request headers are `Authorization` and `Content-Type`; the response
may expose no additional non-safelisted headers. `Access-Control-Allow-Credentials` is
not emitted. Existing application response bodies, statuses, routes, and authentication
rules remain authoritative.

Requests with an absent `Origin` remain normal same-origin/backend requests and retain
their current behavior. A disallowed cross-origin actual request receives no
`Access-Control-Allow-Origin`; a disallowed preflight is rejected by the middleware.

## State transitions

None.

## Security & permissions

- `CORS_ALLOWED_ORIGINS` is an origin allowlist, not an HTTP host allowlist.
  `ALLOWED_HOSTS` continues to validate only incoming `Host` headers and its production
  validation/format remain unchanged.
- CORS never enables cookies or credentialed requests: middleware uses
  `allow_credentials=False`.
- The explicit origin comparison is exact. Subdomains, lookalike domains, an origin
  with a different port, and `null` are not authorized unless a future approved spec
  adds a separately validated exact origin.
- Validation must fail closed before the application serves production traffic and must
  never log secrets (the origin list is configuration, not a secret).
- Middleware placement must ensure CORS headers are present for allowed-origin API
  responses, including authentication failures and application error responses, while
  preserving existing Trusted Host and request-body protections.

## Edge cases

- The login JSON request preflights because of `Content-Type: application/json`; an
  allowed-origin `OPTIONS /api/auth/login` returns a successful CORS preflight response
  rather than the current `405`.
- Authenticated frontend requests may send `Authorization`; that header is permitted
  without enabling credentials or cookies.
- A request without `Origin` (health check, server-to-server intake, provider webhook,
  Railway health probe, or same-origin backend client) is not a CORS request and keeps
  its existing semantics.
- An allowed origin does not bypass JWT authentication, HMAC verification, endpoint
  authorization, request limits, or `ALLOWED_HOSTS` validation.
- Comma-only entries, whitespace-only entries, repeated origins, `*`, `null`,
  `https://*.example.com`, `http://...`, loopback/local names, URL paths, query strings,
  fragments, credentials, and production ports are invalid configuration.

## Acceptance criteria

- AC-01: With production configuration containing exactly
  `CORS_ALLOWED_ORIGINS=https://robust-creativity-production-f6de.up.railway.app`, an
  `OPTIONS /api/auth/login` preflight from that Origin for `POST` with
  `Content-Type` returns a successful CORS response containing that exact origin,
  permits `POST`, permits `Content-Type`, and does not emit
  `Access-Control-Allow-Credentials`.
- AC-02: An actual API request from that allowed Origin receives the exact
  `Access-Control-Allow-Origin` response header; its normal application status and
  authentication behavior are unchanged.
- AC-03: A different origin receives no allow-origin response header; its preflight is
  not authorized.
- AC-04: Preflight permits `Authorization` for authenticated frontend requests and no
  method outside `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, or no header outside
  `Authorization` and `Content-Type` is authorized.
- AC-05: Production startup rejects unset/blank CORS origins and rejects wildcard,
  malformed, local/test, non-HTTPS, path-bearing, duplicate, or missing-required-origin
  CORS configuration without weakening existing `ALLOWED_HOSTS` validation.
- AC-06: A request without `Origin` preserves current same-origin/backend behavior;
  development Compose with its unset setting still functions through `/api`.
- AC-07: Focused tests cover the allowed preflight, allowed actual request, disallowed
  origin, production validation, and existing no-Origin behavior. Ruff, Ruff format,
  mypy strict, the relevant backend suite, and all existing required project gates pass.

## Open decisions

None.

## Follow-up / future specs

- Adding another fixed frontend origin, Railway preview deployments, a custom frontend
  domain, cookies, credentialed CORS, or CSRF changes requires a separate approved
  security spec.

## Implementation notes

The expected implementation is limited to typed configuration parsing/validation,
FastAPI's `CORSMiddleware` registration, `.env.example` and configuration documentation,
and focused backend tests (principally runtime-security/application tests). No new
dependency is needed. The Railway backend service must be configured with the exact
production value after the implementation is deployed.
