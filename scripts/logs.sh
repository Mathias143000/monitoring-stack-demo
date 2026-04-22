#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

require_repo_root

if [[ $# -gt 0 ]]; then
  output_file="$1"
  mkdir -p "$(dirname "${output_file}")"
  docker_compose logs --timestamps >"${output_file}"
  log "Docker Compose logs written to ${output_file}"
  exit 0
fi

docker_compose logs --timestamps
