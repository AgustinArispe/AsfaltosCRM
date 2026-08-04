# Skills del proyecto

Estas skills están vendorizadas y versionadas para que el criterio utilizado por el
equipo sea reproducible. `.agents/skills.lock.json` es la fuente de verdad de cada
repositorio upstream, commit auditado, licencia y adaptación local.

## Jerarquía y uso

`AGENTS.md` y los requisitos funcionales tienen prioridad sobre las skills. Las skills
son herramientas de criterio especializado, revisión y consulta; no autorizan cambios
de arquitectura, producto ni dependencias por iniciativa propia.

No se ejecutan automáticamente en todas las tareas. Se aplican sólo cuando corresponde:

- `emil-design-eng`: implementación de interfaces e interacción.
- `pick-ui-library`: antes de incorporar una librería UI importante.
- `review-animations`: revisión de una funcionalidad con motion terminada.
- `find-animation-opportunities`: refinamiento puntual, no cada feature.
- `ui-ux-pro-max`: UX, jerarquía visual, densidad y sistema visual.
- `fixing-accessibility`: componentes interactivos, formularios, modales, teclado y drag & drop.
- `webapp-testing`: flujos funcionales completos en el navegador.

Motion debe explicar una interacción: priorizar drag and drop, modales, feedback,
cambios de estado y aparición/desaparición; evitar decoración y respetar
`prefers-reduced-motion`.

`webapp-testing` usa únicamente Playwright contra el stack de Docker Compose del proyecto
(`localhost:5173` y `localhost:8000`). No usa servidores alternativos, `shell=True`,
comandos generados sin revisión ni instalaciones globales. No se incluyen scripts de
instalación de las fuentes upstream.

Para actualizar una skill, volver a auditar la fuente, confirmar el commit exacto,
revisar sus archivos y actualizar el lock en el mismo cambio.
