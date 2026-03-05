#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

load_env

LLM_HEALTH_URL="${LLM_HEALTH_URL:-http://127.0.0.1:8000/v1/models}"
RAG_HEALTH_URL="${RAG_HEALTH_URL:-http://127.0.0.1:8001/health}"
APP_HEALTH_URL="${APP_HEALTH_URL:-http://127.0.0.1:5000/api/chat/health}"
LLM_HEALTH_AUTH_KEY="${LLM_HEALTH_AUTH_KEY:-${SILICONFLOW_API_KEY:-}}"

exit_code=0
external_count=0

llm_status_ok() {
  local code

  if [[ -n "${LLM_HEALTH_AUTH_KEY}" ]]; then
    code="$(http_code "${LLM_HEALTH_URL}" 3 "Authorization: Bearer ${LLM_HEALTH_AUTH_KEY}")"
    [[ "${code}" =~ ^2[0-9][0-9]$ ]]
    return $?
  fi

  code="$(http_code "${LLM_HEALTH_URL}" 3)"
  [[ "${code}" =~ ^2[0-9][0-9]$ || "${code}" == "401" ]]
}

check_one() {
  local name="$1"
  local url="$2"
  local pid="-"
  local ok=1
  local managed=0
  local status="DOWN"

  if service_pid_if_alive "${name}" >/dev/null; then
    pid="$(service_pid_if_alive "${name}")"
    managed=1
  fi

  if [[ "${name}" == "llm" ]]; then
    llm_status_ok && ok=0
  else
    http_ok "${url}" 3 && ok=0
  fi

  if [[ "${ok}" -eq 0 ]]; then
    status="HEALTHY"
    if [[ "${managed}" -eq 0 ]]; then
      status="HEALTHY_EXT"
      external_count=$((external_count + 1))
    fi
    printf '%-6s %-12s %-8s %s\n' "${name}" "${status}" "${pid}" "${url}"
  else
    printf '%-6s %-12s %-8s %s\n' "${name}" "${status}" "${pid}" "${url}"
    exit_code=1
  fi
}

printf '%-6s %-12s %-8s %s\n' "NAME" "STATUS" "PID" "HEALTH_URL"
printf '%-6s %-12s %-8s %s\n' "------" "------------" "--------" "----------"
check_one "llm" "${LLM_HEALTH_URL}"
check_one "rag" "${RAG_HEALTH_URL}"
check_one "app" "${APP_HEALTH_URL}"

if [[ "${external_count}" -gt 0 ]]; then
  log "WARN" "${external_count} service(s) are healthy but not tracked by current pid files (likely external/leftover process)."
fi

if [[ "${exit_code}" -eq 0 ]]; then
  log "OK" "Stack is healthy."
else
  log "ERR" "Stack is not fully healthy."
fi

exit "${exit_code}"