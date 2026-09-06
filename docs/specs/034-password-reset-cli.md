# CRM-034 — Production Password Reset CLI

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-09-06
Implementation commit: ca6547d1a1efc35dba4bcc95609fcb3f30932396

## Goal

Allow an authorized production operator to safely reset the password of an existing
FAA CRM user without exposing a password in a command, log, or source file.

## Context

FAA CRM has no public registration or password-reset flow. User passwords use the
existing Argon2 hashing boundary, and password replacement revokes existing JWTs by
incrementing `auth_session_version` (CRM-016).

## Dependencies

- CRM-001 — Core CRM
- CRM-016 — Application Security Hardening

## Scope

- Add an operator-only Python module CLI that targets one existing user by email.
- Prompt interactively for a new password and confirmation with `getpass`.
- Validate the password with the same constraints as the existing User API requests.
- Delegate the update to the existing `UserService` password-change mechanism.

## Non-goals

- Public password-reset endpoints, email delivery, reset tokens, MFA, or self-service
  account recovery.
- Creating users or demo data, changing roles or activation state, or modifying the
  database schema.

## Business rules

This command does not alter FAA roles or visibility rules in
[`BUSINESS_RULES.md`](../BUSINESS_RULES.md).

## Data model

No schema changes. The existing User password hash, `updated_at`, and
`auth_session_version` fields are updated through the existing service transaction.

## Contracts / API

The command is run as `python -m app.scripts.reset_user_password --email <email>`.
It exits nonzero with a clear message when the email does not identify a user, the
password confirmation differs, or the password violates the existing constraints.

## State transitions

No domain state transitions. A successful reset invalidates issued JWTs through the
existing session-version increment.

## Security & permissions

The CLI is intended only for an authorized operator in the backend production runtime.
It never accepts a password argument, prints a password, or logs a password. It uses
the existing Argon2 hashing and service layer; it does not use manual SQL updates or a
new hashing implementation.

## Edge cases

- Email comparison follows the existing normalized email behavior.
- A missing user is reported before requesting a password.
- A concurrent password reset remains serialized by the existing User row lock.

## Acceptance criteria

- AC-01: Given an existing user email and matching valid interactive password inputs,
  the CLI changes only that user's password through `UserService`, and the new password
  authenticates while the old password does not.
- AC-02: The CLI rejects mismatched or invalid interactive passwords without changing
  the stored password.
- AC-03: A missing email exits clearly without prompting for or exposing a password.
- AC-04: A successful reset revokes existing JWTs through the existing
  `auth_session_version` mechanism.

## Open decisions

None.

## Follow-up / future specs

None.

## Implementation notes

Reuse `PasswordInput` validation and `UserService`; do not duplicate password policy
or hashing logic in the CLI.
