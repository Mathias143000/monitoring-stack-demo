#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log() {
  printf '[%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

ensure_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    fail "Required command not found: ${command_name}"
  fi
}

detect_python() {
  local candidates=(
    "${REPO_ROOT}/.venv/Scripts/python.exe"
    "${REPO_ROOT}/venv/Scripts/python.exe"
    "${REPO_ROOT}/.venv/bin/python"
    "${REPO_ROOT}/venv/bin/python"
  )
  local candidate

  for candidate in "${candidates[@]}"; do
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return
    fi
  done

  if command -v python >/dev/null 2>&1; then
    printf 'python\n'
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    printf 'python3\n'
    return
  fi

  fail "Python interpreter not found. Install python or python3."
}

copy_env_example() {
  if [[ ! -f "${REPO_ROOT}/.env" ]]; then
    cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
    log "Created .env from .env.example"
  fi
}

load_env_file() {
  local env_file="${1:-${REPO_ROOT}/.env}"
  if [[ -f "${env_file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${env_file}"
    set +a
  fi
}

docker_compose() {
  docker compose "$@"
}

wait_for_http() {
  local url="$1"
  local expected_status="${2:-200}"
  local attempts="${3:-30}"
  local delay_seconds="${4:-2}"
  local headers=("${@:5}")
  local attempt
  local status

  for ((attempt = 1; attempt <= attempts; attempt += 1)); do
    status="$(
      curl -sS -o /dev/null -w '%{http_code}' "${headers[@]}" "${url}" || true
    )"
    if [[ "${status}" == "${expected_status}" ]]; then
      return 0
    fi
    sleep "${delay_seconds}"
  done

  fail "Timed out waiting for ${url} to return HTTP ${expected_status}"
}

require_repo_root() {
  cd "${REPO_ROOT}"
}
