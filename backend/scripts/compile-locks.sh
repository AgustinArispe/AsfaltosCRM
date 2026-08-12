#!/usr/bin/env bash
set -euo pipefail

readonly EXPECTED_PYTHON="3.13.15"
readonly EXPECTED_PIP_TOOLS="7.6.1"

cd "$(dirname "${BASH_SOURCE[0]}")/.."

actual_python="$(python -c 'import platform; print(platform.python_version())')"
actual_pip_tools="$(python -c 'from importlib.metadata import version; print(version("pip-tools"))')"

if [[ "${actual_python}" != "${EXPECTED_PYTHON}" ]]; then
  echo "Expected Python ${EXPECTED_PYTHON}, found ${actual_python}." >&2
  exit 1
fi

if [[ "${actual_pip_tools}" != "${EXPECTED_PIP_TOOLS}" ]]; then
  echo "Expected pip-tools ${EXPECTED_PIP_TOOLS}, found ${actual_pip_tools}." >&2
  exit 1
fi

export CUSTOM_COMPILE_COMMAND="./scripts/compile-locks.sh"

python -m piptools compile --quiet --rebuild "$@" \
  --output-file requirements.lock requirements.in
python -m piptools compile --quiet --rebuild "$@" \
  --output-file requirements-dev.lock requirements-dev.in
