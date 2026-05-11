# FVEval-Compatible Subset Evaluation

## Scope

This report evaluates the imported 30-case FVEval-compatible subset with the local
`evaluation/run_fveval_subset.py` runner.

Evidence type: local subset runner / deterministic scaffold evaluation.

This is not an official FVEval reproduction. It does not reproduce FVEval's
commercial property-equivalence flow, and it does not run JasperGold, Codex, or
Qwen. Reference SVA fields remain evaluation metadata only and are omitted from
prompt payloads.

## Base

- Base Git SHA: `4b6ada886b403ae8b38bd634076b8f883f8a74da`
- Branch: `stage/fveval-subset-eval`
- Stage 3 checkpoint tag: `stage3-checkpoint-a13eeec`
- Source benchmark: FVEval-compatible subset from `https://github.com/NVlabs/FVEval`
- Source commit: `141afe7dcf03a0b86547b94657d9d610b6087724`

## Commands

```powershell
python evaluation/run_fveval_subset.py --markdown evaluation/results/fveval_subset_results.md
python -m pytest -q
python -m ruff check .
git diff --check
```

## Aggregate Metrics

| Metric | Value |
| --- | ---: |
| Cases | 30 |
| Syntax scaffold pass | 30/30 |
| Valid JSON rate | 30/30 |
| Fallback rate | 30/30 |
| Hallucinated signal rate | 0/30 |
| Exact/reference match | 0/20 reference-eligible cases |
| Jasper syntax/proof | not run |

The fallback rate is `30/30` because this run did not provide external model
predictions. The runner generated deterministic fallback assertions for all
cases. This must not be interpreted as LLM performance.

## Metrics By Subset

| Subset | Cases | Syntax scaffold | Valid JSON | Fallback | Hallucinated signals | Exact/reference match | Jasper |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| NL2SVA-Human | 10 | 10/10 | 10/10 | 10/10 | 0/10 | 0/10 | not_run |
| NL2SVA-Machine | 10 | 10/10 | 10/10 | 10/10 | 0/10 | 0/10 | not_run |
| Design2SVA | 10 | 10/10 | 10/10 | 10/10 | 0/10 | n/a | not_run |

Design2SVA exact/reference matching is not reported as functional equivalence
because multiple completions can be valid. The local runner does not implement
the official FVEval equivalence procedure.

## No-Leakage Verification

Existing tests verify that:

- `reference_sva` is not included in prompt payloads.
- `expected_sva` is not included in prompt payloads.
- source metadata and notes are omitted from emitted prompt payloads.
- emitted prompt payloads do not contain reference assertion text.

The runner also records `reference_available` as a boolean so downstream prompt
construction can know a reference exists without exposing the answer.

## Claim Boundary

Supported by this PR:

- The 30-case FVEval-compatible subset runner completes.
- The three subset families are reported separately.
- Prompt payload answer leakage checks are present and pass.
- Current local deterministic fallback behavior is recorded.

Not supported by this PR:

- Official FVEval reproduction.
- JasperGold proof or syntax results for generated outputs.
- Commercial property-equivalence results.
- Codex, Qwen, or other LLM quality on the subset.
- Functional correctness from Design2SVA exact/reference matching.

## Follow-Up

To turn this external anchor into a model-quality result, run a bounded
schema-constrained LLM subset with prompt payload export/audit enabled, then
evaluate the generated SVA with JasperGold or an explicitly documented
equivalence flow.
