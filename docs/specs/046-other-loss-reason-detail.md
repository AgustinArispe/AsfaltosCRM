# CRM-046 — Other Loss Reason Detail

Status: Approved
Owner: FAA CRM team
Last updated: 2026-09-17
Implementation commit: N/A

## Goal

Permitir que vendedores y supervisores expliquen una pérdida cuando seleccionan el
motivo `OTRO`, conservando ese texto como evidencia auditable del episodio y
mostrándolo en el detalle e historial de la oportunidad.

## Context and authority

El usuario aprobó explícitamente que el texto se guarde permanentemente y se muestre
en el detalle y en el historial. Esta spec amplía CRM-001, CRM-012, CRM-020 y CRM-024
sólo para el detalle del motivo `OTRO`; no cambia estados, transiciones, permisos ni
métricas por categoría.

## Scope

- Agregar `loss_reason_detail` nullable a la oportunidad actual y a cada episodio
  inmutable de pérdida mediante una migración Alembic.
- Exigir texto Unicode plano, recortado, no vacío y de hasta 500 caracteres cuando
  `loss_reason=OTRO` en nuevas transiciones a `PERDIDA`.
- Rechazar `loss_reason_detail` para cualquier motivo distinto de `OTRO`.
- Conservar el detalle en `OpportunityLossEvent` al reabrir; limpiar sólo la proyección
  actual de `Opportunity` junto con `loss_reason`.
- Extender los contratos tipados de request y response para transportar el detalle y
  exponer los episodios de pérdida dentro del detalle de oportunidad.
- Mostrar un textarea condicional, etiquetado y con error asociado en el flujo
  `Marcar como perdida`.
- Mostrar el texto junto a `Otro` en el resumen de pérdida actual y en cada episodio
  de pérdida del historial de la oportunidad.
- Mantener el Lost workspace categorizado por el enum `OTRO`; el texto libre no agrega
  filtros, agrupaciones ni métricas nuevas.

## Non-goals

- Agregar o renombrar motivos de pérdida.
- Permitir texto libre para `PRECIO`, `SIN_RESPUESTA`, `COMPETENCIA` o
  `PROYECTO_CANCELADO`.
- Convertir el detalle en HTML, Markdown, una nota editable o un campo buscable.
- Editar un episodio de pérdida después de confirmarlo.
- Cambiar reapertura, pipeline, permisos, notificaciones o cálculos de Dashboard.

## Data and API contract

- `opportunities.loss_reason_detail` y
  `opportunity_loss_events.loss_reason_detail` son `TEXT NULL`.
- La base de datos garantiza que el detalle sólo existe con motivo `OTRO` y que toda
  nueva escritura de dominio respeta la obligatoriedad. La migración identifica filas
  `OTRO` anteriores con el texto explícito `Detalle no registrado (pérdida anterior)`
  antes de activar la restricción.
- `POST /opportunities/{id}/lose` acepta `loss_reason_detail`; Pydantic rechaza campos
  extra, detalle vacío, detalle mayor a 500 caracteres y combinaciones incompatibles.
- `OpportunityDetail` expone el detalle actual y una lista ordenada de episodios con
  `status_history_id`, motivo, detalle y timestamp, suficiente para presentar la
  evidencia junto a la transición correspondiente.
- Las respuestas del Lost workspace exponen el detalle del episodio actual para que el
  contrato no pierda información, aunque la lista compacta no está obligada a mostrarlo.

## Accessibility and UX

- Elegir `OTRO` revela un `textarea` nativo con label persistente, `required`, límite
  visible de 500 caracteres y ayuda asociada.
- Cambiar desde `OTRO` a otro motivo limpia el borrador de detalle para impedir enviar
  una combinación inválida.
- Un detalle faltante o inválido mantiene abierto el modal, marca solamente el campo
  correspondiente con `aria-invalid`, asocia el error mediante `aria-describedby` y
  mueve el foco al campo cuando corresponde.
- La confirmación pending conserva motivo y texto, bloquea duplicados y no anuncia
  éxito antes de la respuesta autoritativa.

## Acceptance criteria

- AC-01: `OTRO` revela un campo de texto accesible; los demás motivos no lo muestran.
- AC-02: frontend y backend rechazan `OTRO` sin detalle no vacío y rechazan detalle
  con cualquier otro motivo.
- AC-03: el detalle se recorta, conserva saltos de línea como texto plano y nunca
  supera 500 caracteres.
- AC-04: una pérdida exitosa persiste el mismo detalle en la oportunidad actual y en
  su episodio inmutable.
- AC-05: reabrir limpia el detalle actual pero preserva el episodio; una pérdida
  posterior crea otro episodio independiente con su propio detalle.
- AC-06: el detalle actual aparece junto a `Otro` y cada episodio aparece vinculado a
  su transición en Activity/historial.
- AC-07: la migración actualiza de forma explícita los registros `OTRO` anteriores y
  su downgrade es reversible.
- AC-08: tests de modelos, servicio, API, frontend y migración cubren combinaciones
  válidas e inválidas, reapertura, historial, errores y accesibilidad.
- AC-09: Ruff, mypy strict, pytest/coverage, Alembic, frontend tests/build, npm audit y
  Docker Compose health checks pasan antes de commit o push.

## Open decisions

None.
