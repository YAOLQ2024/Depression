#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

mkdir -p "${STACK_LOG_DIR}"

touch "$(log_file llm)" "$(log_file rag)" "$(log_file app)"

tail_n="${1:-120}"
tail -n "${tail_n}" -F "$(log_file llm)" "$(log_file rag)" "$(log_file app)"