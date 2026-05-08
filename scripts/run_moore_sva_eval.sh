#!/usr/bin/env bash
set -euo pipefail

export JASPER_BIN="${JASPER_BIN:-/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

"${PYTHON_BIN}" evaluation/run_sva_eval.py \
  --jasper-check \
  --out evaluation/results/sva_eval_jasper_moore.json
