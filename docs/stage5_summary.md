# Stage 5 Summary

Stage 5 starts from the v0.4 agentic baseline and targets the main remaining
research bottleneck: SVA generation and repair. The merged v0.4 results showed
strong DV triage and coverage closure behavior, while SVA repair reached 15/23
scaffold success. This stage adds a controlled path toward retrieval-assisted
Design2SVA and feedback-aware repair.

## Added

- First-class Design2SVA task fixtures in `benchmarks/design2sva_cases.json`.
- Typed task and candidate companions for Design2SVA in `app/models/agent.py`.
- Strict Design2SVA task and candidate JSON schemas under `copilot/schemas/`.
- A bounded Design2SVA context builder using module interface, clock/reset,
  hierarchy, assigns, always blocks, and signal logic retrieval.
- A candidate generator supporting deterministic scaffold, replay, and LLM
  modes without sending external prompts by default.
- `evaluation/run_design2sva_eval.py` with `--limit`, `--k`, `--dry-run`,
  `--replay`, `--llm`, and `--jasper-check`.
- Local pass@k, provenance, hallucination, JSON-validity, and repair-loop
  metrics.
- `tools/import_fveval_subset.py` for offline local NL2SVA/Design2SVA-style
  fixture import.
- Result-table refresh support for `evaluation/results/design2sva_results.md`.

## Local Smoke Result

The local dry-run command:

```bash
python evaluation/run_design2sva_eval.py --limit 3 --k 3 --dry-run --out evaluation/results/design2sva_eval_local.json
```

produces three local fixture cases and nine deterministic scaffold candidates.
It reports `syntax@1 = 1.0`, `syntax@k = 1.0`, `valid_json_rate = 1.0`, and
`hallucinated_signal_rate = 0.0`. Because this is a dry run, `proven@1`,
`proven@k`, and `non_vacuous@k` remain `0.0` with formal metrics marked
`not_run`.

## Claim Boundary

Stage 5 is infrastructure and local evaluation scaffolding unless a later run
explicitly records real LLM and JasperGold execution. It does not claim
ProofLoop-level performance, production signoff, or formal proof correctness of
generated assertions.
