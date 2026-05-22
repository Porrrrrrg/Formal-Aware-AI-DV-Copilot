# Codex/LLM Subset Quality Gate

Subset commands:

```bash
python scripts/run_codex_llm_eval.py --task sva_repair --limit 3 --out evaluation/results/sva_repair_codex_subset.json --acknowledge-external-send --timeout 600
python scripts/run_codex_llm_eval.py --task triage --limit 3 --packet-source actual --out evaluation/results/agent_eval_codex_subset.json --acknowledge-external-send --timeout 600
python scripts/run_codex_llm_eval.py --task coverage --limit 3 --packet-source actual --out evaluation/results/coverage_eval_codex_subset.json --acknowledge-external-send --timeout 600
```

Gate result: **failed; full Codex/LLM run was not executed**.

The evaluator result JSON files are valid, but no Codex model JSON was produced. Every LLM attempt failed before model execution because the local Codex CLI executable returned `Access is denied`. The backend doctor now classifies this as `permission_denied` before benchmark execution.

| Task | Cases | LLM JSON Validity | LLM Success | Fallback Rate | LLM Error Rate | Hallucinated Signal Rate | Accuracy Metric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SVA repair | 3 | 0/3 | 0.000 | 1.000 | 1.000 | 0.000 | final exact match 1.000, fallback only |
| Failure triage | 3 | 0/3 | 0.000 | 1.000 | 1.000 | 0.000 | issue/action 1.000, fallback only |
| Coverage closure | 3 | 0/3 | 0.000 | 1.000 | 1.000 | n/a | gap/action 1.000, fallback only |

Gate policy:

- JSON validity below 0.90: stop full run.
- Fallback rate above 0.25: stop full run.
- Hallucinated signal rate could not be measured on actual model outputs because no model outputs were produced.

Failed cases:

- `repair_arbiter_mutex_syntax`, `repair_arbiter_spurious_unknown_signal`, `repair_arbiter_single_req1_wrong_grant`: Codex CLI invocation failed; structured repair fallback produced valid local scaffold outputs.
- `apb_C6`, `apb_C5`, `apb_C11`: Codex CLI invocation failed; structured triage fallback was scored.
- `apb_C10`, `apb_C12`, `apb_C9`: Codex CLI invocation failed; structured coverage fallback was scored.

These metrics must not be reported as Codex performance. They are a failed real-LLM gate plus deterministic fallback behavior.

For rerun recovery, use `scripts/run_real_llm_subset_gate.sh` or `scripts/run_real_llm_subset_gate.ps1`. Those scripts stop before benchmark execution when the backend doctor or contract test fails.
