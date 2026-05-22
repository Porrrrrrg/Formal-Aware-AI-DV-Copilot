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

runs=(
  "arbiter_rr2 correct prove"
  "arbiter_rr2 bug_double_grant prove"
  "arbiter_rr2 bug_turn_update prove"
  "rv_buffer correct prove"
  "rv_buffer bug_overwrite prove"
  "rv_buffer bug_inready prove"
  "apb_regblock correct prove"
  "apb_regblock bug_wrong_addr prove"
  "apb_regblock bug_read_latency prove"
)

for run in "${runs[@]}"; do
  read -r design variant mode <<<"${run}"
  echo "==> ${design} ${variant} ${mode}"
  "${PYTHON_BIN}" tools/run_jasper.py --design "${design}" --variant "${variant}" --mode "${mode}"
done

"${PYTHON_BIN}" tools/build_evidence_packet.py \
  --case benchmarks/arbiter_rr2/cases/rtl_bug_double_grant.json \
  --report jasper/reports/arbiter_rr2_bug_double_grant_prove/properties.rpt \
  --trace-dir jasper/reports/arbiter_rr2_bug_double_grant_prove/traces \
  --rtl benchmarks/arbiter_rr2/rtl/arbiter_rr2_bug_double_grant.sv \
  --out jasper/reports/arbiter_rr2_bug_double_grant_prove/evidence_packet.json

"${PYTHON_BIN}" tools/validate_json.py \
  copilot/schemas/evidence_packet.schema.json \
  jasper/reports/arbiter_rr2_bug_double_grant_prove/evidence_packet.json
