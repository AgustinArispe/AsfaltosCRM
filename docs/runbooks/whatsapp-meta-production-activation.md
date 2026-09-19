# Activación productiva de Meta WhatsApp

Este runbook activa la integración ya implementada sin colocar secretos en el
repositorio, logs, tickets, capturas ni comandos. Requiere que CRM-049 esté aprobado y
que se use una conversación/contacto de prueba controlado por FAA.

## Alcance y condiciones previas

- No activar si el backend no tiene un dominio público HTTPS estable.
- No activar si el volumen persistente para medios no está montado en el backend.
- No ejecutar mensajes, templates ni Broadcasts contra contactos comerciales durante
  la verificación.
- Antes de cambiar configuración, registrar sólo el identificador del deployment, la
  hora UTC y el operador autorizado; nunca valores de variables ni capturas de ellos.

## Railway: backend

En el servicio backend de producción, configurar las variables ya soportadas. Los
nombres son los contratos de configuración; los valores se cargan únicamente en la UI
segura de Railway.

| Grupo | Variables |
| --- | --- |
| Runtime | `APP_ENVIRONMENT`, `DATABASE_URL`, `JWT_SECRET`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `WEB_INTAKE_SIGNING_SECRET`, `STALE_OPPORTUNITY_DAYS` |
| WhatsApp | `WHATSAPP_PROVIDER`, `WHATSAPP_DEV_ROUTES_ENABLED`, `WHATSAPP_MEDIA_STORAGE`, `WHATSAPP_MEDIA_STORAGE_ROOT`, `WHATSAPP_IMAGE_MAX_BYTES`, `WHATSAPP_DOCUMENT_MAX_BYTES`, `WHATSAPP_IMAGE_MIME_TYPES`, `WHATSAPP_DOCUMENT_MIME_TYPES`, `WHATSAPP_BROADCAST_BATCH_SIZE`, `WHATSAPP_BROADCAST_CLAIM_TIMEOUT_SECONDS` |
| Meta | `META_GRAPH_API_VERSION`, `META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID`, `META_WABA_ID`, `META_WEBHOOK_VERIFY_TOKEN`, `META_APP_SECRET`, `META_REQUEST_TIMEOUT_SECONDS`, `META_RETRY_MAX_ATTEMPTS`, `META_RETRY_BASE_SECONDS`, `META_RETRY_MAX_SECONDS` |

Set `WHATSAPP_PROVIDER` to `meta`, `WHATSAPP_MEDIA_STORAGE` to `filesystem`, and
disable development routes. Railway supplies `PORT`; the backend image uses it and
falls back to its local-development port only when it is absent.

Attach one Railway Volume to the backend service. Its mount path and
`WHATSAPP_MEDIA_STORAGE_ROOT` must be the same absolute path. Confirm that the service
account can write there before enabling webhook traffic. Keep this volume attached
across deployments and include it in the existing backup/recovery procedure.

Deploy once and verify backend readiness plus the absence of `/docs`, `/redoc`, and
`/openapi.json`. Startup must fail closed for missing/invalid Meta variables; do not
work around a startup failure by changing source code or weakening validation.

## Meta Business configuration

1. Confirm that the selected App, WABA, and Phone Number ID are the intended FAA
   production resources and that the App is eligible for live traffic.
2. Configure the callback URL as
   `https://<FAA-backend-host>/api/whatsapp/provider/webhook`.
3. Supply the same private verify token held in the Railway backend variable and
   complete Meta's GET subscription challenge.
4. Subscribe the WABA/App to the `messages` webhook field, which carries incoming
   messages and delivery/read/failure status notifications.
5. Confirm the configured access token has the minimum Meta permissions needed for
   sending, media, and template discovery for this WABA. Do not copy it into a local
   shell, source file, browser, or support request.
6. Confirm the controlled utility/human template and any approved marketing templates
   required for later Broadcast use are present and approved in the selected WABA.

## Controlled smoke test

Perform these steps in order, waiting for the listed evidence before continuing:

1. Request the public backend health endpoint and confirm Railway reports the current
   deployment healthy.
2. Complete Meta's callback verification and retain only the success timestamp and
   deployment ID.
3. From the controlled test number, send one text to FAA's configured number. Confirm
   one Inbox conversation/message appears; repeat the same provider delivery only when
   Meta's test tooling supports replay, then confirm no duplicate message,
   conversation, Customer, or Opportunity was created.
4. Send one controlled image or PDF. Confirm attachment metadata appears without a
   public provider URL; open it through the authenticated Inbox and confirm it remains
   available after a controlled backend redeploy.
5. Reply with free-form text while the backend indicates the 24-hour window is open.
   Confirm the existing status transitions appear as Meta sends `sent`, `delivered`,
   and `read` notifications.
6. Use a controlled conversation whose window is closed. Confirm the composer blocks
   free-form text and permits only the existing approved-template flow. Send one
   approved controlled template if allowed by Meta configuration.
7. Force no failures. If Meta naturally reports a safe `failed` test event, confirm it
   appears in the existing Inbox status model without revealing raw provider details.
8. Review Railway application/proxy logs and browser UI for the prohibited data listed
   in CRM-049. Do not export raw webhook payloads, signatures, tokens, media URLs, or
   customer data as evidence.

Stop after the controlled checks. Broadcast execution remains its existing explicit,
consent-gated workflow and is not part of activation smoke testing.

## Rollback

1. In the Railway backend service, change only `WHATSAPP_PROVIDER` to `disabled` and
   deploy the staged configuration.
2. Confirm the backend is healthy and `/api/whatsapp/provider/webhook` plus all
   `/api/whatsapp` routes return the normal `404` response.
3. Disable or remove the Meta webhook subscription/callback only after the backend
   rollback is healthy, so any temporary redelivery cannot reach a partially changed
   service.
4. Do not delete the media volume, database records, templates, or provider settings
   during rollback. They are needed for investigation and a later controlled retry.
5. Record the deployment ID, UTC rollback time, safe failure category, and follow-up
   owner. Rotate a credential only through Meta/Railway if there is evidence it was
   exposed; never place either old or new value in the incident record.

## Credential rotation

Create the replacement secret in the appropriate Meta/Railway control plane, stage it
as a service variable, deploy, repeat the handshake and controlled text smoke test,
then revoke the previous Meta credential. Record timestamps and actor only.
