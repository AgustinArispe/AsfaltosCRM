# CRM-064 — Lost opportunities workspace

Status: Approved

## Scope

- Expose **Perdidas** next to **Ganadas** for authenticated sellers and supervisors,
  superseding the Lost navigation restrictions in CRM-042. Existing action permissions
  and loss and reopen workflows still apply.
- Use the Ganadas filter layout and current-month default. Support date of loss,
  customer/company/ID, product, origin, province, responsible user and unassigned, plus
  multiple loss reasons. Keep direct links, URL filters and cursor pagination.
- Show current losses, lost quoted kilograms, losses without a quote, and historical
  closure/reopen counts. Rank current reasons by cases or kilos. Reason rows filter
  the list. Place a brief recommendation below the chart based on the leading reason
  for that measure, using cases when there are no quoted kilos. Use a general
  recommendation when the top reasons tie. The history shows the latest loss, reason
  detail, original stage and quoted products.
- Use the closure snapshot for loss date, reason, stage, origin, province and product
  quantities. The responsible filter uses the current assignment. Retain historical
  breakdown fields for existing consumers.
- Reuse the same recommendations in the commercial Dashboard after the results
  summary. Rank Dashboard reasons by case count across the same filtered historical
  episodes as its loss KPI, including episodes that were later reopened. Include the
  reason counts in the overview response and omit the recommendation when no matching
  episodes are available.

## Acceptance criteria

- Both roles can open Perdidas and enter an opportunity directly from its results.
- Filters apply to both totals and rows; reasons are ranked across the filtered set,
  independently of page size. Reopened episodes remain in historical counts.
- The recommendation follows the filtered breakdown and stays hidden when it is empty.
- The workspace retains working filters, opening, reopening, retries and pagination
  at desktop and narrow widths.

## Open decisions

None.
