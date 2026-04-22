#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

require_repo_root
PYTHON_BIN="$(detect_python)"

log "Running pytest."
"${PYTHON_BIN}" -m pytest -q "$@"
