#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

require_repo_root
load_env_file
ensure_command curl

output_dir="${1:-artifacts/evidence}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:19090}"
ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:19093}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:13000}"
LOKI_URL="${LOKI_URL:-http://localhost:13100}"
TEMPO_URL="${TEMPO_URL:-http://localhost:13201}"

mkdir -p "${output_dir}"

loki_start="$(date -u -d '15 minutes ago' +%s)000000000"
loki_end="$(date -u +%s)000000000"

docker_compose ps >"${output_dir}/compose-ps.txt"
docker_compose logs --timestamps >"${output_dir}/compose-logs.txt"
curl -fsS "${PROMETHEUS_URL}/api/v1/alerts" >"${output_dir}/prometheus-alerts.json"
curl -fsS "${ALERTMANAGER_URL}/api/v2/alerts" >"${output_dir}/alertmanager-alerts.json"
curl -fsS "${GRAFANA_URL}/api/health" >"${output_dir}/grafana-health.json"
curl -fsS --get \
  --data-urlencode 'query={compose_service="app"}' \
  --data-urlencode "start=${loki_start}" \
  --data-urlencode "end=${loki_end}" \
  --data-urlencode 'limit=100' \
  "${LOKI_URL}/loki/api/v1/query_range" >"${output_dir}/loki-app-logs.json"
curl -fsS --get --data-urlencode 'limit=10' "${TEMPO_URL}/api/search" >"${output_dir}/tempo-traces.json"

log "Evidence bundle written to ${output_dir}."
