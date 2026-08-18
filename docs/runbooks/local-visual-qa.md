# Entorno local canónico de Visual QA

El único entorno local de referencia visual de FAA CRM usa el proyecto Docker Compose
`asfaltoscrm` y el código del `HEAD` actual. Los proyectos con sufijos de specs son
aislados y temporales; nunca deben presentarse como la aplicación canónica.

## URLs canónicas

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health: http://localhost:8000/health
- PostgreSQL local: `localhost:5432`

## Reconstruir e iniciar

Desde la raíz del repositorio:

```bash
docker compose -p asfaltoscrm --env-file .env.example up -d --build
docker compose -p asfaltoscrm --env-file .env.example ps
```

El backend espera PostgreSQL, ejecuta `alembic upgrade head` y recién después inicia
FastAPI. El frontend usa `/api` y Vite lo redirige al servicio `backend` dentro de la
red Compose.

## Dataset sintético CRM-027

El seed es exclusivamente de desarrollo, exige el provider Fake y rechaza producción,
otro nombre de base o datos que no reconozca como propios. No agrega endpoints y no
contacta servicios externos.

Credenciales locales determinísticas:

- Supervisor: `qa.supervisor@faa.test` / `FAA-Visual-QA-2026!`
- Vendedor: `qa.vendedor@faa.test` / `FAA-Vendedor-QA-2026!`

Crear el dataset sobre una base vacía:

```bash
docker compose -p asfaltoscrm --env-file .env.example exec \
  -e QA_SUPERVISOR_PASSWORD='FAA-Visual-QA-2026!' \
  -e QA_SELLER_PASSWORD='FAA-Vendedor-QA-2026!' \
  backend python -m app.scripts.seed_visual_qa
```

Recrear el dataset conocido:

```bash
docker compose -p asfaltoscrm --env-file .env.example exec \
  -e QA_SUPERVISOR_PASSWORD='FAA-Visual-QA-2026!' \
  -e QA_SELLER_PASSWORD='FAA-Vendedor-QA-2026!' \
  backend python -m app.scripts.seed_visual_qa --reset
```

`--reset` se detiene sin modificar nada si encuentra Users, Products, Customers,
Conversations o Broadcasts ajenos al fixture. Antes de cualquier reset manual distinto
de este comando, crear y validar un `pg_dump` fuera del volumen.

Consultar conteos sin modificar datos:

```bash
docker compose -p asfaltoscrm --env-file .env.example exec \
  backend python -m app.scripts.seed_visual_qa --summary
```

El dataset incluye Users de ambos roles, catálogo activo/inactivo, Customers de varias
provincias, Legendary manual y automático, Pipeline denso en las cuatro etapas, Lost y
reopen, Notes/history, Notifications activas e históricas, métricas con fechas y
volúmenes, Inbox Fake con estados y adjuntos sintéticos, conversación `NEEDS_REVIEW`,
templates humanos y Broadcasts Draft/Processing/Completed con outcomes variados.

## Entornos aislados CRM-026

CRM-026 debe usar un proyecto inequívoco por ejecución, por ejemplo
`asfaltoscrm_crm026_<run-id>`, puertos no canónicos y sus propios volúmenes. Su harness
debe detener y limpiar exclusivamente ese proyecto al finalizar. Nunca dejar un stack
aislado atendiendo `5173/8000` ni usarlo para capturas de referencia.

Para Visual QA manual, abrir solamente http://localhost:5173. Si `docker compose ls`
muestra stacks temporales todavía activos, detenerlos sin borrar sus volúmenes hasta
confirmar su procedencia. No usar `docker system prune` como mecanismo de cleanup.
