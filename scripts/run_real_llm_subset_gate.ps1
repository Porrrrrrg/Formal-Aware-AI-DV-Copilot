$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Fail-Gate {
    param([string]$Reason)
    python scripts/update_codex_subset_quality.py --gate-failed --reason $Reason
    Write-Error $Reason
    exit 1
}

python scripts/doctor_llm_backend.py
if ($LASTEXITCODE -ne 0) { Fail-Gate "backend doctor failed" }

python scripts/test_llm_backend_contract.py
if ($LASTEXITCODE -ne 0) { Fail-Gate "backend contract test failed" }

if ($env:JASPERLOOP_LLM_CMD) {
    python evaluation/run_sva_repair_eval.py `
        --llm `
        --limit 3 `
        --out evaluation/results/sva_repair_codex_subset.json
    python evaluation/run_agent_eval.py `
        --systems structured `
        --llm `
        --limit 3 `
        --out evaluation/results/agent_eval_codex_subset.json
    python evaluation/run_coverage_eval.py `
        --systems structured `
        --llm `
        --limit 3 `
        --out evaluation/results/coverage_eval_codex_subset.json
} else {
    python scripts/run_codex_llm_eval.py `
        --task sva_repair `
        --limit 3 `
        --out evaluation/results/sva_repair_codex_subset.json `
        --acknowledge-external-send
    python scripts/run_codex_llm_eval.py `
        --task triage `
        --limit 3 `
        --packet-source actual `
        --out evaluation/results/agent_eval_codex_subset.json `
        --acknowledge-external-send
    python scripts/run_codex_llm_eval.py `
        --task coverage `
        --limit 3 `
        --packet-source actual `
        --out evaluation/results/coverage_eval_codex_subset.json `
        --acknowledge-external-send
}

python scripts/update_codex_subset_quality.py
