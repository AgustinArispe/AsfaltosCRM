# CRM-026 — Final Browser, Accessibility & Responsive QA

Status: Approved
Owner: FAA CRM team
Last updated: 2026-08-18
Implementation commit: N/A

## Goal

Validar FAA CRM como producto real en un navegador reproducible después de CRM-027,
CRM-028 y CRM-029, encontrar defectos, corregirlos dentro de los límites aprobados y
probar el estado final mediante journeys semánticos, accesibilidad, responsive, zoom,
temas, estados adversos y una baseline visual pequeña.

CRM-026 no redefine el diseño. CRM-027, CRM-028 y CRM-029 son la dirección visual y de
producto aprobada; CRM-018–025 conservan autoridad funcional por feature. Un cambio sólo
procede cuando QA demuestra un defecto contra esas fuentes.

## Context

FAA CRM usa React 19, TypeScript, Tailwind/Vite, un router interno tipado y FastAPI con
PostgreSQL. CRM-015 ya establece los gates estáticos, unitarios, de coverage, auditoría
y Docker Compose. CRM-029 dejó el stack canónico saludable y documentó como único gap
la falta de un runtime Playwright permitido para completar la matriz visual/browser.

El usuario autoriza expresamente instalar Playwright y las dependencias mínimas de
browser/testing necesarias para este cierre. La suite debe ser parte del repositorio,
usar datos sintéticos determinísticos, ejecutarse contra los servicios Docker Compose
canónicos y producir evidencia útil sin depender de estado personal, datos reales ni
infraestructura WhatsApp externa.

La instrucción explícita de CRM-026 reemplaza el supuesto anterior de un proyecto
Compose aislado con puertos alternativos: tanto local como CI usan exclusivamente el
proyecto `asfaltoscrm`, frontend `localhost:5173`, backend `localhost:8000` y la base
sintética protegida por `seed_visual_qa`. En CI el runner es efímero; localmente el seed
conserva todas sus guardas antes de cualquier reset.

## Dependencies

- CRM-001 — Core CRM, authentication and roles
- CRM-015 — Quality and Reproducibility Hardening
- CRM-016 — Security Hardening
- CRM-018 — Frontend Design System
- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-021 — Dashboard & Metrics
- CRM-022 — Notifications UI
- CRM-023 — WhatsApp Inbox 2.0
- CRM-024 — Customers, Products & Lost UI
- CRM-025 — WhatsApp Broadcast UI
- CRM-027 — Visual Design & Product Polish
- CRM-028 — Visual Clarity & Dashboard Simplification
- CRM-029 — Brand Identity & Dashboard Interaction Polish

## Scope

- Instalar y configurar Playwright para Python como dependencia de desarrollo bloqueada,
  con Chromium administrado por Playwright y un runner revisable del repositorio.
- Agregar sólo las dependencias auxiliares mínimas justificadas para auditoría a11y y
  comparación visual determinística si Playwright no las resuelve por sí solo.
- Documentar instalación, browser setup, variables, comandos locales, ejecución CI,
  artefactos y actualización deliberada de screenshots.
- Verificar el stack canónico, migraciones head y seed sintético antes de cada suite;
  restaurar el fixture conocido después de journeys mutantes.
- Ejercitar comportamiento real como `SUPERVISOR` y `VENDEDOR`, incluyendo visibilidad,
  permisos y acciones autorizadas, no sólo acceso a rutas.
- Cubrir autenticación, Pipeline, Opportunity, Quote, Lost, Dashboard, Notifications,
  WhatsApp, Envíos masivos, Customers, Products, Users, AppShell y navegación cruzada.
- Ejecutar matrices de viewport, zoom efectivo, sidebar, Light/Dark, reduced motion,
  teclado, estados adversos, console y network.
- Mantener una baseline visual acotada para superficies estables y determinísticas.
- Investigar y, si se reproduce, corregir el rechazo de `seed_visual_qa --reset` sobre
  teléfonos sintéticos ya normalizados, sin debilitar ninguna protección.
- Clasificar cada hallazgo P0/P1/P2/P3 y corregir obligatoriamente P0/P1/P2 dentro de
  CRM-026; corregir P3 sólo si es localizado, inequívoco y de bajo riesgo.
- Integrar el gate browser apropiado en GitHub Actions y ejecutar la suite completa del
  repositorio antes de marcar la spec `Implemented`.

## Non-goals

- Otro rediseño visual, una nueva dirección de color, layout o composición, o reabrir
  decisiones CRM-027/028/029 sin un defecto demostrable.
- Implementar capacidad comercial, permiso, filtro, métrica, estado, transición,
  contrato provider o regla de consentimiento nuevos.
- Debilitar autorización para facilitar una prueba, crear datos reales, contactar Meta
  o usar un provider distinto de Fake.
- Usar CRM-012/014/016, otro proyecto Compose, puertos alternativos, servidores Vite/
  FastAPI iniciados fuera de Docker o una base histórica como entorno browser.
- Convertir screenshots de cada página/estado en un gate masivo o afirmar correctness
  mediante pixels; las aserciones principales son semánticas y de negocio visible.
- Introducir Selenium, Cypress, una segunda librería E2E, un framework de componentes,
  un chart library, state management o dependencias no relacionadas.
- Crear CRM-030 u otra spec de visual polish automáticamente.

## Reproducible browser test architecture

### Runtime and ownership

La suite usa la API síncrona nativa de Playwright para Python, headless Chromium y
scripts/tests tipados bajo un directorio de quality/browser dedicado. El runner nunca
inicia servidores: primero verifica los servicios Docker Compose existentes y aborta
con una instrucción clara si frontend, backend o base no están saludables.

Los locators priorizan `get_by_role`, `get_by_label`, nombres accesibles y texto estable.
`data-testid` sólo se agrega cuando una estructura dinámica no tiene un selector
semántico razonable; no se seleccionan clases CSS ni estructura DOM accidental.

Configuración compartida controla base URLs, credenciales sintéticas, browser, locale
`es-AR`, timezone `America/Argentina/Buenos_Aires`, color scheme, reduced motion,
viewport, captura de trace y directorios de artefactos. La suite es serial cuando los
journeys mutan el fixture; ningún test depende de paralelismo ni de una carrera de poll.

### Environment preflight and reset

Antes de browser QA se verifica:

1. `docker compose -p asfaltoscrm --env-file .env.example ps` muestra database,
   backend y frontend healthy;
2. `/health` responde `status=ok` y `database=ok`;
3. `alembic current --check-heads` confirma head;
4. `seed_visual_qa --summary` reconoce el dataset sintético esperado; y
5. `seed_visual_qa --reset` recrea el fixture determinístico con Fake provider y las
   guardas de ambiente/base/ownership activas.

El runner no contiene una API de cleanup ni borra filas directamente. Tras una suite
mutante vuelve a ejecutar el mismo reset protegido para devolver el entorno canónico a
su baseline. Si el comando detecta datos ajenos, falla sin modificar nada.

### Console and network guard

Cada context registra `pageerror`, `console.error`, requests fallidas y respuestas 5xx.
La suite falla por excepciones runtime, errores React, warnings de hidratación/runtime,
requests inesperadamente fallidas o 5xx. Un test de error puede declarar de forma
local y explícita el endpoint/status esperado; la excepción nunca se convierte en una
allowlist global silenciosa.

Traces, screenshot actual, console/network log y reporte a11y se conservan al fallar.
En ejecuciones exitosas se retiene sólo el reporte resumido y las baselines versionadas.

## Roles and authorization matrix

### Supervisor

Se comprueba navegación completa, Users, catálogo Product completo, acciones
administrativas de Customers/Products/Users, edición de responsable, import CSV y todas
las acciones comerciales y de comunicación autorizadas.

### Vendedor

Se comprueba visibilidad global de Opportunities sin filtro por vendedor, ausencia de
Users y de controles supervisor-only, catálogo activo, acciones comerciales permitidas,
Customers, Lost, Notifications, WhatsApp y Envíos masivos conforme autorización real.
Acceso directo a una ruta supervisor-only debe quedar bloqueado de forma segura tanto
en UI como en API; el test no modifica permisos ni acepta sólo ocultamiento visual.

## Core journey matrix

### Authentication

- login válido para ambos roles;
- login inválido con error comprensible y sin sesión parcial;
- logout y retorno al login;
- ruta protegida sin sesión y deep link protegido después de autenticación.

### Pipeline and Opportunity

- carga de las cuatro etapas, búsqueda, sort, origen y filtros;
- abrir Opportunity con mouse y teclado;
- DnD pointer entre etapas permitidas y alternativa keyboard Space/flechas/Enter/Escape;
- optimistic state, rollback cuando corresponde, persistencia backend y reload;
- información Customer, Activity/Notes, note creation, WhatsApp handoff, Quote y Loss;
- acciones visibles según estado y rol, sin saltos de state machine.

### Quote

Se cubre `Producto -> Cantidad -> Revisar -> Confirmar`, selección grande, foco en kg,
Enter seguro, Escape/back, draft, validación, editar, quitar, múltiples líneas, una sola
confirmación final y resultado persistido. Cancelar o fallar no puede mover una
Opportunity `NUEVA` prematuramente.

### Lost

Se prueban búsqueda/filtros, evidencia histórica, detalle canónico y reapertura elegible
sólo a `NEGOCIACION`, con persistencia y aparición posterior en Pipeline.

### Dashboard

Se prueban CTAs de atención, cinco KPIs, selector Creadas/Ganadas/Perdidas, peak
significativo, click y keyboard focus de día no cero, detalle paginado y navegación.
Resultados cerrados expone total/conversión/ganadas/perdidas; Pipeline vigente expone
las cuatro etapas. Productos/Origen/Provincias preserva selector, valores, porcentajes y
detalle exacto accesible. También se verifica un estado sin actividad.

### Notifications

Se prueban estado read/unread, Todas/Sin leer, navegación, read individual,
`Marcar activas como leídas`, historia resuelta y sincronización del badge.

### WhatsApp

Con Fake provider se prueban selección, unread/waiting, mensajes inbound/outbound,
contexto CRM, Opportunity vinculada, suggestions/linking cuando existen, composer,
Enter/Shift+Enter, ventana freeform, template-required y attachment affordance. Se
verifican failed y `UNKNOWN` sin retry indebido ni contacto externo.

### Envíos masivos

Se valida que el propósito se entienda como templates aprobados a Customers explícitos,
no campaign builder. El journey cubre Draft, template, recipients, elegibilidad,
consentimiento, validación, confirmación deliberada, inicio/proceso y detalle/auditoría.
Las proyecciones disponibles deben representar DRAFT/PROCESSING/COMPLETED y outcomes
READ/DELIVERED/SENT/FAILED/UNKNOWN/BLOCKED sin inventarlos ni vaciar lotes desde browser.

### Customers, Products and Users

- Customers: búsqueda, detalle, create/edit, contenido largo, CSV como acción secundaria
  y controles supervisor-only;
- Products: active/inactive, create/edit, deactivate/reactivate e historia preservada;
- Users supervisor: list/create/edit, activate/deactivate y password administration;
- Vendedor: ausencia de administración y rechazo seguro de acceso directo.

## Responsive, zoom and themes

### Viewports

La matriz mínima usa `1920x1080`, `1440x900`, `1366x768`, `1280x800` y un viewport
narrow/mobile-class de `390x844`. Este último valida el contrato responsive básico,
drawer/one-panel fallbacks y acciones alcanzables; no exige una aplicación mobile-native.

En cada nivel relevante se inspeccionan sidebar expandida/colapsada o drawer responsive,
overflow de documento, acciones primarias, overlays, charts, donuts, tablas y regiones
scrollables. Pipeline puede tener scroll horizontal local; ninguna página puede tener
overflow horizontal persistente.

### Effective zoom

La matriz `100% | 125% | 150% | 200%` se reproduce reduciendo el CSS viewport efectivo
mientras se mantiene un framebuffer físico representativo. La relación se documenta
como `css viewport = physical viewport / zoom factor`; no se escala una screenshot ni
se usa `transform: scale`. Para Chromium, un control adicional con CDP/page scale sólo
se acepta si altera métricas CSS observadas y se valida mediante `innerWidth`,
`devicePixelRatio` y overflow; la reducción de viewport es el método portable de gate.

Dashboard, Pipeline, WhatsApp, Opportunity/Quote, Customers, Lost y Users se prueban a
150/200 cuando su layout es sensible. Donuts no se miniaturizan, panels no se solapan,
tablas conservan fallback/scroll local y dialogs mantienen header/body/actions accesibles.

### Light, Dark and reduced motion

Los journeys críticos se ejecutan en Light y Dark. System se cubre mediante una prueba
de persistencia/reacción a preferencia porque CRM-018 lo mantiene como tercera opción.
Se valida FAA yellow, stages, green local de WhatsApp, coral Lost, focus, selected,
disabled, modal separation y chart distinction sin alterar colores salvo defecto medido.

Un proyecto/contexto con `reduced_motion="reduce"` verifica que no existan animaciones
espaciales/loops obligatorios y que datos, focus y acciones sean inmediatos.

## Accessibility verification

La suite combina auditoría automática WCAG con journeys keyboard-first. La dependencia
a11y, si se agrega, debe ser un wrapper pequeño o el motor Axe oficial, ejecutado sólo
en rutas reales ya cargadas. No reemplaza Biome ni las aserciones de interacción.

Se verifica:

- landmarks, heading order y nombres accesibles;
- labels/descriptions, required, `aria-invalid` y errores vinculados;
- Tab/Shift+Tab, Enter, Space y Escape según cada widget;
- focus visible, trap modal, foco inicial, retorno al trigger y ausencia de foco perdido;
- buttons/links/rows/charts con semántica nativa o patrón ARIA completo;
- live/status feedback mesurado, disabled explicable y estado no sólo por color;
- tablas/listas/legends y exact detail para visualizaciones;
- acceso keyboard al detalle diario de Dashboard; y
- reduced motion.

Una violación automática sólo puede excluirse si es falsamente positiva y existe una
justificación concreta, localizada y versionada. No se permiten disable rules globales.

## Error, empty and loading evidence

Journeys o intercepts locales prueban loading, vacío, validación, API failure,
unavailable, permission denied, mensaje WhatsApp failed, `UNKNOWN`, Dashboard sin
actividad, stage vacío y búsqueda sin resultados. Cada caso debe comunicar qué ocurrió,
si algo fue guardado y cuál es el siguiente paso posible. Los intercepts no simulan una
regla de negocio ni dejan una allowlist de errores activa fuera del test.

## Visual regression baseline

La baseline versionada queda limitada a:

1. Pipeline desktop Light;
2. Dashboard desktop Light;
3. WhatsApp desktop Light;
4. Opportunity detail;
5. Quote modal;
6. Dashboard desktop Dark;
7. Pipeline a 150% efectivo; y
8. WhatsApp responsive.

Usa seed/reset determinístico, clock/viewport/theme/reduced-motion fijados, fonts listas
y masking sólo de evidencia genuinamente inestable. La comparación permite un umbral
pequeño documentado para rasterización; un cambio se actualiza deliberadamente y se
revisa, nunca mediante aceptación automática. Las screenshots no sustituyen asserts de
roles, labels, datos o estado.

## Defect policy

| Priority | Meaning | CRM-026 action |
| --- | --- | --- |
| P0 | Seguridad, data loss o core product inutilizable | Corregir y volver a ejecutar toda la aceptación. |
| P1 | Workflow primario roto | Corregir y cubrir con regresión browser/unitaria. |
| P2 | Accesibilidad, responsive o usabilidad real | Corregir y verificar en toda la matriz afectada. |
| P3 | Cosmetic polish | Corregir sólo si es localizado, evidente, bajo riesgo y coherente con CRM-027/028/029. |

Un fix que cambie materialmente UX aprobada, datos, seguridad o negocio se documenta y
queda fuera; no se implementa silenciosamente. CRM-026 permanece Draft/Approved, nunca
Implemented, mientras exista un P0/P1/P2, blocker a11y/responsive o error runtime conocido.

## Seed reset investigation

Se reproduce el caso `seed_visual_qa --reset` con teléfonos sintéticos ya normalizados.
Si el guard compara representaciones equivalentes de forma inconsistente, el fix debe
normalizar sólo dentro de la identificación exacta del fixture antes de decidir ownership.
Permanecen obligatorias las guardas de development, Fake provider, nombre de database,
dataset ownership y abort-before-mutation. Reset debe ser idempotente; tests cubren
baseline, forma normalizada, dato ajeno y prohibiciones de producción/provider/base.

## CI and documentation

GitHub Actions agrega un job browser independiente que:

1. instala locks Python/frontend;
2. instala el Chromium exacto con sus dependencias del sistema;
3. construye y levanta `docker compose -p asfaltoscrm --env-file .env.example`;
4. verifica health/migrations y carga/reset el seed sintético;
5. ejecuta Playwright/a11y/visual en headless mode;
6. sube trace, screenshots actuales, console/network y reporte sólo ante fallo; y
7. detiene el stack canónico del runner efímero.

El runbook documenta instalación local del browser, comandos de preflight/reset, suite
funcional, matriz completa, actualización visual y ubicación de artifacts. CI no usa
credenciales Meta, datos reales ni estado mutable externo.

## Quality gates

Antes de aceptación final pasan:

- frontend: Biome, TypeScript, Vite production build, 160+ unit/integration tests,
  coverage vigente, npm audit y Playwright;
- backend: Ruff check/format, mypy strict, compileall, full pytest/coverage >= 93%,
  Alembic check/current, lock verification y dependency audit;
- infrastructure: Docker Compose smoke, health, proxy/API, authentication,
  seed/reset canónico y `git diff --check`;
- GitHub Actions final con backend, frontend, browser y Docker jobs verdes.

## Acceptance criteria

- AC-01: La spec y el runbook reflejan CRM-027/028/029 como baseline aprobada, el stack
  canónico exclusivo y ninguna decisión de rediseño nueva.
- AC-02: Playwright Python y Chromium están bloqueados/reproducibles; instalación,
  browser setup, comandos, environment, CI y artifacts están documentados.
- AC-03: Preflight prueba frontend/backend/database healthy, Alembic head y seed
  sintético; reset protegido es idempotente antes/después de journeys mutantes.
- AC-04: Supervisor y Vendedor pasan la matriz de navegación, permissions, Users,
  Customers, Opportunities, WhatsApp, Envíos masivos y data visibility sin debilitar auth.
- AC-05: Authentication cubre login válido/inválido, logout y protected/deep-link routes.
- AC-06: Pipeline cubre toolbar, filtros, Opportunity, DnD pointer/keyboard, optimistic/
  rollback, persistencia y reload sin alterar state machine.
- AC-07: Opportunity/Quote/Loss/Reopen cubren detalle, Activity/Notes, handoff WhatsApp,
  cuatro pasos Quote, keyboard/draft/validation y resultado autoritativo persistido.
- AC-08: Dashboard cubre attention, KPIs, series/peaks/day detail, donut closed,
  Pipeline vigente, dimensions y exact alternatives con significado backend correcto.
- AC-09: Notifications, WhatsApp Fake y Envíos masivos cubren sus estados, mutaciones,
  constraints, outcomes e historia sin side effects externos ni retry prohibido.
- AC-10: Customers, Products y Users cubren CRUD/activation/deactivation/password/import
  según rol, long content y preservación histórica aprobada.
- AC-11: Viewports 1920/1440/1366/1280 y 390, sidebar variants y zoom efectivo
  100/125/150/200 no producen page overflow, clipping, overlap ni controles off-screen.
- AC-12: Light/Dark y System persistence conservan contraste/semántica; reduced motion
  deja toda información e interacción inmediata.
- AC-13: Auditoría automática y keyboard-first no dejan violaciones WCAG críticas/serias,
  focus traps rotos, nombres ausentes, errores desvinculados ni chart detail inaccesible.
- AC-14: Estados loading/empty/error/unavailable/permission/failed/UNKNOWN/no-results
  comunican resultado, persistencia y siguiente acción sin inventar datos.
- AC-15: No quedan excepciones runtime, `console.error`, React warnings, 5xx ni requests
  fallidas inesperadas; fallos intencionales están acotados al test que los provoca.
- AC-16: Las ocho baselines visuales son determinísticas, pequeñas, revisables y verdes;
  screenshots siguen siendo guard complementario, no aserción primaria.
- AC-17: Hallazgos están registrados con P0/P1/P2/P3, evidencia y fix/defer; todo P0/P1/
  P2 y blocker release está resuelto antes de `Implemented`.
- AC-18: El defecto de teléfono normalizado de `seed_visual_qa --reset` queda reproducido
  y corregido con cobertura, o documentado como no reproducible sin debilitar guardas.
- AC-19: Todos los quality gates locales y el job CI browser reproducible pasan; failure
  artifacts son útiles y success artifacts permanecen acotados.
- AC-20: El reporte final incluye setup/version/browser, roles/journeys, matrices,
  a11y/motion/visual/console, defectos, seed, tests/coverage/audits, Docker, CI, commits,
  worktree y las siete respuestas explícitas de release readiness.

## Open decisions

None.

## Follow-up / future specs

- Operaciones/deployment/recovery continúan bajo CRM-017; CRM-026 no los redefine.
- Safari o Firefox sólo se agregan si FAA define una necesidad operacional posterior.
- Cualquier cambio material de UX/negocio descubierto se documenta para la spec
  propietaria y no genera automáticamente otra spec visual.

## Implementation notes

Implementar sólo después de publicar esta revisión Draft y establecer `Status:
Approved`. Mantener commits separados para Draft, aprobación, implementación verificada
y documentación `Implemented` con el hash final. Registrar la aceptación en un reporte
versionado sin datos sensibles, incluyendo defectos y evidencia de cada matriz.
