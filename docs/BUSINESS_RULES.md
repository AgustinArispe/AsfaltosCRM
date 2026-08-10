# Reglas de negocio — FAA CRM

Este documento es la fuente permanente de las reglas comerciales del CRM. Describe
qué comportamiento debe respetar el producto; `AGENTS.md` define cómo desarrollar el
software. Una regla de negocio sólo cambia por solicitud explícita del usuario, nunca
por conveniencia técnica.

## Producto

- El CRM es exclusivo para Fábrica Argentina de Asfaltos (FAA).
- Es una aplicación interna de escritorio y desktop-first.
- No existe un requisito de aplicación móvil dedicada.
- Sólo se requiere responsive básico para evitar roturas en pantallas pequeñas.
- La experiencia debe ser simple, rápida, clara, visual y con bajo ruido.

## Usuarios

- Los roles existentes son `SUPERVISOR` y `VENDEDOR`.
- Todos los usuarios pueden ver todas las oportunidades. No existe visibilidad
  restringida por vendedor.
- `assigned_user_id` puede identificar al responsable de una oportunidad, pero no
  controla su visibilidad.
- Los roles siguen controlando las acciones administrativas ya implementadas.
- No introducir nuevas restricciones de visibilidad.

## Customers

- Un `Customer` puede tener múltiples `Opportunities`.
- Sus campos principales son `name`, `company`, `email`, `phone` y `province`.
- El soft delete conserva el historial.
- Un cliente eliminado no puede usarse para crear nuevas oportunidades, pero su
  historial comercial válido continúa disponible.
- `legendary_historical_override` permite marcar manualmente como Legendarios a
  clientes históricos.

## Legendario

- La regla automática, a implementar en el futuro, considera Legendario a un cliente
  que tuvo al menos dos oportunidades `GANADA` por año durante tres años calendario
  consecutivos.
- Una vez que existe cualquier secuencia histórica válida de tres años consecutivos,
  el cliente mantiene la condición de Legendario.
- `legendary_historical_override` también convierte al cliente en Legendario.
- No implementar gamificación adicional.

## Opportunities

- Una `Opportunity` pertenece a un `Customer`.
- El pipeline principal es `NUEVA` → `COTIZADA` → `NEGOCIACION` → `GANADA`.
- `PERDIDA` es un estado terminal, pero no una columna principal del Kanban.
- Para la operación normal, `GANADA` y `PERDIDA` son estados terminales.
- Las transiciones ordinarias respetan el orden del pipeline; los estados no pueden
  saltarse arbitrariamente. Cualquier estado abierto puede pasar a `PERDIDA` según las
  reglas de pérdidas.
- La creación y cada cambio de estado se registran en el historial.
- `current_status_entered_at` indica cuándo la oportunidad ingresó en su estado actual.

## Cotizaciones

- El CRM no genera presupuestos comerciales. FAA los prepara por fuera del CRM.
- Para pasar de `NUEVA` a `COTIZADA` se debe registrar al menos un producto y su
  cantidad positiva en kilogramos. Una cotización puede incluir múltiples productos.
- El CRM conserva únicamente la cotización vigente o final; no existe historial de
  versiones.
- Los productos y cantidades cotizados no pueden modificarse en `GANADA` ni
  `PERDIDA`.

## Products

- FAA tiene aproximadamente diez productos.
- Los productos pueden activarse y desactivarse, pero no se eliminan físicamente.
- Un producto inactivo no puede agregarse a una nueva cotización.
- Los productos inactivos continúan apareciendo en el historial y las métricas.
- Por ahora, los productos no tienen precios, SKU, stock ni categorías comerciales.

## Pérdidas

- Una oportunidad puede pasar a `PERDIDA` desde `NUEVA`, `COTIZADA` o `NEGOCIACION`.
- `NUEVA` → `PERDIDA` es válida sin productos cotizados.
- Los motivos actuales son `PRECIO`, `SIN_RESPUESTA`, `COMPETENCIA`,
  `PROYECTO_CANCELADO` y `OTRO`.
- Las oportunidades perdidas no aparecen en el Kanban principal, pero permanecen
  disponibles para búsqueda, historial y métricas.
- Si existía una cotización, se conserva al marcar la oportunidad como perdida.

## Notificaciones

- Una oportunidad en `NUEVA`, `COTIZADA` o `NEGOCIACION` que permanece catorce días
  o más sin cambiar de estado genera una notificación interna.
- No se envían notificaciones por email.
- Las notificaciones son globales para el equipo y registran `read_at` y
  `resolved_at`.
- Una notificación se resuelve cuando la oportunidad cambia de estado.
- Editar productos cotizados o el responsable no resuelve la notificación.

## Métricas

- La tasa de conversión por oportunidades es `GANADAS / (GANADAS + PERDIDAS)`.
- La tasa de conversión por volumen es
  `kg GANADOS / (kg GANADOS + kg PERDIDOS)`.
- Si el denominador de una tasa es cero, el resultado es `null`.
- También se utilizan kilogramos cotizados, ganados, perdidos y abiertos; productos
  más consultados y vendidos; conversión por producto; leads por origen; distribución
  por provincia; timeline; y snapshot del pipeline.
- Las métricas se calculan en el backend. El frontend sólo las visualiza.

## Lead Intake Web

- El formulario web puede crear un `Customer` o identificar uno existente.
- Cada submission válido y nuevo crea una `Opportunity` en `NUEVA`, con `source=WEB`
  y `assigned_user_id=NULL`.
- La idempotencia es obligatoria: reintentar el mismo submission no debe duplicar la
  oportunidad.
- El matching de clientes es conservador por email y teléfono; no se usa fuzzy
  matching.
- Los datos existentes del cliente no se sobrescriben. El intake sólo completa campos
  vacíos.
- `lead_intakes` conserva el snapshot del submission y su `message`.

## WhatsApp — objetivo

WhatsApp pasa a ser un módulo principal del CRM. Debe permitir:

- recibir mensajes de clientes y mostrar las conversaciones dentro del CRM;
- responder desde el CRM;
- asociar conversaciones a un `Customer` y relacionarlas con una `Opportunity` cuando
  corresponda;
- priorizar conversaciones que esperan respuesta;
- soportar mensajes de texto, imágenes y PDFs u otros documentos.

El frontend nunca se comunica directamente con Meta. Toda comunicación pasa por
FastAPI.

## WhatsApp — nuevos contactos

- Cuando escribe por primera vez un número desconocido, se resuelve el `Customer` de
  forma conservadora por teléfono y se crea si no existe.
- También se crea una conversación y, cuando se trata de un nuevo contacto comercial,
  una `Opportunity` en `NUEVA` con `source=WHATSAPP`.
- Los mensajes posteriores de la misma conversación no crean oportunidades nuevas
  automáticamente. No se crea una oportunidad por cada mensaje.

## WhatsApp — mensajería

- Se deben soportar las direcciones `INBOUND` y `OUTBOUND`.
- Los tipos iniciales son `TEXT`, `IMAGE` y `DOCUMENT`.
- Inicialmente no se implementan audio, stickers, ubicación, contactos ni video. El
  video requiere una decisión posterior.
- Cada mensaje conserva su ID externo, dirección, estado, timestamps de envío,
  entrega, lectura y fallo, y metadata del attachment cuando corresponda.

## WhatsApp — respuesta rápida

Responder rápido es una prioridad del negocio. El CRM debe distinguir:

- conversaciones no leídas;
- conversaciones esperando respuesta;
- tiempo desde el último mensaje inbound;
- tiempo hasta la primera respuesta.

Estas métricas podrán visualizarse más adelante.

## WhatsApp — ventana y templates

- La integración debe respetar las reglas vigentes de WhatsApp Business Platform.
- Dentro de la ventana permitida se puede responder según las reglas de Meta.
- Fuera de la ventana, el CRM debe usar templates aprobados cuando corresponda.
- El frontend no puede ignorar estas restricciones.
- Meta/WhatsApp es la fuente de verdad para templates, estados y políticas de
  mensajería.

## WhatsApp — marketing y broadcast

- El CRM no crea campañas de marketing. El equipo de marketing diseña el contenido y
  la campaña fuera del CRM.
- El CRM puede seleccionar contenido o templates ya preparados, seleccionar
  destinatarios válidos, enviar mediante WhatsApp, registrar trazabilidad y mostrar
  resultados enviados, entregados, leídos y fallidos.
- No se crea un editor creativo, constructor de campañas ni generador de contenido de
  marketing.
- Internamente puede existir un concepto `Broadcast` o `Send Batch` para representar
  el envío ejecutado desde el CRM.

## WhatsApp — consentimiento

- Los envíos de marketing deben respetar opt-in y opt-out.
- No se envían campañas a contactos sin autorización válida.
- La persistencia exacta del consentimiento se definirá al diseñar el módulo.

## WhatsApp — tiempo real

- No introducir infraestructura pesada inicialmente.
- La primera estrategia preferida es polling eficiente.
- SSE o WebSocket pueden evaluarse más adelante si la experiencia lo requiere.
- No agregar Redis ni Celery únicamente por mensajería.

## WhatsApp — provider

- La integración debe estar desacoplada del proveedor concreto.
- El dominio y la aplicación no dependen directamente de requests HTTP a Meta.
- Debe existir una abstracción equivalente a `WhatsAppProvider`, con una futura
  implementación `MetaCloudApiProvider`.
- Durante desarrollo y tests puede existir un `FakeWhatsAppProvider` para construir y
  validar gran parte del módulo sin credenciales reales.

## WordPress

- WordPress y Contact Form 7 (CF7) existen en FAA.
- La integración web es server-to-server.
- CF7 mantiene el email actual y, adicionalmente, envía el lead al CRM.
- La integración exacta con WordPress se implementará posteriormente.
