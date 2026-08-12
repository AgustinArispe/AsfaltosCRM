# Production security contract

CRM-017 must satisfy this contract before FAA CRM is deployed to production. It is a
deployment precondition, not a hosting implementation.

## Application-owned controls

The deployed backend must set `APP_ENVIRONMENT=production`. Startup rejects Fake
WhatsApp or media components, enabled simulation routes, placeholder/reused secrets,
untrusted hosts, unsafe PostgreSQL credentials, media limits over 16 MiB, and invalid
Meta configuration. It disables `/docs`, `/redoc`, and `/openapi.json`.

JWT access tokens are HS256-only and include `sub`, `iat`, `exp`, and the persisted
User session-version claim. Production lifetime is one to sixty minutes. Password
change or a transition to inactive increments that version, invalidating all previous
tokens. Tokens issued before the CRM-016 migration lack the required claim and are
intentionally invalid after deployment; operators must communicate this one-time login
renewal.

Application request-body boundaries return `413` before parsing for these exact paths:

| Path | Maximum complete request body |
| --- | ---: |
| `POST /api/intake/web` | 32 KiB |
| `POST /api/whatsapp/provider/webhook` | 2 MiB |
| `POST /api/whatsapp/media` | 17 MiB |
| `POST /api/customer-imports/dry-run` | 2.25 MiB |

Authenticated media uses `private, no-store`, `nosniff`, validated MIME, safe filename
encoding, opaque IDs, and no provider/storage path disclosure. Images may render inline;
PDFs/documents download as attachments.

## Edge-owned controls for CRM-017

The production reverse proxy/platform owns public TLS termination, static Vite
production hosting, and enforcement on every frontend/API/media/error response of:

- HTTPS-only and HSTS `max-age=31536000`; enable `includeSubDomains` or preload only
  after every affected hostname is HTTPS-ready.
- CSP: `default-src 'none'; base-uri 'self'; object-src 'none'; frame-ancestors 'none';
  form-action 'self'; script-src 'self'; style-src 'self'; connect-src 'self';
  font-src 'self'; img-src 'self' blob:; media-src 'self' blob:`.
- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy:
  no-referrer`, and `Permissions-Policy: camera=(), microphone=(), geolocation=(),
  payment=(), usb=()`.
- At-least-as-strict request limits matching the application table.

Rate limits are state shared across workers, return `429` plus `Retry-After`, and must
not rely on application-memory counters:

| Endpoint | Initial policy |
| --- | --- |
| `POST /api/auth/login` | 5/min per trusted client IP, burst 10; 60/min global |
| `POST /api/intake/web` | 60/min per source, burst 20; 300/min global |
| `POST /api/whatsapp/provider/webhook` | 600/min per provider source, burst 200; 1,200/min global |

CRM-017 records its proxy chain and trusts forwarded host/client headers only from that
known chain. It verifies that public docs are unavailable, Vite dev/reload is absent,
the production CSP works with the built frontend, and rate/body/header controls apply
to success and error responses. Logs, proxy diagnostics, and metrics must exclude
secrets, authorization headers, signatures, request bodies, provider payloads, and
storage keys.

## Verification handoff

CRM-017 staging smoke tests must prove HTTPS/header policy, body limits, `429` behavior,
trusted host handling, disabled docs, authenticated media disposition, and backend
production startup with secret values supplied only by the deployment secret manager.
It must not connect real WordPress or Meta production credentials without an explicit
operational approval.
