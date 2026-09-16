# CRM-045 — Overdue Opportunity Attention

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-16
Implementation commit: N/A

## Goal

Make an open Opportunity that has remained in the same commercial stage for one week
immediately recognizable as `¡Atrasado!` in Pipeline and Notifications, and surface the
same operational total inside the Dashboard's existing active-opportunity section.

## Context

CRM-003 already generates `OPPORTUNITY_STALE` notifications from
`current_status_entered_at`; CRM-019 permits an attention marker on Pipeline cards;
CRM-022 presents the notification workspace; and CRM-041 supplies the Dashboard active
Pipeline surface and stale-notification total. This spec changes the governing stale
threshold from fourteen days to seven and defines one consistent user-facing concept.
It supersedes prior exact fourteen-day references while preserving their remaining
notification lifecycle and commercial behavior.

## Dependencies

- CRM-003 — Stale Opportunity Notifications
- CRM-019 — Pipeline 2.0
- CRM-022 — Notifications UI
- CRM-041 — Dashboard Commercial Overview and Outcome Navigation
- CRM-042 — Dashboard Visibility and Per-user Lead Notifications

## Scope

- Change the default stale-opportunity threshold to seven full days in the same stage.
- Show a restrained but prominent `¡Atrasado!` marker on eligible Pipeline cards.
- Present active `OPPORTUNITY_STALE` rows as `¡Atrasado!` in Notifications.
- Integrate the authoritative stale-notification total into the existing Dashboard
  `Oportunidades activas` surface, with navigation to active Notifications.
- Reuse shared frontend eligibility logic and existing notification contracts.

## Non-goals

- New persistence, notification types, API routes, polling, email, push, scheduler, or
  escalation levels.
- Changing commercial stages, transition rules, assignment, filters, Dashboard metric
  formulas, layouts, or the behavior of `NEW_LEAD` notifications.
- Marking terminal `GANADA` or `PERDIDA` Opportunities as overdue.

## Business rules

- `NUEVA`, `COTIZADA`, and `NEGOCIACION` are overdue when
  `current_status_entered_at <= now - 7 days`.
- Exact equality at seven days is overdue. A timestamp newer than that boundary is not.
- A status change resets eligibility through the existing
  `current_status_entered_at` update and resolves the active stale notification.
- Quote or assignment edits do not reset the stage clock.
- `OPPORTUNITY_STALE` keeps its persisted type and API representation; `¡Atrasado!` is
  its concise user-facing label.
- Dashboard uses the existing authoritative unresolved stale-notification total. It
  does not infer a separate total from period metrics or filtered Pipeline counts.

## Data model

No schema or migration change. Existing Opportunities, Notifications, recipient state,
and partial uniqueness remain authoritative.

## Contracts / API

Existing Opportunity, Notification, and Metrics routes and payloads remain compatible.
`STALE_OPPORTUNITY_DAYS` retains positive-integer validation and defaults to `7`.

## State transitions

The CRM-003 notification lifecycle is unchanged: generation creates at most one active
stale notification per Opportunity, stage change or deletion resolves it, reading is
per recipient, and a later overdue stage may generate a new notification.

## Security & permissions

Existing authenticated visibility and per-user read rules remain unchanged. The
Dashboard and Pipeline do not expose additional Customer or Opportunity data.

## Edge cases

- Invalid or future timestamps never render as overdue.
- Pipeline eligibility is restricted to the three open stages even if an old terminal
  timestamp is present.
- A missing or failed Dashboard stale-total request keeps the active-opportunity
  section usable and shows no invented count.
- Zero overdue Opportunities does not create a warning treatment.

## Acceptance criteria

- AC-01: The configured default and business documentation define seven days, and
  notification generation includes exact seven-day equality while excluding newer,
  terminal, and deleted Opportunities.
- AC-02: Pipeline cards in the three open stages show `¡Atrasado!` at seven days or
  later, do not show it before the boundary, and expose the label in their accessible
  name.
- AC-03: `OPPORTUNITY_STALE` rows use the visible and accessible label `¡Atrasado!`;
  `NEW_LEAD` rows retain `Nueva oportunidad recibida`.
- AC-04: The Dashboard active-opportunity surface shows the unresolved overdue total
  without adding a standalone Dashboard section, and links to the active Notifications
  view.
- AC-05: Status changes continue to resolve the active notification and remove the
  Pipeline overdue marker after authoritative refresh.
- AC-06: Light/Dark, desktop/responsive, keyboard, focus, and reduced-motion behavior
  remain accessible and consistent with the shared design system.
- AC-07: Focused backend, frontend, and browser coverage verifies the threshold and all
  three presentation surfaces.

## Open decisions

None

## Follow-up / future specs

Operational scheduling of the existing generator remains deployment work.

## Implementation notes

Keep overdue date math in one pure frontend helper. Reuse the Dashboard's already
loaded stale-notification total and existing active Notifications route rather than
adding a request or section. Use semantic tokens for a compact warning badge; do not
add glow, animation, or a large alert card.
