#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

require_repo_root
PYTHON_BIN="$(detect_python)"
copy_env_example

log "Running Ruff lint checks."
"${PYTHON_BIN}" -m ruff check .

log "Running Bash syntax validation."
shopt -s nullglob
for script in scripts/*.sh; do
  bash -n "${script}"
done
shopt -u nullglob

if command -v shellcheck >/dev/null 2>&1; then
  log "Running shellcheck."
  shellcheck scripts/*.sh
else
  log "shellcheck is not installed; skipping static shell lint."
fi

if command -v docker >/dev/null 2>&1; then
  log "Validating docker compose configuration."
  docker compose config >/dev/null

  log "Validating Prometheus alert rules with promtool."
  workspace_path="${REPO_ROOT}"
  if command -v cygpath >/dev/null 2>&1; then
    workspace_path="$(cygpath -m "${REPO_ROOT}")"
  fi

  MSYS_NO_PATHCONV=1 docker run --rm \
    --entrypoint promtool \
    -v "${workspace_path}:/workspace" \
    --workdir /workspace \
    prom/prometheus:v3.4.2 \
    check rules alerts.yml
fi

log "Lint validation completed successfully."
