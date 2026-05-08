#!/usr/bin/env bash
set -euo pipefail

export JASPER_BIN="${JASPER_BIN:-/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

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

"${PYTHON_BIN}" scripts/build_all_evidence_packets.py
