#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

fail_gate() {
  local reason="$1"
  python scripts/update_codex_subset_quality.py --gate-failed --reason "${reason}"
  echo "${reason}" >&2
  exit 1
}

python scripts/doctor_llm_backend.py || fail_gate "backend doctor failed"
python scripts/test_llm_backend_contract.py || fail_gate "backend contract test failed"

if [[ -n "${JASPERLOOP_LLM_CMD:-}" ]]; then
  python evaluation/run_sva_repair_eval.py \
    --llm \
    --limit 3 \
    --out evaluation/results/sva_repair_codex_subset.json
  python evaluation/run_agent_eval.py \
    --systems structured \
    --llm \
    --limit 3 \
    --out evaluation/results/agent_eval_codex_subset.json
  python evaluation/run_coverage_eval.py \
    --systems structured \
    --llm \
    --limit 3 \
    --out evaluation/results/coverage_eval_codex_subset.json
else
  python scripts/run_codex_llm_eval.py \
    --task sva_repair \
    --limit 3 \
    --out evaluation/results/sva_repair_codex_subset.json \
    --acknowledge-external-send
  python scripts/run_codex_llm_eval.py \
    --task triage \
    --limit 3 \
    --packet-source actual \
    --out evaluation/results/agent_eval_codex_subset.json \
    --acknowledge-external-send
  python scripts/run_codex_llm_eval.py \
    --task coverage \
    --limit 3 \
    --packet-source actual \
    --out evaluation/results/coverage_eval_codex_subset.json \
    --acknowledge-external-send
fi

python scripts/update_codex_subset_quality.py
