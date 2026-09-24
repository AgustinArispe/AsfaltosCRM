#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
if [ ! -f .env.demo ]; then
  umask 077
  {
    printf 'DEMO_POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 24)"
    printf 'DEMO_JWT_SECRET=%s\n' "$(openssl rand -hex 32)"
    printf 'DEMO_WEB_INTAKE_SECRET=%s\n' "$(openssl rand -hex 32)"
  } > .env.demo
fi

# Ignore inherited production variables; only the generated local demo file is read.
docker_endpoint="$(env -i PATH="$PATH" HOME="$HOME" docker context inspect --format '{{.Endpoints.docker.Host}}')"
case "$docker_endpoint" in
  unix://*) ;;
  *)
    echo "PULSE demo requires a local Docker context; found: $docker_endpoint" >&2
    exit 1
    ;;
esac

exec env -i PATH="$PATH" HOME="$HOME" docker compose --env-file .env.demo -f compose.demo.yml "$@"
