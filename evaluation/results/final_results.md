# Final Results

This is the canonical curated result table for the cleaned JasperLoop-DV repository. Raw local Qwen outputs, JasperGold logs, traces, waves, and run artifacts remain local/untracked.

| Task | Backend | Cases | JSON validity | Fallback | Hallucinated signal | Task metric | Formal status | Boundary |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| SVA repair | Local Qwen/Qwen3-14B-AWQ via `JASPERLOOP_LLM_CMD` | 23 | 1.000 | 0.000 | 0.043 | Exact/repair success 0.913 | Local LLM output mechanics only | Not Codex CLI; not formal proof by itself |
| SVA repair re-check | JasperGold on saved local Qwen final candidates | 23 | n/a | n/a | n/a | 22/23 syntax pass; 22 proven | 0 falsified, 0 undetermined, 0 vacuous | Scoped to project harnesses/properties; not full intent equivalence |
| Failure triage | Local Qwen/Qwen3-14B-AWQ after evidence-cue improvements | 53 | 1.000 | 0.000 | 0.000 | Issue/action accuracy 1.000/1.000 | Not a formal re-check task | Not JasperGold-backed triage validation |
| Coverage closure | Local Qwen/Qwen3-14B-AWQ | 14 | 1.000 | 0.000 | n/a | Gap/action accuracy 1.000/1.000 | Local LLM output mechanics only | Coverage plans still require project-specific review |

## Interpretation

- The final triage score reflects a full 53-case local Qwen rerun after the assumption/vacuity and stimulus-vs-coverage evidence improvements.
- The JasperGold-backed result applies only to the saved local Qwen SVA repair final candidates.
- The coverage and triage rows are not JasperGold-backed formal validation.
- These results are not Codex CLI performance, not official FVEval performance, and not production DV signoff.
