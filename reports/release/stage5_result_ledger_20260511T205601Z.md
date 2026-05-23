# Stage 5 Result Ledger

Created UTC: `20260511T205601Z`

Base commit: `a63af615567e3ebaaaba79e8f2ed90dcd5b577eb`

Recommended tag after merge: `stage5-pre-skills-checkpoint-<shortsha>`

## Ledger

| Area | Primary artifacts | Status | Evidence boundary |
| --- | --- | --- | --- |
| Stage 4 checkpoint baseline | `reports/release/stage4_checkpoint_20260511T152017Z.md`, `reports/release/stage4_result_ledger_20260511T152017Z.md`, `reports/release/stage4_artifact_inventory_20260511T152017Z.json` | Frozen Stage 4 baseline at tag `stage4-checkpoint-581102f` | Historical evidence baseline; Stage 5 does not mutate Stage 4 claims |
| Unified CLI / orchestrator | `docs/cli_usage.md`, `docs/workflow_usage.md`, `app/cli.py`, `app/workflow.py` | Unified user-facing entry points exist for core JasperLoop workflow commands | System integration capability only; no new benchmark result |
| Moore handoff automation | `docs/moore_handoff.md`, `app/workflow.py`, handoff tests | `jasperloop moore-handoff` prepare/validate/import workflows exist | Manifest-driven handoff automation; no raw Jasper logs and no Moore run in this checkpoint |
| Intent alignment evaluator | `docs/intent_alignment.md`, `app/alignment/*`, `reports/alignment/intent_alignment_smoke_summary_20260511T180423Z.md`, `reports/alignment/intent_alignment_smoke_manifest_20260511T180423Z.json` | Static/offline heuristic evaluator exists with CLI integration and smoke evidence | Heuristic/static evaluator only; not formal equivalence and not a substitute for human review |
| End-to-end replay demo | `docs/e2e_demo.md`, `examples/workflows/sva_repair_demo/*`, `reports/workflows/e2e_demo_summary_20260511T191259Z.md`, `reports/workflows/e2e_demo_manifest_20260511T191259Z.json` | Replay backend demo completes the local workflow chain | Offline replay evidence only; not real model performance |
| Local Qwen workflow backend | `docs/local_qwen_workflow.md`, `app/local_llm_backend.py`, `reports/local_llm/qwen_workflow_readiness_blocker_20260511T185244Z.md` | LOCAL_ONLY backend boundary and readiness manifest path exist | Backend safety/plumbing; no cloud fallback |
| Local Qwen runtime fix | `reports/local_llm/qwen_runtime_fix_summary_20260511T202643Z.md`, `reports/local_llm/qwen_runtime_fix_manifest_20260511T202643Z.json`, `reports/local_llm/qwen_workflow_subset_summary_20260511T202620Z.md`, `reports/local_llm/qwen_workflow_subset_manifest_20260511T202620Z.json` | `Qwen/Qwen3-14B-AWQ` via local vLLM completed 9-case 3+3+3 workflow subset with valid JSON, no fallback, and no LLM errors | Local-only bounded subset; not full Qwen benchmark and not Qwen-vs-Codex comparison |
| Repo hygiene infrastructure | `docs/repo_map.md`, `docs/artifact_policy.md`, `reports/index.md`, `reports/status/repo_cleanup_implementation_20260511T195542Z.md`, `tests/test_repo_hygiene.py`, `scripts/clean_local_artifacts.py` | Repo map, artifact policy, report index, ignore rules, hygiene tests, and dry-run cleanup helper exist | Hygiene infrastructure only; no evidence deletion or experiment-result change |
| Stage 5 gate closeouts | `reports/status/stage5_gate_status_20260511T193219Z.md`, `reports/status/stage5_runtime_cleanup_gate_20260511T195557Z.md` | Stage 5 Qwen and cleanup boundaries were reviewed and merged | Gate/status evidence only; no experiments |

## Key Metrics

### Validation Baseline

- Current base commit: `a63af615567e3ebaaaba79e8f2ed90dcd5b577eb`
- Local test suite: 329 passed
- Ruff: passed
- `git diff --check`: passed

### Qwen Local Runtime

- Model: `Qwen/Qwen3-14B-AWQ`
- Backend: local vLLM
- Endpoint during evidence capture: `http://127.0.0.1:8000/v1`
- Subset case count: 9
- Task split: 3 SVA repair, 3 triage, 3 coverage
- Status: `ok`
- Valid JSON: `true`
- Fallback count: 0
- LLM error count: 0
- Cloud fallback allowed: false
- Cloud fallback called: false
- Full benchmark: not run
- Qwen-vs-Codex comparison: not supported

### Workflow / Agent Shell

- Unified CLI: present
- Moore handoff automation: present
- Verifier-result import path: present
- Static intent alignment: present
- Replay end-to-end demo: present
- Local backend route: present

### Repo Hygiene

- Report index: present
- Artifact policy: present
- Repo map: present
- Raw artifact ignore protections: present
- Tracked-file hygiene tests: present
- Dry-run cleanup helper: present
- Evidence deletion: none

## Caveats Preserved

- Qwen subset is small 3+3+3 readiness evidence, not a full benchmark.
- Qwen-vs-Codex comparison is unsupported.
- Replay demo is not real model performance.
- Jasper proof does not imply intent alignment.
- `not_flagged_vacuous` is not an independent explicit non-vacuity certificate.
- Best-of-candidates pass@k is not single-output repair success.
- FVEval-compatible subset is not official FVEval reproduction.
- The project is not production signoff automation.

## Checkpoint Decision

Stage 5 is ready to freeze as a pre-skill-assimilation baseline. Stage 6 is
intentionally deferred until DV-engineer Claude Skills are read, categorized,
mapped to JasperLoop modules, and evaluated for safe implementation.
