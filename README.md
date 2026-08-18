# Asfaltos CRM

CRM web de Fábrica Argentina de Asfaltos, construido con React, TypeScript,
Tailwind CSS, FastAPI, PostgreSQL, SQLAlchemy, Alembic y Docker Compose.

## Requisitos

- Docker Desktop con Docker Compose v2 o superior.
- Git.

No hace falta instalar Python, Node ni dependencias del proyecto en la máquina: se ejecutan dentro de contenedores.

## Inicio desde cero

```bash
git clone https://github.com/AgustinArispe/AsfaltosCRM.git
cd AsfaltosCRM
cp .env.example .env
docker compose up --build
```

Al iniciar, el servicio `backend` espera que PostgreSQL esté saludable y ejecuta `alembic upgrade head` antes de levantar FastAPI.

Abrir:

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Documentación interactiva de la API: http://localhost:8000/docs
- Health check de API y base de datos: http://localhost:8000/health

El frontend utiliza `/api` como base y Vite redirige esas solicitudes internamente al backend durante el desarrollo.

Para revisión visual local, usar exclusivamente el proyecto Compose `asfaltoscrm`, las
URLs anteriores y el [runbook de Visual QA](docs/runbooks/local-visual-qa.md). Los
proyectos aislados con sufijos de specs no representan la aplicación canónica.

Para detener los servicios:

```bash
docker compose down
```

Los datos de PostgreSQL persisten en el volumen `postgres_data`. Para eliminar también esos datos de desarrollo, ejecutar explícitamente:

```bash
docker compose down -v
```

## Variables de entorno

Copiar `.env.example` como `.env` y ajustar sus valores si hace falta. El archivo `.env` está excluido de Git y no debe subirse. En particular, reemplazar `POSTGRES_PASSWORD` por una contraseña segura fuera del entorno local.

| Variable | Descripción | Valor de desarrollo |
| --- | --- | --- |
| `POSTGRES_DB` | Nombre de la base de datos | `asfaltos_crm` |
| `POSTGRES_USER` | Usuario de PostgreSQL | `asfaltos` |
| `POSTGRES_PASSWORD` | Contraseña local de PostgreSQL | `change_me` |
| `POSTGRES_PORT` | Puerto de PostgreSQL publicado en el host | `5432` |
| `JWT_SECRET` | Secreto de al menos 32 caracteres para firmar tokens JWT | reemplazar el ejemplo |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del access token en minutos | `60` |
| `ALLOWED_HOSTS` | Hosts HTTP aceptados por FastAPI, separados por comas y sin comodines | `localhost,127.0.0.1,backend,testserver` |
| `WEB_INTAKE_SIGNING_SECRET` | Secreto HMAC exclusivo del servidor que envía leads Web; mínimo 32 caracteres | reemplazar el ejemplo |
| `STALE_OPPORTUNITY_DAYS` | Días sin cambio de etapa antes de crear una notificación interna | `14` |
| `BACKEND_PORT` | Puerto de FastAPI publicado en el host | `8000` |
| `FRONTEND_PORT` | Puerto de Vite publicado en el host | `5173` |
| `VITE_API_BASE_URL` | Base pública usada por el cliente HTTP del frontend | `/api` |

Generar un secreto de desarrollo con una herramienta segura, por ejemplo
`openssl rand -hex 32`. No versionar el valor resultante.

## Lead Intake Web

`POST /api/intake/web` es la única puerta de entrada actual para formularios Web.
Identifica o crea el cliente de forma conservadora y registra atómicamente una
oportunidad `NUEVA`, su historial inicial y el snapshot inmutable del envío. No usa el
JWT de usuarios del CRM: la integración debe ejecutarse entre servidores y firmar cada
body exacto con HMAC-SHA256.

Los headers requeridos son `X-FAA-Intake-Timestamp` (Unix timestamp en segundos) y
`X-FAA-Intake-Signature`. La entrada firmada es la concatenación exacta:

```text
{timestamp}\nPOST\n/api/intake/web\n{raw_body}
```

La firma se envía como `sha256={hex_digest}`. Por ejemplo, desde un backend Python:

```python
import hashlib
import hmac

signed = timestamp.encode() + b"\nPOST\n/api/intake/web\n" + raw_body
signature = "sha256=" + hmac.new(
    signing_secret.encode(), signed, hashlib.sha256
).hexdigest()
```

El timestamp se acepta durante cinco minutos. `external_submission_id` es obligatorio:
un replay con el mismo snapshot devuelve el resultado original, mientras que reutilizar
el ID con otros datos devuelve conflicto. `WEB_INTAKE_SIGNING_SECRET` debe existir solo
en el servidor que integra el formulario y en el backend del CRM; nunca debe incluirse
en JavaScript, WordPress público ni el repositorio. El rate limiting debe configurarse
en el reverse proxy o la plataforma de despliegue, no en memoria dentro de FastAPI.
La validación y operación productiva de WordPress/Contact Form 7 se detalla en el
[runbook de intake WordPress](docs/runbooks/wordpress-production-intake.md).

## Notificaciones internas

Una notificación `OPPORTUNITY_STALE` avisa que una oportunidad abierta (`NUEVA`,
`COTIZADA` o `NEGOCIACION`) lleva al menos `STALE_OPPORTUNITY_DAYS` sin cambiar de
etapa. Los avisos son globales para el equipo: la lectura es compartida, mientras que
`resolved_at` se registra automáticamente cuando la oportunidad avanza, se pierde, se
gana o se elimina lógicamente. El historial resuelto se conserva.

La generación es idempotente y se ejecuta manualmente con:

```bash
docker compose exec backend python -m app.scripts.generate_notifications
```

En producción este comando debe programarse periódicamente mediante cron o el
scheduler de la plataforma. El backend no depende de navegación del usuario y no
incorpora un scheduler residente, Celery ni Redis.

## Métricas comerciales

Los endpoints autenticados `/api/metrics/overview`, `/products`, `/sources`,
`/provinces`, `/timeline` y `/pipeline` calculan agregados directamente en PostgreSQL.
Los primeros cinco reciben `from` y `to` timezone-aware y usan un período semiabierto
`[from, to)`; `source`, `product_id` y `province` son filtros opcionales compartidos.

Las altas y el volumen cotizado se atribuyen a `opportunity.created_at`. Las ganancias,
pérdidas y sus kilogramos se atribuyen a la entrada al estado terminal mediante
`current_status_entered_at`. La conversión por oportunidades es
`ganadas / (ganadas + perdidas)` y la de volumen es
`kg ganados / (kg ganados + kg perdidos)`; ambas devuelven `null` cuando no existe
denominador. `/pipeline` es un snapshot actual sin período y `/timeline` devuelve todos
los buckets, incluidos los vacíos, según el calendario
`America/Argentina/Buenos_Aires`.

## Primer supervisor y autenticación

El CRM no ofrece registro público. Para crear el primer supervisor, ejecutar el
comando idempotente dentro del contenedor backend; la contraseña se solicita de forma
interactiva y no queda escrita en el comando:

```bash
docker compose exec backend python -m app.scripts.create_supervisor \
  --email supervisor@faa.com.ar \
  --full-name "Supervisor FAA"
```

Si ese email ya corresponde a un supervisor, el comando termina correctamente sin
crear otro usuario. Si pertenece a un vendedor, se detiene sin modificarlo.

Luego se puede iniciar sesión con `POST /api/auth/login`, copiar el `access_token` y
usarlo como Bearer token desde el botón **Authorize** de Swagger en `/docs`. Los tokens
expiran y cada request vuelve a comprobar que el usuario continúe activo.

El frontend guarda el access token en `sessionStorage`: la sesión sobrevive a una
recarga de la pestaña, pero no se conserva al cerrar esa sesión del navegador. Al
iniciar, valida el token mediante `GET /api/auth/me`; una respuesta `401` limpia la
sesión local. Esta decisión es deliberada para el MVP actual, cuya API entrega Bearer
tokens y todavía no implementa cookies HttpOnly ni refresh tokens.

## Pipeline frontend

El Kanban consulta por separado las cuatro etapas visibles (`NUEVA`, `COTIZADA`,
`NEGOCIACION` y `GANADA`) con páginas de hasta 100 oportunidades. Si una etapa supera
ese tamaño, el cliente continúa solicitando páginas hasta completar el `total`; de esta
forma no se truncan oportunidades ni se cargan las oportunidades `PERDIDA` que no
pertenecen al tablero principal.

Las tarjetas pueden avanzar mediante drag and drop o mediante su botón `Mover a`, que
ofrece la misma operación para teclado y tecnologías de asistencia. Las transiciones
simples usan actualización optimista con reversión ante error. La cotización espera la
selección de productos y la confirmación del backend antes de cambiar de columna.

## Migraciones

Alembic incluye una migración inicial (`0001_initial_schema`) que establece el historial de migraciones antes de incorporar las entidades del CRM. Se aplica automáticamente al arrancar el backend.

Comandos útiles:

```bash
# Ver la revisión aplicada
docker compose exec backend alembic current

# Aplicar migraciones pendientes
docker compose exec backend alembic upgrade head

# Crear una nueva migración cuando existan modelos SQLAlchemy
docker compose exec backend alembic revision --autogenerate -m "describe change"
```

## Estructura

```text
.
├── backend/          # FastAPI, SQLAlchemy y Alembic
├── frontend/         # React + TypeScript + Tailwind CSS (Vite)
├── docker-compose.yml
├── .env.example
├── AGENTS.md         # Reglas permanentes para el desarrollo
└── README.md
```

## Verificación

Docker Compose incluye health checks para PostgreSQL, backend y frontend. Consultar el estado con:

```bash
docker compose ps
curl http://localhost:8000/health
```

### Calidad del backend

Las declaraciones directas viven en `backend/requirements.in` y
`backend/requirements-dev.in`; Docker, CI y los entornos de calidad instalan los
artefactos exactos y verificados por hash `requirements.lock` y
`requirements-dev.lock`. El [runbook de dependencias](docs/runbooks/dependency-management.md)
documenta la actualización determinista, la reproducción byte a byte y el manejo
explícito de vulnerabilidades. El backend usa Ruff como linter y formatter, mypy strict
como type checker y pytest con coverage mínimo de 93%. La medición base al adoptar el
gate fue 93,56%.

```bash
# Lint
docker compose exec backend ruff check app tests performance quality

# Verificar formato (o aplicar con: ruff format app tests)
docker compose exec backend ruff format --check app tests performance quality

# Tipado estricto de aplicación y tests
docker compose exec backend mypy --strict app tests performance quality

# Tests y coverage
docker compose exec backend pytest \
  --cov=app --cov-report=term-missing --cov-fail-under=93

# Compilación y consistencia de migraciones
docker compose exec backend python -m compileall -q app tests performance quality
docker compose exec backend alembic check
docker compose exec backend alembic current --check-heads

# Reproducibilidad y auditoría del grafo Python bloqueado
docker compose exec backend ./scripts/verify-locks.sh
docker compose exec backend python -m quality.audit_dependencies \
  --output artifacts/pip-audit.json
```

La suite frontend exige `npm run check` (Biome), `npm run coverage`, `npm run build` y
`npm audit --audit-level=high`. Vitest conserva reportes de statements, branches,
functions y lines y aplica pisos de 85%, 75%, 86% y 88%, respectivamente. GitHub
Actions ejecuta todos los gates en cada push y pull request y conserva los reportes de
coverage y `pip-audit` durante siete días.

El smoke de CI puede reproducirse sin ejecutar nuevamente las suites:

```bash
./scripts/ci-compose-smoke.sh
```

Construye y levanta un proyecto Compose aislado, espera health checks, verifica API,
frontend, proxy y Alembic head, y siempre elimina sus contenedores y volúmenes.

### Pre-commit

Pre-commit ejecuta Ruff lint, Ruff format check, mypy strict y Biome con los mismos
comandos rápidos de CI. Las suites PostgreSQL, coverage, auditorías de red y Docker
permanecen en CI o como comandos explícitos para no volver lentos los commits.
Para instalarlo sin dependencias globales, usar un entorno virtual local:

```bash
python3.13 -m venv .venv
.venv/bin/pip install --require-hashes \
  -r backend/requirements.lock -r backend/requirements-dev.lock
.venv/bin/pre-commit install
.venv/bin/pre-commit run --all-files
```

### Trazabilidad SDD de tests

Los nuevos tests importantes de aceptación deben referenciar `CRM-NNN AC-NN` cuando
sea práctico, mediante docstring, comentario adyacente o grupo de tests. Un test puede
cubrir varios criterios y un criterio puede necesitar varios tests; no se exige una
correspondencia artificial ni se modifican tests históricos sólo para agregar IDs.
