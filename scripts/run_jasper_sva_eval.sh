#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${JASPER_ENV:-}" ]]; then
  # shellcheck disable=SC1090
  source "${JASPER_ENV}"
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  else
    PYTHON_BIN="python3"
  fi
fi

: "${JASPER_BIN:=jg}"
export JASPER_BIN

"${PYTHON_BIN}" evaluation/run_sva_eval.py \
  --jasper-check \
  --out evaluation/results/sva_eval_jasper_local.json
