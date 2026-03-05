#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
STACK_LOG_DIR="${ROOT_DIR}/logs/stack"

mkdir -p "${STACK_LOG_DIR}"

log() {
  local level="$1"
  shift
  printf '[%s] %s\n' "${level}" "$*"
}

sanitize_var() {
  local var_name="$1"
  local value="${!var_name-}"
  [[ -z "${value}" ]] && return 0
  value="${value//$'\r'/}"
  printf -v "${var_name}" '%s' "${value}"
  export "${var_name}"
}

normalize_conda_prefix_for_var() {
  local var_name="$1"
  local cmd="${!var_name:-}"
  [[ -z "${cmd}" ]] && return 0

  local first_token="${cmd%% *}"
  if [[ "${first_token}" == */conda ]] && [[ ! -x "${first_token}" ]]; then
    if command -v conda >/dev/null 2>&1; then
      local detected
      detected="$(command -v conda)"
      cmd="${detected}${cmd#${first_token}}"
      printf -v "${var_name}" '%s' "${cmd}"
      export "${var_name}"
      log "WARN" "${var_name} had invalid conda path: ${first_token}"
      log "WARN" "${var_name} rewritten to use: ${detected}"
    fi
  fi
}

ensure_conda_run_no_capture_for_var() {
  local var_name="$1"
  local cmd="${!var_name:-}"
  [[ -z "${cmd}" ]] && return 0

  if [[ "${cmd}" == *"conda run "* ]] && [[ "${cmd}" != *"--no-capture-output"* ]]; then
    cmd="${cmd/conda run /conda run --no-capture-output }"
    printf -v "${var_name}" '%s' "${cmd}"
    export "${var_name}"
    log "INFO" "${var_name} auto-added conda flag: --no-capture-output"
  fi
}

load_env() {
  local env_file="${ROOT_DIR}/.env"
  if [[ -f "${env_file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${env_file}"
    set +a
  fi

  local vars_to_sanitize=(
    CONDA_CMD
    SILICONFLOW_API_KEY
    SILICONFLOW_API_URL
    SILICONFLOW_MODEL
    EMOLLM_ROOT
    LLM_START_CMD
    RAG_START_CMD
    APP_START_CMD
    LLM_HEALTH_URL
    RAG_HEALTH_URL
    APP_HEALTH_URL
    LLM_HEALTH_AUTH_KEY
    STACK_LOG_MODE
    LLM_PORT
    RAG_PORT
    APP_PORT
  )
  local v
  for v in "${vars_to_sanitize[@]}"; do
    sanitize_var "${v}"
  done

  # If CONDA_CMD is configured but invalid, fallback to current shell conda.
  if [[ -n "${CONDA_CMD:-}" ]] && [[ ! -x "${CONDA_CMD}" ]]; then
    if command -v conda >/dev/null 2>&1; then
      local detected
      detected="$(command -v conda)"
      log "WARN" "CONDA_CMD not executable: ${CONDA_CMD}"
      log "WARN" "Fallback to detected conda: ${detected}"
      export CONDA_CMD="${detected}"
    fi
  fi

  # If .env already expanded START_CMD with a bad conda prefix, rewrite it.
  normalize_conda_prefix_for_var "LLM_START_CMD"
  normalize_conda_prefix_for_var "RAG_START_CMD"
  normalize_conda_prefix_for_var "APP_START_CMD"

  # conda run 默认会捕获输出，导致 tail -f 不实时。这里统一改为实时输出。
  ensure_conda_run_no_capture_for_var "LLM_START_CMD"
  ensure_conda_run_no_capture_for_var "RAG_START_CMD"
  ensure_conda_run_no_capture_for_var "APP_START_CMD"
}

pid_file() {
  local name="$1"
  echo "${STACK_LOG_DIR}/${name}.pid"
}

log_file() {
  local name="$1"
  echo "${STACK_LOG_DIR}/${name}.log"
}

is_pid_alive() {
  local pid="$1"
  kill -0 "${pid}" >/dev/null 2>&1
}

service_pid_if_alive() {
  local name="$1"
  local file
  file="$(pid_file "${name}")"
  if [[ -f "${file}" ]]; then
    local pid
    pid="$(cat "${file}")"
    if [[ -n "${pid}" ]] && is_pid_alive "${pid}"; then
      echo "${pid}"
      return 0
    fi
  fi
  return 1
}

http_code() {
  local url="$1"
  local timeout="${2:-3}"
  local header="${3:-}"

  if [[ -n "${header}" ]]; then
    curl -s -o /dev/null -m "${timeout}" -w "%{http_code}" -H "${header}" "${url}" || true
  else
    curl -s -o /dev/null -m "${timeout}" -w "%{http_code}" "${url}" || true
  fi
}

http_ok() {
  local url="$1"
  local timeout="${2:-3}"
  local header="${3:-}"
  local code
  code="$(http_code "${url}" "${timeout}" "${header}")"
  [[ "${code}" =~ ^2[0-9][0-9]$ ]]
}

wait_for_http() {
  local url="$1"
  local timeout_sec="$2"
  local name="$3"
  local service_key="${4:-}"
  local start_ts now_ts
  start_ts="$(date +%s)"

  while true; do
    if http_ok "${url}" 3; then
      log "OK" "${name} is healthy: ${url}"
      return 0
    fi

    if [[ -n "${service_key}" ]]; then
      if ! service_pid_if_alive "${service_key}" >/dev/null; then
        log "ERR" "${name} process exited before health check passed."
        log "ERR" "Check log: $(log_file "${service_key}")"
        return 1
      fi
    fi

    now_ts="$(date +%s)"
    if (( now_ts - start_ts >= timeout_sec )); then
      log "ERR" "Timed out waiting for ${name}: ${url}"
      if [[ -n "${service_key}" ]]; then
        log "ERR" "Check log: $(log_file "${service_key}")"
      fi
      return 1
    fi
    sleep 2
  done
}

prepare_service_log() {
  local name="$1"
  local cmd="$2"
  local workdir="$3"
  local logf="$4"
  local mode="${STACK_LOG_MODE:-rotate}"

  case "${mode}" in
    rotate)
      if [[ -f "${logf}" ]] && [[ -s "${logf}" ]]; then
        local bak
        bak="${logf}.$(date +%Y%m%d_%H%M%S)"
        cp "${logf}" "${bak}" 2>/dev/null || true
      fi
      : > "${logf}"
      ;;
    truncate)
      : > "${logf}"
      ;;
    append)
      touch "${logf}"
      ;;
    *)
      log "WARN" "Unknown STACK_LOG_MODE=${mode}, fallback to append"
      touch "${logf}"
      ;;
  esac

  {
    echo ""
    echo "========== ${name} start $(date '+%Y-%m-%d %H:%M:%S') =========="
    echo "cmd: ${cmd}"
    echo "workdir: ${workdir}"
    echo "log_mode: ${mode}"
    echo "==============================================================="
  } >> "${logf}"
}

start_bg() {
  local name="$1"
  local cmd="$2"
  local workdir="$3"
  local pidf logf launch_cmd
  pidf="$(pid_file "${name}")"
  logf="$(log_file "${name}")"

  if service_pid_if_alive "${name}" >/dev/null; then
    local old_pid
    old_pid="$(service_pid_if_alive "${name}")"
    log "INFO" "${name} already running with PID ${old_pid}"
    return 0
  fi

  rm -f "${pidf}"
  prepare_service_log "${name}" "${cmd}" "${workdir}" "${logf}"

  launch_cmd="${cmd}"
  if command -v stdbuf >/dev/null 2>&1; then
    launch_cmd="stdbuf -oL -eL ${cmd}"
  fi

  log "INFO" "Starting ${name}: ${cmd}"
  if command -v setsid >/dev/null 2>&1; then
    nohup setsid bash -lc "cd \"${workdir}\" && export PYTHONUNBUFFERED=1 && ${launch_cmd}" >>"${logf}" 2>&1 < /dev/null &
  else
    nohup bash -lc "cd \"${workdir}\" && export PYTHONUNBUFFERED=1 && ${launch_cmd}" >>"${logf}" 2>&1 < /dev/null &
  fi

  local new_pid=$!
  echo "${new_pid}" >"${pidf}"
  log "INFO" "${name} started with PID ${new_pid}. Log: ${logf}"
}

service_port() {
  local name="$1"
  case "${name}" in
    llm) echo "${LLM_PORT:-8000}" ;;
    rag) echo "${RAG_PORT:-8001}" ;;
    app) echo "${APP_PORT:-5000}" ;;
    *) echo "" ;;
  esac
}

pids_listening_on_port() {
  local port="$1"

  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null | awk 'NF' | sort -u
    return 0
  fi

  if command -v fuser >/dev/null 2>&1; then
    fuser -n tcp "${port}" 2>/dev/null | tr ' ' '\n' | awk 'NF' | sort -u
    return 0
  fi

  ss -ltnp 2>/dev/null | awk -v p=":${port}" '
    $1 == "LISTEN" && $4 ~ (p"$") {
      n = split($0, a, "pid=");
      for (i = 2; i <= n; i++) {
        split(a[i], b, ",");
        if (b[1] ~ /^[0-9]+$/) print b[1];
      }
    }
  ' | sort -u
}

kill_pid_and_group() {
  local pid="$1"
  local sig="${2:-TERM}"

  kill "-${sig}" -- "-${pid}" >/dev/null 2>&1 || true
  kill "-${sig}" "${pid}" >/dev/null 2>&1 || true
}

wait_pid_exit() {
  local pid="$1"
  local timeout_sec="${2:-5}"
  local i

  for ((i = 0; i < timeout_sec; i++)); do
    if ! is_pid_alive "${pid}"; then
      return 0
    fi
    sleep 1
  done

  ! is_pid_alive "${pid}"
}

force_stop_by_port() {
  local name="$1"
  local port
  port="$(service_port "${name}")"
  [[ -z "${port}" ]] && return 0

  local pids=()
  mapfile -t pids < <(pids_listening_on_port "${port}")
  if (( ${#pids[@]} == 0 )); then
    return 0
  fi

  log "WARN" "${name} still listening on :${port}, stopping PIDs: ${pids[*]}"

  local p
  for p in "${pids[@]}"; do
    kill_pid_and_group "${p}" TERM
  done
  sleep 1

  mapfile -t pids < <(pids_listening_on_port "${port}")
  if (( ${#pids[@]} > 0 )); then
    for p in "${pids[@]}"; do
      kill_pid_and_group "${p}" KILL
    done
    sleep 1
  fi

  mapfile -t pids < <(pids_listening_on_port "${port}")
  if (( ${#pids[@]} > 0 )); then
    log "ERR" "${name} still listening on :${port} after force stop. Remaining PIDs: ${pids[*]}"
    return 1
  fi

  log "OK" "${name} listeners on :${port} are stopped"
  return 0
}

stop_by_pidfile() {
  local name="$1"
  local pidf
  pidf="$(pid_file "${name}")"

  if [[ ! -f "${pidf}" ]]; then
    log "INFO" "${name} pid file not found, trying port-based stop"
    force_stop_by_port "${name}" || true
    return 0
  fi

  local pid
  pid="$(cat "${pidf}")"
  if [[ -z "${pid}" ]]; then
    rm -f "${pidf}"
    log "INFO" "${name} pid file empty, cleaned"
    force_stop_by_port "${name}" || true
    return 0
  fi

  if is_pid_alive "${pid}"; then
    kill_pid_and_group "${pid}" TERM
    if ! wait_pid_exit "${pid}" 5; then
      kill_pid_and_group "${pid}" KILL
      wait_pid_exit "${pid}" 2 || true
    fi
    log "OK" "Stopped ${name} (PID ${pid})"
  else
    log "INFO" "${name} PID ${pid} not alive, cleaned"
  fi

  rm -f "${pidf}"

  # 兜底清理：即便父 PID 结束，也确保端口监听进程被停止。
  force_stop_by_port "${name}" || true
}