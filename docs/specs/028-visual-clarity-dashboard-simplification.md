# CRM-028 — Visual Clarity & Dashboard Simplification

Status: Draft
Owner: FAA CRM team
Last updated: 2026-08-18
Implementation commit: N/A

## Goal

Resolver los problemas visuales que permanecen después de CRM-027: neutralizar el
modo Light, unificar controles, eliminar el último acento decorativo del sidebar,
reforzar la lectura de Pipeline y simplificar radicalmente los gráficos de Dashboard.
El resultado debe ser más claro a primera vista sin cambiar reglas de negocio,
contratos, permisos, métricas, filtros, navegación, polling ni state machines.

La dirección está explícitamente aprobada por el usuario. Esta spec sigue el flujo SDD
normal antes de implementar y no adelanta el pase final reproducible de CRM-026.

## Context and diagnosis

CRM-027 implementó la jerarquía de superficies y eliminó la mayor parte del lenguaje
genérico de cards. La revisión del frontend actual y del entorno visual canónico detecta
los siguientes remanentes concretos:

- Light usa un canvas gris verdoso y superficies secundarias beige que dan una sensación
  envejecida y reducen la neutralidad de FAA yellow;
- el item activo del sidebar todavía usa `box-shadow: inset 2px 0` como barra izquierda;
- search, filtros, botones y selects comparten tokens, pero no altura, padding o estados
  en todas las toolbars; Pipeline conserva estilos paralelos;
- Pipeline distingue etapas mediante puntos, pero NUEVA y NEGOCIACION no tienen todavía
  la identidad azul/violeta aprobada y las zonas necesitan mayor separación tonal;
- Evolución comercial superpone varias líneas, puntos y un range control, y exige más
  explicación que lectura inmediata;
- Resultados cerrados dibuja sólo la conversión como arco y no representa de forma
  completa las dos partes ganadas/perdidas;
- Productos, Origen y Provincia comparten la misma lista de barras aunque las preguntas
  y cantidades de categorías son distintas;
- Lost conserva una tabla gris con identidad destructiva demasiado débil;
- WhatsApp necesita diferencias tonales más claras entre Inbox, conversación y contexto;
- el grupo de acciones de Opportunity no expresa claramente WhatsApp como handoff de
  comunicación y el flujo de cotización sigue siendo un formulario compacto repetido,
  no una secuencia guiada.

CRM-028 especializa la presentación de CRM-018–027. Las specs propietarias conservan
autoridad de comportamiento. La autorización explícita de CRM-028 enmienda únicamente
la elección visual de CRM-021 para Origen/Provincia: permite los gráficos acotados
definidos aquí sin modificar datos ni semántica.

## Dependencies

- CRM-004 — Commercial Metrics
- CRM-018 — Frontend Design System
- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-021 — Dashboard & Metrics
- CRM-023 — WhatsApp Inbox 2.0
- CRM-024 — Customers, Products and Lost Workspaces UI
- CRM-027 — Visual Design & Product Polish

CRM-026 permanece después de CRM-028 y conserva el QA final reproducible.

## Scope

- Refinar tokens Light/Dark y estados compartidos sin crear un segundo sistema visual.
- Normalizar las familias compact/standard de controles compartidos y toolbars.
- Eliminar la barra izquierda decorativa del sidebar.
- Refinar Pipeline, Dashboard, Lost, WhatsApp, Opportunity detail y Quote.
- Ajustar Notifications, Customers, Products y Broadcasts sólo cuando consuman el
  control compartido refinado.
- Agregar tests frontend focalizados y revisar la aplicación Docker canónica con el
  dataset sintético existente.

## Non-goals

- Cambiar comportamiento comercial, reglas, visibilidad, roles, permisos, endpoints,
  schemas, persistencia, métricas backend, filtros soportados, polling o navegación.
- Implementar CRM-026, agregar Playwright al repositorio o convertir screenshots en
  un gate pixel-perfect.
- Agregar una librería de charts, iconos, componentes, motion o estado.
- Agregar filtros, tendencias, comparaciones, estadísticas, datos o drilldowns no
  respaldados por contratos existentes.
- Rediseñar WhatsApp, Notifications, Customers, Products o Broadcasts fuera de los
  ajustes de jerarquía/controles aquí expresamente definidos.
- Copiar identidad WhatsApp, convertir FAA yellow en superficie dominante o introducir
  gradients, glassmorphism, glow, neon o motion decorativo.

## Visual foundation

### Light and Dark tokens

Light usa un canvas neutral gris muy claro, `surface-primary` casi blanco y escalones
secundarios grises neutros. Beige/verde queda fuera de las superficies estructurales.
FAA yellow aparece sólo en acción primaria, foco, selección pequeña y evidencia de
marca. Los estados semánticos conservan tintes muted locales y nunca colorean el canvas.

Dark mantiene sus pasos de luminancia deliberados y adopta los mismos roles nuevos. No
se lo aclara ni invierte mecánicamente. Ambos temas deben preservar contraste de texto,
focus, selected, disabled, modal, charts y estados. Los tokens de etapa quedan:

| Estado | Rol visual | Uso permitido |
| --- | --- | --- |
| `NUEVA` | azul informativo | dot, header tint, chart segment |
| `COTIZADA` | amber | dot, header tint, chart segment |
| `NEGOCIACION` | violeta | dot, header tint, chart segment |
| `GANADA` | verde success | dot, header tint, chart segment |
| `PERDIDA` | coral/rojo | Lost, donut/segment, destructive evidence |

Texto, label, posición y forma acompañan siempre al color. Los tonos se implementan
como tokens semánticos compartidos, no valores feature-locales.

### Controls

La familia compacta mide 36 CSS px y la standard 44 CSS px. Search, FilterControl,
selects compactos, summary de filtros y botones compactos comparten radio, border,
padding vertical, font, hover, active, focus, disabled y transición. Los formularios
mantienen labels visibles; las toolbars pueden ocultar visualmente labels obvios si el
control conserva nombre accesible y valor autoexplicativo.

Pipeline, Dashboard y Lost componen la misma `Toolbar`, `SearchField`, `FilterControl`
y Button cuando la responsabilidad coincide. Los popovers conservan labels internos,
Escape seguro y retorno de foco dentro de las capacidades actuales. No se introduce
una abstracción que calcule filtros ni conozca contratos de negocio.

## Sidebar

El item seleccionado usa fondo tintado sutil, texto 600 e icono FAA yellow. No usa
`border-left`, inset line ni otra barra lateral decorativa. Su forma, fondo, peso e
`aria-current` distinguen la ruta aun sin color. Hover, focus y selected permanecen
visualmente distintos; collapsed conserva tooltip, badge y orientación.

## Pipeline

Pipeline conserva exactamente cuatro columnas activas y todas las reglas CRM-019.
Cada work zone recibe un fondo neutral con un tint mínimo de etapa y mayor contraste
respecto del gutter. El header concentra nombre, dot y count; el color no se extiende
como banda saturada ni borde decorativo. Las cards siguen siendo objetos elevados de
bajo peso con hover, focus, selected, dragging, drop válido y moving diferenciados.

La toolbar usa 36 px de altura uniforme y el lenguaje:
`Buscar oportunidades… | Más recientes | Todos los orígenes | Filtros · N`.
El empty local permanece pequeño. No se agregan metadata, WhatsApp en cards, filtros,
transiciones o queries.

## Dashboard simplification

### Operational attention and KPIs

Atención se presenta como filas/celdas alineadas con icono semántico, número/estado,
label corto y una acción sólo cuando el handoff existente es veraz. El texto de apoyo
no debe producir columnas de alturas arbitrarias: se recorta a una línea útil o pasa a
nombre/descripción accesible. El estado calmo sigue compacto.

Los cinco KPIs permanecen exactamente CRM-021/CRM-004, pero la banda reduce fondos
individuales: valores grandes, labels breves, contexto secundario y dividers. No hay
delta, flecha ni tendencia nueva.

### Evolution

Se elige **una serie simple seleccionable a la vez**. Un SegmentedControl ofrece
`Creadas`, `Ganadas` y `Perdidas`; el default es `Creadas`. El gráfico usa barras
verticales simples por cada bucket backend, escala desde cero y no agrega, interpola ni
recalcula datos. Esto resulta más claro que tres líneas superpuestas y conserva la
granularidad `day | month` autoritativa. El título/contexto informa que Creadas usa
fecha de creación y Ganadas/Perdidas ingreso al estado terminal.

Cada barra ofrece fecha y valor exactos mediante nombre accesible/title; labels del eje
se espacian para no colisionar. La tabla exacta conserva simultáneamente Creadas,
Ganadas, Perdidas, Kg ganados y Kg perdidos según el contrato existente, aunque el
gráfico visual muestre una serie. No se agrega chart library ni navegación de datos
innecesaria.

### Results closed and distributions

- `Resultados cerrados` usa un donut completo de dos segmentos: Ganadas y Perdidas.
  El centro muestra total cerrado; la leyenda muestra cada valor absoluto y porcentaje.
  El porcentaje de conversión retornado permanece visible; si el denominador es null,
  no se dibuja un donut falso.
- `Pipeline actual` mantiene todos los estados backend en una barra segmentada simple,
  con lista exacta, snapshot y advertencia de que el período no aplica.
- `Volumen cotizado por producto` mantiene barras horizontales con label, kg exactos y
  oportunidades cotizadas.
- `Leads por origen` usa donut sólo porque el contrato actual tiene una cantidad pequeña
  y acotada de categorías; conserva lista de valores/conversión exacta. Si el total es
  cero, usa empty state y no dibuja proporciones.
- `Actividad por provincia` usa donut con top cuatro provincias y un quinto segmento
  `Otras` cuando existan más categorías. `Sin provincia` es una categoría explícita y
  nunca se absorbe silenciosamente. La lista/tabla accesible conserva cada provincia
  original, su cantidad y contexto exacto; `Otras` sólo agrupa la representación visual.

Los donuts usan SVG/DOM focalizado, máximo cinco segmentos, tokens compartidos, labels
externos/lista y no dependen de hover o color para comprenderse.

## Lost workspace

Lost mantiene sus filtros, estadísticas, cursor y navegación CRM-024. Su identidad usa
coral/rojo de forma contenida: icono/título contextual, counts y reason chips. Las
estadísticas permanecen en una banda con dividers y un leve tint destructivo local; la
lista prioriza Customer, motivo y fecha sobre metadata. Los chips de motivo comparten
una única familia visual y texto, sin rainbow por motivo. Hover/focus y filas alternan
por surface, no por bloques grises pesados.

## WhatsApp polish

No se rediseña CRM-023. Conversation sigue siendo primaria; Inbox adopta un secondary
neutral más denso y CRM context se retrae otro paso tonal. La row seleccionada combina
surface-selected neutral, peso e indicador no lateral; unread/waiting siguen con texto,
dot/icono y backend authority. El composer se percibe como una única zona elevada
local: textarea, attachment/template utilities y send action tienen spacing y control
states comunes. No se usa WhatsApp green ni se alteran mensajes, templates o polling.

## Opportunity detail and quote flow

El detalle sigue read-first. Su grupo de acciones ordena primero la próxima acción
comercial Primary, luego acciones Secondary/Ghost y al final la acción destructive.
`Abrir WhatsApp` usa verde de comunicación en texto/icono/borde/fondo restrained, con
contraste y label; no utiliza FAA yellow y no implica envío ni conversación nueva.

Quote mantiene una sola capa modal y los endpoints CRM-020, pero pasa de fieldsets
repetidos a un flujo visual enfocado:

1. `Elegir producto`: selección clara del catálogo elegible;
2. `Indicar cantidad`: input de kg grande y enfocado;
3. `Agregar`: valida y suma una línea sin mutación backend;
4. `Revisar cotización`: lista compacta editable/removible, total kg y confirmación
   backend única.

En edición, las líneas actuales se cargan en la revisión y pueden editarse mediante el
mismo producto/cantidad. Inactivos históricos permanecen según CRM-020; duplicados y
cantidades no positivas se bloquean antes de confirmación y siguen sujetos al backend.

Enter desde producto avanza a cantidad; Enter desde cantidad válida agrega la línea;
Enter nunca confirma toda la cotización fuera del botón final enfocado. Escape vuelve
de cantidad a producto o de revisión al detalle cuando no hay draft sucio; un draft
sucio nunca se descarta silenciosamente. Modal más ancho, spacing 20–24 px y máximo
viewport-safe evitan el layout apretado en laptop/zoom.

## Accessibility, responsive and motion

- Ningún status depende sólo de color; charts conservan headings, legends, lista/tabla
  exacta y nombres accesibles.
- Focus visible, semántica nativa, modal trap/return, Enter/Escape seguro, live regions
  y reduced motion permanecen CRM-018/020/021/023-authoritative.
- Las barras/donuts son legibles sin animación; cualquier transición dura 120–220 ms y
  sólo acompaña hover/selected/cambio deliberado.
- Desktop, laptop, sidebar expanded/collapsed y zoom 125/150 reflow sin overflow de
  página. A 200% la expectativa estructural conserva navegación, título, acción y flujo
  central; Pipeline y tablas exactas pueden usar scroll local aprobado.

## Architecture, dependencies and performance

Se refinan tokens/primitives existentes antes de features. React/TypeScript/Tailwind/
Vite, router, API modules y ownership de hooks no cambian. Los charts usan sólo SVG y
DOM ya aprobados. No se agrega dependencia ni request. Los cálculos visuales se limitan
a escala, porcentaje de presentación y agrupación top-cuatro/Otras desde agregados ya
retornados; nunca redefinen la métrica backend. No se introduce polling, N+1, canvas,
global state ni animation loop.

## Implementation sequence

1. Tokens Light/Dark y roles de etapa/chart.
2. Button, fields, SearchField, FilterControl, Toolbar y sidebar selected state.
3. Pipeline toolbar, work zones, headers/cards y estados.
4. Dashboard attention, KPIs y visualizaciones simplificadas.
5. Lost semantic hierarchy.
6. WhatsApp panel/row/composer polish.
7. Opportunity action hierarchy y Quote guided flow.
8. Control-consistency pass en Notifications/Customers/Products/Broadcasts.
9. Light/Dark, responsive/zoom, accessibility y anti-pattern audit.
10. Gates, canonical Docker visual verification y handoff a CRM-026.

## Acceptance criteria

- AC-01: Light usa canvas/surfaces blancos y grises neutrales sin sensación beige o
  amarillenta; FAA yellow queda reservado a accent/action/selection y Dark conserva
  jerarquía equivalente.
- AC-02: El sidebar no contiene `border-left`, inset left line ni barra decorativa para
  selección; active sigue inequívoco mediante fondo, icono, peso, forma y `aria-current`.
- AC-03: Search, compact select/filter, summary y Button compact comparten 36 px, radio,
  padding, typography, hover, active, focus y disabled; forms standard conservan 44 px.
- AC-04: Pipeline toolbar usa controles compartidos alineados, valores
  autoexplicativos, `Filtros · N` y reset sin labels administrativos visibles.
- AC-05: Pipeline conserva exactamente NUEVA/COTIZADA/NEGOCIACION/GANADA y toda
  semántica CRM-019; work zones tienen separación neutral y stage evidence azul/amber/
  violeta/verde contenida y no color-only.
- AC-06: Pipeline cards/columns conservan hover, focus, selected, drag, valid drop,
  moving, rollback, empty local y board-local scroll sin metadata o acciones nuevas.
- AC-07: Operational attention alinea icono, valor/estado, label y acción veraz, evita
  wrapping incómodo y conserva límites exactos de notification/WhatsApp evidence.
- AC-08: Los cinco KPIs CRM-021 mantienen valores, Decimal/null/contexto autoritativos,
  ganan jerarquía y no agregan tendencias ni cajas equivalentes.
- AC-09: Evolución muestra una sola serie seleccionable Creadas/Ganadas/Perdidas como
  barras desde cero por bucket exacto; default Creadas y semántica temporal explícita.
- AC-10: Evolución conserva tabla exacta accesible, labels/nombres útiles, teclado,
  Light/Dark y reduced motion sin chart dependency.
- AC-11: Resultados cerrados muestra donut completo Ganadas/Perdidas, total, valores
  absolutos, porcentajes y conversión; null no se representa como cero.
- AC-12: Pipeline distribution es una barra segmentada simple con los cinco estados,
  lista exacta, snapshot y contexto no filtrado por período.
- AC-13: Product volume usa barras horizontales con kg y count autoritativos; no se
  inventan precios, rankings o medidas.
- AC-14: Lead sources usa donut acotado y lista exacta; cero total produce empty state.
- AC-15: Province activity usa top cuatro + Otras visual, mantiene Sin provincia
  explícita y una lista/tabla exacta de todas las categorías originales.
- AC-16: Dashboard sigue atención > KPI > análisis, evolución es primaria,
  conversion/Pipeline secundarias y dimensions terciarias, sin métricas falsas.
- AC-17: Lost usa identidad coral/roja contenida, reason chips claros, banda de
  estadísticas y filas legibles sin modificar filtros, cursor, reopen o navegación.
- AC-18: WhatsApp mejora jerarquía tonal, selected row y composer sin cambiar CRM-023,
  usar verde WhatsApp, imitar branding o agregar un rediseño.
- AC-19: Opportunity detail permanece read-first y ordena acciones; Abrir WhatsApp usa
  tratamiento verde accesible sin cambiar su lookup/handoff interno.
- AC-20: Quote ofrece producto → cantidad → agregar → revisar en una modal amplia,
  soporta creación/edición/múltiples líneas/inactivos históricos y realiza una sola
  mutación final existente.
- AC-21: Quote implementa Enter/Escape/focus seguro, validación inline, pending,
  prevención de duplicado y preservación de draft/error conforme CRM-020.
- AC-22: Notifications, Customers, Products y Broadcasts no cambian funcionalidad y
  sólo adoptan refinamientos compartidos necesarios para consistencia de controles.
- AC-23: No hay regresión de keyboard, focus, dialogs, labels/names, non-color evidence,
  contrast, chart alternatives, zoom, reduced motion o live feedback.
- AC-24: Light/Dark y sidebar expanded/collapsed son utilizables en desktop/laptop;
  125/150 y expectativa 200 no generan overflow horizontal de página.
- AC-25: La auditoría no encuentra sidebar left accent, colores visuales feature-locales
  nuevos, gradients arbitrarios, shadows/radii nuevos, nested rectangles innecesarios,
  labels administrativos reintroducidos ni yellow dominante.
- AC-26: No cambia backend, migraciones, business behavior, API/request count, bundle
  dependency count ni polling/rendering de datos; gates y Docker smoke permanecen verdes.
- AC-27: El entorno canónico `localhost:5173` con seed sintético permite inspeccionar
  Pipeline, Dashboard, Lost, Opportunity/Quote y WhatsApp en Light/Dark y evidencia que
  el frontend servido contiene la implementación CRM-028.
- AC-28: CRM-026 permanece Draft/no implementado y conserva Playwright, entornos
  aislados, browser matrix, keyboard/accessibility y QA final después de CRM-028.

## Open decisions

None.

## Follow-up / future specs

- CRM-026 — final reproducible browser/accessibility/responsive/zoom QA después de
  implementar CRM-028.
- Self-service account y cualquier contrato backend pendiente mantienen su ownership
  previo; CRM-028 no los amplía.

## Implementation notes

La implementación debe usar el stack actual y el entorno visual canónico. Si un chart
requiriera una dependencia, debe detenerse antes de agregarla; la composición definida
aquí cabe en SVG/DOM focalizado. Las capturas son evidencia diagnóstica, no baselines
pixel-perfect.
