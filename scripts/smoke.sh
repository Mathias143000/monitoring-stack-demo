#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

require_repo_root
load_env_file
ensure_command curl
PYTHON_BIN="$(detect_python)"

PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:19090}"
APP_URL="${APP_URL:-http://localhost:18080}"
ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:19093}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:13000}"
GRAFANA_USER="${GRAFANA_ADMIN_USER:-admin}"
GRAFANA_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-admin12345}"
INFLUX_URL_PUBLIC="${INFLUX_URL_PUBLIC:-http://localhost:18086}"
LOKI_URL="${LOKI_URL:-http://localhost:13100}"
TEMPO_URL="${TEMPO_URL:-http://localhost:13201}"
TRACE_SERVICE_NAME="${TRACE_SERVICE_NAME:-monitoring-stack-demo-app}"

assert_contains() {
  local body="$1"
  local expected="$2"
  if [[ "${body}" != *"${expected}"* ]]; then
    fail "Response body does not contain expected fragment: ${expected}"
  fi
}

assert_json_field_equals() {
  local payload="$1"
  local field_name="$2"
  local expected_value="$3"

  JSON_PAYLOAD="${payload}" JSON_FIELD="${field_name}" JSON_EXPECTED="${expected_value}" "${PYTHON_BIN}" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["JSON_PAYLOAD"])
field_name = os.environ["JSON_FIELD"]
expected_value = os.environ["JSON_EXPECTED"]
actual_value = payload.get(field_name)

if str(actual_value) == expected_value:
    sys.exit(0)
sys.exit(f"Field {field_name!r} expected {expected_value!r}, got {actual_value!r}")
PY
}

assert_up_metric() {
  local payload="$1"
  local job_name="$2"

  PROM_PAYLOAD="${payload}" PROM_JOB="${job_name}" "${PYTHON_BIN}" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["PROM_PAYLOAD"])
job_name = os.environ["PROM_JOB"]

for item in payload.get("data", {}).get("result", []):
    if item.get("metric", {}).get("job") == job_name and item.get("value", ["", "0"])[1] == "1":
        sys.exit(0)

sys.exit(f"Prometheus did not report up==1 for job={job_name}")
PY
}

wait_for_http "${APP_URL}/health" 200 40 3
wait_for_http "${PROMETHEUS_URL}/-/ready" 200 40 3
wait_for_http "${ALERTMANAGER_URL}/-/ready" 200 40 3
wait_for_http "${GRAFANA_URL}/api/health" 200 40 3
wait_for_http "${INFLUX_URL_PUBLIC}/health" 200 40 3
wait_for_http "${LOKI_URL}/ready" 200 40 3
wait_for_http "${TEMPO_URL}/ready" 200 40 3

health_payload="$(curl -fsS "${APP_URL}/health")"
assert_json_field_equals "${health_payload}" "status" "ok"
assert_json_field_equals "${health_payload}" "database" "ok"

metrics_payload="$(curl -fsS "${APP_URL}/metrics")"
assert_contains "${metrics_payload}" 'app_http_requests_total'
assert_contains "${metrics_payload}" 'app_db_up'

bash "${SCRIPT_DIR}/seed-demo.sh"
curl -fsS "${APP_URL}/demo/slow?delay_ms=950" >/dev/null
sleep 8

loki_start="$(date -u -d '10 minutes ago' +%s)000000000"
loki_end="$(date -u +%s)000000000"

targets_payload="$(
  curl -fsS --get \
    --data-urlencode 'query=up{job=~"app|prometheus|alertmanager|cadvisor|node-exporter|blackbox-app|blackbox-edge|blackbox-grafana|blackbox-prometheus"}' \
    "${PROMETHEUS_URL}/api/v1/query"
)"
assert_up_metric "${targets_payload}" "app"
assert_up_metric "${targets_payload}" "prometheus"
assert_up_metric "${targets_payload}" "alertmanager"
assert_up_metric "${targets_payload}" "cadvisor"
assert_up_metric "${targets_payload}" "node-exporter"
assert_up_metric "${targets_payload}" "blackbox-app"
assert_up_metric "${targets_payload}" "blackbox-edge"
assert_up_metric "${targets_payload}" "blackbox-grafana"
assert_up_metric "${targets_payload}" "blackbox-prometheus"

probe_payload="$(
  curl -fsS --get \
    --data-urlencode 'query=min(probe_success{job=~"blackbox-.*"})' \
    "${PROMETHEUS_URL}/api/v1/query"
)"
PROM_PAYLOAD="${probe_payload}" "${PYTHON_BIN}" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["PROM_PAYLOAD"])
result = payload.get("data", {}).get("result", [])
if result and result[0].get("value", ["", "0"])[1] == "1":
    sys.exit(0)
sys.exit("Synthetic probes are not all successful.")
PY

loki_payload="$(
  curl -fsS --get \
    --data-urlencode 'query={compose_service="app"} |= "request_id="' \
    --data-urlencode "start=${loki_start}" \
    --data-urlencode "end=${loki_end}" \
    --data-urlencode 'limit=20' \
    "${LOKI_URL}/loki/api/v1/query_range"
)"
PROM_PAYLOAD="${loki_payload}" "${PYTHON_BIN}" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["PROM_PAYLOAD"])
if payload.get("data", {}).get("result"):
    sys.exit(0)
sys.exit("Loki query returned no application logs.")
PY

tempo_payload="$(
  curl -fsS --get \
    --data-urlencode 'q={}' \
    --data-urlencode 'limit=5' \
    "${TEMPO_URL}/api/search"
)"
PROM_PAYLOAD="${tempo_payload}" "${PYTHON_BIN}" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["PROM_PAYLOAD"])
traces = payload.get("traces") or payload.get("data") or []
if traces:
    sys.exit(0)
sys.exit("Tempo query returned no traces.")
PY

grafana_payload="$(curl -fsS "${GRAFANA_URL}/api/health")"
assert_json_field_equals "${grafana_payload}" "database" "ok"
assert_contains "${grafana_payload}" '"version"'

grafana_datasources="$(
  curl -fsS -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" "${GRAFANA_URL}/api/datasources"
)"
assert_contains "${grafana_datasources}" '"name":"Prometheus"'
assert_contains "${grafana_datasources}" '"name":"Loki"'
assert_contains "${grafana_datasources}" '"name":"Tempo"'

log "Smoke checks completed successfully."
