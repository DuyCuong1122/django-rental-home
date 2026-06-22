#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
K6_BIN="${K6_BIN:-k6}"
SUITE="${1:-}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

run_suite() {
  local script_path="$1"
  echo "Running ${script_path}"
  "${K6_BIN}" run "${ROOT_DIR}/${script_path}"
}

case "${SUITE}" in
  smoke)
    run_suite "smoke/smoke.js"
    ;;
  load)
    run_suite "load/load.js"
    ;;
  stress)
    run_suite "stress/stress.js"
    ;;
  soak)
    run_suite "soak/soak.js"
    ;;
  all)
    run_suite "smoke/smoke.js"
    run_suite "load/load.js"
    run_suite "stress/stress.js"
    ;;
  *)
    echo "Usage: ${0} {smoke|load|stress|soak|all}"
    echo "Project directory: ${PROJECT_DIR}"
    exit 1
    ;;
esac
