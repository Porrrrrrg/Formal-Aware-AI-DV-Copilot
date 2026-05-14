# Design2SVA Stage 10 Reference Oracle

Stage 10 separates Design2SVA generation quality from harness and embedding
reachability. The reference-oracle mode evaluates the local
`evaluation_metadata.reference_sva` fixture assertion directly. That assertion
is never added to generation prompts.

Run the three-case Jasper audit with:

```bash
python evaluation/run_design2sva_eval.py \
  --limit 3 \
  --k 1 \
  --reference-oracle \
  --jasper-check \
  --out evaluation/results/design2sva_eval_reference_oracle_jasper.json
```

For local replay without JasperGold:

```bash
python evaluation/run_design2sva_eval.py \
  --limit 3 \
  --k 1 \
  --reference-oracle \
  --jasper-replay evaluation/fixtures/design2sva_reference_oracle_replay.jsonl \
  --out evaluation/results/design2sva_eval_reference_oracle_replay.json
```

## Output Fields

Each result includes `harness_reachability_audit` with:

- `reference_sva`: the local oracle assertion being checked.
- `reference_antecedent_metadata`: extracted antecedent or trigger and the
  generated companion `cover property`.
- `reference_antecedent_reachable`: whether the companion cover was reached.
- `clock_reset_metadata`: clock, reset, polarity, harness path, RTL path, and
  module metadata used by the wrapper.
- `harness_reachability_status`: `reachable`, `unreachable`,
  `bounded_uncovered`, `syntax_error`, `unknown`, or `not_run`.

The summary adds:

- `reference_proven@1`
- `reference_non_vacuous@1`
- `reference_antecedent_reachable@1`
- `harness_reachability_status`
- `harness_reachability_status_counts`

## Interpretation

If the reference oracle has a syntax failure, debug the wrapper, schema
normalization, or assertion embedding before changing candidate generation.

If the reference oracle fails proof or its antecedent is unreachable, the likely
bottleneck is harness reachability, reset/clock handling, assertion embedding,
or an invalid task definition.

If the reference oracle proves non-vacuously and candidate runs still fail, the
bottleneck is candidate generation or repair selection rather than the harness.

Dry-run rows only verify file generation and JSON plumbing. Use real JasperGold
or a replay fixture before interpreting proof and reachability metrics.

## Stage 10 Subset Result

The initial Moore/JasperGold reference-oracle subset checked three local
Design2SVA fixture references with `k=1`.

- `reference_proven@1 = 0.000`
- `reference_non_vacuous@1 = 0.000`
- `reference_antecedent_reachable@1 = 0.000`
- `harness_reachability_status = unreachable`
- Failure split: `unreachable_antecedent=2`, `unreachable_cover_goal=1`

This means the immediate bottleneck is not only Codex candidate generation.
The current local reference assertions also fail the reachability audit under
the JasperGold wrapper, so the next debugging target is harness setup,
assertion embedding, reset/clock handling, or invalid Design2SVA task
definitions.
