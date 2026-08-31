# CRM-030 — Frontend Visual Simplification

Status: Draft
Owner: Frontend / Product Design
Last updated: 2026-08-30
Implementation commit: N/A

## Goal

Refinar la presentación y la experiencia de uso del frontend de FAA CRM después de la
revisión visual de CRM-018, manteniendo intacto su éxito funcional. El resultado debe
sentirse menos denso, más jerárquico, más legible a 1440 px y más calmo durante el uso
diario de oficina.

El principio rector es: **menos es más**.

CRM-030 reduce decisiones simultáneas, elimina superficies amarillas lavadas, aumenta
la escala tipográfica y prioriza contenido cómodo antes que la posibilidad de mostrar
todo al mismo tiempo. FAA yellow y FAA navy construyen identidad mediante dosis sólidas
e intencionales sobre una base predominantemente neutral.

## Context and authority

CRM-018 permanece como baseline funcional exitoso. CRM-030 es un refinamiento visual y
de UX focalizado: sólo reemplaza decisiones de presentación expresamente indicadas en
esta spec. Las capacidades, rutas, contratos, reglas, datos y regresiones funcionales
aprobadas por CRM-018 a CRM-029 continúan vigentes.

La revisión posterior a la implementación detectó estos problemas principales:

- la interfaz se percibe pequeña y comprimida a 1440 px;
- Pipeline prioriza mostrar cuatro columnas angostas en vez de tarjetas cómodas;
- Dashboard todavía muestra demasiadas lecturas independientes al mismo tiempo;
- unread, warning, waiting y selected continúan usando superficies crema o amarillas
  lavadas en áreas demasiado grandes;
- Notifications y WhatsApp dependen de ese tratamiento para comunicar estado;
- Broadcasts conserva demasiada complejidad dentro de una única superficie aunque su
  creación ya tiene una secuencia funcional;
- Lost mejoró funcionalmente, pero la lectura de magnitud, causas y oportunidades sigue
  demasiado plana; y
- la escala de títulos, nombres, navegación, métricas y labels primarios no establece
  una jerarquía suficientemente visible.

Esta spec no modifica `docs/BUSINESS_RULES.md`. Ante una diferencia no expresamente
resuelta aquí, prevalece el comportamiento aprobado existente.

## Dependencies

- CRM-018 — Frontend 2.0
- CRM-019 — Pipeline 2.0
- CRM-021 — Dashboard & Metrics
- CRM-022 — Notifications UI
- CRM-023 — WhatsApp Inbox 2.0
- CRM-024 — Customers, Products and Lost Workspaces UI
- CRM-025 — WhatsApp Broadcast UI
- CRM-026 — Frontend Final Polish & Regression Pass
- CRM-027 — Visual Design & Product Polish
- CRM-028 — Visual Clarity & Dashboard Simplification
- CRM-029 — Brand, Dashboard & Interaction Polish

CRM-018 es el baseline funcional. CRM-026 conserva la autoridad sobre la evidencia de
regresión transversal; sus baselines visuales deberán actualizarse deliberadamente
después de aprobar e implementar CRM-030.

## Scope

- Ajustar tokens y usos semánticos de color sin crear un segundo sistema visual.
- Mantener Manrope y reemplazar la escala tipográfica por la definida en esta spec.
- Refinar AppShell, navegación y jerarquía compartida sólo en lo necesario para aplicar
  la nueva escala y el balance FAA yellow/navy.
- Refinar Pipeline, Dashboard, Notifications, WhatsApp Inbox, Envíos masivos y Lost.
- Aplicar progressive disclosure a análisis de Dashboard, creación de Broadcasts,
  filtros avanzados de Lost y contexto CRM secundario ya existente.
- Eliminar elementos visuales expresamente listados en esta spec.
- Mantener Light, Dark y System con equivalencia semántica y contraste accesible.
- Actualizar tests frontend y evidencia visual afectada cuando esta spec sea aprobada
  para implementación.

## Non-goals

- Implementar esta spec durante su etapa Draft.
- Cambiar backend, API, schemas, persistencia, métricas, queries o reglas de negocio.
- Cambiar roles, permisos, visibilidad, navegación, rutas o capacidades existentes.
- Agregar información, campos, filtros, métricas, acciones o funcionalidad para ocupar
  espacio.
- Cambiar las cuatro etapas del Pipeline o sus reglas de drag and drop.
- Cambiar la arquitectura de dos zonas de WhatsApp.
- Cambiar reglas de template, elegibilidad, consentimiento, confirmación, ejecución,
  polling o resultados de Broadcasts.
- Agregar una librería de componentes, un framework UI, un chart library, un sistema de
  iconos, un router o un store global.
- Reemplazar React, TypeScript, Tailwind CSS, Manrope o los charts SVG/DOM existentes.
- Incorporar gradientes, glassmorphism, glow, fondos decorativos o motion ornamental.
- Convertir el producto en una experiencia mobile-first; se conserva desktop-first con
  responsive básico y sin roturas.

## Design principles

### Less is more

Una pantalla no expone varias tareas independientes si puede ofrecer una lectura
principal y revelar el resto bajo demanda. Cada bloque, label, borde y color debe
justificar una decisión o un estado.

### Comfortable before comprehensive

Legibilidad, ancho útil y ritmo tienen prioridad sobre mostrar todas las columnas,
métricas o visualizaciones sin scroll o selección. El scroll horizontal local del
Pipeline es una herramienta deliberada y no un defecto de responsive.

### Neutral foundation, solid punctuation

Canvas y superficies neutrales dominan. FAA navy puede estructurar una zona importante.
FAA yellow aparece sólido en dosis pequeñas: acción primaria, marker, indicador activo,
foco de identidad o acento clave. No se diluye en grandes fondos crema.

### One decision at a time

Tabs, segmented controls, drawers, disclosure y pasos explícitos reducen carga
cognitiva. Ocultar una lectura secundaria no elimina datos: cambia su prioridad.

### Direct evidence

Valores y labels se muestran junto al elemento que explican. Se prefieren números
directos, barras comparativas, barras horizontales y tendencias simples. Leyendas y
donuts no sustituyen labels visibles.

## Revised color system

### Institutional source colors

| Token | Exact source value | Role |
| --- | --- | --- |
| `--brand-yellow` | `#F1B809` | acción primaria, marker compacto, active indicator e identidad FAA |
| `--brand-navy` | `#1B3B5F` | estructura, heading sólido, navegación activa, charts y texto importante |

Los componentes consumen tokens semánticos; no dispersan estos hexadecimales ni crean
amarillos feature-locales. Los estados hover, pressed, disabled, Light y Dark usan
derivaciones semánticas accesibles.

### Exact rules replacing pale-yellow surfaces

1. `--accent-muted`, `--accent-subtle`, `--accent-surface`, `--warning-subtle` y
   cualquier mezcla crema/amarilla quedan prohibidos como background de una fila,
   card, banner, columna, panel, chart, párrafo o sección completa.
2. Una superficie selected o unread usa `--selection-surface`, neutral y derivada de
   navy para cada tema, más peso tipográfico y `--selection-marker` en FAA yellow
   sólido. El marker es un dot de 6–8 px, una marca de hasta 4 px de espesor o un icono
   compacto; no cubre el fondo del contenido.
3. Un warning usa superficie neutral, texto e icono `warning`, y borde/divider warning
   sólo si hace falta contención. El mensaje se ubica junto a la acción afectada y no
   convierte el área circundante en un bloque amarillo.
4. FAA yellow sólido puede ocupar botones primarios de altura máxima standard de 44 px,
   badges/counts compactos, markers, focus/active evidence o un pequeño acento de
   identidad. No aparece detrás de párrafos ni filas completas.
5. FAA navy sólido puede formar, como máximo, uno o dos bloques estructurales fuertes
   por pantalla cuando mejoren jerarquía. Usa foreground claro con contraste AA y no
   compite con un segundo mosaico de cards coloreadas.
6. Estados success, danger, warning e informational conservan color semántico sólo en
   texto, icono, badge, marker, barra o borde local. Ninguno colorea una región grande.
7. Dark no simula amarillo lavado mediante marrones u oliva extensos. Selected usa un
   paso navy/neutral reconocible y warnings conservan contención local.
8. Texto y foreground normales alcanzan contraste WCAG 2.2 AA de 4.5:1; texto grande y
   límites/estados de controles alcanzan al menos 3:1. Color nunca es la única evidencia.

### Solid sectionization selected for CRM-030

- Dashboard usa un header navy sólido dentro del único módulo analítico visible. El
  título, contexto y selector viven allí; el área del gráfico permanece neutral.
- Lost usa un panel analítico navy sólido para la magnitud principal y su contexto; las
  causas se conectan visualmente mediante barras directas sobre una superficie neutral
  o dentro de una zona navy accesible si los labels conservan contraste.
- No se incorpora un gran bloque amarillo. FAA yellow puntúa CTA, selección, markers y
  el dato destacado que lo necesite.

## Exact revised typography scale

Manrope permanece como única familia. Los tamaños son CSS px a zoom 100 % y se
materializan como tokens semánticos compartidos, no como clases arbitrarias por feature.

| Role | Size / line-height | Weight | Required use |
| --- | --- | --- | --- |
| Primary metric / display | `40px / 44px` | 700 | KPI principal, magnitud principal de Lost |
| Workspace title | `32px / 40px` | 700 | título único de cada workspace |
| Section title | `20px / 28px` | 650 | secciones y módulos analíticos primarios |
| Subsection title | `17px / 24px` | 650 | grupos secundarios, headers de columnas |
| Important identity | `16px / 22px` | 650 | Customer/company y nombres de oportunidad principales |
| Body | `15px / 23px` | 400 | copy, contenido y lectura ordinaria |
| Body strong | `15px / 22px` | 600 | valores y labels de alta prioridad |
| Navigation | `15px / 20px` | 600 | sidebar y navegación principal |
| Control / primary action | `14px / 20px` | 600 | buttons, tabs, segmented controls, selects y search |
| Supporting / metadata | `13px / 18px` | 400–500 | fechas, origen y contexto secundario |
| Control label | `13px / 18px` | 600 | label visible cuando sea necesario |
| Micro | `12px / 16px` | 500 | ejes, unidades o metadata terciaria excepcional |

Reglas complementarias:

- contenido esencial nunca usa `Micro`;
- el default de body deja de ser 14 px y pasa a 15 px;
- nombres principales no se renderizan como metadata de 12–14 px;
- KPI values y cantidades principales usan numerales tabulares;
- labels de 12 px sólo permanecen cuando son metadata genuinamente terciaria;
- la jerarquía no depende exclusivamente de uppercase, color o letter-spacing; y
- a 1024 px no se reduce body, navegación ni controles por debajo de esta escala; el
  layout se adapta antes de achicar texto.

## Proposed design changes by screen

### AppShell and shared workspace chrome

- Aumentar navegación a `Navigation` y el título de ruta a `Workspace title`.
- Mantener una sola identidad/título por ruta y eliminar descripciones redundantes.
- Conservar sidebar, grupos, badges, cuenta, tema y logout actuales.
- Usar navy en navegación activa e información importante; FAA yellow queda como icono,
  marker o badge compacto, nunca como fondo extendido del item.
- Mantener acciones compactas en 36 px y acciones/formularios standard en 44 px; el
  aumento tipográfico no crea controles desproporcionados.

### Pipeline

- Mantener exactamente `NUEVA`, `COTIZADA`, `NEGOCIACION` y `GANADA`, su configuración
  única y toda interacción existente.
- Cambiar el mínimo de cada columna de `240px` a `320px` (`20rem`). El ancho de trabajo
  preferido es `336px` (`21rem`) y no se requiere que las cuatro columnas entren a la
  vez.
- Con padding horizontal interno de 8 px por lado, cada Opportunity card conserva un
  ancho exterior mínimo de `304px` (`19rem`) y aproximadamente 280 px de contenido
  después de su propio padding.
- El board usa gap de `16px`, min-width derivado de cuatro columnas de 320 px más tres
  gaps (`1328px`) y scroll horizontal local siempre accesible cuando el workspace sea
  menor. No produce overflow horizontal de página.
- Mantener scroll vertical por columna, sticky headers, keyboard DnD, focus, rollback,
  empty local y estados dragging/drop/moving.
- Usar columnas neutrales. El header tiene separación vertical más fuerte mediante
  título `Subsection`, divider/estructura navy y un marker de etapa compacto. No se
  tinta toda la columna ni se convierte cada header en una banda multicolor.
- Aumentar Customer/company principal a `Important identity`; contacto, origen y edad
  usan `Supporting / metadata` sin agregar campos.
- Mantener cards simples, con suficiente padding y sin nuevas acciones o evidencia.

### Dashboard

La primera pantalla responde, en orden:

1. **Qué requiere atención:** una banda operativa compacta con seguimientos pendientes,
   notificaciones sin leer y conversación esperando, usando los handoffs existentes.
2. **Cómo estamos:** cuatro métricas comerciales primarias: oportunidades creadas,
   conversión por oportunidades, kg cotizados y kg ganados.
3. **Qué inspeccionar:** un único módulo de análisis visible, con `Evolución` como vista
   inicial.

`Resultados cerrados` deja de ser un KPI primario separado: permanece disponible en el
análisis `Resultados`. Seguimientos no se duplica como KPI porque ya ocupa la banda de
atención. No se agregan tendencias, deltas, targets ni datos nuevos.

El módulo analítico usa una navegación local única:

- `Evolución` — default; una serie a la vez (`Creadas`, `Ganadas`, `Perdidas`) con la
  tendencia simple y el detalle diario ya existente;
- `Resultados` — ganadas y perdidas mediante números directos y barras comparativas;
- `Productos` — barras horizontales ordenadas por kg cotizados;
- `Orígenes` — barras horizontales ordenadas por oportunidades creadas;
- `Provincias` — barras horizontales ordenadas por oportunidades creadas; y
- `Pipeline` — barra segmentada o barras directas con labels/counts visibles y contexto
  explícito de snapshot.

Sólo una vista analítica se renderiza como primaria a la vez. El estado del selector es
local al Dashboard y no crea ruta, navegación global ni store. Los datos exactos y el
contexto secundario permanecen bajo disclosure dentro de la vista activa.

Reglas de visualización:

- eliminar todos los donuts del Dashboard;
- usar labels y valores directos; no mostrar una leyenda separada cuando el elemento
  puede etiquetarse en contexto;
- no depender de hover para conocer un valor;
- conservar tabla/lista accesible exacta donde ya existe;
- usar navy como serie/estructura principal y FAA yellow como highlight seleccionado o
  peak compacto, no como fill de todas las barras; y
- mantener filtros actuales, llevando filtros avanzados al disclosure ya existente.

### Notifications

- Mantener exactamente la información, filtros, mark-read, paginación/polling, stale
  evidence y navegación existentes.
- Una fila unread usa fondo neutral/navy-derived, identidad en peso 650 y marker FAA
  yellow sólido de 6–8 px. Se elimina el full-row cream wash.
- Una fila read vuelve a superficie neutral ordinaria; resolved/read continúan con
  evidencia textual, no sólo color.
- Stale y nuevos items usan mensajes compactos neutrales con icono/texto semántico; no
  usan un banner amarillo ancho.
- Aumentar heading a `Section title`, Customer/company a `Important identity`, contenido
  a `Body` y metadata a 13 px.
- Aumentar el ritmo vertical de la fila a un mínimo cómodo de 68 px sin reducir la
  cantidad de información.

### WhatsApp

- Mantener la arquitectura funcional de dos zonas: Inbox y conversación. El contexto
  CRM secundario existente se abre mediante su disclosure/drawer actual y no se muestra
  como una tercera tarea simultánea permanente.
- La conversación seleccionada usa `--selection-surface` neutral/navy-derived, peso
  tipográfico y un marker FAA yellow compacto. No usa pale yellow ni WhatsApp green.
- Un waiting row usa superficie neutral con icono/label warning; no usa fondo crema.
- Template-required, restricción de ventana, disabled reason y espera se presentan como
  status compacto inmediatamente encima o dentro del límite visual del composer.
- Eliminar cualquier background warning aplicado a toda la zona del composer.
- Aumentar padding/ritmo del panel de conversación sin agregar información; message log
  y composer siguen siendo la tarea primaria.
- Mantener mensajes, attachments, templates, polling, unread, waiting, envío, errores y
  navegación exactamente como están aprobados.

### Broadcasts / Envíos masivos

History permanece como una lista/tabla simple con status, fecha, template, destinatarios
y resultado existentes. La creación sigue siendo explícitamente step-based y muestra
una decisión principal por vez:

1. **Template y contenido:** seleccionar template aprobado y completar label,
   parámetros y header media requeridos por ese template.
2. **Destinatarios:** buscar/seleccionar Customers y revisar el conteo seleccionado.
3. **Elegibilidad y revisión:** ejecutar validación, mostrar aptos/excluidos y razones
   seguras, y permitir volver a corregir destinatarios o contenido.
4. **Confirmar:** resumen final inmutable de contenido, destinatarios y elegibilidad con
   una sola acción primaria de confirmación.
5. **Progreso y resultados:** continuar en el detalle operativo existente con progreso,
   outcomes, recipient evidence, retry permitido y audit disclosure.

El stepper comunica actual/completado/pendiente mediante número, label, peso y estado;
FAA yellow puede marcar el paso actual sin pintar el cuerpo del wizard. Cada paso tiene
Back y Continue/Confirm previsibles. Draft, versión, validation token, dirty-state,
errores y pending se conservan al avanzar o retroceder según CRM-025. Cerrar no descarta
trabajo silenciosamente.

Contenido, recipients, eligibility y confirmation nunca se muestran juntos en una
pantalla larga. El paso 5 no crea una vista nueva: presenta el detalle/progreso ya
existente después de confirmar.

### Lost

- Ordenar la primera lectura como: magnitud perdida → motivos → oportunidades.
- El panel navy sólido muestra como dato principal kg perdidos actuales en `Primary
  metric / display`, acompañado por count actual. Histórico y reabiertas se subordinan
  como valores secundarios sin competir con la magnitud actual.
- `Motivos de pérdida` usa barras horizontales simples, ordenadas por magnitud, con
  label, count y kg directos. No usa donut ni leyenda separada.
- Mantener red/coral sólo para badge de `PERDIDA`, motivo, valor semántico o evidencia
  puntual. No usar superficies rojas/rosas grandes.
- Separar análisis y lista mediante espacio, heading y cambio estructural; no mediante
  una sucesión de cards equivalentes.
- Mantener search y filtros más frecuentes visibles; filtros avanzados permanecen en un
  disclosure único con count activo, Apply y Reset existentes.
- Mantener listado, paginación, navegación, reapertura, permisos, datos y filtros
  actuales.

### Other workspaces and overlays

- Customers, Products, Users, Opportunity detail, Login, modals y drawers sólo reciben
  escala tipográfica, tokens y primitives compartidos cuando corresponda.
- No se rediseñan sus flujos ni se agregan datos, acciones o nuevas superficies sólidas.
- Selected, warning y feedback compartidos obedecen las nuevas reglas de color en todas
  las rutas para evitar excepciones feature-locales.

## Interaction model

- Tabs y segmented controls cambian una vista local sin borrar filtros ni datos ya
  cargados innecesariamente.
- Un selector siempre muestra estado selected mediante texto/peso/forma además de color.
- El foco permanece visible y vuelve de drawer/modal/popover según CRM-018.
- Disclosure avanzado conserva nombre accesible, `aria-expanded`, Escape seguro cuando
  corresponda y orden de tab lógico.
- Touch/click targets de acciones principales e icon-only permanecen al menos 44 × 44 px;
  controles compactos de 36 px conservan hit area/spacing suficiente en desktop.
- No se agrega motion decorativo. Transiciones funcionales permanecen entre 120–220 ms
  y respetan `prefers-reduced-motion`.

## Data model

No hay cambios de entidades, campos, relaciones, constraints, persistencia ni
migraciones. Todo draft, estado y dato mostrado utiliza el modelo existente.

## Contracts / API

No hay cambios de endpoints, payloads, schemas, errores, polling ni contratos internos
de negocio. Dashboard reorganiza métricas existentes; no recalcula métricas comerciales
en React ni solicita un nuevo contrato. Broadcasts sólo redistribuye el flujo aprobado
sobre las mutaciones y lecturas existentes.

## State transitions

No cambian máquinas de estado de Opportunity, Notification, WhatsAppConversation,
WhatsAppMessage o WhatsAppBroadcast. Los pasos de Broadcasts son estados de
presentación del flujo existente y no nuevos estados persistidos.

## Security & permissions

Autenticación, roles `SUPERVISOR`/`VENDEDOR`, permisos, visibilidad, sanitización,
attachments, consentimiento y restricciones de WhatsApp permanecen sin cambios. La
presentación progresiva no oculta evidencia requerida para una decisión segura ni
habilita acciones no autorizadas.

## Components to modify

El alcance de implementación esperado se concentra en componentes existentes:

- `frontend/src/styles.css`: tokens, tipografía y eliminación de washes estructurales;
- `layout/AppShell.tsx`, `shared/Workspace.tsx`, `shared/SegmentedControl.tsx`,
  `shared/StatusStates.tsx` y `shared/Badge.tsx`: jerarquía y estados compartidos;
- `pipeline/PipelineBoard.tsx`, `PipelineColumn.tsx` y `OpportunityCard.tsx`;
- `pages/DashboardPage.tsx`, `metrics/DashboardFilters.tsx` y
  `metrics/DashboardVisuals.tsx`;
- `pages/NotificationsPage.tsx`;
- `pages/WhatsAppInboxPage.tsx`, `whatsapp/ConversationList.tsx`, `ChatPanel.tsx` y
  `MessageComposer.tsx`;
- `pages/WhatsAppBroadcastsPage.tsx`, con extracción de componentes de paso sólo si
  separa una responsabilidad real sin introducir abstracción genérica anticipada; y
- `pages/LostPage.tsx`.

Tests asociados y evidencia visual se actualizan sólo por los cambios aprobados. No se
modifican módulos API, hooks de datos o backend salvo que un defecto funcional previo e
independiente se trate en otra tarea/spec.

## Elements to remove

- Pale/cream/yellow full-row, card, banner, composer, selected y section backgrounds.
- Uso estructural de `accent-muted`, `accent-subtle`, `accent-surface` o
  `warning-subtle` como wash grande.
- Donut charts de Dashboard.
- Render simultáneo de Evolution, Results, Pipeline distribution y dimension analyses.
- KPI primario separado de `Resultados cerrados`; el dato se mueve a su análisis.
- Legends separadas cuando labels y valores directos pueden acompañar barras/segments.
- Tint de etapa extendido a toda la columna de Pipeline.
- Warning background extendido a waiting rows o a toda la zona del composer de
  WhatsApp.
- Full-row yellow unread treatment de Notifications.
- Presentación simultánea de contenido, Customers, elegibilidad y confirmación en
  Broadcast creation.
- Superficies red/pink grandes en Lost.
- Labels de 12 px para identidad, contenido esencial, navegación o acciones primarias.
- Copy, borders y cards que repiten una jerarquía ya explicada por proximidad, heading o
  disclosure.

## Responsive and visual review matrix

La implementación futura debe revisarse con dataset determinístico, Manrope cargada,
tema y reduced-motion fijados. Los anchos son viewport CSS a zoom 100 %; CRM-026 conserva
además sus checks de zoom 125/150/200.

| Viewport | Mandatory review target |
| --- | --- |
| `1024 × 768` | Texto conserva la escala; no hay overflow horizontal de página; Pipeline usa scroll horizontal local con cards de 304 px; Dashboard apila atención/KPIs/análisis; WhatsApp y wizard conservan acción primaria accesible. |
| `1280 × 800` | Pipeline no comprime columnas; Dashboard muestra una sola lectura analítica; Notifications mantiene ritmo/identidad sin truncar información esencial; Lost separa análisis/lista. |
| `1440 × 900` | Revisión principal: columnas de 320–336 px y cards cómodas; títulos/KPIs se sienten materialmente mayores; no queda wash amarillo; balance navy/yellow es intencional; Dashboard se lee como overview ejecutivo. |
| `1600 × 900` | Confirmar que el espacio adicional mejora respiración sin estirar cards o crear mosaicos; cuatro columnas pueden entrar si el AppShell lo permite, pero nunca bajan de 320 px ni superan innecesariamente el ancho preferido. |

En cada viewport se revisan Light y Dark para las superficies afectadas. Los targets
visuales obligatorios son:

- ancho de columnas y comodidad de cards de Pipeline;
- carga cognitiva y una sola vista analítica de Dashboard;
- eliminación completa de yellow/cream washes;
- escala de títulos, identidades, navegación, body y métricas;
- balance entre neutral dominante, navy estructural y FAA yellow sólido;
- unread de Notifications;
- selected, waiting y restriction status de WhatsApp;
- pasos, preservación de Draft y foco de Broadcast creation; y
- magnitud, motivos y lista de Lost.

## Edge cases

- Texto largo de Customer/company, provincia, Product o template envuelve o trunca con
  title/nombre accesible sin reducir la tipografía.
- Valores KPI largos y cantidades grandes mantienen numerales tabulares y no solapan.
- Dashboard con null, cero, loading, partial error o filtros sin resultados conserva una
  sola región analítica y no dibuja proporciones falsas.
- Una tab analítica con muchas categorías usa barras/lista y disclosure exacto local;
  no reintroduce un donut ni fuerza overflow de página.
- Pipeline vacío, con muchas cards o durante drag conserva ancho, scroll y feedback.
- Un warning largo de WhatsApp envuelve cerca del composer sin ampliar el color a toda
  la zona ni tapar send/template actions.
- Broadcast validation inválida mantiene al usuario en Eligibility/Review, conserva el
  Draft y ofrece retorno al paso corregible correspondiente.
- Dark y System no reintroducen washes marrones/oliva ni pierden selected, warning o
  focus.
- Zoom y viewport reducidos adaptan composición antes de reducir tipografía o targets.

## Acceptance criteria

- AC-01: CRM-018 a CRM-029 continúan pasando sus regresiones funcionales aplicables; no
  cambian backend, contratos, rutas, reglas, permisos, navegación ni capacidades.
- AC-02: Manrope permanece como única familia y la implementación usa exactamente la
  escala semántica de CRM-030; body es 15 px y contenido esencial nunca baja de 13 px.
- AC-03: Workspace titles son 32/40, section titles 20/28, important identities 16/22,
  navigation 15/20 y primary metrics 40/44 a zoom 100 %.
- AC-04: `#F1B809` y `#1B3B5F` permanecen como fuentes institucionales; ningún
  componente introduce un amarillo alternativo o un hex feature-local.
- AC-05: Ninguna fila, card, banner, panel, columna, composer, párrafo o sección usa un
  background pale/cream/yellow derivado de accent o warning.
- AC-06: Selected y unread combinan superficie neutral/navy-derived, peso/forma/texto y
  marker FAA yellow sólido compacto; el estado se comprende sin color.
- AC-07: Warnings usan superficie neutral y evidencia local de icono/texto/borde junto a
  la acción afectada; Light y Dark alcanzan contraste WCAG 2.2 AA.
- AC-08: Dashboard y Lost son las únicas pantallas que incorporan los bloques navy
  sólidos estructurales definidos; el resto permanece neutral dominante.
- AC-09: Pipeline conserva exactamente cuatro etapas y toda semántica CRM-019, con
  columnas mínimas de 320 px, ancho preferido de 336 px, gap de 16 px y cards exteriores
  mínimas de 304 px.
- AC-10: A 1024, 1280 y 1440 px Pipeline no comprime columnas para hacerlas entrar; usa
  scroll horizontal local accesible y no genera overflow horizontal de página.
- AC-11: A 1440 px Customer/company, contacto y origen de cada card se leen cómodamente
  con la nueva escala y sin agregar campos ni acciones.
- AC-12: Pipeline usa columnas neutrales, headers con jerarquía navy y marker de etapa
  compacto; no tinta toda la columna ni depende sólo del color.
- AC-13: La primera lectura de Dashboard sigue Atención → cuatro KPIs → un único análisis
  y responde qué requiere atención, cómo estamos y qué inspeccionar.
- AC-14: Los cuatro KPIs visibles son oportunidades creadas, conversión por
  oportunidades, kg cotizados y kg ganados; seguimientos permanece en Atención y
  resultados cerrados en su análisis sin duplicación.
- AC-15: Dashboard muestra una sola vista entre Evolución, Resultados, Productos,
  Orígenes, Provincias y Pipeline; default es Evolución y la selección usa estado local.
- AC-16: Dashboard no contiene donuts. Resultados usa comparación directa; Products,
  Origins y Provinces usan barras horizontales; Pipeline usa barra segmentada o directa;
  todos muestran labels/valores sin depender de hover.
- AC-17: Datos exactos, null/zero/error/loading, timeline day detail y filtros existentes
  permanecen accesibles dentro de la vista activa sin nuevas métricas o requests.
- AC-18: Notifications mantiene la misma información y comportamiento; unread no usa
  cream wash, usa marker amarillo de 6–8 px, peso fuerte y superficie navy/neutral.
- AC-19: Notification rows tienen altura mínima cómoda de 68 px, identidad de 16/22 y
  metadata de 13/18, con reflow sin pérdida a 1024 px.
- AC-20: WhatsApp mantiene dos zonas, contratos y comportamiento; selected y waiting
  rows no usan pale yellow y el contexto CRM secundario conserva disclosure existente.
- AC-21: Restricción/template-required/waiting se comunica junto al composer mediante
  status compacto neutral; no existe background warning sobre todo el composer.
- AC-22: Conversation pane gana espacio y ritmo sin nueva información, y send,
  attachments, templates, polling, errores y foco siguen funcionando.
- AC-23: Broadcast creation presenta exactamente cinco pasos visibles: Template/content,
  Recipients, Eligibility/review, Confirm y Progress/results, con una decisión principal
  por paso.
- AC-24: Broadcast content, Customers, eligibility y confirmation nunca aparecen juntos;
  Back/Continue, Draft, version, validation, dirty, pending y error preservan CRM-025.
- AC-25: Broadcast history permanece simple y el quinto paso reutiliza el detalle,
  progreso y resultados existentes sin nueva funcionalidad.
- AC-26: Lost muestra primero kg/count actuales, después motivos como barras directas y
  finalmente oportunidades; el valor principal usa 40/44.
- AC-27: Lost usa navy sólido para jerarquía y red/coral sólo para badges/datos
  semánticos; no presenta superficies red/pink grandes.
- AC-28: Filtros avanzados de Lost permanecen bajo un único disclosure con count y no
  cambian contratos, cursor, permisos, reapertura ni listado.
- AC-29: En 1024×768, 1280×800, 1440×900 y 1600×900 no hay overlap, clipping, texto
  esencial ilegible ni page-level horizontal overflow; el único overflow horizontal
  previsto es local para Pipeline o tablas genuinamente anchas.
- AC-30: Light, Dark y System conservan la misma jerarquía, focus visible, targets,
  teclado, screen-reader labels, reduced motion y contraste AA.
- AC-31: La revisión visual explícita confirma Pipeline comfort, Dashboard cognitive
  load, ausencia de washed yellow, nueva escala, balance solid yellow/navy,
  Notifications unread, WhatsApp selected/warning, Broadcast steps y Lost hierarchy.
- AC-32: No se agrega ninguna dependencia, UI framework, chart library, global state,
  información o funcionalidad para completar espacio.

## Open decisions

None.

La spec permanece Draft hasta recibir aprobación explícita; `Open decisions: None` no
equivale a aprobación ni autoriza implementación.

## Follow-up / future specs

- Actualización deliberada de baselines y ejecución de la matriz transversal de CRM-026
  después de implementar CRM-030.
- Cualquier cambio futuro de backend, métrica, navegación o funcionalidad requiere su
  propia decisión/spec y queda fuera de CRM-030.

## Implementation notes

- Refinar tokens/primitives antes de superficies feature-locales.
- Reutilizar `PipelineColumn`, `SegmentedControl`, `ChartSurface`, controls, feedback y
  overlays existentes cuando su responsabilidad coincida.
- No crear una tabla o wizard genérico sólo para CRM-030. Extraer pasos de Broadcasts
  únicamente para separar responsabilidades concretas del flujo.
- Los charts continúan en SVG/DOM y sólo transforman agregados existentes para escala y
  presentación; la lógica comercial permanece en backend.
- Las pruebas futuras deben priorizar comportamiento, semántica, teclado, estados y
  layout medible; screenshots complementan y no sustituyen asserts.
- La implementación futura deberá completar todos los gates obligatorios del
  repositorio antes de cualquier commit o push de código.
