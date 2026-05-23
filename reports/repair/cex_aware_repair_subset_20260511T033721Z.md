# CEX-Aware SVA Repair Subset Report

Created UTC: 2026-05-11T03:37:21Z

## Scope

Subset-only smoke run for the Stage 3B counterexample-aware SVA repair path. This is not a full repair benchmark and does not claim repair-rate improvement.

## Command

```powershell
$env:JASPERLOOP_LLM_CMD = "python copilot/llm_adapters/replay_json.py --responses <temp-replay-jsonl> --strict-round"; python evaluation/run_sva_repair_eval.py --llm --limit 3 --prompt-version cex_aware --out reports/repair/cex_aware_repair_manifest_20260511T033721Z.json
```

The command used the local replay JSON adapter to exercise the `--llm` path without Qwen or external model export.

## Results

- Cases attempted: 3
- Valid JSON outputs accepted by runner: 3/3
- LLM-source repair actions: 3
- Structured fallback repair actions: 0
- Hallucinated-signal final outputs: 0/3
- Prompt versions: {"cex_aware": 3}
- Jasper checked: 0/3

## Case Rows

| case_id | final_status | success | repair_rounds | final_exact_match | hallucinated_signals | scaffold_success |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| repair_arbiter_mutex_syntax | scaffold_pass | True | 1 | True | None | True |
| repair_arbiter_spurious_unknown_signal | scaffold_pass | True | 1 | True | None | True |
| repair_arbiter_single_req1_wrong_grant | scaffold_pass | True | 1 | True | None | True |

## Notes

- The current committed repair cases do not include structured failing-cycle or signal-value counterexample fields, so those CEX field flags are false for this subset unless supplied by future evidence.
- `jasper_checked` is false because no live JasperGold check was requested for this local subset smoke run.
- The manifest JSON next to this report contains the runner summary and per-case records.
