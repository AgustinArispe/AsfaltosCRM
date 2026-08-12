# CRM-017 — Production Readiness Hardening

Status: Draft
Owner: FAA CRM team
Last updated: 2026-08-12
Implementation commit: N/A

## Goal

Define and verify the final production deployment and operational contract for FAA CRM
before backend feature freeze, without changing approved CRM behavior or introducing
unnecessary platform complexity.

## Context

CRM-013 preserves durable PostgreSQL concurrency and bounded Broadcast processing.
CRM-014 establishes bounded processor batches and external scheduling as the preferred
execution model. CRM-015 provides deterministic builds, locked dependencies, quality
gates, and a development Compose smoke test. CRM-016 establishes typed production
configuration, fail-closed security validation, private media behavior, request limits,
and the proxy-owned security policy.

The current repository Compose file and Dockerfiles intentionally support local
development/quality: PostgreSQL and FastAPI publish host ports, the frontend is Vite's
development server, the backend is root by default, migrations run in each backend
startup command, and `/health` combines process and database availability. They are not
a production topology. CRM-017 separates that operational deployment contract while
preserving the existing `docker compose up --build` development workflow.

## Dependencies

- CRM-013 — Backend Concurrency Hardening
- CRM-014 — Backend Performance Hardening
- CRM-015 — Quality and Reproducibility Hardening
- CRM-016 — Application Security Hardening

## Scope

- Deliver a production-only, single-host/VM deployment definition and operational
  runbooks appropriate to FAA's current scale.
- Run production frontend assets, reverse proxy, backend, PostgreSQL, migrations,
  scheduler, backups, and media storage with private network boundaries and explicit
  ownership.
- Implement structured, correlated, secret-safe operational logging and minimum
  provider-neutral observability.
- Establish health, deployment, backup, restore, recovery, and post-deploy smoke-test
  procedures.
- Reuse CRM-015 gates and CRM-016's production-security contract as release gates.
- Define completion conditions that place backend behavior under feature freeze.

## Non-goals

- New FAA business features, state transitions, roles, permissions, integrations, or
  public business API payloads.
- Frontend UX or navigation redesign.
- Real Meta credential connection, real WordPress production hookup, or live provider
  smoke testing without separate operational approval.
- Kubernetes, Redis, Celery, a new job queue, microservices, PgBouncer, or PostgreSQL
  topology redesign unless separately justified by measured need.
- An expensive monitoring vendor, enterprise secret platform, automatic production
  rollback, automatic Alembic downgrade, or destructive restore tests against
  production.

## Production topology

FAA production uses one dedicated hardened host/VM and a production-only Compose or
equivalent infrastructure definition. The supported topology is:

```text
Internet
  -> HTTPS reverse proxy (only public listener)
     -> static production frontend assets
     -> private FastAPI backend
        -> private PostgreSQL
        -> private filesystem media volume
```

The reverse proxy is the only service with public ports `80` and `443`. It redirects
HTTP to HTTPS and terminates TLS. The backend and PostgreSQL join only an internal
container network: they have no host-published ports and are not reachable directly
from the Internet. PostgreSQL has no public listener, security-group rule, or proxy
route. Administrative database access uses an explicitly authorized private network or
short-lived SSH tunnel, never a new public port.

The frontend is produced by `npm ci` and `npm run build` from the committed lock, then
served as static assets by the proxy or a small static-serving container. Vite dev,
reload, and port `5173` are forbidden in production. The proxy serves immutable,
hashed Vite assets with a long immutable cache lifetime and `index.html` with a
conservative revalidation/no-cache policy; SPA history paths fall back to the built
entry document while `/api` continues to proxy only to the private backend.

CRM-017 may introduce a dedicated `compose.production.yml`, production Docker targets,
and a pinned reverse-proxy image/configuration. It must not weaken or replace the
existing development Compose workflow.

## Container runtime and filesystem

The production backend image creates and runs as a dedicated unprivileged application
user with a fixed nonzero UID/GID. It owns only application-owned writable paths:

- the mounted WhatsApp media root and its temporary object-write subdirectory;
- a bounded runtime temporary directory when a dependency requires one; and
- no source, dependency, configuration, or root filesystem directory.

The media volume is created/mounted with that UID/GID and permissions compatible with
the existing storage boundary (`0700` directories and `0600` objects). The backend root
filesystem is read-only where practical; writable mounts are explicit and minimal. The
frontend/static and proxy images also use unprivileged users where their selected base
image supports it. PostgreSQL uses the image's dedicated database user and only its
private data volume. Production containers drop unnecessary Linux capabilities, do not
run privileged, and do not mount the Docker socket.

## TLS, proxy, and security contract

The production proxy is configured with the actual FAA hostname(s), forwards only the
known proxy chain, and passes/protects `X-Forwarded-For`, `X-Forwarded-Proto`, and Host
information without accepting spoofed client headers from arbitrary sources. Backend
`ALLOWED_HOSTS` contains exact production hosts only. Proxy and backend tests prove
that an untrusted Host is rejected and that neither backend nor database ports are
public.

The proxy implements every CRM-016 edge-owned control on frontend, API, media, and
error responses: HTTPS-only, HSTS `max-age=31536000`, the approved CSP, `nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and minimal
`Permissions-Policy`. It enforces at-least-as-strict request-size limits of 32 KiB for
Web intake, 2 MiB for Meta webhook, 17 MiB for WhatsApp media, and 2.25 MiB for Customer
CSV import. It applies the CRM-016 shared rate-limit buckets, `429`, and `Retry-After`
for login, intake, and burst-tolerant Meta webhook traffic. The application remains the
second, streamed size boundary and does not add process-local rate counters.

## Production secrets

The supported mechanism is host/operator-managed secret files outside the repository,
owned by the deployment account/root with directory mode `0700` and file mode `0600`.
The production Compose/runner references those files as read-only container secrets or
`*_FILE` inputs; it never loads a developer `.env` as the operational source of truth,
commits a secret, prints a secret, or exposes it in a build argument/image layer.

Each secret is injected only into the service that needs it. Deployment credentials are
available only to the deployment operator/CI environment and are distinct from runtime
secrets. Rotation is a documented controlled change: create replacement secret,
restrict its permissions, update the deployment reference, restart/roll the affected
service, validate readiness and affected integration, revoke the old secret, and record
the event without its value. JWT or Web Intake secret rotation explicitly invalidates
existing JWTs or inbound signing clients as appropriate and is scheduled/communicated.

Critical secret inventory:

- PostgreSQL service, application, backup-encryption, and off-host-storage credentials;
- `JWT_SECRET` and `WEB_INTAKE_SIGNING_SECRET`;
- Meta access token, App Secret, webhook verify token, and any Meta deployment
  credentials; and
- production host, TLS/DNS, image registry, SSH/deployment, and backup destination
  credentials.

CRM-016 startup validation remains mandatory and fail closed for production. CRM-017
adds file-based secret delivery support only through a typed, secret-redacted config
boundary; it does not log secret values or implement an unnecessary enterprise secret
manager.

## Structured logging and request correlation

Production application, scheduler, migration, backup, and proxy logs are structured
JSON written to stdout/stderr or the platform's standard collector. Where applicable a
record includes UTC timestamp, level, service, event name, request ID or job run ID,
route/method/status, safe latency, authenticated User ID, relevant domain entity IDs,
and a safe error category/code. User and entity IDs are operational identifiers, not
metric labels.

Request-ID middleware accepts only a bounded, printable, proxy-trusted incoming ID
that matches a documented safe format; otherwise it generates a UUID-compatible ID.
It returns `X-Request-ID`, makes the ID available to request logs/error logs, and never
uses an unbounded client value. CLI/scheduled commands accept or generate a `job_run_id`
and include it in every command log. Proxy logs propagate the same request ID.

Logs, metrics, traces, exception contexts, and proxy diagnostics must never contain
access tokens, JWTs, passwords, raw request bodies, WhatsApp text/message bodies,
customer email/phone, provider media URLs, uploaded content, HMAC/Meta signatures,
storage keys, database URLs, or secret values. Error reporting uses reviewed safe
categories rather than serializing arbitrary exception/request objects.

## Liveness, readiness, and observability

CRM-017 separates two internal health checks:

- liveness proves only that the FastAPI process/event loop is running and does not
  query PostgreSQL or external providers;
- readiness proves startup configuration is valid and PostgreSQL is reachable by a
  short bounded query. It does not require Meta or WordPress availability.

The current database-backed `/health` may remain a compatible readiness alias or be
replaced through an explicitly documented deprecation-free route plan. Provider and
WordPress failures are logged/metriced independently so that an integration outage is
visible but does not make core CRM readiness fail.

The deployment provides provider-neutral collection/alerting that can begin with
host/container logs and a low-cost metrics/log backend. It monitors application
availability, HTTP error rate/latency, database connection/query failures, disk,
database, and media-volume capacity, plus safe aggregate outcomes for Web Intake,
WhatsApp inbound/outbound, Meta verification, Broadcast failures/UNKNOWN/backlog,
notification generation, imports, and scheduler/job failures. Alert thresholds,
ownership, and escalation destination are recorded in the runbooks; no expensive vendor
is required.

## Scheduler and background commands

An external platform scheduler, cron, or systemd timer runs approved commands in a
dedicated short-lived production job container using the same pinned application image
and secret/config boundary. No Redis, Celery, resident worker, or in-process web
scheduler is introduced.

The schedule covers idempotent stale-notification generation, one bounded batch per
active WhatsApp Broadcast through a typed dispatcher that reuses CRM-014's maximum of
ten recipients, and the approved bounded Legendary recomputation maintenance command.
The WordPress smoke command is manual/approved only, not scheduled. Each job has a
documented cadence, runtime timeout, nonzero failure exit code, job-run ID, structured
logs, alert on failure, and non-overlap guard where duplicate execution could race.
The guard is external scheduler locking or a short PostgreSQL advisory-lock boundary;
it does not use process memory. Broadcast concurrency continues to use CRM-013's row
and advisory-lock rules and is not serialized by a long provider-I/O lock.

## Backup, media recovery, and restore verification

PostgreSQL backups use PostgreSQL-native `pg_dump` custom-format dumps or an equivalent
reviewed PostgreSQL-native physical backup suited to the selected host. The conservative
initial policy runs one encrypted off-host backup at least daily, retains 7 daily, 8
weekly, and 12 monthly recovery points, records completion/size/checksum/exit outcome,
and alerts on a missed or failed run. Encryption keys and off-host destination access
follow the production secret policy. Database integrity is checked during the restore
drill, not merely by backup command success.

The same backup run snapshots/copies the private WhatsApp media volume to encrypted
off-host storage and records a manifest tied to the database backup identifier. The
manifest verifies that every backed-up attachment storage reference has recoverable
content. Recovery restores database metadata and the matching media snapshot together;
it must not create durable `storage_key` rows whose content cannot be recovered. Normal
Customer/Opportunity soft deletion never causes historical media deletion or omission
from backup.

A restore drill is mandatory before release and at least quarterly afterward. It runs
only against isolated fresh infrastructure:

```text
select backup -> provision fresh PostgreSQL -> restore database -> restore media
-> alembic current/head verification -> readiness -> bounded authenticated smoke
```

The smoke asserts media authorization/disposition, core protected-route behavior, and
absence of fake/dev routes and public docs. It records elapsed recovery time, backup
identifier, migration revision, manifest result, and failures. It must never overwrite
production. A backup is not verified until this complete restore succeeds.

## RPO and RTO

The proposed initial FAA targets are RPO <= 24 hours and RTO <= 4 hours. Daily backup
frequency is the maximum RPO interval; off-host retention and quarterly restore drills
provide recovery evidence. The four-hour RTO includes provisioning isolated recovery
resources, database/media restore, migration verification, configuration validation,
and bounded smoke checks. Higher-frequency backups, standby databases, or PgBouncer are
not required unless these targets or measured growth prove them necessary.

## Database runtime and migrations

Production keeps SQLAlchemy `pool_pre_ping=True` for stale connection recovery. CRM-017
defines explicit finite pool size, max overflow, pool timeout, and recycle settings only
after accounting for backend worker count, migration runner, scheduler jobs, and the
PostgreSQL connection limit. The sum of their worst-case connections remains below a
documented conservative database budget with administrative headroom. One or a small
measured backend worker count is preferred for FAA's initial scale; PgBouncer is not
introduced without connection-pressure evidence.

Deployment follows this controlled migration sequence:

```text
verified backup/checkpoint -> exactly one migration runner -> alembic upgrade head
-> alembic current --check-heads -> application rollout -> readiness/smoke checks
```

Application workers never race to run migrations at startup. A failed migration halts
rollout, preserves logs and the pre-migration checkpoint, and is investigated before
retry. Application rollback uses a compatible prior image only when schema compatibility
is proven; automatic Alembic downgrade is not assumed safe. If restoration is required,
operators follow the isolated, reviewed database/media recovery runbook.

## Production smoke, CI, and release gate

Post-deploy smoke tests use synthetic/non-PII data and safely scoped credentials. They
verify HTTPS frontend delivery, login/authenticated protected-route behavior where
safely automatable, backend liveness/readiness, frontend-to-backend proxying, database
connectivity, Alembic head, media authentication/disposition, disabled fake/dev routes,
production docs/OpenAPI policy, exact Host behavior, and absence of public backend or
PostgreSQL ports. Real Meta and WordPress smoke checks remain conditional on explicit
credentials and integration availability.

The release gate retains every CRM-015 quality, coverage, lock, audit, and Compose gate
and adds production-image build validation, production configuration/startup validation
with synthetic secrets, production topology/proxy smoke where feasible, and documented
non-production backup/restore drill command availability. CI never restores over normal
CI databases or production; a manually approved isolated environment executes restore
drills.

## Runbooks and backend freeze

CRM-017 creates concise, executable runbooks for deployment, backup/restore, secret
rotation, database recovery, Meta outage, WordPress intake failure, Broadcast
stuck/UNKNOWN, and scheduler/job failure. They identify prerequisites, command owner,
safe diagnostics, recovery/rollback limits, alert/escalation path, and cleanup.

CRM-017 is complete only when its acceptance criteria and final audit findings are
verified in the selected production-like environment, the release gate is green, and
the runbooks have been exercised. At that point backend enters feature freeze: only
bug/security fixes or a newly approved spec may change backend behavior; frontend work
may continue against the frozen contracts.

## Acceptance criteria

- AC-01: A production-only topology exposes only the HTTPS proxy, keeps backend,
  PostgreSQL, and media private, serves a built static frontend, and preserves local
  development Compose/Vite workflow.
- AC-02: Production containers run unprivileged with read-only filesystems where
  practical, bounded writable paths, correctly owned private media volume, and no
  privileged/Docker-socket capability.
- AC-03: Proxy/TLS configuration enforces HTTPS redirect, trusted forwarding, exact
  hosts, CRM-016 headers, body caps, and shared rate-limit policy; public backend/DB
  ports and fake/dev/docs routes are absent.
- AC-04: Restricted file-backed/container-secret delivery covers every critical secret,
  fails closed at startup, records rotation/revocation procedures, and never uses a
  committed/developer `.env` or logs a value.
- AC-05: Structured logs and request/job correlation include the defined safe fields,
  return a bounded `X-Request-ID`, and exclude all listed credential, PII, message,
  media, body, signature, and storage secrets.
- AC-06: Separate liveness and PostgreSQL-backed readiness checks are bounded and Meta
  or WordPress outages remain observable without blocking core readiness.
- AC-07: Provider-neutral monitoring/alerts cover availability, latency/errors,
  database/capacity, intake, WhatsApp/Meta/Broadcast outcomes, imports,
  notifications, and scheduler failures without high-cardinality PII labels.
- AC-08: External scheduled commands are idempotent, bounded, non-overlapping where
  required, correlated, failure-alerted, and cover stale notifications, bounded
  Broadcast processing, and approved maintenance without Redis/Celery.
- AC-09: Automated encrypted off-host PostgreSQL and matching media backups have the
  stated retention, safe manifests/logs/monitoring, and preserve historical media.
- AC-10: An isolated restore drill restores PostgreSQL and matching media, verifies
  Alembic/readiness/authenticated smoke, records recovery evidence, and never writes to
  production.
- AC-11: The approved RPO/RTO targets drive backup cadence, retention, recovery
  procedure, and drill evidence.
- AC-12: Database pool/worker settings fit a documented PostgreSQL connection budget;
  one migration runner completes backup -> upgrade -> head verification -> rollout, and
  failed-migration rollback avoids unsafe automatic downgrades.
- AC-13: Production frontend uses locked `npm ci`, built static SPA assets, immutable
  hashed-asset caching, conservative entry caching, and proxy SPA fallback without Vite
  development behavior.
- AC-14: Automated production-like smoke tests prove the declared network, TLS,
  readiness, migration, proxy, protected-route, media, docs, and fake-route invariants;
  real Meta/WordPress checks remain safely conditional.
- AC-15: Deployment, recovery, outage, Broadcast UNKNOWN, secret-rotation, and
  scheduler-failure runbooks are concise, executable, and exercised.
- AC-16: CRM-015 quality gates plus production image/config/topology validation and
  non-destructive restore-drill availability are green; final audit findings are
  resolved and backend freeze criteria are documented and met.

## Open decisions

- FAA operational owner must approve or amend the proposed initial RPO <= 24 hours and
  RTO <= 4 hours before CRM-017 can be approved; the approved targets determine the
  backup cadence, retention capacity, recovery staffing, and alert escalation.

## Follow-up / future specs

- Scaling, PgBouncer, a standby database, object storage, or a managed/enterprise
  monitoring or secret platform only if measured capacity, RPO/RTO, or operational
  evidence justifies it.
- Any real Meta/WordPress production integration smoke or an authentication architecture
  redesign requires separate explicit approval.

## Implementation notes

Prefer one pinned production Compose definition on a hardened host with a small reverse
proxy and external scheduler over a new orchestration platform. Keep application config,
request correlation, logging, health, and CLI changes strictly typed and secret-safe.
The production definition must make private/public ports, migration runner ownership,
volume ownership, and secret-file mounts mechanically reviewable. Record actual chosen
hostnames, pool budget, proxy trust chain, scheduler cadence, backup destination, and
on-call/escalation details in deployment-only files/runbooks without committing secret
values.
