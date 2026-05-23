#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/run_moore_codex_repair_final_proof.sh [--dry-run] [helper args...]

Runs restored Codex SVA repair candidates through the final JasperGold
syntax/proof/vacuity path on Moore. Raw Jasper logs, traces, and jgproject
directories are written under ignored jasper/reports/ paths.

Moore setup example:
  tcsh -fc 'source /vol/eecs391/cadence.env; setenv JASPER_BIN /vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg; bash scripts/run_moore_codex_repair_final_proof.sh'

Useful dry run:
  bash scripts/run_moore_codex_repair_final_proof.sh --dry-run --manifest-out artifacts/codex_repair_final_proof_dry_run_manifest.json
USAGE
}

DRY_RUN=0
HELP=0
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      HELP=1
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ "${HELP}" -eq 1 ]]; then
  usage
  exit 0
fi

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
  else
    echo "ERROR: Cannot find python3.11 or python3." >&2
    exit 2
  fi
fi

if [[ "${DRY_RUN}" -eq 0 ]]; then
  HOST_NAME="$(hostname -f 2>/dev/null || hostname)"
  if [[ "${HOST_NAME,,}" != *moore* ]]; then
    echo "ERROR: final JasperGold proof must be run on moore.wot.ece.northwestern.edu; current host is ${HOST_NAME}." >&2
    exit 2
  fi

  export JASPER_BIN="${JASPER_BIN:-/vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg}"
  if [[ ! -x "${JASPER_BIN}" ]]; then
    cat >&2 <<ERROR
ERROR: JASPER_BIN is not executable: ${JASPER_BIN}
Source the Cadence environment first. If cadence.env requires csh/tcsh syntax, use:
  tcsh -fc 'source /vol/eecs391/cadence.env; setenv JASPER_BIN /vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg; bash scripts/run_moore_codex_repair_final_proof.sh'
ERROR
    exit 2
  fi

  "${PYTHON_BIN}" tools/run_codex_repair_final_proof.py --jasper-check "${EXTRA_ARGS[@]}"
else
  "${PYTHON_BIN}" tools/run_codex_repair_final_proof.py --dry-run "${EXTRA_ARGS[@]}"
fi
