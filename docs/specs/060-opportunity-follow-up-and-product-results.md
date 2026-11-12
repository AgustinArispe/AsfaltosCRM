# CRM-060 — Opportunity scrolling, follow-up and product results

Status: Approved
Owner: FAA CRM team
Last updated: 2026-11-12
Implementation commit: N/A

## Authorization and scope

The user explicitly requests natural vertical page scrolling in Oportunidades,
removing ¡Atrasado! from opportunity detail, replacing Dashboard's lower losses
panel with won kilograms by product, aligning the quoted-products panel, and
publishing the changes to main.

- The pipeline page owns vertical scrolling. Column card lists do not trap wheel
  movement; horizontal board scrolling and drag/drop remain available.
- Both roles can mark an overdue open opportunity al día from detail. This records
  the latest follow-up time and actor, resolves its active stale notifications
  globally and starts a new seven-day follow-up interval. Stage, original stage
  entry time, quotes and state-change history remain unchanged.
- A stale expected follow-up baseline is rejected to avoid refreshing another
  person's newer follow-up. Retrying the same completed acknowledgement is safe.
- The next stale notice is eligible seven days after the later of stage entry and
  latest follow-up; frontend badges and backend generation use the same baseline.
- Dashboard replaces its lower losses panel with Kilos ganados por producto and
  renames Productos to Kilos cotizados por producto. Both reuse the same ranked
  presentation and backend product metrics, include all positive product rows,
  respect period/dimensions and drill down to the opportunities behind the metric.
- Quoted figures use opportunity creation dates, as the existing quoted KPI does;
  won figures use winning dates, as the won KPI does. Explain these dates in the UI.

## Contracts and persistence

Add nullable last_followed_up_at and last_followed_up_by_user_id to Opportunity via
Alembic. Expose the timestamp in summaries and details. Add authenticated
POST /opportunities/{id}/follow-up with expected_follow_up_since (aware datetime).
Require the opportunity to be open and actually overdue; resolve only stale notices.
Return the updated detail. No deletion of notification evidence or new role policy.

## Acceptance criteria

- AC-01: Wheel up/down over a long column or board space scrolls the page; horizontal
  overflow and keyboard/pointer drag still work.
- AC-02: A current overdue detail offers Marcar al día with pending/error feedback;
  success clears the pipeline badge and refreshes global notification attention.
- AC-03: Reload preserves acknowledgement. Notifications are not recreated until
  seven days later; stage changes start their own interval without falsifying history.
- AC-04: Both roles can act; closed/deleted/non-overdue records cannot be refreshed;
  concurrent stale requests cannot overwrite newer follow-up, and retry is safe.
- AC-05: Product panels show correct quoted/won kg, labels, positive rows and
  period/dimension drilldowns. Backend product totals reconcile with overview KPIs.
- AC-06: Migration, backend/frontend tests, typing, coverage, build, audits, healthy
  Compose and GitHub browser checks pass before main is updated. Review snapshots
  changed by the intended design without weakening visual thresholds.

## Non-goals

No fabricated state transitions, permanently disabling overdue detection, changing
commercial aggregate definitions, removing historical losses, external messages,
new roles, dependency upgrades or direct production database edits.

## Open decisions

None.
