#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

require_repo_root

log "Resetting the monitoring lab."
bash "${SCRIPT_DIR}/stack-down.sh" --volumes
bash "${SCRIPT_DIR}/stack-up.sh"
bash "${SCRIPT_DIR}/smoke.sh"

log "Reset flow completed."
