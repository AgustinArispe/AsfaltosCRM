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
| `BACKEND_PORT` | Puerto de FastAPI publicado en el host | `8000` |
| `FRONTEND_PORT` | Puerto de Vite publicado en el host | `5173` |
| `VITE_API_BASE_URL` | Base pública usada por el cliente HTTP del frontend | `/api` |

Generar un secreto de desarrollo con una herramienta segura, por ejemplo
`openssl rand -hex 32`. No versionar el valor resultante.

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
