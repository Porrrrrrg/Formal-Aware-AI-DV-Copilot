# Stage 3 Result Ledger

Created UTC: 20260511T062042Z

Checkpoint commit: `a13eeeca64817f8257c22c7c4aaacb21527241f6`

## Ledger

| Area | Primary artifacts | Status | Evidence boundary |
| --- | --- | --- | --- |
| Stage 2A Moore evidence packet validation | `reports/jasper/moore_evidence_summary_20260511T004654Z.md`, `reports/jasper/moore_run_manifest_20260511T004654Z.json` | 30 case packets generated, 30 with Jasper reports, 30 with trace references, schema validation passed | Real Moore/JasperGold-backed packet evidence; raw logs and trace directories remain local-only |
| Stage 2D full Codex benchmark | `reports/llm/codex_full_summary_20260511T015713Z.md`, `reports/llm/codex_full_manifest_20260511T015713Z.json`, `reports/llm/codex_full_error_cases_20260511T015713Z.md` | 57 cases attempted, 71/71 valid JSON, 0 fallback, 0 LLM errors | Real Codex full benchmark measurement; no Qwen comparison or production readiness claim |
| Stage 3D Codex repair final Jasper proof | `reports/jasper/codex_repair_final_proof_summary_20260511T053413Z.md`, `reports/jasper/codex_repair_final_proof_manifest_20260511T053413Z.json` | 34 candidates covering 18 repair cases; 34/34 syntax pass, 34/34 proven, 0 parsed vacuous | Live Moore/JasperGold outcomes for restored candidates; best-of-k is not single-output success |
| FIFO/vacuity benchmark expansion | `reports/benchmarks/benchmark_expansion_summary_20260511T031851Z.md` | Local DV labeled cases expanded to 53; 17 FIFO cases and 6 existing-design assumption/vacuity cases added | Benchmark metadata only; expected fields are author labels, not observed Jasper evidence |
| FVEval-compatible subset integration | `reports/benchmarks/fveval_subset_import_20260511T031107Z.md`, `evaluation/results/fveval_subset_results.md` | 30 FVEval-compatible cases imported; runner reports syntax scaffold and leakage safeguards | Not official FVEval reproduction; no commercial property-equivalence flow |
| Qwen readiness | `reports/local_llm/qwen_readiness_20260511T013853Z.md`, `reports/local_llm/qwen_readiness_manifest_20260511T013853Z.json` | Readiness blocked; local vLLM/SGLang/Ollama endpoints unavailable; `LOCAL_ONLY=true` verified no cloud fallback | No Qwen subset, quality, latency, cost, or Qwen-vs-Codex conclusion |
| Stage 3 closeout | `reports/status/stage3_gate_closeout_20260511T060137Z.md`, `reports/research/stage3_research_delta_20260511T060137Z.md` | #32, #27, #26 merged and bounded; open PR queue cleared | Research/gate synthesis only; no new experiment |

## Key Metrics

### Moore Evidence Packets

- Case packets generated: 30
- Packets with Jasper reports: 30
- Packets with trace references: 30
- Designs: `apb_regblock`, `arbiter_rr2`, `rv_buffer`
- Schema validation: passed

### Codex Full Benchmark

- Cases attempted: 57
- LLM adapter outputs: 71
- Valid JSON rate: 71/71 = 100.0%
- Fallback rate: 0/71 = 0.0%
- LLM error rate: 0/71 = 0.0%
- SVA repair scaffold success: 11/18 = 61.1%
- Triage issue/action accuracy: 28/30 = 93.3%
- Coverage gap/action accuracy: 9/9 = 100.0%

### Codex Repair Final-Proof Validation

- Candidate count: 34
- Case count: 18
- Syntax pass: 34/34
- Proven: 34/34
- Proven and not parsed vacuous: 34/34
- Falsified: 0/34
- Timeout or unknown: 0/34
- Case-level pass@1 selected/first candidate: 18/18
- Case-level pass@k best-of-candidates: 18/18

### Expanded Benchmarks

- Total local DV labeled cases after expansion: 53
- New FIFO labeled cases: 17
- New existing-design assumption/vacuity cases: 6
- Coverage-closure cases after expansion: 14
- SVA generation cases after expansion: 33
- SVA repair cases after expansion: 23

### FVEval-Compatible Subset

- Total imported cases: 30
- NL2SVA-Human: 10
- NL2SVA-Machine: 10
- Design2SVA: 10
- Jasper proof: `not_run`
- Reference answers: evaluation metadata only, omitted from emitted prompt payloads

## Release Decision

This checkpoint is suitable as the Stage 3 baseline because the evidence chain is
merged, bounded, and reproducible from committed reports and manifests. The next
work should not mutate this baseline; it should start from the planned tag
`stage3-checkpoint-a13eeec`.
