# CRM-027 — Visual Design & Product Polish

Status: Approved
Owner: FAA CRM team
Last updated: 2026-08-18
Implementation commit: N/A

## Goal

Definir la segunda dirección visual y de product design de FAA CRM sobre las
capacidades ya aprobadas e implementadas por CRM-018 a CRM-025. El resultado debe ser
un producto interno premium, calmo, rápido, comercial, profesional, desktop-first,
distintivo de FAA y cómodo durante una jornada completa, sin cambiar reglas de
negocio, permisos, contratos ni comportamiento aprobado.

CRM-027 es una fase de diseño e implementación visual anterior a CRM-026. CRM-026
continúa siendo el pase final, reproducible y transversal de browser, accesibilidad,
responsive, zoom y flujos; debe validar la implementación de CRM-027, no volver a
diseñarla.

## Context and diagnosis

CRM-018 estableció correctamente IBM Plex Sans, temas Light/Dark/System, tokens
semánticos, geometría suave, sidebar permanente, primitives compartidos y reglas de
accesibilidad. CRM-019 a CRM-025 convirtieron ese contrato en workspaces funcionales.
El frontend actual es coherente y utilizable, pero su composición todavía evidencia
la primera aplicación del design system más que un producto FAA terminado.

La auditoría de `frontend/src/styles.css`, `frontend/src/shared/`, `AppShell`, Pipeline,
Dashboard, Notifications, WhatsApp, Customers, Products, Lost, Broadcasts y detalles
encontró patrones concretos:

- `ui-panel` funciona como envoltorio casi universal para contenido, carga, vacío,
  tabla, métricas, toolbar y módulos, creando demasiados rectángulos equivalentes;
- siguen conviviendo tokens semánticos con colores directos `slate-*`, `amber-*`,
  `rose-*`, blancos y radios locales, especialmente en WhatsApp, formularios y tablas;
- bordes completos, bordes superiores y `border-left` se usan con frecuencia como
  decoración o jerarquía ordinaria;
- Pipeline presenta columnas como fieldsets bordeados y tarjetas visualmente próximas
  a cualquier panel, en vez de zonas de trabajo y objetos manipulables;
- Dashboard repite superficies con peso parecido para atención, KPIs y análisis;
- filtros de Pipeline, Dashboard y Lost usan labels y selects con aspecto de formulario
  administrativo, aunque sus valores ya explican la función;
- AppShell muestra `FAA CRM` y un título global, mientras varios workspaces repiten el
  mismo título y descripción inmediatamente debajo;
- Customers, Products, Lost y Broadcasts repiten tablas/panels genéricos donde una
  lista o composición más específica sería más clara;
- WhatsApp conserva una grilla administrativa con bordes rígidos y varios estilos
  feature-locales, aunque su comportamiento de mensajería ya es maduro;
- los estados vacíos suelen ocupar grandes paneles bordeados y parecen placeholders;
- `/users` es un placeholder `Módulo en preparación`, pese a existir soporte backend
  aprobado para administración de usuarios por supervisores.

Esta spec refina CRM-018; no lo reemplaza. Cuando haya diferencia, CRM-027 especializa
la expresión visual conservando su arquitectura, interacción y accesibilidad. Las
specs CRM-019 a CRM-025 siguen siendo autoridad de comportamiento por feature.

## Dependencies

- CRM-001 — Core CRM
- CRM-018 — FAA CRM Frontend 2.0 Design System
- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-021 — Dashboard & Metrics
- CRM-022 — Notifications UI
- CRM-023 — WhatsApp Inbox 2.0
- CRM-024 — Customers, Products and Lost Workspaces UI
- CRM-025 — WhatsApp Broadcast UI

CRM-026 depende de la futura implementación aprobada de CRM-027 y ocurre después.

## Scope

- Refinar tokens semánticos, superficies, tipografía, densidad, radios, elevación,
  controles, iconografía, motion y estados Light/Dark definidos por CRM-018.
- Evolucionar visualmente primitives compartidos existentes antes de migrar
  composiciones feature-specific.
- Refinar AppShell/sidebar y la jerarquía visual de Pipeline, Dashboard, WhatsApp,
  Notifications, Customers, Products, Lost y Envíos WhatsApp.
- Refinar modales y detalles ya aprobados sin modificar sus flujos, acciones o datos.
- Reemplazar `/users` placeholder con administración de usuarios para `SUPERVISOR`
  usando exclusivamente los contratos CRM-001 existentes.
- Integrar información de cuenta y preferencia de tema en el área de cuenta para ambos
  roles usando `/auth/me` y la persistencia local ya implementada.
- Definir adaptación visual desktop/laptop, sidebar expandida/colapsada y zoom antes
  de la matriz reproducible de CRM-026.
- Definir criterios visuales y de producto observables para la futura implementación.

## Non-goals

- Implementar frontend, modificar producción, agregar dependencias, aprobar esta spec
  o marcarla `Implemented` durante su redacción.
- Cambiar reglas de negocio, visibilidad, roles, permisos, filtros backend, métricas,
  máquinas de estado, rutas canónicas, polling, consentimiento o provider behavior.
- Agregar seller filters, precios, SKU, stock, forecasts, tendencias falsas, métricas
  inventadas, oportunidades adicionales o acciones de WhatsApp en cada Pipeline card.
- Crear autoedición de cuenta, cambio de contraseña propio, preferencias de tema en
  servidor o administración de permisos no respaldada por contratos existentes.
- Reemplazar sidebar por navbar, router manual, React/TypeScript/Tailwind/Vite, IBM Plex
  Sans o el sistema SVG actual.
- Incorporar librería de componentes, charts, iconos, motion o state management sin una
  decisión futura explícita y evidencia de necesidad.
- Convertir FAA CRM en una UI industrial, imitación Caterpillar, gaming/neon, template
  SaaS genérico, dashboard con estética generada por IA, showcase de glassmorphism,
  marketing site o experiencia minimalista que pierda capacidad operativa.
- Duplicar la matriz browser/Playwright, seed sintético, accessibility QA o cleanup de
  CRM-026.

## Core design principle

**Not everything needs a box.**

Consistencia significa lenguaje visual compartido, no obligar a todos los workspaces a
usar la misma sucesión de paneles y cards. Pipeline es un tablero operativo, Dashboard
es una lectura jerarquizada, WhatsApp es mensajería y Customers/Products/Lost/Users son
workspaces administrativos u operativos. Pueden usar composiciones distintas mientras
compartan tokens, tipografía, controles, estados, foco, motion e identidad FAA.

La estructura debe explicar el producto antes que el copy. Whitespace, alineación,
proximidad, peso tipográfico, tono y ritmo son recursos estructurales de primera clase;
un borde o una card son decisiones, no defaults.

## Product design language

La dirección visual se denomina **calma comercial FAA**:

- neutrales cálidos y superficies serenas sostienen la jornada completa;
- IBM Plex Sans y números tabulares producen carácter y precisión sin verse técnicos;
- amarillo FAA identifica la marca, la acción local principal, foco y selección
  relevante, por lo que se usa poco y con intención;
- densidad proviene de jerarquía, alineación y progressive disclosure, no de texto
  diminuto ni controles amontonados;
- geometría suave, elevación mínima y feedback rápido aportan calidad sin decoración;
- cada workspace expresa su trabajo: mover, decidir, conversar, revisar o administrar;
- estados comerciales usan evidencia textual/visual pequeña, no grandes fondos de
  colores semánticos.

## Surface hierarchy

### Levels

| Level | Role | Default treatment | Examples |
| --- | --- | --- | --- |
| 0 — application canvas | Base continua de la aplicación | Tono más retraído, sin borde ni shadow | Fondo detrás de sidebar y workspace |
| 1 — workspace/module surface | Campo principal donde ocurre el trabajo | Cambio tonal o continuidad directa con canvas; borde sólo si el límite lo requiere | Board de Pipeline, conversación activa, área analítica |
| 2 — interactive/local surface | Unidad que se selecciona, manipula o agrupa una responsabilidad local | Tono interactivo, hover/selected y, cuando ayuda, divider o borde sutil | Lead card, conversation row, list row, filtro, bloque KPI |
| 3 — overlay/floating surface | Capa temporal por encima del trabajo | Superficie elevada, shadow compartida, scrim y borde sutil de contención | Modal, popover, tooltip, menú, context overlay |

Level no significa que cada nivel deba verse como una caja. Un Level 1 puede ser sólo
un campo tonal; un Level 2 puede ser una fila separada por divider; Level 3 sí necesita
separación espacial inequívoca.

### Choosing a separator

Usar el mecanismo de menor peso que comunique correctamente la relación:

1. **Whitespace/proximity:** primera elección para agrupar heading, metadata y acciones
   o separar secciones de una misma lectura.
2. **Alignment and grouping:** listas, KPIs y toolbars que comparten baseline no
   requieren cards individuales.
3. **Tonal contrast/background change:** diferencia zonas de trabajo completas o una
   selección tranquila sin dibujar perímetros.
4. **Divider:** separa filas o regiones hermanas de una misma superficie; no rodea cada
   elemento.
5. **Subtle elevation:** sólo para objetos manipulables o superficies que realmente se
   elevan por interacción.
6. **Border:** delimita un control, una región scrollable que necesita contención, un
   dato tabular complejo o un estado que no sería claro de otra forma.
7. **Strong border:** focus, drop target, conflicto o límite operativo excepcional;
   nunca decoración permanente.

No se usan simultáneamente background, borde completo, shadow y accent line para
expresar una sola separación ordinaria.

### Border hierarchy

- **No border:** default para workspace, secciones, grupos de métricas y módulos cuyo
  límite ya surge de tono/espacio.
- **Divider/subtle border:** 1 CSS px, bajo contraste, para filas, headers sticky y
  regiones hermanas.
- **Control/default border:** 1 CSS px con contraste suficiente para inputs/selects y
  superficies interactivas que lo necesiten; aumenta en hover/focus, no en toda card.
- **Strong border:** focus, drag/drop válido, invalid/error o separación crítica. Se
  combina con texto/icono y nunca es la única evidencia.

Se elimina el patrón decorativo de `border-left` en cards, feedback y módulos
ordinarios. Un acento izquierdo puede existir sólo para warning/attention genuino,
cuando su posición refuerza una semántica ya expresada por icono y texto, y no como
firma visual repetida.

## Visual token refinement

CRM-027 mantiene una sola fuente semántica compartida. Los nombres actuales pueden
migrarse mediante aliases durante implementación, pero feature code no consume colores
raw ni inventa tonos locales.

### Canonical surface and text roles

| Token | Semantic use |
| --- | --- |
| `canvas` | Level 0; fondo general estable |
| `surface-primary` | Level 1 principal y contenido de lectura |
| `surface-secondary` | Agrupación tonal secundaria o zona contextual |
| `surface-raised` | Objeto elevado/seleccionable y overlays contenidos |
| `surface-interactive` | Estado base de control, row o card manipulable |
| `surface-hover` | Hover sólo para dispositivos que lo soportan |
| `surface-selected` | Selección persistente, más forma/peso/icono |
| `text-primary` | Identidad, valores y headings |
| `text-secondary` | Body/supporting context |
| `text-tertiary` | Metadata no esencial; nunca placeholder de body esencial |
| `divider` / `subtle-border` | Separación de bajo peso |
| `strong-border` | Foco, límite activo o énfasis excepcional |

Los existentes `surface`, `surface-subtle`, `hover`, `selected`, `border-subtle` y
`border-strong` se alinean con estos roles o se mantienen temporalmente como aliases;
no se permite que coexistencia temporal se vuelva dos sistemas.

### FAA accent roles

| Token | Semantic use |
| --- | --- |
| `accent` | FAA yellow para una acción primaria local, icono seleccionado o dato clave |
| `accent-hover` | Estado hover/pressed con contraste preservado |
| `accent-muted` | Fondo seleccionado sutil, marca pequeña o focus context |
| `on-accent` | Foreground oscuro validado; no se presupone texto blanco |

Una pantalla no reparte amarillo entre múltiples CTA competidores. No se aplica como
fondo global, navegación completa, card completa, banner permanente ni serie de todos
los charts.

### Operational semantic roles

Cada rol tiene al menos `base`, `muted`, `strong/on` cuando sea necesario y una forma/
texto equivalente:

| Role | Meaning | Typical restrained use |
| --- | --- | --- |
| `informational-new` | NUEVA/información neutral activa | Dot, icono, count, pequeña marca |
| `quoted-pending` | COTIZADA/pendiente | Pill, progress segment, stage marker |
| `negotiation` | NEGOCIACION | Pill, icono, chart/stage evidence |
| `success-won-delivered` | GANADA, activo exitoso, entregado | Texto/icono, progress, chart series |
| `danger-lost-error` | PERDIDA, error o destructivo real | Texto/icono, error local, destructive control |
| `warning-attention` | Seguimiento, espera o riesgo accionable | Attention item, dot, icono, warning local |
| `uncertain-unknown` | UNKNOWN/entrega sin confirmar | Icono/shape distintivo y copy explícito |

La mayoría del uso semántico es pequeño: icono, dot, pill, progress indicator, texto de
evidencia, chart series o selected state sutil. Ningún estado obliga a una card completa
coloreada. `uncertain-unknown` no se confunde con warning ni error definitivo.

### Light mode

- Canvas cálido y levemente retraído; `surface-primary` más luminoso, no blanco puro
  repetido en cada módulo.
- `surface-secondary` separa zonas mediante temperatura/luminosidad, no mediante un
  borde gris alrededor de todo.
- `surface-raised` usa una elevación corta sólo cuando realmente flota.
- Dividers permanecen visibles pero subordinados; strong border no domina el layout.
- FAA yellow mantiene foreground oscuro y suficiente contraste; `accent-muted` debe
  verse seleccionado sin parecer warning.
- Colores operativos se oscurecen/desaturan para texto/iconos y usan fondos muted sólo
  en estados locales.
- Shadows son cálidas, breves y de baja opacidad; no producen cards flotantes masivas.

### Dark mode

- Canvas y surfaces forman pasos de luminancia deliberados; no son inversión de Light
  ni una colección de grises casi idénticos.
- `surface-interactive`, hover y selected se reconocen sin glow, neon o blur.
- Dividers son más claros que canvas pero menos prominentes que texto/controles.
- Yellow conserva identidad sin saturar; selected combina fondo tintado, icono/texto y
  forma, no un bloque mostaza.
- Colores operativos se desaturan/levantan para mantener contraste sin luminosidad
  agresiva.
- Shadows se reservan a Level 3 y objetos levantados; la jerarquía principal proviene
  de tonos, no sombras negras grandes.

Ambos temas deben parecer el mismo producto. Cada combinación texto/fondo, icono,
focus, disabled y control se valida para su uso WCAG 2.2 AA; no se acepta un tema como
versión secundaria del otro.

## Typographic hierarchy

IBM Plex Sans 400/500/600 permanece como única familia. Los roles son semánticos y no
se reemplazan por clases arbitrarias feature-locales:

| Role | Intended expression |
| --- | --- |
| Workspace title | 24–28 px, 600, línea compacta; una sola vez por ruta |
| Major metric | 32–40 px según espacio, 600, tabular numerals |
| Section title | 16–20 px, 600, sin eyebrow obligatorio |
| Body | 14–16 px, 400, line-height cómoda |
| Supporting metadata | 12–13 px, 400/500, contraste secundario/terciario válido |
| Label | 12–13 px, 500, sentence case; visible cuando el control lo necesita |
| Compact operational text | 13–14 px, 400/500, alta legibilidad y line-height contenida |

Texto esencial nunca baja de 12 CSS px. Cantidades, fechas, counts y métricas usan
tabular numerals cuando mejora la exploración.

### Redundant-copy rules

- Una ruta tiene un único workspace title. AppShell y page composition acuerdan quién
  lo renderiza; no se repite `Dashboard` o `Pipeline` como `h1` y `h2` consecutivos.
- Se elimina el eyebrow global `FAA CRM` cuando la marca/sidebar ya da contexto.
- No se usa `PANORAMA COMERCIAL`, `GESTIÓN`, `MÓDULO` u otro uppercase eyebrow para
  volver a explicar un heading evidente.
- Descripciones permanentes sólo permanecen si cambian una decisión o previenen un
  error; instrucciones específicas aparecen cerca de la acción relevante.
- Un valor autoexplicativo de filtro no necesita un label visual permanente. Conserva
  nombre accesible y tooltip/description cuando haga falta.
- No se repite status, título o identidad dentro de la misma lectura sin una necesidad
  de sticky context o accesibilidad documentada.

## Spacing and density

Se conserva el ritmo 4/8 de CRM-018 con roles consistentes:

| Context | Guidance |
| --- | --- |
| Workspace outer gutter | 20–32 px según ancho disponible; reduce antes de comprimir contenido |
| Operational section gap | 16–24 px |
| Dashboard major section gap | 24–32 px cuando la jerarquía gana claridad |
| Module padding | 16 px compacto; 20–24 px para lectura primaria |
| Card/object padding | 12–16 px; no padding grande para poco contenido |
| Dense list row | 44–52 px base, crece con contenido real |
| Comfortable primary row | 52–64 px |
| Modal body | 20–24 px; 16 px en subzonas compactas |
| Modal section gap | 20–24 px; actions separadas por espacio/divider intencional |

Control height families:

- **compact 36 px:** filtros/toolbars de escritorio; mantiene target práctico mediante
  hit area/spacing y nunca baja del mínimo WCAG aplicable;
- **standard 44 px:** formularios y acciones primarias;
- **generous 48 px:** login, composer o contextos donde mejora la precisión.

Icon-only controls conservan target de 44 por 44 px aunque el glyph sea 16–20 px. No se
crean contenedores bordeados gigantes para ocupar altura disponible. El espacio vacío es
parte del canvas; un empty state no necesita estirar una card hasta el fondo.

## Radius and shape language

La geometría continúa Apple-like, suave y sobria:

- `radius-control`: 8–10 px para buttons, inputs, selects y rows interactivos;
- `radius-surface`: 12–14 px para objetos/cards y superficies locales reales;
- `radius-overlay`: 16–20 px para modals, popovers grandes y floating context;
- `radius-pill`: full sólo para status, filtros, selección compacta y toggles.

No se introducen radios feature-locales de 4 px ni interfaces dominadas por 90 grados.
Tampoco se convierten cards, tablas, botones ordinarios o cada metadata value en pills.

## Button system

| Variant | Role |
| --- | --- |
| Primary | FAA yellow; acción más importante dentro del contexto local |
| Secondary | Superficie neutral; acción relevante alternativa |
| Ghost | Bajo peso para utilities, dismiss, navegación local y acciones frecuentes |
| Destructive | Sólo pérdida, desactivación o consecuencia genuinamente destructiva |

Rules:

- Un screen o módulo local no muestra varias acciones Primary compitiendo. Flujos por
  pasos cambian cuál es Primary en vez de acumularlas.
- Hover altera tono/border de forma breve; active aporta feedback inmediato y sutil;
  focus es visible, separado y no depende de hover.
- Disabled explica indisponibilidad cuando no es obvia, conserva label legible y no se
  simula sólo con opacidad extrema.
- Loading mantiene ancho/label suficiente, anuncia progreso, bloquea duplicado y no
  transforma una acción en éxito antes de respuesta autoritativa.
- Icon-only requiere nombre accesible, tooltip cuando la convención no sea universal,
  glyph de una sola familia y target 44 px.
- Danger no se usa como énfasis genérico ni para Cancelar.

## Filter and toolbar language

Los filtros se convierten en una toolbar de producto compacta, subordinada al trabajo.
Composición conceptual:

`[ Buscar oportunidades… ] [ Recientes ↓ ] [ Todos los orígenes ] [ Filtros · 2 ]`

- Search conserva label accesible; placeholder puede expresar el dominio cuando el
  nombre visual sería redundante.
- Sort/filter usa el valor actual como label visible cuando es autoexplicativo.
- `Filtros · N` abre un popover origin-aware y muestra cantidad exacta de filtros
  secundarios activos; no cuenta defaults.
- Filtros activos se ven en el trigger y, cuando ayuda, en chips removibles compactos.
  `Restablecer` aparece sólo con cambios.
- Segmented controls se reservan a pocas opciones mutuamente exclusivas; pills/toggles
  sirven a filtros booleanos compactos.
- Popovers agrupan labels y ayuda que sí son necesarias dentro del formulario; reducir
  labels en toolbar no autoriza placeholder-only forms.
- Tab order sigue lectura, Escape cierra el popover seguro, focus vuelve al trigger y
  todos los controles tienen nombre/estado accesible.
- Toolbars responden por wrap/progressive disclosure antes de crear overflow de página.
- Se preservan exactamente debounce, AND semantics, query params, server pagination,
  filtros existentes y ausencia de seller filter de las specs propietarias.

## Sidebar polish

Se conserva sidebar expandida/colapsada, icon navigation, badge, cuenta, tema y logout.
No se reemplaza por navbar ni se vuelve amarilla.

- Active item usa `accent-muted`, texto de peso 600, icono amarillo y un indicador
  pequeño de posición/forma. No usa un bloque mostaza completo.
- Hover y pressed son neutrales; focus es inequívoco y no se confunde con active.
- Collapsed mantiene active marker, tooltips/nombres accesibles, badge y target de
  toggle. La transición no roba foco ni comprime contenido por debajo de mínimos.
- Espacio y divisores sutiles crean grupos mentales sin headings permanentes obligatorios:
  Work (`Pipeline`, `Dashboard`, `Notifications`), Communication (`WhatsApp`, `Envíos
  WhatsApp`), Management (`Clientes`, `Productos`, `Perdidas`) y Administration
  (`Usuarios`) cuando el rol lo permite.
- El área inferior muestra identidad de cuenta, rol, acceso a tema y logout con menor
  peso que navegación. Email puede estar en account disclosure, no siempre visible.
- Badge de Notifications conserva conteo exacto/backend y no compite con active state.
- Visibilidad por rol permanece exactamente backend/spec-authoritative.

## Pipeline visual direction

Pipeline es la superficie diaria principal y recibe la identidad más reconocible del
producto. Conserva exactamente `NUEVA`, `COTIZADA`, `NEGOCIACION`, `GANADA`; `PERDIDA`
permanece fuera del board.

### Board and columns

- Board usa scroll horizontal local ya aprobado; nunca overflow horizontal de página.
- Columnas son work zones tonales Level 1, no cuatro fieldsets con perímetros pesados.
- Header de columna alinea stage label, count compacto y evidencia semántica pequeña.
  Puede ser sticky dentro del board sin parecer una card independiente.
- Stage accents aparecen como dot/icono/pequeña marca o tono seleccionado, no como
  borde superior/izquierdo decorativo completo.
- Separación entre columnas surge de gutter y tono; borde sutil sólo si un tema/ancho
  necesita preservar el límite.
- Empty column usa una línea/ícono sutil y copy breve dentro de la zona, no una gran
  placeholder card.

### Lead cards

La card es un objeto manipulable Level 2 con superficie interactiva y elevación muy
breve. Prioriza en este orden:

1. Customer/company identity;
2. contacto o ubicación cuando sea útil y ya esté proyectado;
3. producto principal/evidencia cotizada soportada;
4. source;
5. Legendary evidence cuando aplique.

Stage age permanece opcional/secundario según CRM-019. No se agrega WhatsApp directo a
cada card; las acciones detalladas siguen en CRM-020. No se rellenan cards con texto
explicativo ni se crean cards grandes para escasa información.

States:

| State | Visual behavior |
| --- | --- |
| Hover | Leve cambio tonal/elevación; sólo pointer fino |
| Keyboard focus | Ring/outline fuerte y claro, sin depender de hover |
| Dragging | Objeto elevado, opacidad contenida y cursor/feedback apropiado; conserva tamaño |
| Valid drop target | Zona tonal + strong outline/instrucción accesible; no flash |
| Optimistic moving | Card ocupa destino con estado `Moviendo…`; no declara éxito antes de reconciliar |
| Selected/open | Estado persistente sutil que vincula card y detalle sin competir con status |

DnD keyboard, transiciones y rollback permanecen CRM-019/020-authoritative.

## Dashboard visual hierarchy

Dashboard recibe el mayor rediseño compositivo. No es una grilla uniforme de cards.

### A. Operational attention

Primera pregunta: **¿Qué necesita atención ahora?**

- Es la primera región visual después del título/filtros y puede usar una banda tonal,
  lista priorizada o composición integrada en vez de cards independientes.
- Sólo incluye evidencia ya soportada: seguimientos/stale notifications, unread
  notifications, existencia de conversaciones esperando respuesta y oportunidades
  creadas cuando CRM-021 lo autoriza.
- No inventa conteo total de conversaciones cuando el backend sólo prueba existencia.
- Cada item distingue cantidad/estado, label, icono y handoff real; no aparenta ser
  clickable si la ruta no preserva el significado.
- Estado sin atención es calmo y compacto, no una celebración ni un panel vacío grande.
- Puede usar microinteraction una vez al ingresar/cambiar evidencia autoritativa para
  dirigir la mirada; nunca pulsa, rebota ni reanima por polling rutinario.

### B. KPI layer

- Los cinco KPIs aprobados se agrupan como una banda/estructura común con dividers y
  cambios de span; no cinco cajas idénticas.
- Valor grande primero, label breve después y una sola línea de contexto autoritativo.
- `Resultados cerrados` conserva su relación paired; conversion null conserva copy
  exacto. No se agregan delta, flechas o tendencias falsas.
- FAA yellow destaca un dato/selección primaria como máximo; success/danger sólo donde
  su significado existe.

### C. Analysis

- `Evolución comercial` ocupa el mayor span y es la visualización analítica primaria.
- Conversión y Pipeline actual son secundarios y se ubican juntos/alrededor sólo si
  conservan mínimos legibles.
- Producto, origen y provincia son terciarios, con ranked bars/listas compactas.
- No todos los módulos tienen header, borde y padding idénticos; su jerarquía surge de
  tamaño, posición, whitespace y peso.
- Se mantienen los SVG/DOM existentes, no se agrega chart library.
- Cada chart conserva título/contexto, leyenda, summary y alternativa textual/tabla
  exacta accesible de CRM-021; ninguna simplificación visual elimina datos.

## Empty states

`EmptyState` se convierte en una familia reutilizable con iconografía SVG compacta,
título corto, una oración útil y acción opcional sólo cuando existe una acción válida.

| Variant | Use | Spatial behavior |
| --- | --- | --- |
| Small | Lista/columna/filtro local | Inline, 48–96 px aprox.; no crea card propia |
| Medium | Módulo o panel principal | Centrado dentro del contenido natural, no estira la página |
| Workspace | Dataset inicial sin contenido y acción relevante | Composición abierta/tonal con acción; no giant bordered container |

Se distinguen dataset vacío, búsqueda/filtro sin resultados, entidad no seleccionada,
permiso/bloqueo y error. Copy sigue el patrón título + una sentencia accionable, por
ejemplo `Todavía no hay productos` / `Creá el catálogo que luego usarás en las
cotizaciones.` / `Crear producto`, sólo para rol autorizado. No se fuerza una acción
cuando la siguiente decisión no existe.

## WhatsApp visual polish

CRM-023 conserva autoridad completa. La UI se acerca a un producto desktop de
mensajería maduro sin copiar marca, verde, logos ni bubbles de WhatsApp.

- El workspace puede ser una superficie Level 1 continua; no necesita una card global
  con borde alrededor de las tres columnas.
- Inbox es denso y scannable, Conversation es la superficie primaria más abierta, CRM
  context es suplementario y tonalmente retraído.
- Separadores verticales son dividers funcionales; en anchos menores context se
  colapsa/overlay según CRM-023.

### Inbox

- Conversation row prioriza identidad, actividad/time y evidencia unread/waiting.
- Selected usa background sutil, strong text y pequeño indicador; elimina `border-left`
  decorativo permanente.
- Unread usa peso/dot/count y texto accesible; waiting usa icono/label semántico sin
  alarma visual. Backend ordering permanece autoritativo.
- Search y toggles adoptan toolbar compacta; no fieldset visual administrativo.

### Active conversation

- Inbound/outbound bubbles comparten geometría FAA, alineación familiar y contraste
  suficiente; no replican forma o color de WhatsApp.
- HUMAN vs Broadcast aparece sólo donde operacionalmente importa mediante label/icono
  compacto, no como banner en cada mensaje.
- Timestamps y delivery states son secundarios pero legibles; `UNKNOWN` usa tratamiento
  inequívoco y copy `Entrega sin confirmar`.
- Media usa preview/document row contenido sin nested card decorativa. Composer es una
  zona anclada, clara y de alta prioridad con attachment/template modes integrados.
- Window/template/reconnect states se insertan cerca del composer/header con tono
  semántico y altura mínima, no como múltiples banners apilados si pueden agruparse.

### CRM context

- Superficie secundaria con secciones abiertas, dividers y progressive disclosure; no
  cada campo dentro de una card.
- Opportunity summaries son compositions compactas; CRM-020 conserva full detail.
- Collapse control mantiene nombre, focus y estado accesible; cerrado libera ancho a
  chat sin perder contexto ni draft.

## Administrative and operational workspaces

### Customers

- Es un workspace de relaciones, no mini-dashboard: título + `Nuevo cliente` Primary,
  `Importar CSV` Secondary sólo para supervisor, toolbar compacta y contenido denso.
- Search no vive dentro de panel propio. Lista/table hybrid prioriza identidad/company,
  una evidencia de contacto, provincia y Legendary.
- Filas populated usan hover/focus/selected y dividers, no cards completas repetidas.
- Detail sigue CRM-024/020; no se agregan métricas por Customer ni N+1.

### Products

- Catálogo pequeño y atractivo: lista/grid compacta adaptable, no giant table por
  defecto. Cada item presenta nombre, active/inactive, metadata ya soportada y acciones
  de supervisor.
- No se inventan precio, SKU, stock, categoría, imagen ni descripción.
- Inactive usa icono/label + tono muted y conserva legibilidad/historia.
- Header puede integrar counts pequeños sin convertirse en dashboard.

### Lost

- Sigue siendo historia/operación, no Dashboard ni quinta columna.
- Toolbar simplifica search, Motivo y `Filtros · N`; no seller filter.
- Estadísticas actuales/históricas se integran como una banda compacta con dividers,
  no tres generic cards.
- Motivos pueden usar semantic chips compactos sin rainbow; el mismo motivo conserva
  mismo tratamiento.
- Lista prioriza Customer, motivo y fecha; reopen y navegación canónica permanecen
  CRM-020/024-authoritative.

### Notifications

- History se presenta como activity feed cronológico compacto, no tabla/card wall.
- Row contiene semantic icon, identidad/contexto Customer/Opportunity, copy breve y
  estrategia temporal: tiempo relativo para exploración reciente con fecha/hora
  absoluta accesible/visible al expandir o cuando evita ambigüedad.
- Unread usa peso, dot/icono y background sutil; transición a read reduce énfasis sin
  reordenar ni desaparecer evidencia.
- Toda la row comunica click affordance y focus; `Todas | Sin leer` permanece un
  SegmentedControl compacto. Badge conserva total exacto.
- Empty/no-unread states son Small/Medium, no giant panels.

### WhatsApp Sends

- Historia se siente operacional/auditable, no marketing campaign manager.
- Execution rows son compactas con template/label, lifecycle, timestamps, recipients y
  outcomes autorizados; no table chrome excesivo.
- Lifecycle indicators y outcome visualization son sobrios, textuales y no rainbow.
- Creación progresiva mejora step hierarchy, summary y siguiente acción sin convertir
  pasos en cards anidadas.
- Recipient results priorizan Customer/outcome/time; attempts/audit siguen bajo demanda.
- `UNKNOWN` se separa de failed/warning con token e iconografía propios y conserva la
  advertencia de duplicado; no se agrega retry.

## Users and account finding

La auditoría determina **B: supervisor user administration already has backend support
and should be surfaced**.

Evidence:

- `/users` ya existe en navegación como destino exclusivo de `SUPERVISOR`, pero renderiza
  `PlaceholderPage`;
- CRM-001 aprueba que supervisores administren usuarios;
- backend expone `GET/POST /api/users`, `GET/PATCH /api/users/{id}` y
  `PUT /api/users/{id}/password` sólo para supervisores;
- el contrato soporta nombre, email, rol `SUPERVISOR | VENDEDOR`, active/inactive y
  reemplazo de contraseña; deactivación/password replacement revocan sesiones según
  CRM-016;
- `/auth/me` ya devuelve nombre, email, rol y active state a cualquier usuario;
- ThemeProvider ya ofrece Light/Dark/System y persiste la elección localmente.

Por lo tanto, la futura implementación de CRM-027:

- reemplaza `/users` placeholder por un workspace supervisor-only compacto de listado,
  alta, edición, activación/desactivación y reemplazo deliberado de contraseña;
- usa sólo los campos/roles/acciones actuales, sin permisos configurables ni delete;
- trata activación y password como acciones de seguridad con confirmación/copy claro;
- mantiene lista densa y administración simple, no un dashboard de usuarios;
- conserva para ambos roles un área de cuenta en sidebar/account disclosure con nombre,
  email, rol, Theme Light/Dark/System y logout.

No existe contrato de autoedición, cambio de contraseña propio ni preferencia de tema
server-side. Esas capacidades quedan fuera de CRM-027. Su ausencia no bloquea el
polish/account baseline; cualquier incorporación futura requiere spec/API explícitos.
No se reutilizan endpoints supervisor-only como si fueran self-service.

## Microinteractions and motion

Motion es funcional, corto, interruptible y poco frecuente:

| Interaction | Guidance |
| --- | --- |
| Press feedback | 100–160 ms, transform muy sutil cuando no altera precisión |
| Hover/color/focus transition | 120–180 ms; hover sólo pointer fino |
| Tooltip/small popover | 125–180 ms, origin-aware; siguientes tooltips pueden ser inmediatos |
| Filter popover/modal | 160–240 ms enter, salida más rápida; modal centrado |
| Sidebar collapse | 180–220 ms, transform/layout coordinado sin bloquear input |
| Card drag | Respuesta directa al puntero; settle breve e interrumpible |
| Context panel collapse | 180–220 ms; chat mantiene prioridad y foco |
| Success/read acknowledgement | Cambio tonal/iconográfico breve, sin celebración |
| Operational attention | Una sola entrada/cambio autoritativo; no loop ni polling reanimation |

No se anima una acción iniciada por teclado cuando la animación demoraría el trabajo.
Se priorizan opacity/transform y transitions interrumpibles; no se animan width/height
de listas densas si provoca layout jank. No hay bounce decorativo, large scale, springs
excesivos, fake loading ni movimiento constante.

`prefers-reduced-motion: reduce` elimina movimiento espacial/path drawing y deja cambios
de color/opacity mínimos sólo si aclaran estado. Datos y controles están disponibles de
inmediato.

## Iconography

Se conserva y amplía el sistema SVG interno `shared/Icon`; no se agrega dependencia.

- 16 px: metadata/status inline;
- 20 px: navigation, buttons y toolbars;
- 24 px: empty-state small/medium o feature anchor excepcional;
- stroke, caps, joins y optical weight consistentes en todas las adiciones;
- icon + text gap de 6–8 px según tamaño;
- iconos decorativos usan `aria-hidden`; icon-only controls reciben accessible name y
  tooltip cuando el significado no es universal;
- status icons no reemplazan labels necesarios y no se usan emoji como iconografía core.

La implementación primero audita/reutiliza glyphs actuales. Un icono nuevo se añade al
sistema existente sólo si ninguna forma actual comunica el concepto.

## Responsive and zoom visual guidance

Se preservan los comportamientos CRM-018–025 y se diseña sobre ancho CSS disponible:

- **1920-class desktop:** jerarquía completa, gutters controlados y spans analíticos;
  no se estira copy/cards indefinidamente.
- **Common laptop:** reduce gutters/gaps, colapsa secundarios antes de comprimir el
  trabajo principal; sidebar puede seguir expandida si hay ancho útil.
- **Sidebar collapsed:** aumenta área de board/chat/análisis y conserva grupos mediante
  spacing/tooltips/active marker.
- **125%:** toolbars wrap/progressive disclosure; Dashboard reordena secundarios.
- **150%:** sidebar colapsa, WhatsApp prioriza chat, detalles pasan a una columna y
  tablas priorizan columnas/list detail.
- **200% structural expectation:** navegación, title, primary action y flujo central
  siguen alcanzables; layouts se apilan o usan overlays/local scrolling documentado.

No hay page-level horizontal overflow. Pipeline, tablas exactas y regiones data-heavy
pueden hacer scroll local etiquetado según sus specs. No se desactiva zoom ni se reduce
tipografía esencial para forzar una composición.

## Accessibility contract

Polish nunca reduce accesibilidad:

- foco visible en Light/Dark y distinguible de selected/error;
- navegación completa por teclado, orden lógico y semantic controls;
- labels visibles en forms; reducir labels visuales de filtros sólo con accessible name
  y valor/contexto inequívocos;
- states nunca color-only; status incluye texto, icono, shape o posición;
- contrast WCAG 2.2 AA para el uso previsto de texto/icono/controls y themes;
- tooltips complementan, no contienen información necesaria inaccesible por touch/
  keyboard;
- charts mantienen alternativas exactas, captions y navegación aprobada;
- modals conservan title/description, initial focus, trap, safe Escape y focus return;
- DnD conserva alternativa Space/arrows/Enter/Escape;
- live regions son mesuradas; motion respeta reduced motion;
- texto útil no se elimina por estética: se reubica, reduce redundancia o pasa a una
  disclosure accesible.

## Design anti-patterns

La implementación de CRM-027 prohíbe explícitamente:

- decorative left borders everywhere;
- every section inside a card;
- every card using identical border;
- excessive nested rectangles;
- excessive uppercase eyebrow text;
- redundant headings;
- labels explaining obvious controls;
- yellow-filled navigation everywhere;
- giant empty bordered containers;
- arbitrary gradients;
- arbitrary shadows;
- rainbow semantic coloring;
- meaningless animations;
- fake statistics;
- fake trends;
- unnecessary explanatory copy;
- generic admin-template styling;
- styling components individually without shared tokens/primitives;
- raw `slate/amber/rose/white` feature colors cuando existe un rol semántico;
- copiar WhatsApp, Caterpillar, Mailchimp, Meta Ads o una estética AI dashboard;
- glassmorphism, neon, glow, fondos industriales o gradients como identidad;
- pills universales, cards universales o shadows universales.

## Shared component strategy

La auditoría encuentra primitives existentes en `frontend/src/shared/`: `Button`,
`IconButton`, `Input/Search/Select`, `Badge`, `Surface`, `EmptyState`, `ErrorState`,
`SegmentedControl`, `Modal`, `ConfirmationDialog`, `Drawer`, `Icon`, feedback, loading y
overlay primitives. También encuentra composiciones repetidas sin primitive claro:
toolbar/filter trigger, metric group, list row, sidebar item y tooltip accesible.

La futura implementación prefiere evolucionar lo existente:

| Primitive/composition | Required evolution |
| --- | --- |
| Button | Consolidar Primary/Secondary/Ghost/Destructive, hover/active/focus/loading/disabled y single-primary rule |
| IconButton | Mantener 44 px target, tooltip/naming coherente y tamaños de glyph |
| Input / Select | Conservar form labels; separar `FilterControl` compacto del Select administrativo |
| SearchField | Variant toolbar con icono, clear, pending y label accesible |
| FilterControl | Trigger/value/count/popover compartido; no cambia query semantics |
| Card / Surface | Reemplazar `ui-panel` universal por roles Level 1/2/3 y opción borderless/divided |
| EmptyState | Variants small/medium/workspace y acción opcional |
| StatusPill / Badge | Mapeo semántico completo incluido UNKNOWN; uso compacto, no value-pill universal |
| SegmentedControl | Shape/densidad/focus comunes, sin fieldset visual pesado |
| Modal | Surface Level 3, spacing, header/actions y motion consistente |
| Tooltip | Accessible, origin-aware, delayed-first/instant-following cuando corresponda; sin dependencia nueva |
| SidebarItem | Active/hover/focus/badge/collapsed y group spacing compartidos |
| Metric | Primitive visual de value/label/context, no dueño de datos ni card obligatoria |
| Toolbar | Layout/wrap/search/filter/actions; no conoce filtros de negocio |
| ListRow | Densidad, dividers, hover/focus/selected y slots semánticos; preserva markup table/list apropiado |

No se crea una abstracción sólo para reducir líneas. La frontera obligatoria es:

1. **visual primitive:** estilo, interacción genérica y accesibilidad;
2. **feature composition:** orden y jerarquía específica de Pipeline/Dashboard/etc.;
3. **data state:** hook/page/API owns loading, polling, filters, mutation y business
   evidence.

Un `ListRow` no reemplaza semantic `<tr>` cuando una tabla es la estructura correcta.
Un `Metric` no calcula métricas. Un `FilterControl` no traduce ni inventa backend query.

## Frontend architecture, security and performance

- Se preserva React/TypeScript/Tailwind/Vite, router interno, API modules tipados,
  feature hooks/state y `frontend/src/shared/`.
- La migración reemplaza raw visual values por tokens/primitives sin mover business
  logic a componentes.
- No se agrega dependencia runtime. CSS transitions/WAAPI o capacidades actuales bastan
  para motion aprobado.
- No se agrega global state, chart library, icon library, font externa ni CSS-in-JS.
- No se altera CSP, bearer handling, provider/media URLs ni rendering de datos no
  confiables.
- Visual refinement no agrega N+1, prefetch masivo, DOM ilimitado, polling o rerenders.
- Hover/elevation/motion no debe producir layout shift; charts y listas conservan
  performance y last-good data.

## Backend gaps and constraints

No hay backend blocker para el alcance visual ni para el baseline de Users:

- supervisor user CRUD/activation/password replacement ya existe;
- current account read existe en `/auth/me`;
- theme es preference client-side aprobada por CRM-018.

Gaps explícitos, fuera de alcance:

- no self-service profile update;
- no self-service password change;
- no server-side/cross-device theme preference;
- no configurable permissions beyond `SUPERVISOR`/`VENDEDOR`;
- user mutations no tienen un contrato nuevo de optimistic concurrency específico de
  CRM-027; esta spec no lo inventa.

Si producto requiere cualquiera de esos comportamientos, necesita una spec de contrato
backend/security separada. Su ausencia no justifica dejar `/users` como placeholder.

## Implementation sequence

Para evitar una mezcla prolongada de lenguajes visuales, una futura implementación
aprobada sigue este orden y deja cada bloque estable antes del siguiente:

1. Tokens: surfaces, text, borders, accent, operational states, typography, spacing,
   radius, elevation y motion.
2. Shared controls: Button/IconButton, fields, Search/FilterControl, SegmentedControl,
   Badge, Surface, EmptyState, Tooltip, Toolbar, Metric y ListRow contracts.
3. AppShell/sidebar/account treatment y eliminación de heading redundante.
4. Pipeline board, columns, lead cards, DnD states y empty columns.
5. Dashboard attention, KPI grouping y analysis hierarchy.
6. WhatsApp Inbox, conversation, messages, composer y CRM context.
7. Notifications activity feed.
8. Customers workspace/list/search/detail entry points.
9. Products compact catalog.
10. Lost toolbar/statistics/list.
11. WhatsApp Sends history/creation/detail/results.
12. Users supervisor workspace and shared account disclosure.
13. Modals, Opportunity/Customer detail, Quote, import and other focused flows.
14. Light/Dark parity pass across every changed primitive/workspace.
15. Responsive/zoom visual adaptation at 1920/laptop/125/150/200 expectations.
16. Handoff to CRM-026 reproducible browser/accessibility/responsive QA.

No workspace comienza creando nuevos feature-local styles para esperar luego la
consolidación. Los primitives necesarios se estabilizan antes de migrar sus consumidores.

## Acceptance criteria

- AC-01: La implementación no usa `border-left` decorativo de forma sistemática; todo
  acento izquierdo restante corresponde a warning/attention semántico explícito y
  también tiene icono/texto.
- AC-02: Canvas, workspace, local interactive y overlay surfaces se distinguen mediante
  tono, whitespace, grouping, divider o elevation antes que bordes completos.
- AC-03: Borders siguen jerarquía no-border/subtle/control/strong y no todos los módulos
  o cards usan el mismo perímetro.
- AC-04: Los tokens canónicos cubren surfaces, text, borders, FAA accent, siete roles
  operativos, interaction y Light/Dark sin raw feature colors.
- AC-05: FAA yellow es selectivo: una acción Primary por contexto local y acentos
  pequeños; no domina navegación, cards, módulos o charts.
- AC-06: IBM Plex Sans mantiene roles workspace/metric/section/body/metadata/label/
  operational, números tabulares y mínimo legible; no hay eyebrows/headings duplicados.
- AC-07: AppShell presenta una sola identidad/título útil por ruta y elimina la secuencia
  redundante `FAA CRM` + ruta + heading repetido + descripción obvia.
- AC-08: Spacing/control/list/modal families producen workspaces densos pero cómodos,
  sin giant empty panels ni padding arbitrario.
- AC-09: Radius scale conserva geometría suave sin 90-degree-heavy UI ni pillification
  de cards, tablas y botones ordinarios.
- AC-10: Button Primary/Secondary/Ghost/Destructive tiene estados hover, active,
  disabled, focus y loading consistentes; varias Primary no compiten en una pantalla.
- AC-11: Pipeline, Dashboard, Lost, Customers y WhatsApp usan toolbars compactas con
  valores autoexplicativos, active-filter count/reset y keyboard accessibility, sin
  cambiar filtros backend ni agregar seller filter.
- AC-12: Sidebar expandida/colapsada conserva arquitectura, rutas, groups mentales,
  badge, account/theme/logout y role visibility; active state es premium y no un bloque
  amarillo grande.
- AC-13: Pipeline conserva cuatro active stages y Lost fuera; sus columnas se perciben
  como work zones y cards como objetos manipulables con todos los estados pointer/
  keyboard/drag/reconciliation aprobados.
- AC-14: Pipeline cards priorizan identidad y evidencia comercial autorizada, no agregan
  WhatsApp directo ni exhiben grandes espacios vacíos.
- AC-15: Dashboard comunica atención > KPIs > análisis; Evolución domina el análisis,
  conversion/Pipeline son secundarios y product/source/province terciarios.
- AC-16: Dashboard no agrega fake statistics/trends, conserva semántica backend y cada
  chart mantiene alternativa textual/tabular exacta.
- AC-17: EmptyState ofrece variants small/medium/workspace intencionales con título,
  una frase y acción opcional válida, sin giant bordered container.
- AC-18: WhatsApp se percibe como messaging workspace con chat primario, inbox denso y
  CRM context suplementario, sin copiar branding/green/shape de WhatsApp.
- AC-19: Mensajes expresan HUMAN/Broadcast, timestamp, delivery, media y UNKNOWN cuando
  corresponde, sin alterar contratos, retry o waiting semantics.
- AC-20: Customers se percibe como relationship workspace; Products como catálogo
  pequeño; Lost como historia operacional; ninguno adopta peso analítico de Dashboard.
- AC-21: Notifications se presenta como activity feed cronológico con unread, time,
  context, click/read transition y exact badge accesibles.
- AC-22: WhatsApp Sends se percibe operacional/auditable, con lifecycle/outcomes/
  UNKNOWN sobrios, no como marketing campaign product.
- AC-23: `/users` deja de ser placeholder para supervisores y usa sólo contratos
  existentes de list/create/edit/activate/deactivate/password; vendedores no acceden.
- AC-24: Ambos roles pueden consultar account information, Theme Light/Dark/System y
  logout sin inventar self-edit, own-password o server preference.
- AC-25: Iconography usa una familia SVG, tamaños 16/20/24, stroke/spacing consistente,
  accessible names y ningún emoji core; no agrega icon dependency.
- AC-26: Motion es funcional, breve, interrumpible, reduced-motion safe, no bloquea
  keyboard/input, no hace loop ni simula loading/tiempo real.
- AC-27: Light y Dark aplican la misma jerarquía de canvas/surfaces/borders/accent/
  semantic/elevation, cumplen contraste previsto y ambos se perciben terminados.
- AC-28: 1920 desktop, laptop, sidebar expanded/collapsed, zoom 125/150 y expectativa
  estructural 200 mantienen navegación, acción primaria y trabajo útil sin page overflow;
  sólo regiones aprobadas hacen scroll local.
- AC-29: Focus, keyboard, semantic controls, labels/names, non-color evidence, contrast,
  reduced motion, chart alternatives y modal focus management no regresan.
- AC-30: Shared primitives evolucionan antes de workspaces; visual primitive, feature
  composition y data state permanecen separados y no nacen abstracciones por line count.
- AC-31: No se elimina ni modifica funcionalidad CRM-018–025, regla comercial,
  autorización, ruta canónica, API, polling o state machine.
- AC-32: Refinement no causa regresión medible de input responsiveness, layout shift,
  bundle/dependency count, request count o rendering/polling behavior.
- AC-33: No se agrega dependencia; una excepción futura requiere justificación explícita,
  impacto de bundle/mantenimiento/accesibilidad y aprobación antes de implementarse.
- AC-34: La revisión visual no presenta anti-patterns prohibidos de esta spec y una
  inspección cruzada reconoce un único lenguaje FAA sin imponer la misma card composition.
- AC-35: CRM-026 ejecuta después de CRM-027 y valida su resultado mediante la matriz
  reproducible definida por CRM-026, sin duplicar decisiones de diseño.

## Relationship to CRM-026

El orden obligatorio queda:

`CRM-018–025 implemented behavior -> CRM-027 visual/product refinement -> CRM-026 final QA`

CRM-027 posee las decisiones visuales: tokens, surface hierarchy, typography, density,
control language, workspace composition, motion e igualdad Light/Dark. CRM-026 conserva
la responsabilidad final de:

- Playwright contra Docker Compose aislado;
- datos sintéticos controlados y migraciones frescas;
- semantic flows y cross-workspace navigation;
- Light/Dark/System;
- responsive y zoom matrix;
- keyboard, focus y browser behavior;
- visual inspection y diagnostic screenshots no pixel-perfect;
- accessibility verification;
- cleanup exclusivo del entorno aislado.

CRM-026 registra defectos contra los AC de CRM-027 o la spec feature propietaria. No
redefine la dirección visual ni crea una segunda capa de tokens/primitives. CRM-027 no
declara calidad final hasta que CRM-026 complete esa validación.

## Open decisions

None. La spec permanece `Draft` porque requiere revisión y aprobación explícita del
usuario; `Open decisions: None` no constituye aprobación.

## Follow-up / future specs

- Self-service account/profile/password sólo mediante una spec backend/security
  explícita si producto lo solicita.
- Preferencia de tema cross-device sólo si se aprueba persistencia backend.
- Una dependencia visual nueva sólo si la implementación demuestra una necesidad no
  cubierta por primitives actuales y obtiene aprobación previa.
- CRM-026 — Final reproducible browser, accessibility, responsive and zoom QA después
  de CRM-027.

## Implementation notes

No implementar esta spec hasta que cambie explícitamente a `Approved`. La futura
implementación debe preservar comportamiento y tests existentes, migrar por la secuencia
definida, probar cada AC relevante y completar todos los gates del repositorio antes de
commit/push. El trabajo visual se revisa en contenido poblado, vacío, error, loading,
Light/Dark, sidebar states y zoom; una captura bonita con datos ideales no demuestra
cumplimiento.

Las recomendaciones externas o vendorizadas son insumos de criterio, no autoridad:
se rechazaron deliberadamente tipografía Inter, green CTA, glassmorphism, gradients,
dark-first y motion decorativo porque contradicen CRM-018, FAA yellow, IBM Plex Sans y
la dirección de producto aprobada.
