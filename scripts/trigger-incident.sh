#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

require_repo_root
load_env_file
ensure_command curl

APP_URL="${APP_URL:-http://localhost:18080}"
INCIDENT_TYPE="${1:-errors}"

case "${INCIDENT_TYPE}" in
  errors)
    hits="${ERROR_HITS:-8}"
    log "Triggering synthetic error burst via ${APP_URL}/demo/error."
    for ((attempt = 1; attempt <= hits; attempt += 1)); do
      status="$(curl -sS -o /dev/null -w '%{http_code}' "${APP_URL}/demo/error" || true)"
      if [[ "${status}" != "503" ]]; then
        fail "Expected /demo/error to return 503, got ${status}"
      fi
    done
    ;;
  latency)
    hits="${LATENCY_HITS:-6}"
    delay_ms="${LATENCY_DELAY_MS:-1500}"
    log "Triggering high-latency requests via ${APP_URL}/demo/slow."
    for ((attempt = 1; attempt <= hits; attempt += 1)); do
      curl -fsS "${APP_URL}/demo/slow?delay_ms=${delay_ms}" >/dev/null
    done
    ;;
  edge-down)
    log "Stopping nginx to simulate edge outage."
    docker_compose stop nginx
    ;;
  edge-up)
    log "Starting nginx after outage simulation."
    docker_compose start nginx
    ;;
  *)
    fail "Unknown incident type: ${INCIDENT_TYPE}. Use one of: errors, latency, edge-down, edge-up."
    ;;
esac

log "Incident action completed."
