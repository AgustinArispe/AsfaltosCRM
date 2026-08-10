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

## Lifecycle

Specs move through these statuses:

- **Draft** — being explored or clarified; it is not an implementation authorization.
- **Approved** — explicitly approved for implementation within its stated scope.
- **Implemented** — acceptance criteria are met and the implementation commit is
  recorded in the spec.
- **Deprecated** — retained for history, but no longer governs new work.

The normal lifecycle is `Draft -> Approved -> Implemented`. A spec may be deprecated
when its feature is replaced or removed.

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
for example `feat: add inbox filters [SPEC-WA-01]`. After the implementation is
verified, set the spec status to `Implemented` and record that commit in
`Implementation commit:`. Tests may reference stable acceptance IDs such as `AC-01`
in test names, docstrings, or comments.

## Changes after implementation

If a new requirement changes an Approved or Implemented spec, update the spec first
with explicit user approval. Preserve the existing acceptance criteria and commit
history where they remain valid, document the changed scope or decision, and only then
update code and tests. Never silently edit `docs/BUSINESS_RULES.md` or a spec to make
the current implementation appear compliant.

Do not create retrospective specs for existing features unless a future task explicitly
requests them.
