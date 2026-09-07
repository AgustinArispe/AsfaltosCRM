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

Recrear el dataset conocido con el reloj canónico de CRM-026:

```bash
docker compose -p asfaltoscrm --env-file .env.example exec \
  -e QA_SUPERVISOR_PASSWORD='FAA-Visual-QA-2026!' \
  -e QA_SELLER_PASSWORD='FAA-Vendedor-QA-2026!' \
  backend python -m app.scripts.seed_visual_qa \
  --reset --anchor '2026-08-18T15:00:00+00:00'
```

`--reset` reconoce el fixture y las raíces exactas que crean los journeys CRM-026
(`Cliente CRM-026`, `Producto CRM-026 editado`, `usuario.crm026@faa.test` y
`Validación CRM-026`). Se detiene sin modificar nada si encuentra cualquier User,
Product, Customer, Conversation o Broadcast ajeno. Antes de cualquier reset manual
distinto de este comando, crear y validar un `pg_dump` fuera del volumen.

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

## Browser QA reproducible CRM-026

CRM-026 usa Playwright Python `1.62.0`, Chromium administrado por Playwright
`151.0.7922.34`, Pillow `12.3.0` para comparación visual y el motor oficial Axe
`4.13.0` para auditoría WCAG. Playwright y Pillow viven en el lock de desarrollo del
backend; Axe vive en el lock de desarrollo del frontend. No se necesita instalación
global ni se contacta infraestructura WhatsApp real.

Preparación local, una sola vez después de cambiar locks:

```bash
python -m pip install --require-hashes \
  -r backend/requirements.lock -r backend/requirements-dev.lock
python -m playwright install chromium
npm ci --prefix frontend
```

La alternativa reproducible recomendada es la imagen del repositorio, que instala
Chromium y sus librerías de sistema desde el target `browser-quality`:

```bash
docker build --target browser-quality -t asfaltoscrm-browser-quality backend
```

Con el stack canónico ya levantado y saludable, ejecutar desde la raíz:

```bash
./scripts/run-browser-qa.sh
```

El runner no inicia servidores alternativos. Verifica database/backend/frontend,
`/health`, Alembic head y el fixture; resetea con todas las guardas, ejecuta los 39
tests seriales en Chromium y vuelve a restaurar el dataset incluso después de un fallo.
La suite cubre roles, journeys, Axe, teclado, Light/Dark, reduced motion, los viewports
`1920x1080`, `1440x900`, `1366x768`, `1280x800`, `390x844` y zoom efectivo
`100/125/150/200` por reducción real del CSS viewport.

Los ocho PNG bajo `backend/quality/browser/baselines/` son la baseline versionada. Una
actualización debe ser deliberada y revisada:

```bash
docker run --rm --network host \
  -e UPDATE_VISUAL_BASELINES=1 \
  -v "$PWD/backend:/app" -v "$PWD/frontend:/frontend:ro" \
  -w /app asfaltoscrm-browser-quality \
  pytest -c quality/browser/pytest.ini quality/browser/test_40_visual_regression.py
```

Ante un fallo se escriben trace `.zip`, screenshot actual/diff y logs en
`backend/artifacts/playwright/`. GitHub Actions ejecuta el job independiente
`Browser quality` sobre un runner efímero, usa el mismo proyecto/URLs canónicos y sube
ese directorio durante siete días sólo cuando falla.

Para Visual QA manual, abrir solamente http://localhost:5173. Si `docker compose ls`
muestra stacks históricos todavía activos, detenerlos sin borrar sus volúmenes hasta
confirmar su procedencia. No usar `docker system prune` como mecanismo de cleanup.
