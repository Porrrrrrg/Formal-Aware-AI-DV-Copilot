# Design2SVA ProofLoop-Style Stage 5

Stage 5 adds retrieval-assisted Design2SVA infrastructure and repair-loop
metrics on top of the v0.4 agentic refactor. The goal is to improve the weakest
full Codex metric, SVA repair, while expanding from repairing known assertions
toward generating assertions from RTL, harness context, and natural-language
intent.

## What Changed

- `benchmarks/design2sva_cases.json` defines first-class Design2SVA tasks with
  RTL path, harness/header path, assertion intent, visible signals, clock/reset
  contract, helper-code policy, and evaluation metadata.
- `copilot/retrieval/design2sva_context.py` builds bounded structured context
  from the RTL index: module interface, clock/reset candidates, hierarchy,
  assigns, always blocks, and signal-specific logic.
- `copilot/agents/design2sva_agent.py` generates schema-validated candidates in
  deterministic scaffold, replay, or LLM mode.
- `evaluation/run_design2sva_eval.py` evaluates pass@k candidates, tracks
  hallucinated signals, valid JSON, fallback/replay/LLM provenance, repair-loop
  rounds, and optional JasperGold feedback.
- `tools/import_fveval_subset.py` imports local FVEval-like fixture folders for
  later NL2SVA/Design2SVA comparison without downloading data.

## Difference From ProofLoop

ProofLoop's core pattern is AST-indexed retrieval plus solver feedback. Stage 5
adopts that direction but remains a JasperLoop-DV scaffold:

- JasperLoop-DV covers SVA generation, SVA repair, DV triage, and coverage
  closure, rather than only Design2SVA.
- Retrieval is lightweight and local: it uses the existing `copilot/retrieval`
  index with fallback parsing, not a full commercial structural database.
- Solver feedback is pluggable through the JasperGold backend facade, but local
  tests and dry runs do not require JasperGold.
- Current Design2SVA results are infrastructure/local unless a run explicitly
  records real LLM and JasperGold execution.

## Local Commands

Dry-run three local fixtures with pass@3:

```bash
python evaluation/run_design2sva_eval.py --limit 3 --k 3 --dry-run --out evaluation/results/design2sva_eval_local.json
```

Replay committed candidate fixtures:

```bash
python evaluation/run_design2sva_eval.py --limit 3 --k 3 --replay --out evaluation/results/design2sva_eval_local.json
```

Refresh result tables after a local Design2SVA run:

```bash
python scripts/refresh_eval_results.py
```

Import a local FVEval-like fixture folder:

```bash
python tools/import_fveval_subset.py --source-dir /path/to/local/fveval-fixture --out benchmarks/fveval_subset/local_import_cases.json
```

The importer supports flat folders and `NL2SVA-Human/`,
`NL2SVA-Machine/`, and `Design2SVA/` subfolders containing JSON, JSONL, or CSV
rows. It does not download FVEval or any private/commercial data.

## Metrics

The Design2SVA evaluator reports:

- `syntax@1` and `syntax@k`
- `proven@1`, `proven@k`, and `non_vacuous@k` when JasperGold checks run
- `hallucinated_signal_rate`
- `fallback_rate`
- `valid_json_rate`
- `average_rounds`
- `repair_success_after_feedback`
- source counts and failure categories

## Claim Boundary

- Dry-run and replay results validate infrastructure only.
- Deterministic scaffold candidates are not hosted model performance.
- `proven@*` and `non_vacuous@k` are not evidence unless JasperGold is actually
  run and the result artifact records measured formal status.
- Exact/reference match on these fixtures is a local scaffold metric, not
  functional equivalence.
- Stage 5 does not claim ProofLoop-level performance, production signoff, or
  unattended RTL verification.
