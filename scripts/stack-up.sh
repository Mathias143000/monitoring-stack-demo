#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

require_repo_root
bash "${SCRIPT_DIR}/bootstrap.sh" --compose-only

COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT:-1}"

log "Building and starting the monitoring lab."
COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT}" docker_compose up --build -d "$@"
docker_compose ps
