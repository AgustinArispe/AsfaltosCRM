#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
branch="$(git branch --show-current)"
if [ "$branch" != "demo/pulse-video" ]; then
  echo "Refused: required branch demo/pulse-video (found $branch)" >&2
  exit 1
fi
demo_password="${PULSE_DEMO_PASSWORD:-PulseVideoLocal2026!}"
exec ./scripts/pulse-demo.sh exec -T \
  -e PULSE_DEMO_GIT_BRANCH="$branch" \
  -e PULSE_DEMO_PASSWORD="$demo_password" \
  backend python -m app.scripts.seed_pulse_video_demo "$@"
