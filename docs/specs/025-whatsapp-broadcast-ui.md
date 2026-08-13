# CRM-025 — Interfaz de Envíos WhatsApp

Status: Draft
Owner: FAA CRM team
Last updated: 2026-08-13
Implementation commit: N/A

## Goal

Proveer una interfaz FAA CRM segura, sobria y auditable para ejecutar y seguir
envíos masivos de WhatsApp a partir de contenido de marketing ya preparado y
aprobado fuera del CRM.

La interfaz debe dejar claro que el CRM ejecuta una comunicación aprobada: no crea
campañas, copy, creatividades, aprobaciones ni templates de Meta.

## Context

`docs/BUSINESS_RULES.md` permite seleccionar contenido/template ya preparado,
elegir destinatarios válidos, enviar y mostrar trazabilidad y resultados, siempre
respetando opt-in y opt-out. CRM-011 implementa el dominio, consentimiento,
validación, inmutabilidad, procesamiento acotado, reintentos y proyecciones de
Broadcast. CRM-018 es obligatorio para toda decisión visual, interacción,
accesibilidad, responsive y arquitectura de frontend de esta especificación.

La UI existente es React/Vite/TypeScript/Tailwind, con router interno, módulos API
tipados, `AppShell` y media WhatsApp autenticada. Aún no tiene destino ni feature
de Broadcast. CRM-011 ofrece el ciclo seguro, pero sus proyecciones actuales tienen
los gaps de edición, validación y paginación registrados en esta spec.

## Dependencies

- CRM-008 — WhatsApp Media Storage
- CRM-010 — WhatsApp Inbox Frontend
- CRM-011 — WhatsApp Broadcast Execution
- CRM-013 — Concurrency Hardening
- CRM-016 — Security Hardening
- CRM-018 — Frontend Design System
- CRM-021 — Dashboard & Metrics
- CRM-023 — WhatsApp Inbox 2.0

## Scope

- Un destino de sidebar y workspace de **Envíos WhatsApp** para historial, creación,
  ejecución y detalle de Broadcasts.
- Historial compacto de ejecuciones con estado, fechas, template/contenido,
  destinatarios y resumen de resultados disponible.
- Flujo progresivo de selección de inputs preparados, Customers explícitos y
  validación de elegibilidad.
- Confirmación deliberada, inputs inmutables después de confirmar, inicio y
  seguimiento conforme al procesador acotado de CRM-011.
- Detalle auditable de outcomes, destinatarios, errores seguros e intentos históricos
  bajo demanda.
- Carga, fallos, polling, accesibilidad, zoom y rendimiento coherentes con CRM-018.

## Non-goals

- Crear campañas, redactar copy, diseñar creatividades, aprobar contenido o editar
  templates de Meta/proveedor.
- Editor o catálogo persistente de templates, constructor de audiencias, segmentación,
  audiencias guardadas, selección inferida, filtros por vendedor o programación no
  respaldada por backend.
- Cambiar consentimiento, estados, semántica del procesador, permisos, proveedor,
  contratos de Inbox, ni enviar email/SMS.
- Analítica comercial, atribución, conversión o ROI. CRM-021 puede resumir salud
  operativa después; CRM-025 es dueño de ejecución y detalle.
- Rediseñar Inbox, mostrar payloads provider/storage URLs, o hacer que un Broadcast
  parezca una respuesta humana.
- Rediseño mobile específico, WebSocket/SSE, browser-side dispatch loops o
  virtualización sin medición.

## Product boundary and visual direction

El encabezado y el flujo separan visualmente dos responsabilidades:

| Preparado fuera del CRM | Ejecutado dentro de FAA CRM |
| --- | --- |
| campaña, copy, creatividad, aprobación y template Meta | selección de template utilizable, parámetros/medio aprobados, Customers explícitos, validación, confirmación, inicio y trazabilidad |

El módulo usa CRM-018: IBM Plex Sans, superficies neutras cálidas, información densa
y silenciosa, geometría redondeada contenida y tokens semánticos Light/Dark/System.
Amarillo FAA enfatiza siguiente paso seguro, confirmación y progreso, nunca superficies
grandes ni texto blanco sin contraste. Rojo queda para fallos reales o advertencias
destructivas. Estado siempre combina texto, icono/forma y color.

Debe sentirse serio, controlado, simple y auditable; no como marketing automation.
Reutiliza los primitives CRM-018 para controles, feedback, tablas, diálogos, focus y
temas, sin sustitutos feature-locales.

## Navigation and default workspace

`Envíos WhatsApp` es el rótulo de sidebar: es más claro que `Envíos` en una futura
aplicación multicanal. Es un destino propio, al nivel de `WhatsApp`, no una vista
dentro del Inbox ni una alteración de su selección de conversaciones.

La ruta futura `/whatsapp-sends` abre historial de ejecuciones recientes y la acción
primaria `Nuevo envío`. Cada fila/tarjeta compacta presenta etiqueta, nombre
amigable e idioma de template, estado, creado/confirmado/iniciado cuando existan,
total de Customers y outcomes aceptado/enviado/entregado/leído/fallido/desconocido
cuando la proyección backend exista. No muestra cada Recipient por defecto.

Sólo se agregan búsqueda o filtros server-side que los contratos respalden. Abrir una
ejecución conserva el contexto de historial. Un Draft puede retomarse; uno confirmado
abre en modo lectura/operación y sus inputs están inequívocamente bloqueados.

## Creation flow

La creación es una secuencia progresiva, no un formulario gigante: pasos numerados,
un resumen persistente y una única siguiente acción segura. Volver conserva el trabajo
seguro del Draft; abandonar/cerrar pide confirmación sólo ante cambios sin guardar. El
contrato aprobado determinará cuándo se crea el recurso persistente y cómo se editan
sus inputs mientras sigue en `DRAFT`.

1. **Contenido preparado.** Elegir un template marketing informado por backend como
   actualmente utilizable. Explicar que fue preparado/aprobado fuera del CRM, sin
   control de edición ni aprobación.
2. **Parámetros y encabezado.** Solicitar sólo valores soportados/requeridos y el medio
   de header si corresponde, con etiquetas claras y validación inline. Un preview de
   sustitución sólo aparece si el backend entrega uno seguro y autoritativo; jamás se
   infiere copy o personalización por Customer.
3. **Customers.** Buscar y seleccionar Customers explícitamente mediante filas compactas
   y acción clara de agregar/quitar; el conteo seleccionado es siempre visible.
4. **Consentimiento y elegibilidad.** Revisar categorías comprensibles: aptos, sin
   opt-in válido, teléfono ausente/inválido, teléfono normalizado duplicado, Customer
   no disponible y otros motivos backend aprobados. Los inelegibles permanecen visibles
   con explicación segura y no pueden enviarse.
5. **Resumen final.** Releer template, idioma, parámetros, medio, referencia externa,
   total seleccionado, aptos, excluidos/bloqueantes y advertencias. Declarar que un
   conjunto broadcast-level aplica igual a todos; CRM-011 no admite interpolación
   por destinatario.
6. **Confirmar.** `Confirmar y bloquear envío` usa token/version de CRM-011. Enter
   desde campos no relacionados ni cerrar el diálogo no puede confirmarlo. Frase
   adicional sólo si investigación UX lo justifica.
7. **Iniciar.** Tras confirmar, `Iniciar procesamiento` ejecuta
   `CONFIRMED -> PROCESSING`; no promete entrega inmediata ni envía directamente.

La confirmación CRM-011 no es parcial. Antes de confirmar, `excluido` significa que
debe ajustarse explícitamente la selección: no que habrá un envío parcialmente
confirmado. Duplicados jamás producen otro Recipient o llamada provider.

## Template, parameters and header media

Meta/proveedor sigue siendo fuente de verdad. El selector sólo muestra la respuesta
fresca de `GET /broadcast-templates`; IDs externos nunca son información primaria.
Cada opción muestra nombre, idioma, categoría marketing, sendability, parámetros y
requisito/tipo de header que entregue el contrato. Consulta incompleta o fallida es
un estado no disponible: se bloquea la confirmación y cache nunca se presenta como
aprobación vigente.

Los parámetros son valores de ejecución del contenido aprobado. La UI exige exactamente
los nombres declarados, no presenta campos libres adicionales ni sugiere personalización
individual. Errores de formato/requerimiento se vinculan y anuncian junto al campo.

Para header image o PDF/document se reutiliza upload autenticado CRM-008: preview visual
de imagen con lectura autenticada y resumen de documento de nombre, tipo y tamaño seguro.
Antes de confirmar puede quitarse/reemplazarse bajo el contrato Draft aprobado. No se
exponen URLs provider/storage: `media_ref` es opaco y los bytes se leen por endpoint
CRM autenticado. MIME, tamaño, disponibilidad y compatibilidad siguen siendo backend.

## Recipient and consent model

Recipients son Customers explícitos, no teléfonos pegados, filtros comerciales ni
segmentos. La búsqueda usa debounce, resultados limitados/paginados, checkbox nativo y
un panel/lista de selección acotado. En cantidades grandes, resultados y seleccionados
usan scroll contenido y carga por página; no hay DOM de miles de filas ni
enriquecimiento por destinatario.

Backend vuelve a decidir consentimiento y elegibilidad. La UI muestra sólo estado y
evidencia mínima permitida para entender exclusiones, y no ofrece override de opt-in/
opt-out. El consentimiento pertenece al Customer y teléfono normalizado exactos; un
cambio de teléfono no lo transfiere. Opt-out posterior puede bloquear un pendiente
confirmado sin llamada provider y se presenta como `Bloqueado` con motivo seguro.

CRM-025 no es gestión genérica de consentimiento. Si no existe superficie aprobada para
registrar/revisar consentimiento desde Customer, la UI explica el requisito sin inventar
una corrección en Broadcast.

## Confirmation, execution and polling

Tras confirmar, parámetros, medio, template, etiqueta, referencia y destinatarios
adoptan lectura con indicador `Contenido y destinatarios bloqueados`. Para cambiar
cualquiera se crea un Broadcast nuevo, según CRM-011.

| Estado backend | Presentación operativa |
| --- | --- |
| `DRAFT` | Borrador pendiente de revisión y confirmación. |
| `CONFIRMED` | Confirmado y bloqueado; todavía no iniciado. |
| `PROCESSING` | Procesando por lotes; los resultados avanzan gradualmente. |
| `COMPLETED` | No hay Recipient listo/en progreso; pueden quedar fallidos, desconocidos o bloqueados. |

`POST /process` solicita sólo un lote limitado. La UI no itera ni paraleliza llamadas
hasta completar. Si el flujo operacional aprobado requiere operador, `Procesar
siguiente lote` muestra reclamados/completados/restantes; si el scheduler es dueño,
el detalle refleja estado persistido. La política concreta sigue abierta.

Polling es moderado, sólo para ejecución activa/detalle abierto, se pausa al ocultar la
página y cancela al cambiar de ejecución. Actualiza estado persistido sin reanimar o
reordenar lectura actual. Falla conserva último dato bueno, muestra `Actualización
pendiente` y hora del último dato, con retry acotado. Mutaciones conservan clave
idempotente durante retry, deshabilitan el trigger y nunca convierten duda de red en
segunda confirmación, inicio, proceso o retry.

## Broadcast detail and outcomes

El detalle presenta template, actor/timestamps, total/elegibles/excluidos cuando estén
disponibles, estado y progreso sobrio. Barra compacta o segmentos acompañan conteos
textuales de aceptados, enviados, entregados, leídos, fallidos, desconocidos y
bloqueados/saltados; no hay animación falsa ni finalización prematura.

La lista de Recipients carga bajo demanda, búsqueda/filtros server-side y filtros
limitados a `Todos`, exitosos entregados/leídos si aporta valor, `Fallidos`,
`Desconocidos` y `Bloqueados/saltados`. Cada fila presenta Customer, teléfono
enmascarado cuando corresponda, outcome, timestamps útiles, error/bloqueo seguro y
estado de retry. No presenta payloads, IDs provider ni URLs. A menor ancho/zoom conserva
columnas prioritarias y detalle de fila, sin overflow de página.

Intentos de `WhatsAppMessage` y auditoría se abren bajo demanda por Recipient o
Broadcast; no cargan ni dominan la vista inicial. El handoff a Inbox usa navegación
aprobada. Allí, los mensajes Broadcast se identifican como campaña/masivo si su
semántica lo requiere, nunca como respuesta humana ni como resolución de
`waiting_for_response`, conforme CRM-011/CRM-023.

## Failures, UNKNOWN and retries

La UI distingue fallo definitivo, bloqueado sin llamada provider y entrega incierta.
Sólo el último `FAILED` que backend declare elegible puede seleccionarse para retry
explícito. La acción explica que crea intento nuevo, conserva el anterior y vuelve a
validar consentimiento, template, medio y Customer. El resultado backend informa filas
aceptadas/rechazadas; el cliente no supone éxito.

`UNKNOWN` es `Entrega sin confirmar`, con riesgo de entrega duplicada. Nunca se
reintenta automática ni manualmente desde CRM-025; sólo evidencia posterior provider
puede reconciliarlo. Retry no se presenta como editar o reenviar mensaje humano y no
oculta historia.

## Frontend architecture, security and performance

- La futura ruta compone feature/page dentro de router y `AppShell` existentes.
  `frontend/src/api/whatsapp-broadcasts.ts` será dueño de contratos tipados; feature/
  hook será dueño de flujo, polling, cancelación, claves idempotentes, último dato bueno
  y traducción de errores. Componentes visuales reciben datos/callbacks, no hacen fetch
  ni aplican reglas de consentimiento.
- Reutiliza APIs Customers/media sólo en sus límites autorizados. No contacta Meta desde
  browser, guarda secretos, registra parámetros/teléfonos/medios sensibles en analytics
  cliente, ni construye URLs provider/storage. CRM-016 y CSP continúan.
- Listados usan cursor/paginación server-side. Abortan búsqueda/filtro/poll obsoleto,
  preservan contenido en refresh y evitan N+1, carga total de Message attempts,
  polling histórico o DOM ilimitado. Virtualización sólo tras medir necesidad.
- `409`, token/version vencido y validación son estados separados de red. El Draft
  recuperable se conserva cuando es seguro y se explica siguiente acción.

## Accessibility, responsive and motion

- Todo paso, búsqueda, checkbox, selector, quitar, revisión, diálogo y retry es
  operable con teclado, orden lógico, foco visible y nombre accesible. Cambios de
  resultados/selección tienen anuncios mesurados.
- Enter sólo avanza/ejecuta en control/formulario seguro; nunca confirma/inicia
  accidentalmente. Escape cierra overlay seguro o vuelve de paso sin perder Draft. El
  diálogo de confirmación recibe foco deliberado, explica inmutabilidad y restaura foco.
- Errores inline se asocian al campo; errores de operación se anuncian sin robar foco.
  Estados, progreso y errores tienen equivalente textual y no dependen de color.
- Desktop/laptop-first: CRM-018 1024 CSS px y zoom común hasta 200 %. Sidebar colapsa
  antes de comprimir, pasos responden al ancho y tablas/listas usan scroll contenido,
  reducción de columnas o detalle de fila; nunca overflow horizontal de página.
- Motion funcional de 150–220 ms, sin layout, loop ni falsa sensación de tiempo real.
  `prefers-reduced-motion` elimina movimiento espacial y deja datos disponibles.

## Backend and product gaps

- El listado Broadcast no incluye outcomes por fila. El historial requiere summary
  paginado por estado sin descargar detalles.
- `POST /validate` devuelve strings internos y `PUT /recipients` listas de IDs.
  Falta proyección tipada/segura/categorizada de elegibilidad, conteos, razones y fila
  afectada; frontend no debe reconstruir reglas ni exponer nombres internos.
- Templates no incluyen preview legible seguro, etiquetas de componentes ni distinción
  completa de header permitido/requerido. No existe catálogo persistente, intencional en
  CRM-011: UI usa discovery fresca y no ofrece selección offline. Preview requeriría
  contrato efímero provider-neutral, nunca editor ni cache presentada como aprobación.
- API crea Draft y reemplaza recipients, pero no edita template, parámetros, medio,
  etiqueta/referencia ni descarta Draft. No soporta retroceso/reemplazo seguro actual.
- Detalle serializa todos los Recipients/audits sin cursor, búsqueda, filtros ni Message
  attempts paginados: no escala a ejecuciones grandes.
- CRM-008 ofrece upload/lectura autenticados opacos, pero falta confirmar que el mismo
  `media_ref` y límites aplican al header Broadcast UI y cómo quitar/reemplazar antes
  de confirmar.
- Backend tiene consentimiento por Customer, pero no superficie frontend aprobada. Esta
  spec sólo explica elegibilidad; corregir opt-in necesita dueño/superficie aparte.
- Backend permite API, CLI o scheduler, pero no comunica política operacional activa ni
  ownership del scheduler por entorno. Browser no puede inferirla ni correr loops.
- Router actual carece de destino Broadcast y contrato de handoff Recipient->Inbox;
  requiere coordinación con deep links pendientes de CRM-023.

## Acceptance criteria

- AC-01: Sidebar ofrece `Envíos WhatsApp` como destino propio; la vista inicial es
  historial compacto, paginado y escaneable, no Inbox.
- AC-02: Cada ejecución expresa estado, fechas, template amigable, destinatarios y
  outcomes respaldados por backend, sin enumerar Recipients por defecto.
- AC-03: `Nuevo envío` sigue contenido, parámetros/medio, Customers, elegibilidad,
  resumen, confirmación e inicio, sin formulario gigante ni autoría de marketing.
- AC-04: Sólo templates marketing utilizables/frescos aparecen; IDs no son primarios y
  indisponibilidad no simula aprobación.
- AC-05: Parámetros/header solicitan sólo inputs soportados, validan inline, usan media
  autenticada sin URLs y no implican personalización por Recipient.
- AC-06: Recipients son explícitos, buscables y acotados; no hay segmentación, seller
  filter, audiencia inferida ni render ilimitado.
- AC-07: Consentimiento muestra conteos/razones seguras, conserva inelegibles visibles,
  no tiene bypass y no confirma parcialmente.
- AC-08: Confirmación es deliberada/idempotente/separada de inicio y deja inputs
  visiblemente bloqueados; cambiarlos exige Broadcast nuevo.
- AC-09: Inicio, estado, proceso manual acotado cuando corresponda y polling reflejan
  procesador backend, sin promesa instantánea ni loop/dispatch browser-side.
- AC-10: Detalle tiene progreso/KPIs textuales, lista paginada/filtrable, teléfono
  protegido, errores seguros e intentos/auditoría bajo demanda, sin payload provider.
- AC-11: Sólo fallos definitivos elegibles permiten retry; `UNKNOWN` advierte duplicado
  y nunca puede reenviarse, preservando intentos previos.
- AC-12: Handoffs Inbox distinguen Broadcast de respuesta humana y nunca resuelven
  `waiting_for_response`.
- AC-13: Polling, red, validación, conflicto token/version y retries preservan último
  dato bueno/Draft seguro y no duplican efectos.
- AC-14: Teclado, foco, diálogos, anuncios, contraste, texto equivalente y reduced
  motion cumplen CRM-018/WCAG.
- AC-15: Layout, zoom y listas/tablas se adaptan sin overflow de página ni rediseño
  mobile, con contención y prioridad de columnas.
- AC-16: Carga/poll/búsqueda son acotados/cancelables/server-side; no N+1, intentos
  completos ni filas ilimitadas.
- AC-17: Módulo aplica App Shell, tokens, tipografía, primitives y motion CRM-018 para
  experiencia FAA premium, sobria y operacional.

## Open decisions

1. **Edición y descarte de Draft.** Definir contrato idempotente/versionado para editar
   o descartar inputs `DRAFT` (template, parámetros, medio, etiqueta y referencia), o
   aprobar otro momento de persistencia que permita volver sin Draft ineditable.
2. **Proyecciones de validación, historial y detalle.** Aprobar contratos para
   elegibilidad segura categorizada, summary de historial y Recipients/intentos/audit
   paginados, buscables y filtrables. Sin ellos no se cumplen revisión/rendimiento.
3. **Preview template/header.** Decidir si provider puede exponer preview/componentes
   seguros provider-neutral; si no, aprobar fallback exacto sin fabricar copy/preview.
4. **Routing de procesamiento.** Definir por entorno scheduler, proceso manual o ambos,
   y la única acción/estado que la UI puede representar honestamente.
5. **Navegación a Inbox.** Aprobar ruta/estado para conversación vinculada de Recipient,
   coordinada con deep-link pendiente CRM-023.

Una spec no puede pasar a `Approved` mientras estas decisiones sigan abiertas.

## Follow-up / future specs

- Superficie de consentimiento por Customer sólo si producto aprueba registro/revisión
  de evidencia desde frontend; no pertenece al Broadcast genérico.
- Salud operacional WhatsApp en CRM-021 si se aprueban contratos agregados, sin ROI.
- Scheduler, alertas, throughput y runbook tras decidir routing de procesamiento.
- Catálogo persistente sólo si necesidad medida demuestra que discovery fresca no basta.

## Implementation notes

Implementar sólo después de aprobar CRM-018, CRM-025 y resolver Open decisions.
Mantener estado visual/acceso a datos en feature tipada; reglas de consentimiento,
sendability, locks, retry y dispatch permanecen en servicios backend. La futura
implementación prueba cada AC con tests de feature y journeys Docker Compose permitidos.
