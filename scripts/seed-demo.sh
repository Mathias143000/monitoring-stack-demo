#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

require_repo_root
load_env_file
ensure_command curl

BASE_URL="${BASE_URL:-http://localhost:18080}"
ERROR_HITS="${ERROR_HITS:-3}"

log "Seeding demo entities via ${BASE_URL}."
curl -fsS -X POST "${BASE_URL}/demo/seed" >/dev/null
curl -fsS -X POST "${BASE_URL}/users" -H 'Content-Type: application/json' -d '{"name":"devops-bot"}' >/dev/null
curl -fsS -X POST "${BASE_URL}/tickets" -H 'Content-Type: application/json' -d '{"title":"Container metrics review","age_hours":2}' >/dev/null
curl -fsS -X POST "${BASE_URL}/tickets" -H 'Content-Type: application/json' -d '{"title":"Synthetic overdue incident","age_hours":30}' >/dev/null

for ((attempt = 1; attempt <= ERROR_HITS; attempt += 1)); do
  status="$(curl -sS -o /dev/null -w '%{http_code}' "${BASE_URL}/demo/error" || true)"
  if [[ "${status}" != "503" ]]; then
    fail "Expected /demo/error to return 503, got ${status}"
  fi
done

log "Demo seed flow completed."
