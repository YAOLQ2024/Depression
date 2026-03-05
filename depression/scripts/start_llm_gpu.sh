#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

load_env

LLM_HEALTH_URL="${LLM_HEALTH_URL:-http://127.0.0.1:8000/v1/models}"
LLM_START_TIMEOUT="${LLM_START_TIMEOUT:-180}"
LLM_MODEL_PATH="${LLM_MODEL_PATH:-${ROOT_DIR}/../EmoLLM/model/EmoLLM_Qwen2-7B-Instruct_lora}"
LLM_SERVED_MODEL="${LLM_SERVED_MODEL:-${SILICONFLOW_MODEL:-emollm-qwen2-7b}}"
LLM_HEALTH_AUTH_KEY="${LLM_HEALTH_AUTH_KEY:-${SILICONFLOW_API_KEY:-}}"

llm_health_code() {
  if [[ -n "${LLM_HEALTH_AUTH_KEY}" ]]; then
    http_code "${LLM_HEALTH_URL}" 3 "Authorization: Bearer ${LLM_HEALTH_AUTH_KEY}"
  else
    http_code "${LLM_HEALTH_URL}" 3
  fi
}

llm_health_ok() {
  local code
  code="$(llm_health_code)"

  if [[ -n "${LLM_HEALTH_AUTH_KEY}" ]]; then
    [[ "${code}" =~ ^2[0-9][0-9]$ ]]
  else
    [[ "${code}" =~ ^2[0-9][0-9]$ || "${code}" == "401" ]]
  fi
}

wait_for_llm() {
  local start_ts now_ts code
  start_ts="$(date +%s)"

  while true; do
    code="$(llm_health_code)"

    if [[ -n "${LLM_HEALTH_AUTH_KEY}" ]]; then
      if [[ "${code}" =~ ^2[0-9][0-9]$ ]]; then
        log "OK" "LLM is healthy: ${LLM_HEALTH_URL}"
        return 0
      fi
    else
      if [[ "${code}" =~ ^2[0-9][0-9]$ || "${code}" == "401" ]]; then
        if [[ "${code}" == "401" ]]; then
          log "OK" "LLM is up (auth required): ${LLM_HEALTH_URL}"
        else
          log "OK" "LLM is healthy: ${LLM_HEALTH_URL}"
        fi
        return 0
      fi
    fi

    if ! service_pid_if_alive "llm" >/dev/null; then
      log "ERR" "LLM process exited before health check passed."
      log "ERR" "Check log: $(log_file "llm")"
      return 1
    fi

    now_ts="$(date +%s)"
    if (( now_ts - start_ts >= LLM_START_TIMEOUT )); then
      log "ERR" "Timed out waiting for LLM: ${LLM_HEALTH_URL} (last code: ${code})"
      if [[ -n "${LLM_HEALTH_AUTH_KEY}" ]]; then
        log "ERR" "LLM_HEALTH_AUTH_KEY was provided but endpoint did not return 2xx."
        log "ERR" "Check API key correctness in .env (and strip CRLF)."
      fi
      log "ERR" "Check log: $(log_file "llm")"
      return 1
    fi

    sleep 2
  done
}

if [[ -z "${LLM_HEALTH_AUTH_KEY}" ]]; then
  log "WARN" "LLM_HEALTH_AUTH_KEY/SILICONFLOW_API_KEY is empty; health check may rely on 401 response."
fi

if llm_health_ok; then
  log "OK" "LLM already reachable: ${LLM_HEALTH_URL}"
  exit 0
fi

if [[ -z "${LLM_START_CMD:-}" ]]; then
  if command -v vllm >/dev/null 2>&1; then
    LLM_START_CMD="vllm serve \"${LLM_MODEL_PATH}\" --host 127.0.0.1 --port 8000 --served-model-name \"${LLM_SERVED_MODEL}\" --dtype auto --max-model-len 4096 --gpu-memory-utilization 0.90"
  elif command -v python3 >/dev/null 2>&1; then
    LLM_START_CMD="python3 -m vllm.entrypoints.openai.api_server --host 127.0.0.1 --port 8000 --model \"${LLM_MODEL_PATH}\" --served-model-name \"${LLM_SERVED_MODEL}\" --dtype auto --max-model-len 4096 --gpu-memory-utilization 0.90"
  else
    log "ERR" "No python3/vllm found. Please set LLM_START_CMD in .env"
    exit 1
  fi
fi

start_bg "llm" "${LLM_START_CMD}" "${ROOT_DIR}"
wait_for_llm