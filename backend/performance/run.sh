#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
profile="${2:-baseline}"
output_directory="${3:-performance-artifacts}"

if [[ -z "${PERFORMANCE_DATABASE_URL:-}" ]]; then
  echo "PERFORMANCE_DATABASE_URL is required (postgresql://...)" >&2
  exit 2
fi

case "${profile}" in
  baseline)
    conversation_count=1000
    message_count=10000
    ;;
  large)
    conversation_count=10000
    message_count=100000
    ;;
  *)
    echo "Profile must be baseline or large" >&2
    exit 2
    ;;
esac

database_url="${PERFORMANCE_DATABASE_URL/postgresql:/postgresql+psycopg:}"
template_signature="1b06fe566d00ed0a4c6dc2f547350326d10613cb9b0f754625c451da95c7ee35"
script_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

seed() {
  psql "${PERFORMANCE_DATABASE_URL}" \
    --set=conversation_count="${conversation_count}" \
    --set=message_count="${message_count}" \
    --set=broadcast_recipient_count=120 \
    --set=broadcast_count=25 \
    --set=template_signature="${template_signature}" \
    --file="${script_directory}/seed.sql"
}

benchmark() {
  DATABASE_URL="${database_url}" python -m performance.benchmark \
    --profile "${profile}" \
    --output "${output_directory}/benchmark-${profile}.json"
}

plans() {
  DATABASE_URL="${database_url}" python -m performance.explain \
    --output-dir "${output_directory}/plans-${profile}"
}

mkdir -p "${output_directory}"
case "${action}" in
  seed) seed ;;
  benchmark) benchmark ;;
  explain) plans ;;
  all)
    seed
    benchmark
    plans
    ;;
  *)
    echo "Usage: $0 {seed|benchmark|explain|all} {baseline|large} [output-dir]" >&2
    exit 2
    ;;
esac
