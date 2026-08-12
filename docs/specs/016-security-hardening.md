# CRM-016 — Application Security Hardening

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-12
Implementation commit: 4b15dc667364ba10c13a33dd66e2fc8865b3b44c

## Goal

Close the Release Candidate application-security findings before production deployment
without changing approved FAA CRM or WhatsApp business behavior.

## Context

CRM-001 through CRM-015 define the implemented product, provider boundaries,
authenticated media, signed public ingress, concurrency behavior, and reproducible
quality gates. The current application already uses Argon2 password hashing, fixed
HS256 JWT verification, active-user lookup, HMAC-authenticated Web intake, signed Meta
webhooks, `TrustedHostMiddleware`, strict request schemas, private media storage, MIME
allowlists, magic-byte checks, and secret-safe provider mappings.

The Release Candidate audit identified narrower production gaps. Runtime mode is not
explicitly typed; Fake Provider currently enables the WhatsApp simulation router by
itself; a password replacement does not revoke an already issued JWT; public request
bodies can reach FastAPI before a complete body-size boundary rejects them; and the
repository has no production proxy contract for TLS, rate limits, security headers,
request limits, or API-documentation exposure. Docker Compose intentionally runs Vite's
development server and is a development/CI entry point, not production infrastructure.

CRM-016 owns application hardening and a verifiable production-security contract.
CRM-017 will own the concrete production proxy, hosting, secret installation, and
deployment readiness.

## Dependencies

- CRM-001 — Core CRM
- CRM-002 — Web Lead Intake
- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API
- CRM-008 — WhatsApp Media Storage
- CRM-009 — Meta Cloud API Provider
- CRM-011 — WhatsApp Broadcast Execution
- CRM-012 — CRM Commercial Completion
- CRM-013 — Backend Concurrency Hardening
- CRM-015 — Quality and Reproducibility Hardening

## Scope

- Introduce one explicit typed application environment: `development`, `test`, or
  `production`.
- Centralize startup security validation and fail production startup for unsafe runtime
  combinations.
- Require double opt-in before registering WhatsApp development simulation routes.
- Add durable JWT session-version validation so password changes revoke prior tokens.
- Require and validate only JWT claims with a concrete authentication purpose.
- Bound public intake, provider webhook, authenticated media-upload, and Customer-import
  request bodies before unbounded parsing.
- Define production proxy/platform rate limits, TLS, response headers, body limits, and
  operational verification without selecting unnecessary infrastructure.
- Preserve the current same-origin Bearer-token architecture while documenting its XSS
  residual risk and required CSP mitigation.
- Harden authenticated media response disposition and preserve upload/storage safety.
- Disable public API documentation in production.
- Preserve strict Trusted Host behavior, absence of permissive CORS, and current HMAC
  and Meta webhook verification.
- Add focused security tests and a typed/documented contract consumed by CRM-017.

## Non-goals

- Any change to FAA commercial, WhatsApp, consent, Broadcast, state-machine, role, or
  visibility behavior.
- MFA, SSO, OAuth provider login, a new role, or authorization redesign.
- Refresh tokens, Redis, token blacklists, a session table, or a distributed cache.
- Automatic migration from `sessionStorage` Bearer tokens to cookies or a CSRF redesign.
- Frontend UX or navigation redesign.
- Production hosting, proxy implementation, domain/DNS provisioning, certificate
  provisioning, or deployment automation.
- Real Meta credentials, WordPress production connection, or live provider smoke tests.
- Antivirus, sandboxing, image/PDF re-encoding, content sanitization, or a new media
  processing dependency.
- A new public media endpoint, public object URL, or change to storage retention.

## Runtime environment and fail-closed startup

`APP_ENVIRONMENT` is required and maps to one typed enum value: `development`, `test`,
or `production`. There is no inferred environment from provider choice, hostnames,
debug flags, tests, or deployment naming, and an absent/unknown value stops startup.
Docker Compose declares `development`; normal CI declares `test`; a production
deployment must declare `production` explicitly.

Application assembly consumes one immutable typed security/runtime settings object and
one central validation policy. Domain services do not read the environment and do not
contain environment branches. The central policy validates all relevant settings before
routers are registered or the application begins serving traffic. Secret values are
redacted from settings representations and startup errors.

In `production`, startup fails for any of the following:

- Fake WhatsApp Provider or Fake media storage;
- enabled WhatsApp development routes;
- missing, placeholder, default, insufficient, or mutually reused secrets;
- absent, wildcard, local, test, Compose-only, malformed, or otherwise untrusted
  `ALLOWED_HOSTS` entries;
- missing or invalid Meta provider configuration, non-HTTPS/untrusted provider
  transport, or unbounded provider timeout/retry configuration;
- JWT expiration outside the production bound;
- a public FastAPI documentation configuration;
- a debug/reload/development-server behavior represented in application configuration;
- a configured upload/body limit above the production maximum in this spec.

The production deployment contract also forbids Uvicorn reload/debug operation and the
Vite development server. Those process-level controls are verified by CRM-017 because
they cannot be made trustworthy by a domain-service environment check.

## WhatsApp development routes

`WHATSAPP_DEV_ROUTES_ENABLED` is a strict boolean with a safe default of `false`.
The `/api/whatsapp/dev` router is constructed and registered only when all three facts
are true:

1. `APP_ENVIRONMENT=development`;
2. the selected concrete provider is `FakeWhatsAppProvider`;
3. `WHATSAPP_DEV_ROUTES_ENABLED=true`.

Fake Provider alone is insufficient. The explicit flag alone is insufficient. Test and
production environments never register the router. Production configuration containing
the enable flag or Fake Provider is rejected at startup, so changing only one variable
cannot expose the routes. Tests may assemble an explicit development-mode application
when exercising the simulator; application tests for `test` and `production` assert
that every development path is absent from the route table and OpenAPI document.

## JWT session revocation and validation

### Durable session version

`users` gains `auth_session_version`, a positive non-null integer with an initial value
of `1`. It is authentication evidence only and is not returned by normal User API
responses. The access token carries the same integer in one short, documented claim
such as `ver`.

Current-user authentication decodes a typed claim result, loads the User as it does
today, and accepts the token only when the User exists, is active, and its persisted
version exactly matches the claim. Authentication failures remain the current generic
`401` response and never disclose whether the subject, activity state, claim, or
version failed.

Changing a password locks the User and updates the password hash and increments
`auth_session_version` in the same transaction. A security-reset application operation,
if later exposed, must revoke sessions through that same version increment rather than
adding a second mechanism. CRM-016 does not add a new reset endpoint or reset UX.

Deactivation continues to fail on the active-user lookup and also increments the
version when transitioning from active to inactive. Reactivation therefore does not
revive a token issued before deactivation. Role changes remain immediately effective
because authorization uses the freshly loaded persisted User role; token claims do not
duplicate role authority.

The Alembic migration adds and backfills the column, installs the positive-value
constraint, and leaves every existing User at version `1`. Tokens issued before this
deployment do not contain the required version claim and become invalid once the new
code is active. This one-time logout is intentional and documented in the deployment
runbook. No token rows, blacklist, refresh-token data, or Redis state are introduced.

### JWT claim policy

The JWT policy preserves:

- one fixed allowlisted algorithm, `HS256`;
- required `sub` and `exp` claims;
- active User lookup and persisted-role authorization;
- generic authentication failures.

It additionally requires `iat` and `ver`. `iat` is an aware issuance NumericDate used
to reject a token issued implausibly in the future and to prove that `exp` is after
issuance and within the configured maximum lifetime. A small fixed clock-skew leeway of
at most 30 seconds may be used consistently for timestamp validation. `ver` exists only
for durable revocation.

`JWT_ACCESS_TOKEN_EXPIRE_MINUTES` remains configurable but must be an integer from 1 to
60 inclusive in production; the existing 60-minute behavior remains valid. Token
creation and validation share the same typed bound, and a signed token whose lifetime
exceeds it is rejected. `iss`, `aud`, JWT IDs, refresh claims, roles, emails, and other
claims are not added because the current single same-origin issuer/consumer has no
concrete need for them.

## Public request body-size protection

Field, file, MIME, and schema limits remain authoritative after transport acceptance,
but they are not the first body-size boundary. Production uses exact path/method limits
at the reverse proxy or platform, and the application independently enforces the same
or a lower typed byte cap with an ASGI receive counter. A valid `Content-Length` above
the cap is rejected early; missing or chunked length is still counted while streaming.
The boundary returns a generic `413 Payload Too Large` before Pydantic parsing, multipart
parsing, HMAC work, JSON mapping, storage, or database effects.

Initial production limits are:

| Boundary | Application payload limit | Maximum complete HTTP request body |
| --- | ---: | ---: |
| `POST /api/intake/web` | current fields within 32 KiB | 32 KiB |
| `POST /api/whatsapp/provider/webhook` | signed raw JSON within 2 MiB | 2 MiB |
| `POST /api/whatsapp/media` | configured file limit, at most 16 MiB | 17 MiB including multipart overhead |
| `POST /api/customer-imports/dry-run` | existing 2,000,000-byte CSV | 2.25 MiB including multipart overhead |

The proxy limit may be lower only when it still accepts every application-valid request
and its documented multipart overhead. The application rejects production media limits
above 16 MiB. Intake and Meta verification continue signing/verifying the exact bounded
raw bytes. Media and CSV handlers retain their per-file `limit + 1` reads as a second
check; accepting a small file inside an oversized multipart envelope is prohibited.

## Rate-limit policy

Rate limiting belongs to the shared production proxy/platform or another deployment
boundary with state shared across application workers. Process-local dictionaries,
counters, and locks are prohibited. CRM-016 does not select Redis or an enterprise API
gateway.

The CRM-017 deployment must start with the following reviewed token-bucket equivalents,
return `429` with `Retry-After`, and expose only aggregate safe metrics:

- `POST /api/auth/login`: 5 requests per minute per trusted client IP with burst 10,
  plus a 60-per-minute deployment-wide ceiling. Every attempt counts, so response
  differences cannot become an oracle. Proxy/client-IP trust is limited to the known
  proxy chain.
- `POST /api/intake/web`: 60 requests per minute per source with burst 20 and a
  deployment-wide ceiling of 300 per minute. HMAC verification remains mandatory and
  rate limiting does not replace it.
- `POST /api/whatsapp/provider/webhook`: a burst-tolerant initial ceiling of 600
  requests per minute per provider source with burst 200 and 1,200 per minute globally.
  Static Meta IP allowlisting is not assumed. Valid Meta redelivery remains idempotent,
  and operators monitor `429` and tune only from measured legitimate traffic/provider
  guidance.

Exact production values and any tuning are recorded in the CRM-017 deployment artifact.
Limits cannot be silently disabled. Health checks and authenticated internal CRM routes
are not placed under the login/public-ingress buckets.

## Production TLS and security headers

Production is HTTPS-only. The trusted edge redirects or rejects plain HTTP before the
application and sends HSTS on successful and error responses. The initial HSTS policy
is `max-age=31536000`; `includeSubDomains` and preload are enabled only after CRM-017
confirms ownership and HTTPS readiness for every affected subdomain.

The production edge applies, including to API errors and authenticated media:

- `X-Content-Type-Options: nosniff`;
- `Content-Security-Policy` with `default-src 'none'`, `base-uri 'self'`,
  `object-src 'none'`, `frame-ancestors 'none'`, `form-action 'self'`,
  `script-src 'self'`, `style-src 'self'`, `connect-src 'self'`,
  `font-src 'self'`, `img-src 'self' blob:`, and `media-src 'self' blob:`;
- `X-Frame-Options: DENY` as legacy clickjacking defense consistent with
  `frame-ancestors 'none'`;
- `Referrer-Policy: no-referrer`;
- a minimal `Permissions-Policy` disabling at least camera, microphone, geolocation,
  payment, and USB.

The enforced CSP targets the actual Vite production build: same-origin hashed module
scripts/styles, same-origin API requests, inline React SVG, and authenticated media
fetched into `blob:` URLs. It does not permit `unsafe-eval`, broad `unsafe-inline`,
arbitrary `data:`, third-party scripts, or provider/media origins. A production build
and browser smoke test must pass with this policy. A later dependency requiring a new
source needs explicit review and the narrowest directive change.

## Browser token storage and CSRF

CRM-016 retains the current tab-scoped `sessionStorage` Bearer token. This avoids an
unreviewed auth/CSRF migration and preserves existing API clients, but JavaScript running
in the origin can read and exfiltrate the token. Tab lifetime and logout cleanup reduce
persistence; they do not mitigate XSS.

Required mitigations are the strict production CSP above, no third-party script origin,
React text rendering rather than HTML injection, no `dangerouslySetInnerHTML` for
untrusted data, maintained dependency audits, short bounded JWT lifetime, and immediate
version revocation after security-sensitive User changes.

Bearer-header authentication does not require CSRF protection in the current
architecture because browsers do not automatically attach the `Authorization` header
cross-site and no permissive CORS policy authorizes another origin to do so. HMAC public
ingress is not cookie-authenticated. A future HttpOnly-cookie proposal is justified only
by an explicit security requirement or evidence that residual token-readable XSS risk
is unacceptable; it requires a separate approved spec covering `Secure`, `HttpOnly`,
`SameSite`, login/logout semantics, CSRF tokens/origin checks, and proxy behavior.

## Media download and upload hardening

Authenticated upload preview and Message attachment reads remain private and never
expose a filesystem path, storage key, object URL, provider media ID/URL, or checksum.
Every media response uses validated `Content-Type`, `Cache-Control: private, no-store`,
and `X-Content-Type-Options: nosniff`.

`Content-Disposition` is always generated from a sanitized leaf filename with safe
RFC-compatible encoding and no control characters:

- allowlisted JPEG, PNG, and WebP images may use `inline`;
- PDF and every document type use `attachment` by default;
- missing filenames receive a safe server-generated download name;
- inline document/PDF rendering requires a separately approved preview UX and threat
  review.

Upload validation preserves the existing separate maximum sizes, MIME allowlists,
declared-versus-detected MIME match, magic-byte inspection, nonempty content, filename
sanitization, immutable checksum verification, opaque references, atomic private
filesystem storage, traversal/symlink defenses, and authentication. Structurally
malformed files can still pass a signature-level inspector and may exercise browser or
downstream parser vulnerabilities. Attachment disposition, `nosniff`, CSP, patched
dependencies/browsers, and user caution are the accepted residual controls in this
scope; antivirus and content re-encoding remain non-goals.

## API documentation, hosts, CORS, and secrets

Production FastAPI assembly disables `/docs`, `/redoc`, and `/openapi.json`; the paths
return not found and are not merely hidden from navigation. Development and test may
retain them for engineering and contract tests. If internal production documentation
later becomes operationally necessary, CRM-017 must expose it only through a separately
authenticated internal boundary, not by re-enabling the public routes.

Production `ALLOWED_HOSTS` is explicit and exact. Wildcards, empty entries, URL schemes,
paths, ports in host names, localhost/loopback, `testserver`, and Compose service names
are rejected. Host validation runs for health, documentation, API, webhook, media, and
error paths. Forwarded host/client information is trusted only from the known production
proxy chain documented by CRM-017.

The same-origin architecture remains in force. No CORS middleware or permissive origin,
header, method, or credential rule is added. A later multi-origin frontend requires a
separate approved security review. Moving authentication to cookies also requires the
new CSRF review described above.

Production secret policy requires:

- independently generated JWT and Web-intake secrets with at least 32 random bytes of
  effective material, at least 32 characters at the application boundary, and no known
  placeholder/default value; the two values must differ;
- present, non-placeholder Meta access token, App Secret, and webhook verify token in
  Meta/production mode, with App Secret at least 32 characters and all CRM-009 Meta IDs,
  timeouts, TLS-host, and retry validation preserved;
- a PostgreSQL URL using the expected driver with a nonempty, non-placeholder password
  for the current password-authenticated deployment. The platform owns password length,
  rotation, and secret-manager delivery because the application cannot measure their
  actual entropy reliably.

The application validates shape, required presence, separation, and known unsafe
values, not speculative entropy. Startup failures identify only the setting name and
safe reason. Secret values, authorization headers, signatures, database URLs, request
bodies, provider payloads, and configuration object representations are never logged or
returned.

## Deployment security contract

CRM-016 implementation must add one reviewed, typed/documented production-security
contract consumed by CRM-017. It records, without secret values:

- application environment and allowed hostnames;
- provider/storage modes and development-route state;
- JWT lifetime/claim policy and secret-validation status;
- public request-body caps;
- rate-limit buckets and trusted client-IP/proxy-chain ownership;
- HTTPS/HSTS and the exact response-header/CSP policy;
- API-documentation exposure state;
- media disposition rules;
- verification commands and responsible application-versus-edge owner for each control.

The application-owned items are enforced by typed startup validation and tests.
Proxy/platform-owned items are mandatory deployment preconditions, represented in the
runbook/contract and verified in CRM-017 staging/production smoke tests. CRM-016 does
not provision the proxy, certificates, domains, secret manager, production containers,
or hosting.

## Contracts / API

No business request or response payload changes. Access tokens gain only required `iat`
and session-version validation; token strings remain opaque to the frontend. Older
tokens and wrong-version tokens return the existing generic `401`.

Oversized protected requests return `413` with a bounded generic response and no
application effect. Rate-limited edge requests return `429` with `Retry-After`.
Production documentation paths return `404`. Authenticated PDF/document content changes
from the current universal inline behavior to safe attachment disposition. Existing
image preview behavior remains compatible.

## State transitions and permissions

No business or provider state transition changes. Both existing roles retain their
approved permissions and global visibility.

Authentication evidence changes are:

```text
password change or explicit security reset: auth_session_version N -> N + 1
active -> inactive:                         auth_session_version N -> N + 1
```

These updates occur under the existing User row lock in the same transaction as the
password/activity change. Concurrent security changes serialize and cannot lose an
increment. JWT validation is read-only and performs no token/session persistence.

## Edge cases

- Missing or misspelled `APP_ENVIRONMENT` never silently becomes development or
  production.
- Fake Provider plus a false/missing development flag has no simulation routes;
  development flag plus Meta Provider also has no routes and fails safe validation.
- A password-change transaction rollback preserves both the prior hash and prior
  version; a committed change invalidates every older token immediately.
- A token with a valid signature but missing, boolean/non-integer, nonpositive, future,
  expired, overlong-lifetime, or wrong-version claims receives the same generic `401`.
- Concurrent deactivation/reactivation or password changes use the locked persisted
  version; reactivation cannot revive pre-deactivation tokens.
- A false or absent `Content-Length` cannot bypass the streamed byte counter; an
  oversized body causes no HMAC parsing, provider mapping, upload, import, or database
  side effect.
- A legitimate burst of duplicate Meta events remains signature-verified and
  idempotently processed within the documented burst bucket; edge throttling preserves
  Meta retry behavior and is operationally visible.
- Header policy applies to `401`, `403`, `404`, `413`, `429`, `5xx`, health, and media
  responses, not only the frontend HTML success path.
- A hostile filename containing path separators, quotes, percent signs, Unicode, or
  CR/LF cannot inject response headers or select a storage path.
- A production proxy misconfiguration cannot make the application accept Fake Provider,
  dev routes, unsafe secrets, public docs, or untrusted hosts; proxy-only protections
  are still a CRM-017 deployment gate.

## Acceptance criteria

- AC-01: Required typed runtime settings distinguish development, test, and production,
  central validation rejects every documented unsafe production combination without
  logging secrets, and Docker/CI declare their intended non-production environment.
- AC-02: WhatsApp simulation routes exist only with development + Fake Provider + an
  explicit true enable flag and are absent from test, Meta, and every production route
  table even when one setting is misconfigured.
- AC-03: An Alembic-backed positive User session version is included in new JWTs;
  password change immediately rejects an older JWT, a new login token works, and
  deactivation/reactivation never revives a pre-deactivation token.
- AC-04: JWT verification remains fixed to HS256, requires valid `sub`, `exp`, `iat`, and
  version claims within the bounded lifetime, uses the active persisted User/role, and
  returns one generic failure for malformed, expired, future, unsigned/wrong-algorithm,
  or wrong-version tokens.
- AC-05: Proxy contract and application receive limits reject oversized intake,
  webhook, media multipart, and Customer CSV multipart bodies with `413` before parsing
  or side effects while preserving current field/file validation and exact-byte HMAC
  verification for valid requests.
- AC-06: The production contract defines shared deployment-level login, intake, and
  burst-tolerant Meta webhook rate limits with `429`, `Retry-After`, safe metrics, and no
  process-local in-memory counter or new enterprise dependency.
- AC-07: Production HTTPS/HSTS and response-header tests enforce the documented CSP,
  `nosniff`, clickjacking, referrer, and permissions policies on success/error/media;
  the real Vite production build works without broad `unsafe-inline` or `unsafe-eval`.
- AC-08: The security documentation records `sessionStorage` token XSS residual risk,
  mandatory CSP/text-rendering controls, why Bearer auth currently needs no CSRF token,
  and the separate-review conditions for any HttpOnly-cookie migration.
- AC-09: Authenticated images use safe inline disposition, PDFs/documents default to
  attachment, every response has private cache and `nosniff`, filenames are injection-
  safe, and no provider URL, storage key/path, checksum, or secret leaks through body,
  header, error, log, or metric.
- AC-10: Existing upload size/MIME/magic-byte/filename/filesystem/checksum tests remain
  green, malformed-file residual risk is documented, and no antivirus, re-encoding, or
  new media-processing dependency is introduced.
- AC-11: Production returns `404` for `/docs`, `/redoc`, and `/openapi.json`, while
  development/test contract tooling remains available under explicit non-production
  settings.
- AC-12: Trusted Host tests cover accepted exact production hosts and rejected wildcard,
  local/test/malformed/untrusted hosts on all ingress classes; same-origin operation has
  no permissive CORS and no cookie-auth CSRF behavior.
- AC-13: Production validates strong distinct JWT/intake secrets, required safe Meta
  credentials/configuration, and meaningful PostgreSQL credential shape without ever
  emitting their values or accepting repository placeholders.
- AC-14: Security regression tests preserve Web-intake HMAC freshness/exact-body checks,
  Meta challenge/signature-before-parse behavior, active-user and role authorization,
  provider/storage redaction, and the global PostgreSQL lock-order requirements.
- AC-15: A reviewed production-security contract assigns every application and edge
  control, records verifiable body/rate/header/docs/media policy without secrets, and
  makes the CRM-017 production deployment/smoke gate explicit without implementing
  hosting in CRM-016.
- AC-16: All CRM-015 quality, vulnerability, coverage, migration, Docker Compose, and
  acceptance-test traceability gates pass with no approved business behavior, role,
  frontend UX, provider state, or public business payload change.

## Open decisions

None

## Follow-up / future specs

- CRM-017 — Production readiness and deployment: implement and verify the production
  proxy/platform, TLS/certificates, static Vite hosting, domains, secret delivery,
  concrete rate/body/header controls, deployment smoke tests, monitoring, and runbooks.
- HttpOnly-cookie/CSRF architecture only if a later security review proves that the
  residual `sessionStorage` risk requires migration.
- Antivirus, file sandboxing, or content re-encoding only if a separately approved risk
  assessment justifies the dependency and operational model.

## Implementation notes

Keep environment parsing, secret-safe settings, startup validation, route assembly,
request-size policy, JWT claim DTOs, and deployment-contract serialization in small
strictly typed boundaries. Do not let domain services call `getenv()` or inspect
environment names. Preserve one row lookup for current-user authorization and extend it
with the persisted session-version comparison.

Use one Alembic migration for `users.auth_session_version`, deterministic backfill, and
the positive constraint. Reuse User row locking for password/activity changes. Keep
proxy-only requirements declarative and testable so CRM-017 can implement them without
duplicating application policy. Security tests should reference the owning `CRM-016`
acceptance criteria where practical and use synthetic secrets/provider payloads only.
