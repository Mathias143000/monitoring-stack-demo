#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

compose_only=0
if [[ "${1:-}" == "--compose-only" ]]; then
  compose_only=1
fi

copy_env_example
ensure_command docker
docker compose version >/dev/null

if [[ "${compose_only}" -eq 0 ]]; then
  PYTHON_BIN="$(detect_python)"
  "${PYTHON_BIN}" --version >/dev/null
fi

log "Bootstrap checks completed successfully."
