# CRM-026 — Frontend 2.0: accesibilidad, responsive y pulido final

Status: Draft
Owner: FAA CRM team
Last updated: 2026-08-13
Implementation commit: N/A

## Goal

Definir el pase final transversal de calidad para FAA CRM Frontend 2.0 una vez que
las especificaciones de rediseño por feature estén implementadas. No introduce
ninguna capacidad de negocio: verifica que el CRM completo se perciba como un único
producto premium, rápido, coherente, accesible y resistente al espacio disponible.

CRM-018 es la autoridad visual y de interacción. CRM-019 a CRM-025 mantienen la
autoridad de comportamiento de cada workspace; esta spec sólo comprueba y corrige su
consistencia de presentación e interacción dentro de esos límites.

## Context

FAA CRM es un producto interno, desktop-first, para trabajo comercial sostenido. La
base actual es React 19, TypeScript, Tailwind/Vite, router interno pequeño, módulos API
tipados y primitives iniciales. CRM-015 ya establece Biome, TypeScript/Vite build,
Vitest/Testing Library con coverage y npm audit; Biome tiene diagnósticos a11y
habilitados. La suite actual usa jsdom, no tiene runner browser/E2E ni framework a11y
adicional.

La aplicación actual todavía refleja la UI anterior en varios lugares. Este pase ocurre
después de implementar CRM-018 a CRM-025 y no convierte sus actuales implementaciones,
sus Open decisions ni sus contratos backend en requisitos nuevos. La UI debe seguir
renderizando evidencia backend autoritativa, no duplicar reglas comerciales.

## Dependencies

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

## Scope

- Auditoría y corrección transversal de consistencia visual, interacción, accesibilidad,
  teclado, responsive/zoom, motion, carga/error/vacío, perceived speed y browser QA.
- Validación de todas las superficies autenticadas: AppShell/sidebar, Pipeline,
  Opportunity/quote, Dashboard, Notifications, Inbox WhatsApp, Customers, Products,
  Lost, Envíos WhatsApp, usuario/cuenta y Login cuando corresponda.
- Revisión del uso efectivo del sistema CRM-018 y consolidación limitada de primitives
  donde una responsabilidad ya sea realmente compartida.
- Matriz repetible de QA manual y automatizada para rutas, temas, zoom, diálogos,
  navegador y flujos representativos mediante Docker Compose.
- Revisión de dependencias y rendimiento frontend después de las implementaciones de
  CRM-019 a CRM-025.
- Revisión de un modelo interno de navegación/deep link común para los handoffs que
  cruzan workspaces.

## Non-goals

- Agregar una funcionalidad comercial, modificar reglas de negocio, permisos,
  consentimiento, contratos backend o state machines, salvo bloquear y referenciar una
  necesidad ya identificada por la spec propietaria.
- Rediseñar o reinterpretar los requisitos de CRM-019 a CRM-025.
- Crear producto mobile-native, patrones de marketing site, motion decorativo,
  pixel-perfect screenshot coupling, global state management sin evidencia, o sustituir
  React/TypeScript/Tailwind/Vite.
- Añadir más de un framework de accesibilidad, una librería duplicada, un runtime de
  fuente externa, o una dependencia de visual regression no justificada.
- Prometer soporte de navegadores legacy o Safari sin necesidad operativa FAA.

## Cross-product QA model

La validación final se ejecuta por capas, en este orden:

1. **Sistema y rutas.** AppShell, navegación, tokens, tema, tipografía, primitives,
   rutas, foco de página y estados globales.
2. **Workspaces.** Cada módulo se revisa contra sus AC ya aprobados, sin reabrir su
   modelo de negocio.
3. **Cruces.** Se prueba la continuidad entre Pipeline, Opportunity, Lost, Customer,
   Notifications, Inbox y Broadcasts mediante el contrato de navegación compartido.
4. **Condiciones reales.** Teclado, tamaños/zoom, Light/Dark/System, reduced motion,
   carga/refresco/error/vacío y navegador.
5. **Rendimiento y regresión.** Se mide antes de añadir complejidad, se ejecutan gates
   existentes y se conserva evidencia útil y no frágil.

Cada hallazgo se clasifica como: incumplimiento de CRM-018/feature, defecto de
accesibilidad/UX, regresión responsive/performance, o bloqueo de contrato. Un bloqueo
no se resuelve con fallback silencioso de frontend.

## Global visual consistency and design-system enforcement

Todas las rutas auditadas deben usar tokens semánticos CRM-018, IBM Plex Sans
autoalojada en pesos aprobados 400/500/600, Light/Dark/System, ritmo de espacio 4/8,
shape/radius/elevation compartidos, jerarquía clara de controles y focus visible.
FAA amarillo es selectivo para identidad, foco, selección y acción importante; éxito,
advertencia y destrucción conservan tokens semánticos y siempre texto/forma además de
color. Legendary mantiene su tratamiento aprobado sin competir con información
operativa.

La auditoría identifica botones, badges, inputs/selects, modals/dialogs, toasts,
feedback, tooltips, filtros, colores directos, radios, sombras y patrones de interacción
duplicados. Una feature adopta el primitive CRM-018 cuando su responsabilidad ya exista;
una consolidación sólo procede si elimina divergencia real de semántica, accesibilidad o
comportamiento. Markup verdaderamente único no se abstrae preventivamente.

Ninguna ruta debe parecer otra aplicación: Dashboard puede ser más elevado
analíticamente y WhatsApp más familiar para mensajería, pero ambos mantienen la misma
tipografía, tokens, control hierarchy, estados, motion y aplicación FAA.

## AppShell and sidebar

La auditoría cubre sidebar expandida y colapsada: logo/orientación, iconos pequeños con
tooltip/nombre accesible, ruta activa distinguible por posición/forma/peso además de
color, badge de Notifications según estado backend, cuenta/usuario anclada y toggle
teclado-operable. Persistencia de sidebar y tema sigue el contrato CRM-018 y no puede
alterar sesión ni trabajo en curso.

Cambiar de sidebar no provoca saltos perceptibles, pérdida de foco, scroll inesperado,
cierre de Draft/diálogo seguro ni ancho inutilizable para el contenido. Las rutas
cambian el foco al heading/main según CRM-018 sin borrar selección, filtros, composer o
trabajo no enviado que la feature deba conservar.

## Keyboard and dialog strategy

El modelo global exige Tab/Shift+Tab en orden lógico, focus visible, controles nativos,
Space/Enter donde correspondan, Escape sólo para overlay seguro, restauración de foco
tras diálogo y ningún foco perdido después de mutación, navegación o refresh. Focus trap
se usa únicamente en modal/dialog; popovers, menus y regiones scrollables mantienen
modelos apropiados y no crean trampas.

Las excepciones son explícitas y no se homogeneizan de modo peligroso:

| Contexto | Comportamiento que se verifica |
| --- | --- |
| Pipeline | Enter abre card; DnD tiene alternativa de teclado Space/flechas/Enter/Escape. |
| Opportunity | Enter sólo ejecuta acción segura; formularios protegen cambios sucios y Notes conserva semántica multilinea. |
| Quote | Enter progresa sólo el paso/foco seguro y nunca duplica submit final. |
| WhatsApp | Enter envía mensaje válido; Shift+Enter agrega línea; foco y composer sobreviven refresh apropiado. |
| Broadcast | Enter nunca confirma ni inicia una ejecución inmutable accidentalmente. |
| Destructivo | Ninguna regla global de Enter facilita pérdida, desactivación, eliminación, reopen o confirmación irreversible. |

Todos los diálogos comparten geometry, scrim/backdrop, título/descripción, foco inicial,
trampa, Escape/backdrop seguro, restauración de trigger, scroll interno, tamaño máximo
responsive, acciones alineadas y protección dirty/pending. Se evita stack de diálogos:
subflujos cambian contenido/paso dentro de un solo diálogo cuando sea apropiado.

## Accessibility strategy

El objetivo es WCAG 2.2 AA donde aplique. La revisión por ruta incluye landmarks y
jerarquía de headings, nombres accesibles, labels/descripciones, aria-invalid y
asociación de errores, controles keyboard-reachable, orden/foco, semántica de diálogo,
live regions mesuradas, estados no sólo por color, contraste Light/Dark, loading/
disabled, tablas/listas útiles, alternativas exactas de charts, icon-only controls y
tooltips accesibles.

Se prefieren HTML y primitives nativos antes que ARIA adicional. Inputs tienen label
visible; iconos decorativos están ocultos a lectores; controles icon-only tienen nombre;
errores críticos son anunciables junto al campo y un toast nunca es la única evidencia
de un fallo accionable. Carga/refresco no anuncia cada poll ni roba foco. Charts
conservan tabla/resumen/valores exactos según CRM-021.

Biome a11y continúa como diagnóstico estático. Testing Library/Vitest añade sólo tests
focalizados de roles, nombres, keyboard, diálogos, focus y estados críticos. Una
integración automatizada a11y se evalúa únicamente si funciona con el stack mantenido,
cubre rutas reales y evita duplicar Biome o una segunda suite de reglas superpuesta.
Automatización complementa, nunca reemplaza, revisión manual de teclado, contraste,
screen reader y navegador.

## Responsive and zoom matrix

La matriz prueba el espacio real disponible luego de sidebar expandida y colapsada, no
sólo presets de dispositivo. Incluye large desktop, normal desktop, laptop, narrow
supported desktop, y zoom 125 %, 150 % y 200 % donde el flujo sea sensible a
accesibilidad. Se revisan por lo menos:

| Área | Resultado requerido |
| --- | --- |
| General/AppShell | Sin overflow horizontal persistente; navegación, heading y acción primaria alcanzables. |
| Dialogs/forms | Tamaño máximo adaptable, scroll interno, header/actions alcanzables, texto sin solape. |
| Pipeline | Columnas con mínimo definido y board-local horizontal scroll cuando lo requiere CRM-019; no scroll de página. |
| Dashboard | Grids reflow; chart/tabla conserva lectura y alternativa textual. |
| WhatsApp | Chat central se mantiene prioritario; panels se adaptan sin romper composer/historial. |
| Tables/lists | Columnas prioritarias, detalle o región scrollable etiquetada; no tipografía reducida por debajo de umbral legible. |
| Broadcasts | Pasos, validación y recipient list conservan acciones y conteos con scroll contenido. |

No se desactiva zoom ni se achica tipografía esencial para conservar un layout. Se
prueban etiquetas españolas largas, fechas/números tabulares, estados, filtros activos,
mensajes de error y contenido vacío.

## Forms, loading, errors and empty states

La auditoría recorre Customer, Product, Opportunity edit, Quote, Loss, Reopen, Notes,
imports, Broadcast creation, template/media WhatsApp y cuenta. Verifica labels,
requerido/opcional, tipo/autocomplete cuando corresponda, helper/error asociado,
Save/Cancel, pending/disabled explicable, reglas Enter/Escape, dirty protection y éxito
sin borrar entrada ante fallo recuperable.

La jerarquía común de estados es:

| Situación | Tratamiento |
| --- | --- |
| Carga inicial de ruta | Skeleton contextual que reserva geometry; no spinner de página rutinario. |
| Carga acotada | Skeleton/local loading del panel, tabla, diálogo o sección afectada. |
| Refresco background | Contenido actual permanece; indicador de actualización sólo si ayuda. |
| Mutación | Pending y resultado en el control/entidad afectada; previene duplicado. |
| Poll/red recuperable | Último dato bueno, indicador stale/conexión y retry acotado. |
| API/validación | Mensaje seguro, consistente, accionable y próximo al contexto. |
| Vacío | Diferencia ausencia real, resultado de filtro/búsqueda y estado específico como no leídas, no métricas, no Lost o no elegibles. |

No se exponen HTTP, SQL, nombres de clase/dominio, provider, storage ni detalles
internos; el frontend traduce evidencia backend segura sin inventar causa. Vacíos son
compactos y útiles, sin ilustraciones enormes ni copy de marketing.

## Motion and perceived performance

Motion operativo es corto, funcional, interrumpible y tokenizado: microfeedback
aprox. 150–220 ms, overlays hasta 240 ms y salida más rápida. Se anima opacidad/
transform, no geometry/layout; ningún transition bloquea input, se repite para llamar
atención, ni simula tiempo real. Dashboard puede revelar cambios analíticos con algo más
de riqueza, pero refresh rutinario no reinicia gráficos ni distrae.

prefers-reduced-motion: reduce elimina movimiento espacial/continuo, scroll animado,
revelaciones repetidas y demoras; deja un estado genuinamente calmo, inmediatamente
legible y operable.

La QA mide route change, open dialog, Pipeline drag/transición, typing y actualizaciones
WhatsApp, filtros, Dashboard y recipient views de Broadcast. Objetivos: acknowledgement
inmediato, mínima inestabilidad visual, preservación de datos autoritativos durante
refresh, ausencia de blanking innecesario y ninguna feature cara bloqueando navegación o
input principal. Lazy loading, memoización, code splitting y virtualización sólo se
adoptan ante perfil/medición que justifique su coste.

## Dependencies, bundle and browser/theme QA

La revisión de dependencias verifica que no haya dos librerías para una responsabilidad,
que la decisión de charts de CRM-021 sea medida y accesible, que icon/font/chart bundles
sean proporcionados y que IBM Plex sea sólo autoalojada en pesos aprobados. Route/feature
lazy loading se aplica cuando el análisis de chunk e interacción lo justifican, no como
optimización ritual. No hay dependencia runtime de fuentes de terceros.

La baseline inicial de QA es Chrome/Chromium estable actual y Edge estable actual, por
ser el mínimo de esta spec y compatibles con el stack moderno. Firefox se prueba para
comportamiento browser-sensitive (dialog, DnD, scroll, focus o CSS) o cuando FAA lo use;
Safari se incorpora sólo con requerimiento operativo FAA. No se promete legacy support.
La decisión de navegadores soportados se documenta antes de producción.

Cada ruta se revisa en Light, Dark y System: primera pintura sin theme flash, persistencia
sin perder workflow, surfaces, borders, focus, disabled, warning/success/destructive,
FAA yellow, Legendary, charts, tooltips y diálogos con contraste intencional. System
sigue cambio de preferencia según CRM-018 sin quebrar trabajo activo.

## Functional browser QA and quality gates

Los journeys se ejercitan contra la aplicación real levantada por Docker Compose y
localhost:5173/localhost:8000, según la política del repositorio. Datos de QA son
controlados y se eliminan mediante procedimiento seguro y acotado después de cada
ejecución. La matriz funcional incluye:

- login/logout/restauración de sesión;
- Pipeline filtros/sort, transición drag y alternativa teclado;
- Opportunity detail/edit, Quote, Loss y Reopen;
- Customer create/edit/import y Product management;
- Notifications read/navigation;
- Dashboard filters y estados;
- WhatsApp conversation, send y media;
- Broadcast create/validation sólo cuando los contratos aprobados lo permitan;
- sidebar collapse, tema y navegación/deep links.

Se preservan gates CRM-015: TypeScript strict, Biome, tests frontend/coverage vigente,
Vite build y npm audit. Cualquier browser/a11y check nuevo entra sólo si tiene runtime
y mantenimiento razonables, es estable contra Docker y produce señal clara. No se hace
obligatorio un screenshot pixel-perfect; visual regression se propone sólo con
justificación medida.

## Cross-spec routing review

CRM-019, CRM-020, CRM-022, CRM-023, CRM-024 y CRM-025 deben converger en una única
representación interna tipada de navegación. Debe poder abrir contexto exacto de
Opportunity activa, Opportunity perdida, Customer y conversación WhatsApp, preservar
return/origen razonable y no crear combinaciones independientes de query params, estado
efímero o hacks por feature.

La revisión determina el cambio mínimo sobre el router interno actual: URL/ruta,
parámetros validados, estado de retorno transitorio cuando aporte valor, restauración de
foco y fallback seguro ante entidad no disponible. No agrega endpoint ni cambia contratos
de negocio. CRM-026 no elige silenciosamente esta representación mientras las specs
dueñas la mantengan abierta.

## Acceptance criteria

- AC-01: Rutas autenticadas, Login cuando aplique y AppShell se revisan como producto
  único y cumplen tokens, IBM Plex, themes, shape, spacing, surface, control hierarchy,
  focus, status y FAA-yellow CRM-018.
- AC-02: Duplicaciones de primitives/patrones se consolidan sólo con responsabilidad
  real; no quedan one-off colors/radii/shadows ni interacción divergente donde CRM-018
  provee contrato.
- AC-03: Sidebar expandida/colapsada conserva orientación, active route, tooltips,
  badge backend, cuenta, teclado, persistencia y ancho útil sin interrumpir trabajo.
- AC-04: Tab, Shift+Tab, Space, Enter, Escape, foco de ruta/mutación y retorno de
  diálogo son consistentes; excepciones Pipeline/Opportunity/Quote/WhatsApp/Broadcast
  protegen acciones riesgosas.
- AC-05: Auditoría WCAG 2.2 AA por ruta cubre semántica, nombres, labels/errors, focus,
  dialogs, live regions, contraste, estados no-color, tablas/listas/charts e icon-only
  controls; automatización focalizada complementa keyboard/browser manual.
- AC-06: Matriz de viewport, sidebar y zoom 125/150/200 % verifica acciones, texto,
  dialogs, charts, tables/lists, Pipeline scroll local, chat prioritario y ningún
  overflow persistente de página.
- AC-07: Dialogs comparten geometry, backdrop, focus trap/inicial/retorno, Escape
  seguro, scroll/tamaño responsive, acciones y dirty protection sin stacks evitables.
- AC-08: Formularios comparten labels, required/optional, validación asociada, pending,
  Save/Cancel, Enter/Escape, dirty handling y preservación ante fallo.
- AC-09: Carga inicial, scoped load, refresh, mutación, polling/red, API/validación y
  vacío son contextuales, seguros, distinguibles y preservan último contenido útil.
- AC-10: Motion usa tokens funcionales, no bloquea input ni produce jank/atención
  repetida; reduced motion es realmente calmo.
- AC-11: Perceived-performance QA mide flujos críticos, evita blanking/layout shift y
  adopta lazy loading/memoización/virtualización sólo con evidencia.
- AC-12: Dependencias, chunks, fonts, icons y charts no duplican responsabilidad ni
  agregan peso injustificado; no hay font runtime third-party.
- AC-13: Chrome/Chromium y Edge actuales pasan matriz funcional; Firefox/Safari se
  incluyen según baseline operacional, sin promesa legacy.
- AC-14: Light, Dark y System pasan rutas, charts/tooltips/dialogs/focus/status con
  contraste correcto, sin theme flash ni pérdida de workflow.
- AC-15: Journeys Docker Compose cubren login, Pipeline, Opportunity/Quote/Lost,
  Customer/Product/Import, Notifications, Dashboard, WhatsApp, Broadcast cuando sea
  posible, sidebar y theme con datos QA limpiados de forma segura.
- AC-16: TypeScript, Biome, tests/coverage, build, audit y smoke CRM-015 siguen como
  gates; pruebas browser/a11y nuevas son estables, proporcionadas y no pixel-perfect.
- AC-17: Navegación interna coherente cubre Opportunity activa/perdida, Customer e
  Inbox exacto, con return/focus seguro y sin hacks por feature.
- AC-18: Un vendedor se orienta sin entrenamiento de estructura, encuentra acciones
  frecuentes con poca búsqueda, acelera con teclado y percibe FAA, Dashboard e Inbox
  como partes intencionales de un producto incluso con zoom.

## Open decisions

1. **Navegación transversal tipada.** CRM-022, CRM-023, CRM-024 y CRM-025 ya registran
   como bloqueo una representación común Opportunity/Customer/Inbox. Antes de aprobar
   CRM-026 debe resolverse por la spec/decisión dueña; CRM-026 sólo valida su aplicación
   transversal y no duplica contratos.
2. **Entorno y datos repetibles de browser QA.** Existen Vitest/jsdom y Docker Compose,
   pero no un runner browser ni fixture/cleanup aprobado para journeys Frontend 2.0.
   Antes de convertir la matriz en gate, aprobar la menor estrategia reproducible que
   use Docker, datos controlados y limpieza segura, junto con baseline FAA Chrome/Edge y
   cualquier necesidad Firefox/Safari.

Una spec no puede pasar a Approved mientras estas decisiones sigan abiertas.

## Follow-up / future specs

- Cambio backend o contrato producto que desbloquee una decisión CRM-020 a CRM-025 queda
  en su spec propietaria.
- Visual regression sólo si el equipo mide valor superior a coste y define baselines
  semánticos/no frágiles.
- Auditoría periódica de accesibilidad y browser baseline posterior a producción.

## Implementation notes

Este pase se planifica después de implementar las specs feature-specific aprobadas. Cada
corrección conserva dueño de feature y se prueba contra su AC más matriz CRM-026. No
introducir dependencia, state store, abstracción compartida o cambio router sin evidencia
y decisión aprobada. La evidencia QA registra entorno, viewport/zoom, tema, navegador,
ruta/flujo, resultado e issue vinculado, nunca información sensible de Customers o
WhatsApp.
