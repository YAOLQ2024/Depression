#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

load_env

RAG_HEALTH_URL="${RAG_HEALTH_URL:-http://127.0.0.1:8001/health}"
RAG_START_TIMEOUT="${RAG_START_TIMEOUT:-120}"
EMOLLM_ROOT="${EMOLLM_ROOT:-${ROOT_DIR}/../EmoLLM}"

if http_ok "${RAG_HEALTH_URL}" 3; then
  log "OK" "RAG already healthy: ${RAG_HEALTH_URL}"
  exit 0
fi

if [[ ! -f "${EMOLLM_ROOT}/rag_official_api.py" ]]; then
  log "ERR" "rag_official_api.py not found under ${EMOLLM_ROOT}"
  log "ERR" "Set EMOLLM_ROOT in .env, e.g. EMOLLM_ROOT=/home/ZR/data2/Depression/EmoLLM"
  exit 1
fi

if [[ -z "${RAG_START_CMD:-}" ]]; then
  if command -v uvicorn >/dev/null 2>&1; then
    RAG_START_CMD="uvicorn rag_official_api:app --host 127.0.0.1 --port 8001"
  else
    RAG_START_CMD="python3 -m uvicorn rag_official_api:app --host 127.0.0.1 --port 8001"
  fi
fi

# 明确开启访问日志，避免“有请求但日志文件看不到”的误判。
if [[ "${RAG_START_CMD}" == *"uvicorn"* ]]; then
  [[ "${RAG_START_CMD}" == *"--log-level"* ]] || RAG_START_CMD="${RAG_START_CMD} --log-level info"
  if [[ "${RAG_START_CMD}" != *"--access-log"* && "${RAG_START_CMD}" != *"--no-access-log"* ]]; then
    RAG_START_CMD="${RAG_START_CMD} --access-log"
  fi
fi

start_bg "rag" "${RAG_START_CMD}" "${EMOLLM_ROOT}"
wait_for_http "${RAG_HEALTH_URL}" "${RAG_START_TIMEOUT}" "RAG" "rag"