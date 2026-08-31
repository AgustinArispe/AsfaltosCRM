# CRM-031 — Visual Consistency & Product Polish

Status: Approved
Owner: Frontend / Product Design
Last updated: 2026-08-31
Implementation commit: N/A

## Goal

Completar un pase de consistencia visual sobre el baseline funcional CRM-018 y la
dirección de simplificación CRM-030. El producto debe sentirse deliberadamente
diseñado, normalizado y sobrio: menos patrones decorativos, menos excepciones locales y
una geometría única por familia de componente.

CRM-031 no rediseña workflows. Conserva rutas, capacidades, contratos y reglas de
negocio. La autorización explícita del usuario para crear e implementar esta spec
aprueba este alcance; `Open decisions` es `None` antes de modificar código.

## Context and authority

- CRM-018 permanece como baseline funcional y de regresión.
- CRM-030 permanece Draft y funciona sólo como dirección visual de referencia. CRM-031
  no implementa por implicación sus cambios de arquitectura de información o workflow.
- Los requisitos explícitos de CRM-031 son la autoridad para los refinamientos aquí
  documentados y no modifican `docs/BUSINESS_RULES.md`.
- El worktree previo contiene trabajo de QA y cambios en curso ajenos a CRM-031; la
  implementación preserva esos cambios y separa los hunks propios.

## Dependencies

- CRM-018 — FAA CRM Frontend 2.0 Design System
- CRM-019 — Pipeline 2.0
- CRM-021 — Dashboard & Metrics
- CRM-022 — Notifications UI
- CRM-023 — WhatsApp Inbox 2.0
- CRM-024 — Customers, Products and Lost Workspaces UI
- CRM-025 — WhatsApp Broadcast UI
- CRM-029 — Brand, Dashboard & Interaction Polish
- CRM-030 — Frontend Visual Simplification, Draft visual reference only

## Scope

- Auditar y corregir tokens y primitives compartidos antes de intervenir workspaces.
- Eliminar usos decorativos de reglas izquierdas y superiores en la UI de producto.
- Eliminar superficies crema o amarillo lavado de los workspaces principales.
- Conservar `#F1B809` y `#1B3B5F` como colores institucionales sólidos, deliberados y
  accesibles.
- Normalizar geometría, tipografía y estados de componentes visuales equivalentes.
- Refinar sin cambiar workflow: AppShell/sidebar, Pipeline, Dashboard, Notifications,
  WhatsApp, Broadcasts, Lost y superficies compartidas relacionadas.
- Preservar Light, Dark y System con equivalencia semántica.
- Revisar visualmente 1024, 1280 y 1440 px y regenerar de forma intencional la
  evidencia/baselines afectados.

## Non-goals

- Cambiar backend, API, schemas, persistencia, métricas o reglas comerciales.
- Rediseñar navegación, rutas, pasos, decisiones o capacidades existentes.
- Implementar el nuevo Dashboard progressive-disclosure de CRM-030 mientras esa spec
  siga Draft.
- Agregar campos, métricas, filtros, acciones o información.
- Agregar dependencias, framework UI, chart library, store o sistema de iconos.
- Cambiar Manrope, React, TypeScript o Tailwind CSS.
- Introducir gradientes, motion decorativo, glassmorphism o mosaicos de cards
  coloreadas.
- Quitar bordes estructurales inferiores o completos necesarios para tablas, grids,
  overlays, campos, focus o comprensión de una región.

## Visual contract

### Color

| Source token | Exact value | Contract |
| --- | --- | --- |
| `--brand-yellow` | `#F1B809` | CTA primaria, indicador compacto, badge/count, icono o highlight puntual |
| `--brand-navy` | `#1B3B5F` | estructura, selección, tabs, heading/panel sólido y charts |

Neutral domina canvas, filas, cards y paneles. No existen tokens de surface crema o
amarillo lavado. En Light y Dark, selected/unread usan una surface neutral derivada de
navy, peso tipográfico y, si hace falta, un dot/badge amarillo sólido. Warning usa
surface neutral, icono/texto semántico y contención compacta; nunca un panel crema.

Yellow no aparece detrás de párrafos, filas, columnas ni banners grandes. Navy puede
formar uno o dos bloques estructurales sólidos por workspace. Red permanece reservado a
loss/error/destructive y no cubre regiones extensas.

### Borders

- Quedan prohibidos `border-left`, `border-inline-start`, `border-top`,
  `border-block-start` y sombras `inset` equivalentes cuando actúan como acento,
  selección, status o decoración.
- Selected se expresa por surface, peso, icono y elemento compacto que no sea una regla
  lateral/superior.
- Stage se expresa con header surface, label y dot/badge.
- Separación real usa `border-bottom`, gap o full-border según el contrato.
- Se permiten bordes superiores exclusivamente estructurales: footer de modal/drawer,
  separación entre regiones apiladas en responsive y spinner circular animado. No
  pueden transportar color de marca, stage, status o selección.

### Typography tokens

Manrope es la única familia. Los features no crean tamaños locales para roles que ya
tienen token.

| Role | Size / line-height | Weight |
| --- | --- | --- |
| Display / primary metric | `40px / 44px` | 700 |
| Workspace title | `32px / 40px` | 700 |
| Section title | `20px / 28px` | 650 |
| Subsection title | `17px / 24px` | 650 |
| Important identity | `16px / 22px` | 650 |
| Body | `15px / 23px` | 400 |
| Body strong | `15px / 22px` | 600 |
| Navigation | `15px / 20px` | 600 |
| Control | `14px / 20px` | 600 |
| Metadata / label | `13px / 18px` | 500 / 600 |
| Micro, exceptional only | `12px / 16px` | 500 |

### Geometry contracts

| Family | Contract |
| --- | --- |
| `StatusBadge` / pill / Legendary | `24px` height, `10px` horizontal padding, no vertical padding, `13px/18px`, weight 650, `6px` icon gap, pill radius, `1px` full border |
| Button default | `44px` min-height, `14px/20px`, `14px` horizontal padding, control radius, `8px` icon gap |
| Button compact | `36px` height, `14px/20px`, `12px` horizontal padding, same radius/gap |
| IconButton default / compact | square `44px` / `36px`; same state contract as Button |
| Input / Select | `44px` min-height, `15px/23px`, `12px` horizontal padding, control radius |
| Search / Filter | `36px` height, `14px/20px`, same control radius and border |
| Tabs / Segmented | `40px` control height; `14px/20px`, weight 600, `12px` horizontal padding |
| Filter chip | `36px` height; `13px/18px`, weight 600, `10px` horizontal padding, pill radius |
| Sidebar navigation row | `44px` min-height, `15px/20px`, weight 600, `12px` horizontal padding |
| Table row | `56px` minimum content row; headers `40px` minimum; cells share baseline and vertical padding |
| Operational list row | one class per family and identical min-height/padding for every state; Notification `64px`, WhatsApp conversation `68px` |
| KPI group | identical group grid, `120px` minimum height, `16px` padding, label/number/footer aligned through fixed grid rows |
| Modal / Drawer header | `72px` minimum height, `20px` block and `20–24px` inline padding, section-title typography |

Status text may change width naturally. A status column left-aligns all badges on one
baseline and reserves width from the longest content through table layout; it does not
hardcode widths by state.

## Changes by screen

### Shared primitives and AppShell

- Eliminar surface tokens amarillos lavados y mapear status a neutral/semantic compact.
- Convertir Badge/StatusBadge en la única geometría de pill; Legendary reutiliza el
  mismo wrapper y sólo cambia icono/tone.
- Normalizar Button, IconButton, fields, search/filter, segmented controls, headers,
  rows y typography mediante tokens/clases compartidas.
- Sidebar selected usa surface navy/neutral, texto/icono fuerte y un pequeño dot o
  badge amarillo opcional; no usa regla izquierda/superior. Collapsed y expanded
  comparten exactamente ese estado.

### Pipeline

- Quitar la regla superior del header de etapa y cualquier regla lateral de card
  selected.
- Conservar columnas neutrales y el workflow de cuatro etapas.
- Estructurar el header con surface navy controlada, dot de stage, título y count.
- Mantener cards simples; identidad y metadata usan los tokens compartidos.

### Dashboard

- Mantener IA, filtros, métricas, charts y drill-down actuales.
- Quitar acentos top/left y alinear todos los KPI del grupo en altura, padding y
  baseline.
- Usar una summary/analysis surface navy sólida y como máximo un KPI amarillo sólido
  cuando la lectura actual justifique el primary highlight; el resto permanece neutral.
- No crear un conjunto de cards coloreadas ni rediseñar progressive disclosure.

### Notifications

- Unread usa selection surface navy/neutral, peso fuerte y dot amarillo sólido.
- Eliminar wash amarillo y regla izquierda; todos los rows conservan `64px` mínimo y
  exactamente la misma grid/padding.
- Warning de actualización queda compacto, neutral y semántico.

### WhatsApp

- Conversation selected usa selection surface, texto fuerte y dot amarillo, sin regla
  lateral/superior.
- Restricción de ventana vive junto al composer como estado compacto con icono, copy y
  acción existentes, sobre surface neutral.
- Mensajes inbound/outbound del mismo tipo comparten max-width, padding, radius y
  metadata; no se agrega contenido.

### Broadcasts

- Conservar el wizard explícito y su persistencia entre pasos.
- Todas las instancias de status usan `StatusBadge` y la misma geometría/alineación.
- Historia conserva una tabla simple con headers/rows normalizados; no cambia
  ejecución, eligibility, confirmación, progreso ni resultados.

### Lost

- Quitar acento superior decorativo y mantener red estrictamente semántico.
- Usar navy sólido para jerarquía analítica, con magnitud principal y contexto en
  foreground accesible.
- Todas las métricas de summary comparten geometría; causas conservan barras directas y
  Opportunities quedan visualmente separadas sin cambiar filtros ni datos.

## Components to modify

- Semantic tokens and shared CSS contracts in `styles.css`.
- `Badge` / `StatusBadge`, `LegendaryBadge`, `Button`, `IconButton`, `FormControls`,
  `SegmentedControl`, `Workspace`, `Modal` and `Drawer` only where contract alignment is
  needed.
- `AppShell`, Pipeline column/card primitives, Dashboard visual surfaces, Notification
  rows, WhatsApp list/chat/composer/template state, Broadcast tables/wizard and Lost
  summary/list.
- Existing tests and visual baselines affected by intentional presentation changes.

## Elements to remove

- Decorative left/top rules and equivalent inset stripes.
- `accent-muted`, `accent-subtle`, `accent-surface`, `warning-subtle`,
  `quoted-pending-muted` and `legendary-subtle` as yellow/cream surface roles.
- Full-row unread/selected yellow backgrounds.
- Large warning-yellow banners in WhatsApp, Notifications or Broadcasts.
- Feature-local pill padding/radius/font overrides.
- One-off tiny text for body, identity, actions or ordinary metadata.
- Arbitrary per-state badge widths and geometry.

## Visual QA matrix

Review Light and Dark at 1024, 1280 and 1440 CSS px. Use the canonical Docker Compose
app on `localhost:5173` and backend on `localhost:8000`.

At every width compare side by side:

- StatusBadge examples including `Completado con incidencias`, `Enviando` and
  `Borrador`;
- primary/secondary/compact buttons and filter/search controls;
- KPI cards in one row and their label/value/footer baselines;
- sidebar selected state expanded and collapsed;
- Pipeline headers/cards and local scrolling;
- unread/read Notification rows;
- selected/unselected WhatsApp conversations, restriction state and message bubbles;
- Broadcast history statuses and wizard step geometry; and
- Lost summary, reason bars and opportunity table.

The review checks page-level horizontal overflow, clipped text/actions, visible focus,
keyboard interaction and contrast. Baselines are regenerated only after review.

## Acceptance criteria

- **AC-01:** Product UI has zero decorative `border-left` or equivalent inline-start
  rule; source audit identifies and documents any structural exception.
- **AC-02:** Product UI has zero decorative `border-top` or equivalent block-start rule;
  source audit identifies and documents any structural exception.
- **AC-03:** Core workspaces contain no pale/cream yellow surface, in Light or Dark.
- **AC-04:** `#F1B809` remains visibly present only in deliberate compact/primary uses;
  `#1B3B5F` has clear structural presence.
- **AC-05:** One semantic component type has one shared geometry contract globally.
- **AC-06:** Every status pill is 24px high with shared padding, radius, typography,
  border and icon gap; no state defines arbitrary geometry or width.
- **AC-07:** Sidebar, Pipeline, Notifications, WhatsApp, Broadcasts, Dashboard and Lost
  satisfy the screen contracts without functionality or navigation regressions.
- **AC-08:** Typography uses the shared scale; essential body, identity, navigation and
  action text is not rendered as Micro at 1440 px.
- **AC-09:** Light/Dark/System, keyboard/focus, reduced-motion and accessible names
  remain valid; automated accessibility checks report no critical/serious violations.
- **AC-10:** Visual QA at 1024, 1280 and 1440 shows no page-level horizontal overflow or
  clipped essential actions; intentional baselines are recorded.
- **AC-11:** Frontend unit tests, TypeScript and production build pass; all repository
  gates and Docker health checks pass before push.
- **AC-12:** Git diff contains no backend/API/schema/business-rule change and no new
  package dependency attributable to CRM-031.

## Open decisions

None.

## Follow-up / future specs

- CRM-030 can be reviewed and approved independently if its Dashboard progressive
  disclosure, Pipeline width or Broadcast architecture changes are still desired.
