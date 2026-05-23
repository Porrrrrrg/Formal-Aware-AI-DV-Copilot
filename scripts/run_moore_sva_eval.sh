#!/usr/bin/env bash
set -euo pipefail

echo "Moore is one possible JasperGold host environment; this script is a compatibility wrapper."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/run_jasper_sva_eval.sh" "$@"
