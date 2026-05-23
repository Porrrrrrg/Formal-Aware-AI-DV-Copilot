# FVEval Subset Import

UTC timestamp: `20260511T031107Z`

## Sources

- FVEval repository: https://github.com/NVlabs/FVEval
- Source commit: `141afe7dcf03a0b86547b94657d9d610b6087724`
- License: Apache-2.0 as declared by the source repository.
- Paper reference: https://arxiv.org/abs/2410.23299

## Imported Cases

| Subset | Count | Source path | Selection |
| --- | ---: | --- | --- |
| NL2SVA-Human | 10 | `data_nl2sva/data/nl2sva_human.csv` | first 10 rows |
| NL2SVA-Machine | 10 | `data_nl2sva/data/nl2sva_machine.csv` | first 10 rows |
| Design2SVA | 5 | `data_design2sva/data/design2sva_pipeline.csv` | first 5 rows |
| Design2SVA | 5 | `data_design2sva/data/design2sva_fsm.csv` | first 5 rows |

Total imported cases: 30.

## Local Mapping

The import writes `benchmarks/fveval_subset/cases.json` with these fields:

- `problem_spec`: source prompt for NL2SVA, source RTL for Design2SVA.
- `property_intent`: local assertion intent field.
- `allowed_signals` and `signals`: identifiers extracted from source testbench/header context.
- `expected_sva` and `reference_sva`: evaluation-only references when present.
- `testbench_header` and `testbench`: source testbench context.
- `source`: repository path, commit, and license metadata.

Reference fields are retained for scoring only. They are omitted by
`evaluation/run_fveval_subset.py --emit-prompts`.

## Runner Status

Command run:

```powershell
python evaluation\run_fveval_subset.py --out evaluation\results\fveval_subset_results.json --emit-prompts evaluation\results\fveval_subset_prompts_sanitized.json
```

Summary:

- Cases: 30.
- Syntax pass: 1.000 using the deterministic fallback.
- Exact/reference match: 0.000 over 20 reference-eligible NL2SVA cases.
- Valid JSON: 1.000.
- Fallback: 1.000.
- Hallucinated signal rate: 0.000.
- Jasper proof: `not_run`.

The temporary JSON result and sanitized prompt audit files were removed after
verification; the committed result artifact is
`evaluation/results/fveval_subset_results.md`.

## Limitations

- This is a local subset import and runner, not an apples-to-apples FVEval
  result.
- The local runner does not reproduce FVEval's commercial Jasper/property
  equivalence flow.
- Design2SVA has multiple valid completions, so exact/reference matching is not
  a functional correctness metric for that subset.
- Jasper proof is reported as `not_run` until a local external-design harness
  integration is explicitly added.
