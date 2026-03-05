#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

load_env

APP_HEALTH_URL="${APP_HEALTH_URL:-http://127.0.0.1:5000/api/chat/health}"
APP_START_TIMEOUT="${APP_START_TIMEOUT:-90}"

"${SCRIPT_DIR}/start_llm_gpu.sh"
"${SCRIPT_DIR}/start_rag.sh"

if http_ok "${APP_HEALTH_URL}" 3; then
  log "OK" "App already healthy: ${APP_HEALTH_URL}"
  exit 0
fi

if [[ -z "${APP_START_CMD:-}" ]]; then
  APP_START_CMD="python3 start_app_gpu.py"
fi

start_bg "app" "${APP_START_CMD}" "${ROOT_DIR}"
wait_for_http "${APP_HEALTH_URL}" "${APP_START_TIMEOUT}" "APP" "app"

log "OK" "All services are up."
log "INFO" "Check with: ${SCRIPT_DIR}/check_stack.sh"
log "INFO" "Log mode: ${STACK_LOG_MODE:-rotate} (set STACK_LOG_MODE=append|truncate|rotate in .env)"
log "INFO" "Watch logs: tail -n 120 -f ${STACK_LOG_DIR}/llm.log ${STACK_LOG_DIR}/rag.log ${STACK_LOG_DIR}/app.log"