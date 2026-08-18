# CRM-029 — Brand Identity & Dashboard Interaction Polish

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-18
Implementation commit: 82cd586

## Goal

Realizar el último pase visual y de producto dirigido antes de CRM-026: consolidar la
identidad FAA con el amarillo canónico, convertir Pipeline en un tablero operativo de
altura útil completa, mejorar la lectura e interacción del Dashboard y pulir las
superficies operativas expresamente incluidas sin rediseñar comportamiento comercial.

La dirección visual de esta spec fue aprobada explícitamente por el usuario. CRM-029
especializa CRM-018, CRM-021, CRM-027 y CRM-028 sólo en los puntos aquí documentados.
CRM-026 permanece Draft y no se implementa como parte de este trabajo.

## Context and diagnosis

CRM-027 y CRM-028 dejaron una aplicación coherente con Light/Dark, controles
compartidos, etapas semánticas y visualizaciones SVG/DOM simples. La revisión del
frontend actual y del dataset canónico de Visual QA encuentra los siguientes gaps
concretos:

- el accent actual no coincide con la referencia FAA aprobada, aproximadamente
  `rgb(241 184 9)`, y logo/favicon usan tonos distintos;
- el sidebar reutiliza el mismo glyph de inbox para Notifications y WhatsApp, por lo
  que comunicación no se reconoce con rapidez;
- Pipeline tiene un mínimo fijo de altura pero no consume de forma consistente el
  workspace vertical disponible, y las listas de cada columna no tienen scroll local;
- la toolbar comparte primitives parcialmente, pero el botón de refresh y el trigger
  de filtros no tienen exactamente la misma familia compacta;
- la atención operativa del Dashboard mezcla separación débil, CTAs de poco affordance
  y una conversación en espera sin acción clara;
- Evolución permite seleccionar barras, pero no distingue picos significativos ni
  puede mostrar las Opportunities contribuyentes porque `/metrics/timeline` sólo
  devuelve agregados;
- Resultados cerrados y Pipeline vigente se leen como superficies independientes, y
  Producto/Origen/Provincia siguen siendo tres módulos separados;
- WhatsApp, Lost, el handoff WhatsApp de Opportunity y Quote requieren el último ajuste
  de identidad e interacción pedido;
- `Envíos WhatsApp` describe el canal, pero no deja tan claro como `Envíos masivos` que
  se trata de ejecuciones template-based a múltiples Customers y no de chat individual.

El entorno canónico `asfaltoscrm` está documentado en
`docs/runbooks/local-visual-qa.md`, usa `localhost:5173` y `localhost:8000`, y su seed
sintético cubre ambos roles, nueve Products, dieciséis Customers, veintidós
Opportunities, Pipeline, Lost, métricas, Notifications, WhatsApp y Broadcasts.

## Dependencies

- CRM-004 — Commercial Metrics
- CRM-018 — FAA CRM Frontend 2.0 Design System
- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-021 — Dashboard & Metrics
- CRM-023 — WhatsApp Inbox 2.0
- CRM-024 — Customers, Products and Lost Workspaces UI
- CRM-025 — WhatsApp Broadcast UI
- CRM-027 — Visual Design & Product Polish
- CRM-028 — Visual Clarity & Dashboard Simplification

CRM-026 ocurre después de CRM-029 y conserva su pase final reproducible transversal.

## Scope

- Token semántico de marca FAA basado en `rgb(241 184 9)`, logo y favicon coherentes.
- Sidebar sin borde lateral decorativo y con icono reconocible de WhatsApp neutral.
- Pipeline de altura útil completa, scroll local por columna, color de etapa contenido y
  toolbar completamente normalizada.
- Dashboard: atención operativa accionable, Evolución con peak y detalle diario,
  cluster Resultados/Pipeline y un único análisis por dimensión seleccionable.
- Contrato backend mínimo, autenticado y paginado para Opportunities contribuyentes a
  un bucket diario exacto de Evolución.
- Pulido dirigido de WhatsApp, Lost, acción WhatsApp de Opportunity, Quote y naming de
  Broadcasts.
- Tests focalizados de contratos, semántica, teclado, selector, peaks, charts, quote,
  handoff y copy.
- Visual QA canónica en Light/Dark, desktop/laptop, sidebar expandida/colapsada y
  equivalentes de zoom 125 % y 150 %.

## Non-goals

- Implementar CRM-026, su harness Playwright aislado o su matriz final completa.
- Cambiar reglas comerciales, roles, visibilidad, estados, transiciones, consentimiento,
  polling, provider behavior o contratos no expresamente documentados aquí.
- Crear métricas, tendencias, prices, filtros, oportunidades, campañas, templates,
  Products, Provinces o categorías que el backend no suministra.
- Descargar una lista no acotada de Opportunities al navegador, hacer N+1, agregar un
  detalle por cada bucket al payload agregado o calcular métricas comerciales en React.
- Rediseñar Notifications, Customers, Products o la estructura de tres paneles de
  WhatsApp.
- Agregar librería de charts, iconos, componentes, motion, router o estado; no se agrega
  ninguna dependencia.
- Usar FAA yellow como surface grande, pintar el producto con verde WhatsApp, convertir
  Lost en una tabla roja o crear motion decorativo.
- Renombrar rutas, modelos o clases internas Broadcast/`whatsapp-sends`.

## FAA brand identity

La referencia aprobada se representa mediante un token base semántico de marca, por
ejemplo `brand-accent: rgb(241 184 9)`, del cual se derivan los roles `accent`,
`accent-hover`, `accent-muted`, `on-accent`, selected y focus ya definidos por
CRM-018/027. Los componentes no dispersan el RGB ni crean otro amarillo local.

Light usa el amarillo canónico en acciones primary y marca con foreground carbón
validado; hover/pressed oscurecen el solid sin perder contraste. Dark conserva la misma
identidad canónica con muted/surface y focus ajustados a su fondo. El token canónico
puede mantenerse idéntico para marks sólidos y derivar tonos accesibles por rol; no se
presupone texto blanco.

El mark FAA de sidebar/login usa el accent canónico con texto oscuro. El wordmark puede
usar accent sólo cuando mantiene legibilidad; el subtítulo permanece neutral. El favicon
SVG usa el mismo token de referencia materializado en el asset y la misma relación
amarillo/carbón. No se genera una fotografía ni un bitmap: logo y favicon siguen siendo
assets SVG/code-native del sistema existente.

## Sidebar and icons

- No existe `border-left`, inset line ni barra decorativa en el selected item.
- Selected conserva background muted, forma, peso 600, icono accent y `aria-current`.
- WhatsApp usa un glyph reconocible de burbuja/teléfono dentro de `shared/Icon`; no
  reutiliza el inbox de Notifications.
- El icono de sidebar hereda el color neutral/FAA del item y nunca usa verde WhatsApp.
- Expanded/collapsed conserva label/tooltip, badge, target, grupos, account, theme,
  logout, foco y ancho útil.
- Notifications, Customers y Products sólo reciben este cambio compartido.

## Pipeline operational board

### Height and local scrolling

En desktop/laptop, la página Pipeline se comporta como un workspace flex vertical. La
región Kanban ocupa el espacio restante luego de heading, toolbar y feedback cuando la
altura disponible lo permite. Las cuatro work zones se extienden hasta el borde útil
inferior en vez de aparecer como columnas flotantes cortas.

La región completa conserva scroll horizontal local según CRM-019. Dentro de cada
columna el header permanece visible y la lista de cards usa scroll vertical local sólo
cuando su contenido excede la altura disponible. En alturas muy restringidas, zoom o
errores visibles, el documento puede crecer antes de volver el board inutilizable; no se
crea page-level horizontal overflow ni una altura fija que oculte acciones.

### Stage identity

La configuración única de etapas conserva exactamente:

| Stage | Token visual | Evidencia permitida |
| --- | --- | --- |
| `NUEVA` | azul informativo | dot, tint mínimo, count, drop feedback |
| `COTIZADA` | amber | dot, tint mínimo, count, drop feedback |
| `NEGOCIACION` | violeta | dot, tint mínimo, count, drop feedback |
| `GANADA` | verde success | dot, tint mínimo, count, drop feedback |

Header indicator, superficie, count y valid drop derivan del mismo stage token. Las
cards siguen neutrales; color nunca reemplaza label, posición, count o instrucciones de
DnD. `PERDIDA` no entra al board.

### Toolbar normalization

La secuencia visible es `Search | sort | origin | Filters | Refresh`. Todos usan la
familia compacta de 36 CSS px, el mismo radius-control, padding, tipografía, border,
hover, active, focus y alineación de glyph/label. `Filters · N` cuenta sólo secundarios
activos; reset sigue disponible cuando corresponde. Refresh usa un icono compartido,
estado `Actualizando…` y no compite como segundo Primary.

## Dashboard operational attention

`Lo que necesita seguimiento ahora` contiene siempre tres unidades coherentes cuando
la evidencia está disponible:

1. Seguimientos pendientes.
2. Notificaciones sin leer.
3. Conversaciones esperando.

Cada unidad usa icono semántico, count o estado fuerte, explicación de una línea y CTA
de link real con hover/focus. Seguimientos y notificaciones abren el workspace
Notifications; conversaciones abre WhatsApp. Los labels son veraces (`Ver seguimientos`,
`Revisar notificaciones`, `Abrir WhatsApp`) y no afirman que el destino ya está filtrado.
La existencia de conversación conserva el límite CRM-021: muestra `Hay` o equivalente,
nunca inventa un total. La región usa tres internal surfaces sutiles o dividers claros
en una grid consistente; texto que parece botón sin semántica interactiva queda prohibido.

Los estados cero y unavailable permanecen compactos, pero la estructura no colapsa en
alturas inconsistentes cuando sólo una evidencia tiene valor.

## Commercial evolution

### Single-series bars and meaningful peaks

Se conserva `Creadas | Ganadas | Perdidas`, una serie por vez, barras desde cero y tabla
exacta completa. El selector hace inequívoca la serie activa mediante selected state,
texto y color apropiado. Ejes se reducen a baseline, máximo útil y fechas espaciadas sin
colisión.

La función de peak es pura y testeable:

- si el máximo es `0`, no hay peak;
- si un máximo positivo ocurre una o dos veces, esos buckets son peaks;
- si el máximo se repite más de dos veces, ninguno recibe peak artificial.

Un peak conserva el fill semántico de su serie y agrega outline/accent FAA canónico más
un nombre accesible que lo identifica; no se resaltan ceros ni todas las barras.

### Required backend contract for day detail

La auditoría confirma que `/metrics/timeline` no expone IDs/detalle contribuyente. En
cumplimiento del stop explícito, CRM-029 documenta antes de implementar el siguiente
contrato mínimo; el frontend no descarga Opportunities para reconstruirlo.

`GET /metrics/timeline/day-opportunities` es autenticado y acepta:

- `bucket: date` en calendario `America/Argentina/Buenos_Aires`;
- `series: created | won | lost`;
- los mismos `source`, `product_id` y `province` opcionales de metrics dimensions;
- `page` positivo y `page_size` acotado, default 20 y máximo 100.

No acepta un período ni granularidad: el bucket diario es el intervalo local exacto
`[00:00, día siguiente 00:00)` convertido a UTC. `created` filtra `created_at`; `won` y
`lost` filtran respectivamente estado actual `GANADA`/`PERDIDA` y
`current_status_entered_at`, reproduciendo exactamente CRM-004 y el timeline actual.
Las dimensiones reutilizan la misma lógica de `MetricsService`, incluido Product y
Province, para que `total` coincida con la barra seleccionada.

La respuesta tipada incluye `bucket`, `series`, `timezone`, `page`, `page_size`, `total`
y `items`. Cada item expone sólo:

- `opportunity_id`;
- `customer_name` y `customer_company` opcional;
- `current_status`;
- `source`;
- líneas cotizadas existentes con `product_id`, `product_name`, `quantity_kg` e
  `is_active`.

No expone contacto, provider IDs, precios, assignee, notas ni historia. Ordena por el
timestamp relevante descendente y `Opportunity.id DESC`. Usa eager loading acotado para
Customer/Product y no modifica schema/persistencia ni requiere migración.

### Day detail interaction

Sólo una barra no cero con `granularity=day` abre el detalle. Focus de teclado, click y
activación nativa seleccionan el mismo bucket; hover puede mostrar valor pero no dispara
requests. El frontend hace una request paginada on-demand, aborta una selección obsoleta
y puede cachear por filtros/serie/día durante la sesión del Dashboard.

El popover compacto, no modal, se ancla a la región de chart y no roba foco por mero
focus de una barra. Expone título fecha/serie, loading/error/empty seguro, items con
Customer/company, current/relevant status, source y Products/kg existentes, más
`Cargar más` cuando `loaded < total`. Escape lo cierra y una apertura deliberada permite
navegar con links semánticos. La Opportunity usa ruta canónica Pipeline o Lost según su
`current_status`; no se fabrica una ruta histórica distinta.

Para granularidad mensual las barras conservan valor/tabla pero no prometen este
drilldown diario.

## Results analytical cluster

`Resultados cerrados` y `Distribución vigente` viven dentro de una misma región
analítica, comparten heading rhythm, padding, dividers y responsive rules, y responden
preguntas diferentes:

- Resultados cerrados: donut completo Ganadas/Perdidas para el período, total cerrado,
  valores absolutos, porcentajes y conversión `ganadas / cerradas`; null no dibuja un
  círculo falso.
- Distribución vigente: barra segmentada y legend/count de las cuatro etapas visibles
  del Pipeline principal (`NUEVA`, `COTIZADA`, `NEGOCIACION`, `GANADA`) usando exactamente
  su palette. Es snapshot actual y dice que el período no aplica. `PERDIDA` permanece en
  Lost y no se representa como quinta columna del board.

El cluster no mezcla conversión de período con composición actual ni los presenta como
fragments flotantes sin relación.

## Dimension analysis

Las tres visualizaciones inferiores se reemplazan por un único módulo centrado
`Distribución comercial` con SegmentedControl:

- Productos;
- Origen;
- Provincias.

Sólo una dimensión es primaria. El módulo combina donut/ring central y ranked
legend/list lateral con valores absolutos y porcentajes. Donut nunca es el único medio:
cada dimensión conserva exact table/detail accesible con todas las categorías y el
contexto secundario backend.

Semánticas:

- Product usa `kg_quoted` y muestra oportunidades cotizadas como contexto.
- Origin usa Opportunities creadas según CRM-004/021 y conversión retornada.
- Province usa `opportunities_created`, conserva `Sin provincia` y su contexto exacto.

Cuando una dimensión excede la cantidad legible, el donut usa Top 4 + `Otras`; el
ranked/table exacto conserva cada categoría original. `Otras` sólo existe en la
representación visual. La palette categórica compartida usa azul, amber, violeta, verde
y neutral; FAA yellow no pinta todas las slices.

## Dashboard responsive behavior

- Large desktop: Evolución y el Results cluster forman una fila equilibrada; Evolución
  conserva el mayor span. Dimension analysis ocupa la fila siguiente.
- Laptop/zoom: el cluster pasa debajo antes de reducir sus donuts; legend y chart se
  apilan por contenido disponible.
- Ningún donut baja de un tamaño práctico; las legends envuelven o apilan y la tabla
  exacta sigue disponible.
- No existe overflow horizontal de página. Chart/table overflow genuino es local y
  etiquetado.

## WhatsApp directed polish

Se conserva la estructura CRM-023 y sus contratos.

- selected conversation: FAA selected tint, texto fuerte y forma, sin green branding ni
  barra izquierda;
- unread count: accent FAA compacto con nombre exacto;
- waiting: icono/label warning y surface local sutil, sin alarma;
- inbound/outbound: alineación existente y dos tonos FAA/neutrales más distinguibles;
- composer: `focus-within` visible y local, sin glow global;
- template-required: warning local junto al composer, con icono/texto y razón backend.

No se cambia polling, ordering, read state, template policy, send semantics ni el layout
de tres paneles.

## Opportunity WhatsApp action

El handoff usa el nuevo glyph reconocible de WhatsApp y mantiene texto accesible. Sólo
este botón usa el green de comunicación ya tokenizado, con background/border/text de
contraste validado; sidebar, chat general y marca FAA no heredan ese verde. Lookup,
matching y navegación interna CRM-019/020 no cambian.

## Lost directed polish

Lost usa coral/red sólo en reason chips, heading/status icon, estadísticas pequeñas y
selected/filter evidence. La fila refuerza esta jerarquía:

1. Customer/company;
2. reason;
3. lost date;
4. source;
5. quote evidence.

Typography, spacing y contrast hacen secondary metadata subordinada; hover/focus sigue
neutral. No se colorea la tabla completa ni se cambia cursor, filtros, stats o reopen.

## Quote flow

Quote conserva una sola modal, draft local, reglas CRM-020 y una única mutación final,
pero presenta cuatro pasos explícitos:

1. Producto: targets de selección grandes y selected Product inequívoco.
2. Cantidad: título dominante, Product seleccionado visible e input kg grande/enfocado.
3. Revisar: líneas agregadas, total y acciones Editar/Quitar claras; permite volver a
   agregar sin mutar backend.
4. Confirmar: summary final limpio y una sola acción Primary
   `Confirmar cotización`/`Guardar cambios`.

Enter avanza sólo Product -> Cantidad -> agregar línea y activa confirmación únicamente
si el botón final tiene foco. Escape/back vuelve un paso; draft sucio pide confirmación
antes de descartarse. Error/pending preservan draft. No hay tabla/formulario denso,
precios, historial de versiones ni cambio de validaciones backend.

## Broadcast workspace naming

El rótulo seller-facing elegido es **Envíos masivos**, más directo que `Difusiones` para
el equipo FAA y claramente distinto de chat individual. Cambian sidebar, page title,
heading/copy, modal y tests de display donde corresponda. Rutas `/whatsapp-sends`, tipos,
endpoints y nombres internos Broadcast permanecen iguales.

La explicación visible dice: `Envíos con plantillas aprobadas a Customers seleccionados,
con validación de elegibilidad y consentimiento.` No usa `campaign builder`, no llama al
workspace campaña ni sugiere que el CRM redacta/aprueba contenido.

## Accessibility and motion

- Todos los controles nuevos/revisados tienen nombre accesible, semántica nativa,
  focus visible, orden lógico y estado no sólo por color.
- Bars no cero son buttons; `aria-expanded`/`aria-controls` conectan detalle cuando
  corresponda. Cero y mes no se anuncian como drilldown disponible.
- Popover tiene heading, close accesible, Escape y links; focus por sí solo no es
  secuestrado.
- Donuts conservan `role=img` summary, legend/list y exact table; selector usa semántica
  CRM-018 y teclado.
- WhatsApp icon es decorativo dentro de botones/links ya nombrados.
- Quote vincula errores mediante `aria-describedby`/`aria-invalid`, mantiene focus por
  paso y protege draft.
- Motion queda en 120–220 ms para hover/selected/focus; no anima keyboard navigation,
  layout, polling ni chart loops. `prefers-reduced-motion` conserva datos inmediatos.

## Architecture, security and performance

- React/TypeScript/Tailwind/Vite, router interno, API modules y ownership hooks no
  cambian.
- `MetricsService` es dueño del query diario; router/schema sólo validan/presentan.
- El frontend metrics API y hook de detalle son tipados, abortables y feature-locales.
- Decimal kg viaja como Decimal/string; no se convierte a float en backend/domain.
- No hay migration, schema PostgreSQL, secrets, external URL, provider call o change de
  locks. El endpoint es read-only y no adquiere locks.
- No hay dependencia nueva, chart library, N+1, per-bucket eager request, polling o
  download ilimitado.

## Testing and canonical QA

Tests focalizados cubren:

- token/Brand/favicon y sidebar WhatsApp icon/accessibility donde sea estable;
- Pipeline stage/config semantics, height/scroll classes y toolbar family/order;
- attention unit CTA semantics;
- dimension selector y exact table retention;
- peak function con zero, one, two y three equal maxima;
- day detail service/API filters, timezone, series, pagination, ordering and response;
- frontend day detail focus/click/Escape/loading/error/navigation;
- Resultados donut total/percent/conversion/null;
- Pipeline active-stage segmented semantics;
- Opportunity WhatsApp icon accessible handoff;
- Quote four-step Enter/Escape/Edit/Remove/one-final-submit behavior;
- `Envíos masivos` display label and explanatory copy;
- WhatsApp selected/unread/waiting/composer/template state where testable.

Visual QA usa sólo el stack canónico ya levantado en `localhost:5173/8000`, con el seed
sintético documentado. Se inspeccionan Light/Dark, Pipeline, Dashboard, WhatsApp, Lost,
Opportunity modal, Quote, Envíos masivos y sidebar expanded/collapsed en desktop y
equivalentes CSS de 125 %/150 %. Screenshots son diagnóstico, no pixel gate. No se
instala Playwright ni otra dependencia como parte de CRM-029; si el runtime canónico no
ofrece el runner permitido, se registra la limitación sin implementar CRM-026.

Antes del commit de implementación deben pasar todos los gates obligatorios del
repositorio: Ruff check/format, mypy strict, backend tests/coverage/compileall, Alembic
check/current, frontend Biome/tests/coverage/TypeScript/Vite build/npm audit,
dependency/lock checks y health/smoke Docker Compose. CI es autoridad final antes de
push/documentación Implemented.

## Acceptance criteria

- AC-01: Un token semántico base representa `rgb(241 184 9)` y Brand, Primary, selected,
  focus y favicon derivan coherentemente sin raw yellow disperso ni large yellow fill.
- AC-02: Light/Dark conservan foreground/hover/muted/focus de marca accesibles y el mark
  FAA es inequívocamente amarillo/carbón en sidebar expanded/collapsed.
- AC-03: Sidebar no tiene left accent; selected conserva forma/peso/`aria-current`, y
  WhatsApp usa glyph reconocible neutral/FAA con accessible label/tooltip.
- AC-04: Pipeline ocupa la altura útil del workspace cuando es práctica, columnas se
  extienden y cards hacen scroll vertical local al desbordar sin page horizontal overflow.
- AC-05: Las cuatro stages mantienen configuración genérica y usan azul/amber/violeta/
  verde en indicator, tint, count y drop feedback sin inundar cards/surfaces.
- AC-06: Toolbar Pipeline muestra Search/sort/origin/Filters/Refresh con exactamente la
  familia compacta común de altura/radius/padding/hover/focus/icon/type.
- AC-07: Atención operativa contiene tres unidades coherentes con icono, estado fuerte,
  explicación, CTA semántica, spacing y hover/focus; no inventa count waiting ni destino
  prefiltrado.
- AC-08: Evolución conserva una serie seleccionable, bars simples, axes mínimos, fechas
  legibles, selected inequívoco y exact table completa.
- AC-09: Peak resalta con accent FAA sólo uno o dos máximos positivos; zero o tres/más
  máximos iguales no producen highlight artificial.
- AC-10: El contrato paginado `GET /metrics/timeline/day-opportunities` reproduce
  timezone/series/dimensions de CRM-004, devuelve sólo identidad/status/source/quote
  útil y no requiere migration.
- AC-11: Focus/click de una barra diaria no cero abre el mismo detalle acotado, con
  loading/error/pagination/Escape y navegación canónica Pipeline/Lost; no hay download
  ilimitado ni per-bucket request inicial.
- AC-12: Resultados cerrados muestra donut completo, absolute counts, percentages, total
  y conversion meaning; null conserva estado explícito sin fake ring.
- AC-13: Distribución vigente usa barra/legend compactas y la misma palette de las cuatro
  stages visibles, con snapshot y no-period context.
- AC-14: Resultados y Distribución forman un cluster visual único pero diferencian
  closed-period outcomes de current Pipeline composition.
- AC-15: `Distribución comercial` ofrece Productos/Origen/Provincias como selector único;
  cada vista muestra donut, ranked legend, absolutos, porcentajes y exact table.
- AC-16: Product usa kg cotizados, Origin created semantics y Province activity; Top 4 +
  Otras sólo agrupa dibujo, preserva Sin provincia y cada categoría exacta.
- AC-17: Desktop equilibra Evolución + cluster y coloca dimension debajo; laptop/zoom
  apila antes de miniaturizar donuts/legends y nunca genera page overflow.
- AC-18: WhatsApp conserva tres paneles/polling/comportamiento y mejora selected, unread,
  waiting, inbound/outbound, composer focus y template warning con accent/semántica
  contenida, sin global WhatsApp green.
- AC-19: Opportunity usa icono WhatsApp reconocible y treatment green accesible sólo en
  el handoff, sin cambiar lookup, safe state o navegación interna.
- AC-20: Lost usa coral/red en reason/status/stats/filter evidence y una jerarquía clara
  Customer > reason > date > source > quote sin colorear la tabla completa.
- AC-21: Quote muestra Producto/Cantidad/Revisar/Confirmar, targets e input grandes,
  selected Product, summary, Edit/Remove y exactamente una final mutation action.
- AC-22: Quote mantiene Enter/Escape/focus/draft/error/pending seguros y todas las reglas
  comerciales CRM-020 sin dense form/table.
- AC-23: Workspace/heading/sidebar usa `Envíos masivos` y copy explica templates
  aprobados + Customers seleccionados + eligibility/consent; no se presenta como campaña.
- AC-24: Notifications, Customers y Products sólo cambian por shared brand/sidebar/
  control consistency o corrección de regresión accesible.
- AC-25: Focus, names, dialog/popover semantics, chart alternatives, non-color evidence,
  contrast, reduced motion y keyboard behavior cumplen CRM-018/WCAG 2.2 AA donde aplica.
- AC-26: Tests focalizados requeridos y gates completos quedan verdes; frontend/backend
  health en Docker canónico responde y npm audit no introduce vulnerabilidades.
- AC-27: QA canónica cubre rutas/temas/sidebar/125/150 solicitados sin runtime error ni
  overflow; cualquier limitación de runner se informa explícitamente.
- AC-28: No se agrega dependencia, métrica, filter, polling, request masivo, state
  machine, business rule o feature CRM-026.

## Open decisions

None.

## Follow-up / future specs

- CRM-026 — final reproducible browser, accessibility, responsive, zoom and cross-flow
  QA after CRM-029.
- Month-level Opportunity drilldown sólo mediante requisito explícito posterior; el
  contrato CRM-029 es deliberadamente diario.

## Implementation notes

Implementado en `11ccafe` y verificado en `82cd586` sin dependencias ni migraciones
nuevas y sin incluir alcance de CRM-026. El backend incorpora únicamente el contrato
paginado diario
`GET /api/metrics/timeline/day-opportunities`; el frontend consume ese boundary acotado
para el detalle por barra y mantiene los agregados existentes para las visualizaciones.

Verificación completada el 2026-08-18:

- backend: Ruff lint/format, mypy strict, compileall, Alembic check/current y 389 tests
  pasaron sobre PostgreSQL aislado, con 93.00% de coverage;
- frontend: TypeScript, build, 160 tests, coverage focalizada y npm audit pasaron;
- Docker Compose canónico respondió healthy en frontend, backend y PostgreSQL, y un
  smoke read-only verificó que agregado y detalle diario coinciden en datos canónicos;
- el runtime Python Playwright exigido por la skill vendorizada no está instalado. No
  se agregó una dependencia sin aprobación: la cobertura visual manual Light/Dark,
  sidebar y zoom 125/150 queda informada como limitación del runner y permanece dentro
  del cierre reproducible previsto por CRM-026, tal como permite AC-27.
