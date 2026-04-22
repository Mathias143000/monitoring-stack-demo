#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

require_repo_root

remove_volumes=0
pass_args=()
for arg in "$@"; do
  case "${arg}" in
    --volumes)
      remove_volumes=1
      ;;
    *)
      pass_args+=("${arg}")
      ;;
  esac
done

cmd=(down --remove-orphans)
if [[ "${remove_volumes}" -eq 1 ]]; then
  cmd+=(--volumes)
fi

log "Stopping the monitoring lab."
docker_compose "${cmd[@]}" "${pass_args[@]}"
