# Backend performance release runbook

This runbook implements the CRM-014 release evidence workflow. It is opt-in and is
not a normal push-CI gate. Run the baseline profile for a Release Candidate; run the
large profile when the host and release window can accommodate it.

## Safety and prerequisites

Use a disposable PostgreSQL database whose name ends in `_performance`. The seed
refuses every other database name and refuses a database containing Customers or
WhatsApp Conversations. It never truncates or resets data. Apply the normal Alembic
migrations before seeding.

The commands require PostgreSQL `psql`, the backend Python environment, `git`, and a
`PERFORMANCE_DATABASE_URL` in `postgresql://...` form. Never point this variable at a
development, test, staging, or production database.

Example with the Compose PostgreSQL container:

```bash
docker exec asfaltoscrm-db-1 createdb -U "$POSTGRES_USER" asfaltos_crm_performance
DATABASE_URL="postgresql+psycopg://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:$POSTGRES_PORT/asfaltos_crm_performance" \
  backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
export PERFORMANCE_DATABASE_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:$POSTGRES_PORT/asfaltos_crm_performance"
```

## Profiles and commands

The deterministic seed `14` baseline contains exactly 1,000 conversations, 10,000
messages, 10,000 status events, 1,000 attachments, 1,000 Customers/Opportunities, and 25 Broadcasts with 120
recipients each. The optional large profile contains 10,000 conversations, 100,000
messages, and 100,000 status events. Both use the same fixed timestamps, values,
recipient selection, and consent ordering.

From `backend/`:

```bash
./performance/run.sh seed baseline ../performance-artifacts
./performance/run.sh benchmark baseline ../performance-artifacts
./performance/run.sh explain baseline ../performance-artifacts
```

Or run all three phases against a fresh migrated database:

```bash
./performance/run.sh all baseline ../performance-artifacts
```

Use `large` in place of `baseline` for the optional release profile. Create a fresh
database before changing profiles or repeating the seed.

The benchmark performs two warmups and ten measured samples by default. Its JSON
artifact records exact row counts, seed profile, PostgreSQL version, Alembic revision,
Git commit, host, arguments, per-sample duration/query count/rows, median, P95, and
maximum. It measures conversation list (including search), detail, newest/older
message history, both polling paths, filtered overview/product/province/day/month
metrics, Broadcast validation, and confirmation revalidation.

To change sample counts without changing normal CI:

```bash
DATABASE_URL="${PERFORMANCE_DATABASE_URL/postgresql:/postgresql+psycopg:}" \
  python -m performance.benchmark --profile baseline --warmups 3 --samples 20 \
  --output ../performance-artifacts/benchmark-baseline.json
```

## EXPLAIN evidence

The EXPLAIN phase runs `ANALYZE` and then `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)`
with fixed IDs, periods, and cursors against the seeded data. It covers conversation
and message polling, filtered overview/product/province/timeline metrics, Broadcast
recipient claiming, single and batched latest-consent lookup, and Opportunity
list/detail queries containing the correlated `reopen_count` expression.

Each plan is written as text, and `plans.json` records planning/execution time,
estimated and actual rows, loops, shared/temp buffers, observed scan nodes, and sort
spill detection. The claiming query uses `FOR UPDATE SKIP LOCKED` only in the disposable
database and rolls back immediately; no provider call occurs.

Review these fields before proposing a change:

- estimated versus actual rows and loop multiplication;
- sequential, bitmap, and index scans in relation to selected-row percentage;
- join strategy and repeated correlated subplans;
- explicit sort method, memory, disk/temp spill, and buffer reads;
- planning and execution time across both profiles.

Do not add an index, denormalized field, polling table/timestamp, or change
`Opportunity.reopen_count` from intuition alone. Preserve the artifacts as before
evidence. If repeated measurements demonstrate a justified schema/index change, first
record the before plan and benchmark in CRM-014, specify the proposed change and
expected invariant, and obtain approval before implementing or measuring an after
plan. `pg_trgm` remains a future option only if measured Customer/Conversation search
volume and plans justify it.
