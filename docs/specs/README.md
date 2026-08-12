# Feature specifications

This directory contains concise, feature-level specifications for FAA CRM work. A
specification describes one feature or module and is the implementation contract for
that scope. It must not duplicate the repository-wide development rules in
`AGENTS.md` or the FAA-wide business rules in `docs/BUSINESS_RULES.md`.

## Source-of-truth hierarchy

When sources disagree, use this order:

1. Explicit user-approved requirement
2. `docs/BUSINESS_RULES.md`
3. Approved feature spec
4. Implementation
5. Tests

Code and tests cannot redefine a requirement. A conflict with an Approved spec must be
reported before implementation or behavior changes.

## Spec IDs and filenames

Every feature specification uses one stable ID in the `CRM-NNN` form, such as
`CRM-001` or `CRM-006`. Keep the existing numeric descriptive filenames, for example
`001-core-crm.md`; the filename is not an alternative ID. Do not introduce other ID
formats.

## Lifecycle

Specs move through these statuses:

- **Draft** — being explored or clarified; it is not an implementation authorization.
- **Approved** — explicitly approved for implementation within its stated scope.
- **Implemented** — acceptance criteria are met, the implementation commit is verified,
  and a separate documentation commit records that implementation hash in the spec.
- **Deprecated** — retained for history, but no longer governs new work.

The normal lifecycle is `Draft -> Approved -> implementation -> verified implementation
commit -> separate documentation commit -> Implemented`. This keeps implementation
commits independent from the later documentation hash.

A spec may only become `Approved` when:

- `Open decisions` is `None`;
- acceptance criteria are testable;
- scope and non-goals are explicit; and
- it does not conflict with `docs/BUSINESS_RULES.md`.

Approved and Implemented specs should normally keep `Open decisions: None`; known
out-of-scope roadmap items belong in `Follow-up / future specs`.

Recommended workflow:

A. Draft and review the spec.
B. Set `Status: Approved`.
C. Implement and test the approved scope.
D. Commit the implementation referencing the spec ID.
E. Update the spec to `Status: Implemented` and record the implementation hash.
F. Commit that documentation update separately.

## When a spec is required

Create or update a spec before changes involving:

- persistence or schema;
- business rules;
- integrations;
- security or authentication;
- state machines;
- non-trivial API contracts;
- behavior spanning multiple modules.

Small styling changes, refactors, and bug fixes do not need a new spec when they do not
change behavior. If a supposedly small change changes behavior, use a spec.

## Working with specs

Before coding, locate the relevant spec or create one from [`_TEMPLATE.md`](_TEMPLATE.md).
Read `docs/BUSINESS_RULES.md`, then verify that the spec is `Approved` and that the
requested scope does not conflict with either source. Implement only the approved
scope and test its acceptance criteria.

Implementation commits should reference the spec ID in the commit message or body,
for example `feat: add WhatsApp API [CRM-006]`. After the implementation is verified,
update the spec and record that hash in `Implementation commit:` in a separate
documentation commit. Tests may reference stable acceptance IDs such as `AC-01` in
test names, docstrings, or comments.

The `Dependencies` section lists feature/spec dependencies only, never package
dependencies. The `Follow-up / future specs` section records known approved future work
outside the current scope.

## Changes after implementation

If a new requirement changes an Approved or Implemented spec, update the spec first
with explicit user approval. Preserve the existing acceptance criteria and commit
history where they remain valid, document the changed scope or decision, and only then
update code and tests. Never silently edit `docs/BUSINESS_RULES.md` or a spec to make
the current implementation appear compliant.

Retrospective specifications may be created when an explicit task requests them. They
must describe implemented behavior only.

## Draft specifications

None.

## Approved specifications

None.

## Implemented specifications

These specifications capture behavior already implemented and tested:

- [`CRM-001`](001-core-crm.md) — Implemented — core CRM domain, authentication, and
  roles.
- [`CRM-002`](002-web-lead-intake.md) — Implemented — authenticated server-to-server
  web intake.
- [`CRM-003`](003-stale-notifications.md) — Implemented — stale opportunity
  notifications.
- [`CRM-004`](004-commercial-metrics.md) — Implemented — backend commercial metrics.
- [`CRM-005`](005-whatsapp-core.md) — Implemented — fake-provider WhatsApp core domain.
- [`CRM-006`](006-whatsapp-internal-api.md) — Implemented — authenticated internal
  WhatsApp API and fake-provider support.
- [`CRM-007`](007-whatsapp-query-layer.md) — Implemented — typed WhatsApp Inbox query
  projections.
- [`CRM-008`](008-whatsapp-media-storage.md) — Implemented — durable provider-agnostic
  WhatsApp media storage.
- [`CRM-009`](009-meta-cloud-api-provider.md) — Implemented — production Meta Cloud API
  provider and webhook integration.
- [`CRM-010`](010-whatsapp-inbox-frontend.md) — Implemented — desktop-first WhatsApp
  Inbox frontend.
- [`CRM-011`](011-whatsapp-broadcasts.md) — Implemented — safe WhatsApp Broadcast
  execution, marketing consent, recipient tracking, and auditable delivery processing.
- [`CRM-012`](012-crm-commercial-completion.md) — Implemented — final commercial
  backend completion: Opportunity Notes, automatic Legendary qualification, Lost
  Opportunities workspace and reopen, Customer import, and WordPress production
  operations.
- [`CRM-013`](013-concurrency-hardening.md) — Implemented — backend concurrency,
  idempotency, lock-order, and Broadcast projection hardening.
- [`CRM-014`](014-performance-hardening.md) — Implemented — measured backend
  performance hardening for Broadcast validation/processing, metrics timelines,
  WhatsApp queries, polling, and Opportunity reopen projections.
- [`CRM-015`](015-quality-reproducibility-hardening.md) — Implemented — deterministic
  dependencies, frontend quality/coverage, CI supply-chain, and Docker smoke hardening.
