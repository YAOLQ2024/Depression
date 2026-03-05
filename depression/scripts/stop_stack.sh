#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

load_env

stop_by_pidfile "app"
stop_by_pidfile "rag"
stop_by_pidfile "llm"

log "OK" "Requested stop for app/rag/llm started by these scripts."