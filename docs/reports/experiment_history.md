# Experiment History

This table records the major checkpoints without preserving every intermediate PR report.

| Version/tag | Purpose | Key result | Boundary |
| --- | --- | --- | --- |
| `v1.1.0-repo-clean-llm-gate` | Repository identity cleanup and backend gate diagnostics | Moore wording, artifact policy, benchmark scaffold, parser/evidence, and LLM backend doctor were put in place. | No real LLM or JasperGold-backed benchmark claim. |
| `v1.1.1-local-qwen-subset-gate` | Local Qwen subset gate | 3+3+3 subset gate passed after output-control fixes. | Subset readiness only. |
| `v1.1.2-local-qwen-full-benchmark` | Full local Qwen benchmark | SVA repair, failure triage, and coverage closure ran through local Qwen. | Output mechanics and local task metrics only. |
| `v1.1.3-local-qwen-jasper-recheck` | JasperGold re-check of saved SVA repair finals | 22/23 saved Qwen SVA repair finals passed syntax and proved. | JasperGold-backed only for checked SVA repair finals. |
| `v1.1.4-research-findings` | Research summary | Evidence chain and claim boundaries were consolidated. | Documentation only. |
| `v1.1.5-assumption-vacuity-triage` | Assumption/vacuity scoped improvement | Gold `assumption_constraint_bug` scoped local Qwen gate improved from 3/12 baseline to 12/12. | Scoped gate only. |
| `v1.1.6-local-qwen-triage-rerun` | Full triage rerun after assumption/vacuity fix | Full triage improved to 0.962/0.962; assumption cases reached 12/12. | Full triage only; stimulus-vs-coverage misses remained. |
| `v1.1.7-stimulus-vs-coverage-triage` | Stimulus-vs-coverage scoped improvement | Scoped local Qwen gate fixed `rv_B8` and `fifo_D17` and reached 18/18. | Scoped gate only. |
| `v1.1.8-local-qwen-triage-clean` | Full triage rerun after stimulus-vs-coverage fix | Full local Qwen triage reached 1.000/1.000 with valid JSON 1.000, fallback 0.000, hallucinated signal 0.000. | Full failure-triage only. |
| `v1.1.9-research-findings-update` | Research findings update | The v1.1.5-v1.1.8 triage chain was summarized. | Documentation only. |
