#!/usr/bin/env bash
set -euo pipefail

readonly BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly VERIFY_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${VERIFY_DIR}"
}
trap cleanup EXIT

cp "${BACKEND_DIR}/requirements.in" "${VERIFY_DIR}/requirements.in"
cp "${BACKEND_DIR}/requirements-dev.in" "${VERIFY_DIR}/requirements-dev.in"
cp "${BACKEND_DIR}/requirements.lock" "${VERIFY_DIR}/requirements.lock"
cp "${BACKEND_DIR}/requirements-dev.lock" "${VERIFY_DIR}/requirements-dev.lock"
cp "${BACKEND_DIR}/pyproject.toml" "${VERIFY_DIR}/pyproject.toml"
mkdir "${VERIFY_DIR}/scripts"
cp "${BACKEND_DIR}/scripts/compile-locks.sh" "${VERIFY_DIR}/scripts/compile-locks.sh"

(cd "${VERIFY_DIR}" && ./scripts/compile-locks.sh)

cmp "${BACKEND_DIR}/requirements.lock" "${VERIFY_DIR}/requirements.lock"
cmp "${BACKEND_DIR}/requirements-dev.lock" "${VERIFY_DIR}/requirements-dev.lock"
echo "Python lock files are reproducible."
