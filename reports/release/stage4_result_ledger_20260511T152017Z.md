# Stage 4 Result Ledger

Created UTC: `20260511T152017Z`

Checkpoint commit: `581102fbe91c2724b12faf7200da5db735f68d1f`

Recommended tag: `stage4-checkpoint-581102f`

## Ledger

| Area | Primary artifacts | Status | Evidence boundary |
| --- | --- | --- | --- |
| Stage 3 checkpoint baseline | `reports/release/stage3_checkpoint_20260511T062042Z.md`, `reports/release/stage3_result_ledger_20260511T062042Z.md`, `reports/release/stage3_artifact_inventory_20260511T062042Z.json` | Stage 3 baseline captured at `a13eeeca64817f8257c22c7c4aaacb21527241f6`; 264-test validation was recorded there | Historical release baseline; Stage 4 does not reinterpret Stage 3 evidence |
| Stage 4 gate/report baseline | `reports/status/stage4_gate_status_20260511T063622Z.md`, `reports/status/stage4_second_wave_gate_20260511T141346Z.md` | Gate reports define first-wave and second-wave evidence rules and queue state | Status-only reports; no experiments, model calls, Jasper reruns, schemas, or benchmark labels changed by the gate reports |
| Expanded benchmark evidence | `reports/jasper/expanded_benchmark_evidence_summary_20260511T064639Z.md`, `reports/jasper/expanded_benchmark_evidence_manifest_20260511T064639Z.json` | 53/53 current local-DV cases have schema-valid prove-backed Moore/JasperGold evidence packets; 53 report references and 53 trace-dir references recorded | Packet-level prove evidence only; auxiliary cover/vacuity modes failed under Jasper 2018.09 command support and are not explicit cover/vacuity certificates |
| FVEval-compatible subset evaluation | `reports/fveval/fveval_subset_eval_summary_20260511T141418Z.md`, `reports/fveval/fveval_subset_eval_manifest_20260511T141418Z.json`, `evaluation/results/fveval_subset_results.md` | 30/30 deterministic local subset cases completed; 30/30 valid JSON; 30/30 syntax scaffold; 0/30 hallucinated signals; fallback 30/30 because no external predictions were provided | Local FVEval-compatible runner only; not official FVEval reproduction, no JasperGold, no Codex, no Qwen, and no commercial property-equivalence flow |
| SVA repair ablation local scaffold | `reports/repair/sva_repair_ablation_summary_20260511T064252Z.md`, `reports/repair/sva_repair_ablation_manifest_20260511T064252Z.json`, `reports/repair/sva_repair_ablation_error_cases_20260511T064252Z.md` | Seven variants over 18 repair cases; valid JSON for all attempted outputs; local scaffold success ranged from 12/18 to 13/18 by variant; sanitized handoff artifact contains 126 rows | Local scaffold and exact-template metrics only until separately proved; not a final formal repair-quality claim |
| SVA repair ablation Moore/JasperGold proof | `reports/jasper/sva_repair_ablation_final_proof_summary_20260511T143254Z.md`, `reports/jasper/sva_repair_ablation_final_proof_manifest_20260511T143254Z.json` | 126/126 handoff candidates syntax-pass and proven; 126/126 not flagged vacuous; 0 falsified, 0 vacuous, 0 unknown/timeout | Live Moore/JasperGold final proof for sanitized handoff candidates; Jasper proof alone does not imply intent alignment |
| Qwen status | `reports/local_llm/qwen_readiness_20260511T013853Z.md`, `reports/local_llm/qwen_readiness_manifest_20260511T013853Z.json` | Local backend unavailable; subset not run; `LOCAL_ONLY=true`; cloud fallback not called | Qwen still not run for quality evaluation; no latency, cost, quality, or Qwen-vs-Codex claim |

## Key Metrics

### Stage 3 Checkpoint Baseline

- Stage 3 checkpoint commit: `a13eeeca64817f8257c22c7c4aaacb21527241f6`
- Stage 3 planned tag: `stage3-checkpoint-a13eeec`
- Stage 3 reported validation: `264 passed`, Ruff passed, `git diff --check` passed
- Stage 3 evidence included Moore evidence packets, full Codex benchmark,
  Codex repair final proof, benchmark expansion metadata, FVEval-compatible
  import, Qwen readiness blocker, and Stage 3 closeout

### Stage 4 Gate/Report Baseline

- Initial gate report: `reports/status/stage4_gate_status_20260511T063622Z.md`
- Second-wave gate report:
  `reports/status/stage4_second_wave_gate_20260511T141346Z.md`
- Gate evidence type: report/status only
- Gate rule preserved: scaffold results, LLM outputs, and formal
  Moore/JasperGold evidence must remain separate

### Expanded Benchmark Evidence

- Current benchmark cases attempted: 53
- Evidence packets generated: 53
- Schema-valid packets: 53
- Schema-invalid packets: 0
- `report_found`: 53
- `trace_dir_found`: 53
- Trace file references: 610
- Prove runs: 15/15 succeeded
- Auxiliary cover runs: 0/4 succeeded
- Auxiliary vacuity runs: 0/4 succeeded

### FVEval-Compatible Subset Evaluation

- Total cases: 30
- NL2SVA-Human: 10
- NL2SVA-Machine: 10
- Design2SVA: 10
- Valid JSON: 30/30
- Syntax scaffold: 30/30
- Fallback: 30/30 deterministic local fallback because no external predictions
  were supplied
- Hallucinated signals: 0/30
- Jasper proof: not run

### SVA Repair Ablation Local Scaffold Metrics

- Variants: 7
- Repair cases per variant: 18
- Sanitized handoff rows: 126
- Local scaffold success:
  - `baseline_prompt`: 13/18
  - `cex_aware_prompt`: 13/18
  - `signal_whitelist_only`: 13/18
  - `temporal_hint_only`: 12/18
  - `one_round_repair`: 12/18
  - `multi_round_repair`: 13/18
  - `self_check_before_final`: 12/18
- Qwen: not run

### SVA Repair Ablation Moore/JasperGold Proof

- Candidate count: 126
- Case count: 18
- Variant count: 7
- Syntax pass: 126/126
- Proven: 126/126
- Not flagged vacuous: 126/126
- Falsified: 0/126
- Vacuous: 0/126
- Unknown or timeout: 0/126
- `jasper_vacuity_status` null count: 126

### Qwen Status

- Active backend: unavailable
- Subset status: not run
- `LOCAL_ONLY`: true
- Cloud fallback called: false
- Quality claim: none
- Qwen-vs-Codex comparison: unsupported

## Caveats Preserved

- `not_flagged_vacuous` is not an independent explicit non-vacuity certificate.
- Best-of-candidates pass@k is not single-output repair success.
- Jasper proof does not imply intent alignment.
- The FVEval-compatible subset is not official FVEval reproduction.
- Qwen-vs-Codex comparison is unsupported.

## Validation

Run on `stage/stage4-release-checkpoint`:

| Command | Result |
| --- | --- |
| `git rev-parse HEAD` | `581102fbe91c2724b12faf7200da5db735f68d1f` |
| `python -m pytest -q` | 270 passed before report creation; 270 passed after report creation |
| `python -m ruff check .` | Passed before report creation; passed after report creation |
| `git diff --check` | Passed before report creation; passed after report creation |
| `python -m json.tool reports/release/stage4_artifact_inventory_20260511T152017Z.json` | Passed |

## Release Decision

Stage 4 is ready to tag as `stage4-checkpoint-581102f` after final local
validation passes on this report-only branch. Stage 5 should build new
orchestration and evaluation layers without changing the Stage 4 evidence
claims.
