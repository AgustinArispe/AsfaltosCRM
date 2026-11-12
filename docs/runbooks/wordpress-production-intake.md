# WordPress production intake runbook

CRM-012 does not change the CRM-002 contract. The FAA website's current WordPress Avada
Forms `Contacto` form must deliver the exact UTF-8 JSON bytes to
`POST /api/intake/web`; the timestamp and signature headers must be calculated from
those same bytes after serialization. The form remains AJAX, and its existing Save To
Database action and email notification to `ventas@asfaltos-faa.com.ar` remain enabled
and independent of CRM delivery.

The production site currently exposes Avada 7.7.1 and form post ID `33`. Connector
implementation remains disabled until read-only inspection of that installed version
confirms the server-side submission lifecycle, durable saved-entry ID, callback failure
semantics, and supported saved-entry read API. Current Avada documentation is not
authority for those version-specific facts.

## Avada field mapping

| Avada `Contacto` field | CRM intake field | Mapping rule |
| --- | --- | --- |
| `nombre_&_apellido` | `name` | Trimmed, required |
| `telefono` | `phone` | Trimmed; blank becomes `null` or is omitted |
| `email` | `email` | Trimmed; blank becomes `null` or is omitted |
| `mensaje` | `message` | Preserve text; blank becomes `null` or is omitted |

The connector must also supply the required `external_submission_id`. It must not send
`source`; the CRM route assigns `WEB`. It must not invent `company` or `province` values.

## Installed Avada 7.7.1 inspection gate

An authorized production operator must run this inspection over SSH with a shell user
that can read WordPress code but cannot write WordPress files or the database. Do not
submit a form, invoke an AJAX action, use WP-CLI commands that bootstrap WordPress, or
query entry rows. Set `WP_ROOT` to the already known, explicit WordPress document root;
do not discover it by scanning `/`.

```bash
WP_ROOT=/absolute/production/wordpress/root
test -r "$WP_ROOT/wp-content/themes/Avada/style.css"
test -d "$WP_ROOT/wp-content/plugins/fusion-builder"

rg -n -m 1 '^[[:space:]]*Version:' \
  "$WP_ROOT/wp-content/themes/Avada/style.css"
rg -n -m 1 '^[[:space:]]*Version:' \
  "$WP_ROOT/wp-content/plugins/fusion-builder"

rg -n -C 12 -F 'fusion_form_submission_data' \
  "$WP_ROOT/wp-content/themes/Avada" \
  "$WP_ROOT/wp-content/plugins/fusion-builder"
rg -n -C 12 -F 'awb_custom_form_actions' \
  "$WP_ROOT/wp-content/themes/Avada" \
  "$WP_ROOT/wp-content/plugins/fusion-builder"
```

The second version command intentionally receives a directory: `rg` must report the
plugin file containing the installed Fusion Builder version header. Record each result
as `file:line` plus a SHA-256 hash of that source file, calculated as follows after
replacing the placeholder with the exact reported file. Do not copy `wp-config.php`,
logs, uploads, database dumps, form entries, or secrets into the audit evidence.

```bash
shasum -a 256 /absolute/reported/source-file.php
```

After locating the hook occurrences, trace only the installed PHP source with the
following searches. Expand context around each relevant result with `rg -n -C 30`; do
not infer behavior from symbol names alone.

```bash
rg -n 'wp_ajax(_nopriv)?_|do_action\(|apply_filters\(|wp_send_json|send_json' \
  "$WP_ROOT/wp-content/plugins/fusion-builder"
rg -n 'validat|save.*database|database.*save|notification|wp_mail|mail\(' \
  "$WP_ROOT/wp-content/plugins/fusion-builder"
rg -n '\$wpdb->insert|insert_id|entry_id|submission_id|form.*entr' \
  "$WP_ROOT/wp-content/plugins/fusion-builder"
rg -n 'register_rest_route|WP_Query|get_posts|get_post_meta|SELECT|prepare\(' \
  "$WP_ROOT/wp-content/plugins/fusion-builder"
rg -n 'retention|expiration|expire|delete|trash|cron|wp_schedule' \
  "$WP_ROOT/wp-content/plugins/fusion-builder"
```

The inspection report must quote no submission values and must establish, with
`file:line` evidence:

1. Whether each candidate hook exists and the exact arguments at its invocation.
2. The registered AJAX callback and every called method from validation through the
   final AJAX response.
3. The actual order of validation, database persistence, email notification, candidate
   hooks, and success/error response construction.
4. The statement that creates the durable entry ID, its value immediately after insert,
   and whether that value is passed to or recoverable by either hook.
5. Every return value or exception/error path from a callback and whether it can alter
   persistence, email delivery, or the browser response.
6. The installed admin/service method, REST route, or parameterized query used to read
   a saved entry. A guessed table name or direct unparameterized SQL is not acceptable.
7. Every explicit entry deletion, scheduled cleanup, retention setting, and uninstall
   path. If no automatic retention path exists, report only that none was found in the
   inspected source; do not interpret that as a permanent-retention guarantee.

The preferred ID `avada:contacto:33:<saved-entry-id>` can be approved only if this trace
proves that the ID is durable, belongs to the successfully saved form entry, is exposed
at a post-persistence server-side callback, and remains available for retry lookup. If
any condition fails, implementation requires a connector-owned durable delivery record
with its own opaque UUID, the immutable serialized CRM body, attempt state, and
timestamps; the stable external ID is then
`avada:contacto:33:<delivery-uuid>` and contains no PII. That durable record is the
smallest safe fallback and must be specified with restricted access and bounded
retention before connector implementation.

## Production configuration

Production connection is also gated by completion of CRM-017 and its reverse-proxy,
TLS, shared rate-limit, body-limit, trusted-forwarding, secret-delivery, and staging
smoke requirements. Until then, `/api/intake/web` must not be exposed by deploying the
development Compose topology or publishing the backend directly to the Internet.

- Keep `WEB_INTAKE_SIGNING_SECRET` only in the WordPress server and backend secret
  stores. Use independent values per environment and TLS for every production request.
- Send `X-FAA-Intake-Timestamp` as current Unix seconds and
  `X-FAA-Intake-Signature` as the CRM-002 `sha256=` HMAC. Do not reformat JSON after
  signing.
- Derive one stable `external_submission_id` from the durable Avada submission record
  and reuse it on timeout/retry. Never generate a new ID for a transport retry. The
  preferred candidate `avada:contacto:33:<saved-entry-id>` is not approved until the
  installed 7.7.1 source proves the saved-entry ID boundary.
- Keep the Avada Save To Database action and email notification enabled and independent
  of CRM delivery. A CRM failure must be visible to operations without changing the
  browser result or suppressing the normal FAA email notification.

## Deployment validation

1. Verify the production URL, trusted host, TLS certificate, clock synchronization,
   secret injection and database migration `0007_crm_commercial_completion`.
2. Exercise exact-body HMAC with a synthetic payload. Confirm a stale timestamp and a
   one-byte body change both return generic `401` and create no Customer/Opportunity.
3. Retry the accepted payload with the same external ID and bytes: expect `200` with
   `created=false` and the same IDs. Change the payload under that ID: expect `409`
   and no second Customer/Opportunity.
4. Confirm the Avada entry is saved and the original email arrives for both a successful
   CRM submission and a simulated CRM transport failure. Verify the WordPress retry
   queue preserves bytes and external ID.
5. Soft-delete the synthetic smoke Customer/Opportunity through normal CRM operations;
   retain intake evidence. Never use real customer data for smoke tests.

The optional backend tool refuses non-HTTPS endpoints and requires an explicit phrase:

```bash
WEB_INTAKE_SIGNING_SECRET='from-secret-store' \
python -m app.scripts.smoke_wordpress_intake \
  --endpoint https://crm.example.com/api/intake/web \
  --confirm-production I-CONFIRM-SYNTHETIC-PRODUCTION-INTAKE
```

## Monitoring and rollback

Monitor counts and rates by safe outcome only: accepted (`201`), replay (`200`),
authentication/stale signature (`401`), changed replay (`409`), validation (`422`),
server/database failure (`5xx`) and transport timeout in WordPress. Alert on sustained
authentication failures, any `5xx` burst, retry backlog growth, missing Avada entries,
or missing Avada email notifications.
Logs and alerts must not contain request bodies, identity fields, signatures, secrets,
or full HMAC headers.

Rollback WordPress delivery to email-only by disabling the CRM hook while preserving
the retry records and stable external IDs. Do not rotate the secret as a rollback
mechanism unless compromise is suspected. Backend rollback follows the normal release
procedure; confirm no migration downgrade is attempted while CRM-012 data exists.
