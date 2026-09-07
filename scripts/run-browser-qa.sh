#!/usr/bin/env bash

set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -p asfaltoscrm --env-file "$REPOSITORY_ROOT/.env.example")
QA_ANCHOR="2026-08-18T15:00:00+00:00"
BROWSER_IMAGE="asfaltoscrm-browser-quality"

reset_visual_qa() {
  "${COMPOSE[@]}" exec -T \
    -e QA_SUPERVISOR_PASSWORD='FAA-Visual-QA-2026!' \
    -e QA_SELLER_PASSWORD='FAA-Vendedor-QA-2026!' \
    backend python -m app.scripts.seed_visual_qa \
    --reset --anchor "$QA_ANCHOR"
}

cd "$REPOSITORY_ROOT"

for service in db backend frontend; do
  if ! "${COMPOSE[@]}" ps --status running --services | grep -Fxq "$service"; then
    echo "Canonical service '$service' is not running. Start it with:" >&2
    echo "docker compose -p asfaltoscrm --env-file .env.example up -d --build --wait" >&2
    exit 1
  fi
done

"${COMPOSE[@]}" exec -T db pg_isready -U asfaltos -d asfaltos_crm
curl --fail --silent --show-error http://localhost:8000/health \
  | grep -q '"database":"ok"'
curl --fail --silent --show-error --head http://localhost:5173 >/dev/null
"${COMPOSE[@]}" exec -T backend alembic current --check-heads

reset_visual_qa
"${COMPOSE[@]}" exec -T backend python -m app.scripts.seed_visual_qa --summary

docker build --target browser-quality -t "$BROWSER_IMAGE" backend

set +e
docker run --rm --network host \
  -v "$REPOSITORY_ROOT/backend:/app" \
  -v "$REPOSITORY_ROOT/frontend:/frontend:ro" \
  -w /app \
  "$BROWSER_IMAGE" \
  pytest -c quality/browser/pytest.ini quality/browser
browser_status=$?
set -e

if ! reset_visual_qa; then
  echo "Browser QA cleanup failed; the canonical fixture was not restored." >&2
  exit 1
fi

exit "$browser_status"
