#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly COMPOSE_PROJECT_NAME="crm015-smoke-${GITHUB_RUN_ID:-local}-$$"
readonly PROXY_RESPONSE="$(mktemp)"

export COMPOSE_PROJECT_NAME
export POSTGRES_DB="asfaltos_crm"
export POSTGRES_USER="asfaltos"
export POSTGRES_PASSWORD="ci_smoke_password"
export POSTGRES_PORT="35432"
export JWT_SECRET="ci-smoke-jwt-secret-with-at-least-thirty-two-characters"
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES="60"
export ALLOWED_HOSTS="localhost,127.0.0.1,backend,testserver"
export WEB_INTAKE_SIGNING_SECRET="ci-smoke-intake-secret-with-thirty-two-characters"
export STALE_OPPORTUNITY_DAYS="14"
export WHATSAPP_PROVIDER="fake"
export WHATSAPP_MEDIA_STORAGE="fake"
export BACKEND_PORT="38000"
export FRONTEND_PORT="35173"
export VITE_API_BASE_URL="/api"

cd "${REPOSITORY_DIR}"

cleanup() {
  status=$?
  if [[ ${status} -ne 0 ]]; then
    docker compose ps || true
    docker compose logs --no-color --tail 200 || true
  fi
  docker compose down -v --remove-orphans
  rm -f "${PROXY_RESPONSE}"
  exit "${status}"
}
trap cleanup EXIT

if [[ -n "$(docker compose ps --all --quiet)" ]]; then
  echo "Refusing to reuse existing Compose project ${COMPOSE_PROJECT_NAME}." >&2
  exit 1
fi

docker compose build
docker compose up --detach --wait --wait-timeout 180

backend_health="$(curl --fail --silent --show-error "http://localhost:${BACKEND_PORT}/health")"
if [[ "${backend_health}" != '{"status":"ok","database":"ok"}' ]]; then
  echo "Unexpected backend health response: ${backend_health}" >&2
  exit 1
fi

curl --fail --silent --show-error --output /dev/null \
  "http://localhost:${FRONTEND_PORT}/"

proxy_status="$(curl --silent --show-error --output "${PROXY_RESPONSE}" \
  --write-out '%{http_code}' "http://localhost:${FRONTEND_PORT}/api/auth/me")"
if [[ "${proxy_status}" != "401" ]]; then
  echo "Expected frontend proxy authentication response 401, got ${proxy_status}." >&2
  exit 1
fi
if ! grep --quiet '"detail"' "${PROXY_RESPONSE}"; then
  echo "Frontend proxy did not return the backend authentication payload." >&2
  exit 1
fi

docker compose exec --no-TTY backend alembic current --check-heads
echo "Docker Compose smoke checks passed."
