# CRM-018 — Frontend 2.0

Status: Draft
Owner: Frontend / Product Design
Last updated: 2026-08-28
Implementation commit: N/A

## Goal

Rediseñar y simplificar la experiencia visual del CRM de FAA sin cambiar sus reglas de
negocio, contratos, capacidades ni arquitectura funcional. La interfaz debe sentirse
calma, precisa, moderna, distintiva y extremadamente fácil de recorrer durante el uso
diario de oficina.

El principio rector es: **menos es más**.

Frontend 2.0 no busca llenar el espacio disponible ni sumar información. Busca ordenar
mejor la información existente, reducir repetición, dar prioridad clara a cada flujo y
formalizar un sistema visual pequeño que permita que todas las superficies se sientan
parte del mismo producto.

## Context and authority

Esta revisión reabre CRM-018, previamente implementada por el commit
`370005d65c684c29d8fd9a255f4c728623d32200`, exclusivamente para reemplazar decisiones
de presentación y UX. Las capacidades y reglas implementadas por CRM-019 a CRM-029
continúan siendo el baseline funcional y de regresión.

Ante un conflicto, se aplica la jerarquía definida en `AGENTS.md`: requisito explícito
aprobado, `docs/BUSINESS_RULES.md`, spec funcional aprobada, implementación y tests.
Esta spec no modifica `docs/BUSINESS_RULES.md`.

La auditoría se realizó sobre las pantallas, componentes, estilos y tests actuales del
frontend, incluyendo los baselines visuales disponibles. Los hallazgos principales son:

- el Pipeline ya tiene una estructura correcta de cuatro columnas y tarjetas compactas;
- Dashboard conserva información útil, pero la distribuye entre demasiada microcopy,
  contenedores y elementos con peso visual similar;
- Notifications restringe el contenido a `52rem`, dejando una franja horizontal ociosa;
- WhatsApp combina lista, conversación y contexto CRM con información repetida y una
  jerarquía insuficiente entre la conversación y el panel de apoyo;
- Broadcasts presenta estados y pasos cercanos al modelo técnico antes de explicar el
  flujo mental del usuario;
- Customers y Products ya tienen bases de tabla simples, pero pueden mejorar densidad,
  alineación y jerarquía;
- Lost sigue leyéndose como una tabla administrativa, no como un espacio de análisis
  comercial;
- AppShell repite controles de cuenta, tema y sesión en un pie visualmente cargado;
- existen primitivas útiles, pero se superponen `LoadingState`, `WorkspaceSkeleton`,
  estados de `StatusStates`, `InlineFeedback` y variantes locales de badges, toolbars y
  superficies;
- la fuente actual, IBM Plex Sans, es legible y sólida, pero comunica una identidad más
  técnica y neutral que la buscada para esta etapa;
- el amarillo institucional existe como `#F1B809`; el navy institucional todavía no
  forma parte del sistema.

## Dependencies and affected specifications

Esta spec preserva los comportamientos aprobados e implementados de:

- CRM-019, Pipeline;
- CRM-020, detalle de oportunidad y cotización;
- CRM-021, Dashboard;
- CRM-022, Notifications;
- CRM-023, WhatsApp Inbox;
- CRM-024, Customers, Products y Lost;
- CRM-025, WhatsApp Broadcasts;
- CRM-027, CRM-028 y CRM-029 como baseline visual previo que esta spec reemplaza donde
  exista una diferencia explícita.

CRM-026 deberá actualizar sus baselines visuales después de implementar y aprobar esta
spec. Sus requisitos de evidencia, navegación y pruebas siguen vigentes.

## Scope

- tokens semánticos de color, tipografía, espacio, superficies, bordes, radios, elevación
  y motion;
- nueva tipografía institucional de producto;
- consolidación limitada de primitivas compartidas existentes;
- AppShell y navegación lateral;
- Pipeline y detalle de oportunidad;
- Dashboard;
- Notifications;
- WhatsApp Inbox;
- Broadcasts / Envíos masivos;
- Customers;
- Products;
- Lost opportunities;
- estados vacíos, loading, error y feedback;
- accesibilidad, responsive de laptop/escritorio, consistencia y performance;
- actualización de tests de comportamiento y baselines visuales afectados.

## Non-goals

- cambios de backend, dominio, persistencia, schemas, endpoints o contratos API;
- cambios en reglas comerciales, roles, permisos, visibilidad o máquinas de estados;
- crear campañas de marketing o plantillas de WhatsApp desde el CRM;
- eliminar capacidades existentes de WhatsApp o Broadcasts;
- Redux, un nuevo store global o una reescritura de React;
- una biblioteca grande de componentes o un framework visual externo;
- reemplazar Tailwind CSS;
- un rediseño mobile del producto;
- nuevas métricas, filtros, campos, datos o funcionalidades para ocupar espacio;
- gráficos 3D, gradientes, glassmorphism, fondos decorativos o motion ornamental;
- snapshots extensos como estrategia principal de testing;
- cambios en Users o Login, salvo la aplicación consistente de tokens, tipografía,
  estados y accesibilidad compartidos.

## Design principles

### Less is more

Cada elemento debe justificar su presencia por una tarea, decisión o estado. Se elimina
texto que repite un label, un dato o una relación ya evidente. El espacio libre se usa
para separar prioridades, no como excusa para sumar contenido.

### Calm precision

La interfaz privilegia alineación, ritmo, contraste, tipografía y densidad controlada.
Las superficies neutrales dominan. Amarillo y navy orientan; no compiten ni colorean
todo el producto.

### One clear primary task

Cada pantalla debe hacer obvio qué mirar y qué hacer primero. Las acciones secundarias,
filtros avanzados y contexto de apoyo se revelan cuando son necesarios.

### Information once, in the best place

Cliente, empresa, contacto, oportunidad, estado y origen no deben repetirse en bloques
cercanos. Cada dato tendrá una ubicación principal; las repeticiones sólo se permiten
cuando evitan perder contexto después de scroll o cambio de superficie.

### Dense, not cramped

La herramienta es desktop-first y de uso frecuente. Filas, tarjetas y controles deben
ser compactos, pero preservar targets accesibles, foco visible y una separación que
permita escaneo rápido.

### Progressive disclosure

El detalle avanzado, tablas exactas, contexto CRM, filtros poco frecuentes y evidencia
técnica aparecen mediante tabs, disclosure, drawer o inspector cuando corresponda. La
información útil no se elimina: cambia de prioridad.

### Motion is functional

Sólo se anima para explicar aparición, desaparición, drag and drop, expansión, feedback
o cambio de estado. Las acciones frecuentes deben responder de inmediato y no esperar
una animación.

## Semantic design tokens

Los componentes no podrán introducir hexadecimales ni colores Tailwind directos. Todo
color debe consumirse mediante un token semántico. Los nombres describen función, no
apariencia, salvo los dos tokens institucionales de origen.

### Institutional source colors

| Token | Value | Purpose |
| --- | --- | --- |
| `--brand-yellow` | `#F1B809` | identidad FAA y origen de acciones primarias |
| `--brand-navy` | `#1B3B5F` | segundo color institucional y origen de énfasis secundario |

Se definirán variantes derivadas para hover, pressed y fondos sutiles. El amarillo no
se usará como texto sobre fondos claros. Sus fondos usarán foreground oscuro. El navy
podrá usarse como texto, link, icono, selección o fondo con foreground que alcance el
contraste requerido.

### Required semantic groups

| Group | Required tokens |
| --- | --- |
| Canvas | `--canvas`, `--canvas-subtle` |
| Surfaces | `--surface-primary`, `--surface-secondary`, `--surface-raised`, `--surface-overlay`, `--surface-interactive` |
| Text | `--text-primary`, `--text-secondary`, `--text-tertiary`, `--text-inverse`, `--text-disabled`, `--text-link` |
| Borders | `--border-subtle`, `--border-default`, `--border-strong`, `--divider` |
| Primary action | `--action-primary`, `--action-primary-hover`, `--action-primary-pressed`, `--on-action-primary` |
| Secondary emphasis | `--action-secondary`, `--action-secondary-hover`, `--action-secondary-subtle`, `--on-action-secondary` |
| Selection | `--selection-surface`, `--selection-text`, `--selection-marker` |
| Focus | `--focus-ring`, `--focus-offset` |
| Feedback | `--success-*`, `--warning-*`, `--danger-*`, `--info-*` |
| Disabled | `--disabled-surface`, `--disabled-text`, `--disabled-border` |
| Overlay | `--scrim`, `--shadow-raised`, `--shadow-overlay` |
| Data visualization | `--chart-primary`, `--chart-highlight`, `--chart-secondary-*`, `--chart-grid`, `--chart-axis` |

Semantic mapping:

- primary action maps to FAA yellow with dark foreground;
- secondary action, links, navigation hierarchy and selected-state text map to navy;
- selection combines a navy-derived surface/text treatment with a compact yellow marker;
- charts use navy as the principal series/data accent and yellow only for a selected,
  highlighted or identity-bearing datum;
- red is exclusive to loss, destructive action and error;
- green is exclusive to success/won/active where that meaning is real;
- pipeline stages keep distinct semantic tokens, but use low-chroma surfaces and do not
  turn whole columns into saturated color fields;
- neutral surfaces occupy most of the interface.

Light, dark and system themes remain supported. Both themes must implement the same
semantic contract. A raw brand value may remain constant, while derived interaction
and contrast tokens may differ by theme. Theme changes must not alter hierarchy or
status meaning.

### Spacing, shape and elevation

- base spacing unit: 4px;
- standard control gaps: 8px and 12px;
- standard section rhythm: 16px, 24px and 32px;
- compact control height: minimum 36px only for dense, repeated desktop controls;
- standard interactive height: 40–44px;
- touch/click target: 44px where layout permits, with the clickable area expanded when
  the visible control is intentionally compact;
- control radius: 8px;
- surface radius: 10–12px;
- pill radius: only for status, filters or truly pill-shaped controls;
- borders are separators of last resort; prefer whitespace and surface contrast;
- shadows are reserved for overlays, drawers, sticky layers and intentionally raised
  elements. Normal cards and table rows do not need shadows.

## Typography decision

### Selected family: Manrope

Manrope será la única familia tipográfica principal. Frente a IBM Plex Sans, conserva
excelente legibilidad y números claros, pero ofrece una geometría más contemporánea y
una personalidad ligeramente más distintiva sin verse lúdica. Una sola familia evita
complejidad y mantiene coherencia entre métricas, tablas, formularios y conversación.

Implementation requirements:

- autoalojar archivos WOFF2 con licencia y procedencia documentadas;
- no usar Google Fonts en runtime ni depender de conectividad externa;
- no incorporar un paquete npm para la fuente;
- usar `font-display: swap` y precargar sólo el archivo crítico;
- cargar el rango necesario de una variable font `400 700`, o archivos estáticos
  equivalentes si su medición produce menor costo total;
- fallback: `Arial`, `Helvetica`, `sans-serif`;
- no incluir SF Pro ni otra fuente propietaria de Apple.

### Typography tokens

| Token | Intended use |
| --- | --- |
| `--font-sans` | Manrope and system fallbacks |
| `--text-display` | métricas principales excepcionales, 28–32px / 700 |
| `--text-title` | títulos de workspace o modal, 20–24px / 600 |
| `--text-section` | títulos de sección, 16–18px / 600 |
| `--text-body` | contenido principal, 14px / 400 |
| `--text-body-strong` | labels y valores relevantes, 14px / 600 |
| `--text-small` | metadata secundaria, 12–13px / 400–500 |
| `--text-label` | labels de control, 12–13px / 600 |

Los números de métricas, cantidades, fechas alineadas y contadores usarán
`font-variant-numeric: tabular-nums`. No se usarán pesos 700 de manera generalizada.
Los títulos tendrán tracking ajustado sólo si mejora la lectura de Manrope; el body no
usará tracking decorativo.

## Shared primitives strategy

Se evoluciona la base existente; no se crea un framework paralelo. Antes de sumar una
primitiva se verificará una responsabilidad compartida real.

### Primitives to retain and refine

- `Button` and `IconButton`: primary, secondary, ghost and danger semantics, compact and
  standard size, loading and disabled states;
- `FormControls`: label, description, error, input, textarea, select, checkbox and radio;
- `Modal`, `Drawer`, `ConfirmationDialog` and overlay focus primitives;
- `SegmentedControl` and accessible tabs;
- `Toolbar`, `SearchField` and `FilterControl` as composition primitives;
- `Badge` as the visual base for typed status mappings;
- typed icons and typed internal navigation.

### Consolidations expected

- consolidate `LoadingState`, `WorkspaceSkeleton` and local skeleton variants into one
  state family with inline, section and workspace modes;
- consolidate `InlineFeedback`, error panels and local alert banners into one feedback
  family with inline and notice modes;
- consolidate status pills into one typed `StatusBadge` contract; `LegendaryBadge` may
  remain a semantic wrapper but must use the same foundation;
- consolidate repeated workspace header/action/filter arrangements through the existing
  toolbar composition, without embedding business filters in a universal component;
- consolidate theme, user metadata and logout under one compact account disclosure in
  AppShell;
- consolidate repeated panel/card styling into semantic surfaces and remove `ui-panel`
  usage where a divider or whitespace is sufficient.

### Elements expected to disappear or stop being permanent

- permanent third-column CRM context in WhatsApp;
- duplicate customer/opportunity/status blocks inside WhatsApp;
- explanatory subtitles under self-evident metrics and actions;
- nested cards whose only purpose is to frame another card;
- decorative gradients and broad tinted backgrounds;
- standalone theme and logout controls in the sidebar footer;
- raw backend enum labels in Broadcasts;
- feature-local visual variants that duplicate shared loading, error, empty or status
  primitives.

No generic DataTable will be created unless Customers, Products and another real
consumer share behavior beyond table markup. Feature-specific columns and business
actions remain feature-owned.

## Global interaction and content rules

- labels are direct and concise; helper text appears only when it prevents an error or
  explains a non-obvious constraint;
- one primary action per local decision area;
- destructive actions are not primary and always preserve existing confirmations;
- icon-only controls require an accessible name and a tooltip when meaning is not
  universal;
- hover never carries information unavailable by keyboard or touch;
- loading preserves layout when possible and never blocks unrelated surfaces;
- empty states distinguish true absence, filtered absence and load failure;
- errors preserve the user's draft and provide the smallest useful recovery action;
- transitions use CSS where possible, normally 120–200ms, and never delay the action;
- drag feedback may use up to 200ms for settle/reorder; dialogs and drawers up to 220ms;
- `prefers-reduced-motion: reduce` removes spatial motion and keeps immediate state
  changes or minimal opacity feedback;
- visible text must use sentence case. Provider IDs, command IDs, versions and other
  implementation concepts are not user-facing.

## Screen-by-screen requirements

### 1. Pipeline

- preserve exactly the configured four active columns and the generic
  `PipelineColumn`; Lost remains outside the active board;
- keep cards compact and do not add fields;
- establish card hierarchy as company/customer primary, contact secondary, source and
  Legendary as compact metadata, with stage conveyed primarily by its column;
- do not repeat the stage as a large badge on every card when the column already supplies
  that context;
- Legendary remains recognizable but subtle: a compact yellow identity treatment, not
  a large filled badge;
- use navy for board headings, selected/filter state and secondary actions; use yellow
  for primary action and active FAA identity;
- stage colors remain semantic accents on headers, markers or status badges, not large
  tinted column backgrounds;
- preserve search, source/product filters, ordering, optional time-in-stage view, DnD,
  keyboard activation, optimistic update and rollback behavior;
- empty columns stay lightweight and must not visually compete with populated cards;
- at normal laptop width, four columns remain understandable; horizontal overflow is
  allowed before compressing cards below a scannable width.

### Opportunity detail

- use one clear identity header and avoid repeating customer/company/status in nearby
  panels;
- align status, primary commercial action and secondary actions consistently;
- reduce oversized empty areas and nested framing;
- group contact, source and commercial evidence by task rather than by arbitrary cards;
- keep quote, history, notes, WhatsApp link, loss context and reopen behavior intact;
- tabs and disclosures must preserve lazy loading, dirty-draft protection and focus
  restoration;
- destructive/loss presentation uses red only where semantically required.

### 2. Dashboard

- the commercial situation must be understandable in seconds;
- preserve all backend-authoritative business information and exact-data access;
- replace the current large attention area with a compact, actionable list/strip that
  prioritizes item, reason/age and direct action; remove prose that restates the action;
- present the highest-value metrics in one calm summary band with aligned, tabular
  numbers and short labels;
- keep secondary metric evidence available without giving every metric equal size;
- make commercial evolution the principal chart when data exists;
- group secondary analyses so only one major commercial dimension competes for attention
  at a time, using the existing accessible dimension control;
- use direct labels on bars/series when practical and remove legends that only repeat
  visible labels;
- use navy for the principal series/data accent, yellow for the active selection or one
  deliberate highlight, and semantic colors only for true status meaning;
- avoid pie/donut as the only representation when exact comparison matters;
- retain accessible exact tables and null/empty/error semantics through progressive
  disclosure;
- filters remain compact, show active evidence, and do not visually dominate results;
- independent metric failures continue to leave successful surfaces usable.

### 3. Notifications

- remove the fixed `52rem` content constraint;
- use the available desktop width with one adaptive, compact list rather than adding a
  second information column or more fields;
- each row has a stable scan order: unread/read marker, type, concise event, customer or
  opportunity, and age aligned consistently;
- unread state combines weight, marker and accessible text; it never depends on color
  alone;
- type uses a compact icon/label with an accessible name;
- customer/opportunity destination remains the row's obvious action;
- exact time remains available semantically while visible age is concise;
- All/Unread and bulk acknowledgement remain clear and compact;
- preserve newest-first order, paging, refresh behavior, acknowledgement semantics and
  distinct true-empty/filtered-empty/error states.

### 4. WhatsApp

The primary flow is: **select conversation → understand context → respond**.

- default desktop composition becomes two dominant zones: compact conversation list and
  wide conversation;
- CRM context is a collapsible inspector/drawer opened on demand and is not a permanent
  competing column;
- the conversation pane must own the largest width and strongest visual hierarchy;
- the list prioritizes identity, latest relevant activity, age and unread/waiting state;
- phone, company, opportunity and status appear only where they improve selection and
  are not repeated simultaneously in list, header and inspector;
- the conversation header identifies the active person/customer once and exposes one
  concise control to open CRM context;
- the inspector owns customer details, linked opportunity actions and supporting CRM
  evidence; closing it returns focus to its trigger;
- the message log, composer and latest relevant restriction evidence remain visually
  central;
- the 24-hour/template restriction appears adjacent to the composer as concise status
  and next action. Full explanation is disclosed only when needed;
- human-approved template selection remains explicit and must not expose provider
  metadata;
- preserve attachments, authenticated media, delivery evidence, retry identity,
  pagination, polling/resync, waiting/unread filters, linking/replacing/unlinking and
  opportunity creation;
- responsive behavior may collapse the conversation list or inspector into drawers at
  constrained laptop widths, but must never display three cramped columns;
- offline and recoverable errors remain scoped to the affected action.

### 5. Broadcasts / Envíos masivos

- the page title and initial state explain in one concise sentence that an envío masivo
  sends an approved WhatsApp template to selected CRM customers;
- do not describe the feature as a campaign or template builder;
- history prioritizes name, user-facing status, audience size, result and last activity;
- replace raw enums with a typed presentation mapping. The required user-facing states
  are: `DRAFT` as `Borrador`; a valid unconfirmed draft as the derived state `Listo para
  confirmar`; `CONFIRMED` as `Listo para enviar`; `PROCESSING` as `Enviando`; and
  `COMPLETED` as `Completado` or the outcome-derived `Completado con incidencias` when
  failed/unknown recipients exist. Internal enums and transitions remain unchanged;
- uncertainty and partial results remain explicit; `UNKNOWN` must never be presented as
  success and must not invent an unsupported retry;
- creation is a guided sequence matching the mental model: choose approved content,
  complete required values/media, choose customers, review eligibility, confirm;
- show current step, completed steps and one primary next action; do not expose version,
  validation token, command ID or provider implementation details;
- eligibility distinguishes ready and excluded recipients with plain reasons before the
  irreversible confirmation;
- detail presents a concise summary first, then recipients, results, attempts and audit
  evidence through tabs/disclosures;
- preserve every existing explicit command boundary: draft creation/update, recipient
  selection, validation, confirmation, start, bounded process, safe retry and audit;
- creation must preserve drafts and recoverable input after failures or dismissal rules.

### 6. Customers

- remain primarily table/list based;
- strengthen the identity column: customer/company first, one best contact second;
- align province, Legendary state and actions predictably;
- use row density and whitespace instead of extra cards;
- Legendary remains special but subtle and is never a broad yellow row background;
- search, pagination, import, create, edit, stale-write recovery, delete permissions and
  customer detail navigation remain unchanged;
- seller and supervisor visibility remains exactly as defined by existing rules.

### 7. Products

- keep a simple compact table;
- improve alignment between name, status and actions and use the available width without
  stretching content artificially;
- active/inactive status uses a typed badge with text and shape, not color alone;
- counters remain concise and secondary to the catalog;
- preserve supervisor management actions, seller visibility and all confirmations;
- add no product data or functionality.

### 8. Lost opportunities

- present Lost as a commercial analysis/workspace, not an administrative record table;
- first level: current losses and kg lost, with historical/reopened evidence secondary;
- second level: loss-reason distribution from the existing authoritative `by_reason`
  statistics, using compact horizontal comparison with direct labels;
- third level: current lost opportunities, prioritizing customer/company, reason, kg or
  quote evidence, loss age/date and the action to open/reopen;
- the opportunity action must be immediately visible and keyboard reachable;
- simplify filters into search, the most common reason control and one advanced filter
  disclosure; show active filters compactly and keep reset obvious;
- red is reserved for loss reason, negative result and danger. Do not use red/pink page
  backgrounds or large tinted panels;
- navy supplies headings, links, selected filters and analytical accents so the workspace
  remains part of the same CRM;
- preserve server-authoritative filters/statistics, cursor ordering, exact evidence,
  empty distinctions and reopen eligibility/contracts.

### 9. Sidebar / AppShell

- keep the desktop-first collapsible sidebar and existing typed routes;
- preserve FAA yellow as the primary identity and use navy visibly in navigation labels,
  icons, group hierarchy and supporting chrome;
- selected navigation combines navy text/weight or icon treatment, a navy-derived subtle
  surface and a compact yellow marker; it is recognizable without color alone and does
  not rely only on a pale yellow rectangle;
- remove decorative gradients;
- reduce group separators and labels where spacing provides enough hierarchy;
- unread count remains visible and semantically announced in expanded and collapsed
  modes;
- replace the expanded user/theme/logout stack with one compact account disclosure that
  contains identity, theme choice and logout;
- preserve the sidebar toggle, keyboard order, responsive reachability and active-route
  ownership for detail pages;
- navy must be clearly visible but the sidebar should not become a large saturated navy
  block that compite con FAA yellow or neutral content surfaces.

## Accessibility requirements

- WCAG 2.2 AA is the minimum target for affected surfaces;
- normal text contrast is at least 4.5:1; large text and meaningful UI graphics meet the
  applicable 3:1 requirement;
- state, status, unread, selected, lost, active and disabled meaning never depends on
  color alone;
- all controls use native semantics when available and have accessible names;
- every input has a persistent label; placeholder text is never the only label;
- focus is visible against every theme and surface, using the semantic focus tokens;
- focus order follows visual/task order;
- modals, drawers, disclosures, menus and tabs preserve keyboard operation, focus trap
  where applicable and return focus to the opening control;
- Escape closes dismissible overlays unless a dirty/irreversible flow requires the
  existing confirmation;
- drag and drop retains the existing non-pointer interaction path or equivalent
  accessible command path;
- dynamic success, error, unread and loading changes use appropriately scoped live
  regions without duplicate announcements;
- charts expose visible values where practical and retain an exact semantic table or
  equivalent accessible representation;
- icon-only actions have accessible names and do not use emoji as product icons;
- zoom/reflow at normal laptop widths must not hide primary actions or require both-axis
  scrolling for ordinary forms;
- `prefers-reduced-motion` is respected for all new transitions;
- light, dark and system themes each pass contrast and focus checks.

## Responsive requirements

- primary optimization targets normal laptop and desktop widths from 1024px upward;
- 1440px uses additional width to improve hierarchy, not to add fields;
- at constrained laptop widths, toolbars wrap predictably and secondary controls move
  behind disclosures before content becomes cramped;
- Pipeline may scroll horizontally to preserve useful card width;
- tables may use intentional horizontal overflow with sticky or repeated context only
  when necessary;
- WhatsApp must prefer list/chat plus an on-demand inspector rather than three compressed
  panels;
- no mobile-specific product navigation or workflow redesign is included.

## Performance requirements

- no new runtime UI, animation or chart dependency without a separately justified need;
- prefer current React, Tailwind, typed primitives, CSS transitions and existing SVG
  chart implementation;
- Manrope is self-hosted, subset to used glyphs where license/tooling permits, and avoids
  render-blocking remote requests;
- avoid new per-row or per-card API requests;
- progressive disclosure must not eagerly fetch data currently loaded lazily;
- DnD, message scrolling, filters and list selection must remain responsive with current
  fixture volumes;
- visual changes must not increase polling frequency or broaden API payloads.

## Acceptance criteria

- **AC-01:** CRM-018 is approved before implementation and contains no unresolved open
  decision.
- **AC-02:** the frontend uses semantic tokens for institutional, surface, text, border,
  action, selection, focus, feedback and chart roles; affected components contain no new
  scattered hex values.
- **AC-03:** `#F1B809` remains FAA yellow and `#1B3B5F` is visibly used as the secondary
  institutional color without either color dominating neutral surfaces.
- **AC-04:** yellow is used for primary actions/key FAA highlights and navy for secondary
  emphasis/navigation/selection/links/data accents according to this spec.
- **AC-05:** Manrope is self-hosted with documented license/provenance,
  `font-display: swap`, system fallback and no external runtime request or npm font
  dependency.
- **AC-06:** typography tokens produce a consistent hierarchy and CRM metrics/counts use
  tabular numerals.
- **AC-07:** shared buttons, controls, badges/status, tabs, tables, feedback and
  loading/empty/error states follow one documented primitive contract in both themes.
- **AC-08:** duplicate loading, feedback and status variants identified in this spec are
  consolidated or explicitly justified during implementation review.
- **AC-09:** AppShell selection is recognizable through more than a pale yellow fill;
  navigation, unread count, collapse and responsive keyboard behavior regressions pass.
- **AC-10:** account identity, theme and logout are reachable through one compact,
  accessible disclosure and preserve their current behavior.
- **AC-11:** Pipeline renders the four configured active stages through the generic
  column/card system, with no stage-specific component duplication.
- **AC-12:** Pipeline cards remain compact, add no fields and show the specified
  customer/contact/source/Legendary hierarchy.
- **AC-13:** Pipeline DnD, accessible activation, filters, ordering, optional time view,
  optimistic mutation, rollback and no-per-card-request tests pass.
- **AC-14:** opportunity detail removes nearby identity/status duplication while
  preserving quote, notes, history, WhatsApp, loss and reopen behavior.
- **AC-15:** Dashboard presents an immediately scannable summary, compact actionable
  attention area and one dominant chart/analysis hierarchy without removing exact
  business information.
- **AC-16:** Dashboard charts use navy as principal data accent, yellow selectively, direct
  labels where practical and an accessible exact-data representation.
- **AC-17:** Dashboard filters, null states, independent errors, backend-authoritative
  values and dimension switching retain their current semantics.
- **AC-18:** Notifications no longer uses the `52rem` page constraint and uses desktop
  width through a single compact adaptive list without adding information.
- **AC-19:** every notification clearly exposes unread/read, type, destination context and
  age without relying on color; acknowledgement, paging and empty/error semantics pass.
- **AC-20:** WhatsApp defaults to list plus dominant conversation; CRM context is an
  on-demand accessible inspector/drawer rather than a permanent third competing column.
- **AC-21:** automated and visual review verifies that customer, opportunity and status
  information is not simultaneously duplicated across WhatsApp list, header and context.
- **AC-22:** WhatsApp 24-hour/template restriction remains understandable adjacent to the
  composer without dominating the workspace.
- **AC-23:** all existing WhatsApp capabilities, contracts, polling/resync, offline,
  media, templates, linking and sending regression tests pass.
- **AC-24:** Broadcast history uses user-facing status terminology and never exposes raw
  enum values or technical command/version/provider concepts.
- **AC-25:** a user can complete the Broadcast guided sequence and understand content,
  recipients, eligibility, confirmation, progress and results without campaign-builder
  language.
- **AC-26:** all Broadcast command boundaries, uncertainty, safe retry rules, media and
  audit capabilities remain intact.
- **AC-27:** Customers remains a compact table, preserves all role/import/edit/delete/
  pagination behavior and presents Legendary subtly.
- **AC-28:** Products remains a compact table, adds no functionality and preserves role,
  status and confirmation behavior.
- **AC-29:** Lost prioritizes current loss count/kg, loss reasons, opportunity evidence
  and open/reopen action; no large red/pink surface is used.
- **AC-30:** Lost filters are simplified without changing server-supported filter
  semantics, cursor order, statistics or empty-state distinctions.
- **AC-31:** affected screens pass automated axe checks with no serious or critical
  violations, plus documented keyboard and focus review.
- **AC-32:** light, dark and system themes pass contrast, focus and state-meaning review;
  reduced-motion behavior is verified.
- **AC-33:** layouts are visually reviewed at 1024px, 1280px and 1440px; primary actions
  remain reachable and no screen gains accidental two-axis overflow.
- **AC-34:** browser QA baselines are intentionally regenerated only after functional,
  accessibility and design review; changes are reviewed rather than blindly accepted.
- **AC-35:** frontend tests, TypeScript, build, Biome, coverage, accessibility checks,
  Docker Compose health checks and the repository-wide required quality gates pass.
- **AC-36:** no backend, database, API contract, business-rule, role or permission change
  is included in the implementation commits.

## Regression requirements

Implementation must preserve and test:

- all canonical routes, deep links, typed origins and active sidebar ownership;
- authentication, role visibility and logout;
- theme persistence and system-theme following;
- Pipeline stage configuration, card information boundary, DnD and mutation recovery;
- opportunity detail, quote, loss, reopen, note draft and WhatsApp navigation semantics;
- backend-authoritative Dashboard values, filters, exact tables and partial failures;
- Notifications order, unread counts, active-only acknowledgement and paging;
- WhatsApp ordering, unread/waiting filters, stable selection, message ordering, provider
  evidence, template restrictions, media and conversation/opportunity operations;
- Broadcast draft, eligibility, confirmation, start/process/retry boundaries and audit;
- Customers import, CRUD, stale-write recovery, permissions and pagination;
- Products active/inactive behavior and permissions;
- Lost filters, current versus historical semantics, cursor pagination and reopen rules;
- loading, filtered-empty, true-empty, error and retry distinctions;
- no additional API calls caused solely by rendering or decoration.

Tests should prefer accessible roles, names, visible state and behavior. Update assertions
whose wording or layout intentionally changes, add focused tests for disclosure/focus and
user-facing status mappings, and avoid broad snapshots.

## Implementation sequence

Each step must finish its focused tests and review before the next screen depends on it:

1. tokens and typography;
2. shared primitives;
3. AppShell and sidebar;
4. Pipeline and opportunity detail;
5. Dashboard;
6. Notifications;
7. WhatsApp;
8. Broadcasts;
9. Customers and Products;
10. Lost workspace;
11. accessibility, consistency and polish pass, followed by intentional browser-baseline
    regeneration.

Implementation should use small commits referencing CRM-018. The implementation commit
recorded in this spec is the verified final implementation commit, followed by the
separate documentation commit required by `AGENTS.md`.

## Proposed dependencies

None.

Manrope is a vendored font asset, not an application dependency. Existing React,
Tailwind, `@dnd-kit/react`, SVG/CSS primitives and test tooling are sufficient. Any later
proposal for a UI, animation, chart or state dependency requires a concrete blocker,
comparison with the existing approach and explicit approval.

## Open decisions

None. The Draft as a whole still requires explicit approval before implementation.
