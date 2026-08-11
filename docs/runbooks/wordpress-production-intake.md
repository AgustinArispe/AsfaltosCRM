# WordPress production intake runbook

CRM-012 does not change the CRM-002 contract. WordPress/Contact Form 7 must send the
exact UTF-8 JSON bytes to `POST /api/intake/web`; the timestamp and signature headers
must be calculated from those same bytes after serialization.

## Production configuration

- Keep `WEB_INTAKE_SIGNING_SECRET` only in the WordPress server and backend secret
  stores. Use independent values per environment and TLS for every production request.
- Send `X-FAA-Intake-Timestamp` as current Unix seconds and
  `X-FAA-Intake-Signature` as the CRM-002 `sha256=` HMAC. Do not reformat JSON after
  signing.
- Derive one stable `external_submission_id` from the CF7 submission and reuse it on
  timeout/retry. Never generate a new ID for a transport retry.
- Keep CF7 email delivery enabled and independent of CRM delivery. A CRM failure must
  be visible to operations without suppressing the normal FAA email notification.

## Deployment validation

1. Verify the production URL, trusted host, TLS certificate, clock synchronization,
   secret injection and database migration `0007_crm_commercial_completion`.
2. Exercise exact-body HMAC with a synthetic payload. Confirm a stale timestamp and a
   one-byte body change both return generic `401` and create no Customer/Opportunity.
3. Retry the accepted payload with the same external ID and bytes: expect `200` with
   `created=false` and the same IDs. Change the payload under that ID: expect `409`
   and no second Customer/Opportunity.
4. Confirm the original CF7 email arrives for both a successful CRM submission and a
   simulated CRM transport failure. Verify the WordPress retry queue preserves bytes
   and external ID.
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
authentication failures, any `5xx` burst, retry backlog growth, or missing CF7 email.
Logs and alerts must not contain request bodies, identity fields, signatures, secrets,
or full HMAC headers.

Rollback WordPress delivery to email-only by disabling the CRM hook while preserving
the retry records and stable external IDs. Do not rotate the secret as a rollback
mechanism unless compromise is suspected. Backend rollback follows the normal release
procedure; confirm no migration downgrade is attempted while CRM-012 data exists.
